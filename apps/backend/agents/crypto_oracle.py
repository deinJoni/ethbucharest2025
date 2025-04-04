import logging
from typing import TypedDict, Annotated, Dict, Any, Optional
import operator
from datetime import datetime
import requests

from langchain_openai import ChatOpenAI
from langchain.tools import StructuredTool
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolExecutor
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.agents import AgentAction
from langchain.prompts import PromptTemplate
from core.config import settings

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# --- Configuration (Updated based on PRD) ---
TRADER_GRADE_BUY_THRESHOLD = 50
TRADER_GRADE_CHANGE_BUY_THRESHOLD = 0.05 # 5% represented as 0.05
TRADER_GRADE_SELL_THRESHOLD = 30
TRADER_GRADE_CHANGE_SELL_THRESHOLD = -0.10 # -10% represented as -0.10
AVERAGE_TG_DAYS = 5 # Number of days to average TG over

# --- Crypto Oracle Tool (Returns Dict) ---
def crypto_oracle_analysis(token_id: str, token_symbol: str) -> Dict[str, Any]:
    """
    Analyzes a crypto token based on Token Metrics Trader Grade (TG), 24h % change (TGC),
    and 5-day average TG. Requires token ID and symbol.
    Returns a dictionary containing calculated metrics, the signal, and reasoning components, or an error.
    """
    symbol_cleaned = token_symbol.strip().upper()
    logger.info(f"Starting crypto oracle analysis for symbol: '{symbol_cleaned}' (ID: {token_id})")
    # Initialize result dictionary
    analysis_result: Dict[str, Any] = {
        "token_id": token_id,
        "token_symbol": symbol_cleaned,
        "latest_tg": None,
        "tgc_24h": None,
        "avg_tg_5d": None,
        "signal": "HOLD", # Default signal
        "reasoning_components": {},
        "reason_string": "Analysis did not complete.", # Add field for pre-LLM reason
        "error": None
    }

    api_key = settings.TOKEN_METRICS_API_KEY
    if not api_key or api_key == "YOUR_TOKEN_METRICS_API_KEY":
        logger.error("Token Metrics API key not configured.")
        analysis_result["error"] = "API key missing"
        analysis_result["reasoning_components"]["error"] = "Internal configuration error: API key missing."
        return analysis_result

    headers = {"accept": "application/json", "api_key": api_key}

    if not token_id:
        logger.error(f"Missing token_id for analysis of symbol '{symbol_cleaned}'")
        analysis_result["error"] = "Missing token_id input"
        analysis_result["reasoning_components"]["error"] = "Input error: Token ID was not provided."
        return analysis_result

    # --- Fetch Trader Grade (TG) and 24h Change (TGC) ---
    trader_grade = None
    trader_grade_change = None
    avg_trader_grade = None

    try:
        grade_url = f"https://api.tokenmetrics.com/v2/trader-grades/?token_id={token_id}&limit={AVERAGE_TG_DAYS}"
        logger.info(f"Fetching Trader Grades from: {grade_url}")

        response = requests.get(grade_url, headers=headers, timeout=15) # Increased timeout slightly
        response.raise_for_status()
        trader_grade_response = response.json()

        if trader_grade_response.get("success") and trader_grade_response.get("data"):
            raw_data = trader_grade_response["data"]
            if raw_data:
                try:
                    sorted_data = sorted(raw_data, key=lambda x: datetime.fromisoformat(x['DATE'].replace('Z', '+00:00')), reverse=True)
                except (KeyError, ValueError, TypeError) as sort_e:
                    logger.error(f"Error sorting TG data by DATE for {symbol_cleaned} (ID: {token_id}): {sort_e}.")
                    analysis_result["error"] = "Cannot sort API data"
                    analysis_result["reasoning_components"]["error"] = "Data processing error: Could not sort trader grade history by date."
                    return analysis_result

                if not sorted_data:
                    logger.error(f"TG data became empty after sorting for {symbol_cleaned} (ID: {token_id})")
                    analysis_result["error"] = "No valid data after sorting"
                    analysis_result["reasoning_components"]["error"] = "Data processing error: No valid trader grade history found after sorting."
                    return analysis_result

                # Calculate Average TG first (needs multiple points)
                if len(sorted_data) >= AVERAGE_TG_DAYS:
                    try:
                        recent_grades = [float(d["TM_TRADER_GRADE"]) for d in sorted_data[:AVERAGE_TG_DAYS] if d.get("TM_TRADER_GRADE") is not None]
                        if len(recent_grades) == AVERAGE_TG_DAYS:
                            avg_trader_grade = sum(recent_grades) / AVERAGE_TG_DAYS
                            analysis_result["avg_tg_5d"] = avg_trader_grade # Store in result
                            logger.info(f"Calculated {AVERAGE_TG_DAYS}-day Avg TG for {symbol_cleaned}: {avg_trader_grade:.2f}")
                        else:
                             logger.warning(f"Could not extract {AVERAGE_TG_DAYS} valid TGs for averaging for {symbol_cleaned}. Count: {len(recent_grades)}")
                    except (ValueError, TypeError, KeyError) as avg_e:
                        logger.error(f"Error calculating average TG for {symbol_cleaned}: {avg_e}")

                # Extract Latest TG and TGC from the newest record
                latest_data = sorted_data[0]
                tg_value = latest_data.get("TM_TRADER_GRADE")
                tgc_value = latest_data.get("TM_TRADER_GRADE_24H_PCT_CHANGE")

                if tg_value is not None:
                    try:
                        trader_grade = float(tg_value)
                        analysis_result["latest_tg"] = trader_grade # Store in result
                        logger.info(f"Extracted latest TG for {symbol_cleaned}: {trader_grade}")
                    except (ValueError, TypeError) as conv_e:
                         logger.error(f"Error converting TG '{tg_value}' to float for {symbol_cleaned}: {conv_e}")
                else:
                    logger.error(f"TM_TRADER_GRADE key missing in latest data for {symbol_cleaned}")

                if tgc_value is not None:
                    try:
                        trader_grade_change = float(tgc_value)
                        analysis_result["tgc_24h"] = trader_grade_change # Store in result
                        logger.info(f"Extracted latest TGC for {symbol_cleaned}: {trader_grade_change:.4f}")
                    except (ValueError, TypeError) as conv_e:
                        logger.error(f"Error converting TGC '{tgc_value}' to float for {symbol_cleaned}: {conv_e}")
                else:
                    logger.error(f"TM_TRADER_GRADE_24H_PCT_CHANGE key missing in latest data for {symbol_cleaned}")

            else: # raw_data is empty list
                logger.error(f"Trader Grade data list empty for {symbol_cleaned} (ID: {token_id})")
                analysis_result["error"] = "No data found"
                analysis_result["reasoning_components"]["error"] = "No trader grade data found for this token."
                return analysis_result
        else: # API call success=False or data key missing
             api_msg = trader_grade_response.get('message', 'Unknown API error')
             logger.error(f"Failed to fetch TG data for {symbol_cleaned} (ID: {token_id}). Message: {api_msg}")
             analysis_result["error"] = f"API Error: {api_msg}"
             analysis_result["reasoning_components"]["error"] = f"API Error: Could not fetch trader grade data ({api_msg})."
             return analysis_result

    except requests.exceptions.RequestException as req_e:
         logger.exception(f"API Request error fetching TG for {symbol_cleaned} (ID: {token_id}): {req_e}")
         analysis_result["error"] = "API request failed"
         analysis_result["reasoning_components"]["error"] = f"Network error: Failed to connect to the trader grade API ({type(req_e).__name__})."
         return analysis_result
    except Exception as e: # Catch broader processing errors
        logger.exception(f"Unexpected error processing TG data for {symbol_cleaned} (ID: {token_id}): {e}")
        analysis_result["error"] = "Data processing failed"
        analysis_result["reasoning_components"]["error"] = f"Internal error: Failed processing trader grade data ({type(e).__name__})."
        return analysis_result

    # --- Decision Logic ---
    # Check if primary data was successfully extracted
    if trader_grade is None or trader_grade_change is None:
        logger.warning(f"Cannot make decision for {symbol_cleaned}: Missing latest TG or TGC after processing.")
        analysis_result["error"] = "Missing primary data"
        missing = []
        if trader_grade is None: missing.append("Latest TG")
        if trader_grade_change is None: missing.append("TGC")
        reason_str = f"Data processing error: Could not determine required values ({', '.join(missing)})."
        analysis_result["reasoning_components"]["error"] = reason_str
        analysis_result["reason_string"] = reason_str # Store error reason
        # Signal remains default HOLD
        return analysis_result

    # Apply the logic - Determine signal, reasoning components, and reason string
    signal = "HOLD" # Start with HOLD
    reason_str = "" # Initialize reason string
    reasoning_comps = {
        "latest_tg": trader_grade,
        "tgc_24h": trader_grade_change,
        "avg_tg_5d": avg_trader_grade, # Could be None
        "tg_buy_threshold": TRADER_GRADE_BUY_THRESHOLD,
        "tgc_buy_threshold": TRADER_GRADE_CHANGE_BUY_THRESHOLD,
        "tg_sell_threshold": TRADER_GRADE_SELL_THRESHOLD,
        "tgc_sell_threshold": TRADER_GRADE_CHANGE_SELL_THRESHOLD,
    }

    # BUY Check
    buy_condition_met = False
    avg_tg_check_passed = None # Track avg tg check specifically
    if trader_grade > TRADER_GRADE_BUY_THRESHOLD and trader_grade_change > TRADER_GRADE_CHANGE_BUY_THRESHOLD:
        reasoning_comps["buy_check_1"] = True
        if avg_trader_grade is not None:
            if trader_grade > avg_trader_grade:
                buy_condition_met = True
                avg_tg_check_passed = True
                reasoning_comps["buy_check_2"] = True
                reason_str = f"Latest TG ({trader_grade:.1f}) > {TRADER_GRADE_BUY_THRESHOLD}, Latest TG > Avg TG ({avg_trader_grade:.1f}), AND TGC ({trader_grade_change:.2%}) > {TRADER_GRADE_CHANGE_BUY_THRESHOLD:.0%}."
            else:
                avg_tg_check_passed = False
                reasoning_comps["buy_check_2"] = False
                # Reason for potential HOLD will be set later
        else:
            buy_condition_met = True # Allow BUY without avg check
            avg_tg_check_passed = "skipped_avg_unavailable"
            reasoning_comps["buy_check_2"] = "skipped_avg_unavailable"
            reason_str = f"Latest TG ({trader_grade:.1f}) > {TRADER_GRADE_BUY_THRESHOLD} AND TGC ({trader_grade_change:.2%}) > {TRADER_GRADE_CHANGE_BUY_THRESHOLD:.0%} (Avg TG unavailable)."
    else:
        reasoning_comps["buy_check_1"] = False

    if buy_condition_met:
        signal = "BUY"
    else:
        # SELL Check
        sell_condition_met = False
        sell_reasons = []
        sell_reason_parts = []
        if trader_grade < TRADER_GRADE_SELL_THRESHOLD:
            sell_condition_met = True
            sell_reasons.append("tg_low")
            sell_reason_parts.append(f"Latest TG ({trader_grade:.1f}) < {TRADER_GRADE_SELL_THRESHOLD}")
        if trader_grade_change < TRADER_GRADE_CHANGE_SELL_THRESHOLD:
            sell_condition_met = True
            sell_reasons.append("tgc_low")
            sell_reason_parts.append(f"TGC ({trader_grade_change:.2%}) < {TRADER_GRADE_CHANGE_SELL_THRESHOLD:.0%}")

        if sell_condition_met:
            signal = "SELL"
            reasoning_comps["sell_triggers"] = sell_reasons
            reason_str = " OR ".join(sell_reason_parts)
        else:
            # HOLD Reason
            signal = "HOLD"
            if reasoning_comps.get("buy_check_1") == True and avg_tg_check_passed == False:
                # Specifically failed the Avg TG check for BUY
                reason_str = f"BUY conditions nearly met, but Latest TG ({trader_grade:.1f}) was not > Avg TG ({avg_trader_grade:.1f}). SELL conditions not met."
            else:
                # General HOLD - failed initial BUY check and SELL checks
                 reason_str = f"Conditions for BUY or SELL were not met based on current TG ({trader_grade:.1f}), TGC ({trader_grade_change:.2%}), and Avg TG ({avg_trader_grade:.1f if avg_trader_grade is not None else 'N/A'})."

    analysis_result["signal"] = signal
    analysis_result["reasoning_components"] = reasoning_comps
    analysis_result["reason_string"] = reason_str # Store final calculated reason string
    logger.info(f"Crypto Oracle analysis complete for {symbol_cleaned} (ID: {token_id}): Signal={signal}")
    return analysis_result


# --- Tool & Executor ---
crypto_oracle_tool = StructuredTool.from_function(
    func=crypto_oracle_analysis,
    name="crypto_oracle_analyzer",
    description="Analyzes a token using its ID and symbol based on Token Metrics Trader Grade (TG), 24h change (TGC), and 5d Avg TG. Returns a dictionary with metrics, signal (BUY/SELL/HOLD), and reasoning components or an error.",
)
tool_executor = ToolExecutor([crypto_oracle_tool])

# --- LLM and Prompt ---
llm = ChatOpenAI(
    temperature=0.1,
    api_key=settings.OPENAI_API_KEY,
    model="gpt-4-0125-preview"
)

reasoning_prompt = PromptTemplate.from_template(
    """You are a crypto analysis assistant explaining the result of the Crypto Oracle strategy for {token_symbol}.

    The analysis relies on these key metrics:
    *   Latest Trader Grade (TG): {latest_tg_str} (A score from 0-100 indicating recent trading conditions, higher is generally more favorable)
    *   24h TG Change (TGC): {tgc_24h_str} (The percentage change in the Trader Grade over the last 24 hours, indicating momentum)
    *   5-Day Average TG: {avg_tg_5d_str} (The average Trader Grade over the last 5 days, indicating the recent trend)

    Strategy Rules Used:
    *   BUY: If Latest TG > {tg_buy_threshold} AND Latest TG > 5d Avg TG (if available) AND TGC > {tgc_buy_threshold:.0%}.
    *   SELL: If Latest TG < {tg_sell_threshold} OR TGC < {tgc_sell_threshold:.0%}.
    *   HOLD: Otherwise.

    **Analysis Summary:**

    Based on the Crypto Oracle strategy analysis for {token_symbol}, the resulting signal is **{signal}**.

    The primary reason derived from the calculation is: "{reason_string}"

    **Explanation:**

    Start your explanation with "The signal determined for {token_symbol} is {signal}." - This exact format is critical.
    
    Then elaborate on this result. Clearly explain *why* the signal is {signal} based on the specific reason calculated and the metric values provided ({latest_tg_str}, {tgc_24h_str}, {avg_tg_5d_str}). Maintain a professional and objective tone suitable for a financial analysis website. Stick to the facts from this analysis.
    
    Before concluding, restate the final signal recommendation in this exact format:
    "FINAL RECOMMENDATION: {signal}"
    """
)

# --- LangGraph State (Updated) ---
class AgentState(TypedDict):
    input: Dict[str, str] # Expects {"token_id": "...", "token_name": "..."}
    action: AgentAction | None
    analysis_data: Optional[Dict[str, Any]] # Result from crypto_oracle_analysis tool
    reason_string: Optional[str] # Added: Pre-LLM reason string from tool
    llm_reasoning: Optional[str] # Final explanation from LLM
    # Keep intermediate steps for tracing
    intermediate_steps: Annotated[list[tuple[AgentAction, Dict[str, Any]]], operator.add]


# --- Nodes (Added generate_llm_reasoning_node) ---
def prepare_tool_call_node(state: AgentState):
    logger.info("--- Crypto Oracle: Preparing Tool Call Node ---")
    input_data = state['input']
    token_id = input_data.get('token_id')
    token_name = input_data.get('token_name', 'UnknownSymbol')
    logger.info(f"Input token_id: {token_id}, token_name/symbol: {token_name}")

    if not token_id:
        logger.error("Missing 'token_id' in input for prepare_tool_call_node")
        # Return error state that skips tool execution
        return {
            "analysis_data": { # Store error info here now
                 "token_id": token_id, "token_symbol": token_name, "error": "Missing 'token_id' in input.",
                 "reasoning_components": {"error": "Input error: Token ID was not provided."}
            }
        }

    tool_input = {"token_id": token_id, "token_symbol": token_name}
    action = AgentAction(
        tool="crypto_oracle_analyzer",
        tool_input=tool_input,
        log=f"Preparing Crypto Oracle analysis for {token_name} (ID: {token_id})"
    )
    logger.info(f"Prepared action: {action}")
    return {"action": action, "intermediate_steps": []}


def execute_tool_node(state: AgentState):
    logger.info("--- Crypto Oracle: Executing Tool Node ---")
    action = state.get("action")
    analysis_result_data = None

    # Check if prepare_node already put an error in analysis_data
    if state.get("analysis_data") and state["analysis_data"].get("error"):
         logger.warning(f"Skipping tool execution due to error in prepare step: {state['analysis_data']['error']}")
         # Keep existing analysis_data with error, potentially update intermediate_steps? No action to log.
         return {} # No changes needed

    if not isinstance(action, AgentAction):
         logger.error(f"execute_tool_node received non-action: {action}")
         error_message = f"Internal error: Tool execution step received invalid action state."
         analysis_result_data = {
             "error": error_message,
             "reasoning_components": {"error": error_message}
             # Add token_id/symbol if available from input state?
         }
         # Log a dummy action/error pair
         dummy_action = AgentAction(tool="error_state", tool_input={}, log=error_message)
         return {"analysis_data": analysis_result_data, "intermediate_steps": [(dummy_action, analysis_result_data)]}
    else:
        logger.info(f"Executing tool: {action.tool} with input {action.tool_input}")
        try:
            # Tool now returns a dictionary
            output_dict = tool_executor.invoke(action)
            logger.info(f"Tool output dictionary: {output_dict}")
            analysis_result_data = output_dict

            if isinstance(output_dict, dict) and output_dict.get("error"):
                 logger.warning(f"Crypto Oracle tool reported an error: {output_dict['error']}")

        except Exception as e:
            logger.exception(f"Error executing tool {action.tool}: {e}")
            error_message = f"Tool execution failed: {type(e).__name__}"
            analysis_result_data = {
                 "error": error_message,
                 "reasoning_components": {"error": f"Internal error during tool execution: {str(e)}"},
                 "token_id": action.tool_input.get("token_id"), # Try to preserve context
                 "token_symbol": action.tool_input.get("token_symbol")
            }

    # Log the actual action and the dictionary result
    intermediate_steps = state.get("intermediate_steps", [])
    intermediate_steps.append((action, analysis_result_data))

    # Extract reason_string and store in state
    reason_string = analysis_result_data.get("reason_string") if isinstance(analysis_result_data, dict) else None

    return {
        "analysis_data": analysis_result_data,
        "reason_string": reason_string, # Populate reason_string in state
        "intermediate_steps": intermediate_steps
    }


def generate_llm_reasoning_node(state: AgentState):
    logger.info("--- Crypto Oracle: Generating LLM Reasoning Node ---")
    analysis_data = state.get("analysis_data")
    reason_string = state.get("reason_string") # Get pre-calculated reason
    final_explanation = "Error: Analysis data not found in state." # Default error

    if not analysis_data:
        logger.error("No analysis data found in state for LLM reasoning.")
        return {"llm_reasoning": final_explanation}

    # If tool execution resulted in an error stored in analysis_data
    if analysis_data.get("error"):
        error_msg = analysis_data["error"]
        # Use the reason_string which should contain the error details now
        reasoning_error = reason_string or analysis_data.get("reasoning_components", {}).get("error", "Unknown calculation error")
        logger.warning(f"Skipping LLM reasoning due to previous error: {error_msg}")
        final_explanation = f"Analysis Error for {analysis_data.get('token_symbol', 'token')}: {reasoning_error}"
        return {"llm_reasoning": final_explanation}

    # --- Prepare data for prompt (using pre-calculated reason) ---
    signal = analysis_data.get("signal", "UNKNOWN")
    reasoning_comps = analysis_data.get("reasoning_components", {})
    latest_tg = reasoning_comps.get("latest_tg")
    tgc_24h = reasoning_comps.get("tgc_24h")
    avg_tg_5d = reasoning_comps.get("avg_tg_5d")

    # Check required values exist (especially for formatting)
    if latest_tg is None or tgc_24h is None or reason_string is None:
         logger.error(f"LLM Node: Missing required data (TG, TGC, or Reason String) in state: {state}")
         final_explanation = f"Analysis Error: Could not generate explanation due to missing core metrics or reason."
         return {"llm_reasoning": final_explanation}

    # Format values for prompt
    latest_tg_str = f"{latest_tg:.1f}" if latest_tg is not None else "N/A"
    tgc_24h_str = f"{tgc_24h:.2%}" if tgc_24h is not None else "N/A"
    avg_tg_5d_str = f"{avg_tg_5d:.1f}" if avg_tg_5d is not None else "N/A (unavailable)"

    # Prepare final input for the prompt
    prompt_input = {
        "token_symbol": analysis_data.get("token_symbol", "this token"),
        "latest_tg_str": latest_tg_str,
        "tgc_24h_str": tgc_24h_str,
        "avg_tg_5d_str": avg_tg_5d_str,
        "signal": signal,
        "reason_string": reason_string, # Pass pre-calculated reason
        "tg_buy_threshold": TRADER_GRADE_BUY_THRESHOLD,
        "tgc_buy_threshold": TRADER_GRADE_CHANGE_BUY_THRESHOLD,
        "tg_sell_threshold": TRADER_GRADE_SELL_THRESHOLD,
        "tgc_sell_threshold": TRADER_GRADE_CHANGE_SELL_THRESHOLD,
    }

    try:
        reasoning_chain = reasoning_prompt | llm
        logger.info(f"Invoking LLM with data: {prompt_input}")
        llm_response = reasoning_chain.invoke(prompt_input)

        if hasattr(llm_response, 'content'):
             final_explanation = llm_response.content
        else:
             final_explanation = str(llm_response)

        logger.info(f"LLM generated reasoning: {final_explanation}")
        return {"llm_reasoning": final_explanation.strip()}

    except Exception as e:
        logger.exception("Error invoking LLM for reasoning")
        final_explanation = f"Error generating explanation: {str(e)}"
        return {"llm_reasoning": final_explanation}


# --- Build Graph (Updated) ---
workflow = StateGraph(AgentState)
workflow.add_node("prepare_tool_call_node", prepare_tool_call_node)
workflow.add_node("execute_tool_node", execute_tool_node)
workflow.add_node("generate_llm_reasoning_node", generate_llm_reasoning_node) # Added
workflow.set_entry_point("prepare_tool_call_node")
workflow.add_edge("prepare_tool_call_node", "execute_tool_node")
# workflow.add_edge("execute_tool_node", END) # Removed old edge
workflow.add_edge("execute_tool_node", "generate_llm_reasoning_node") # Added edge
workflow.add_edge("generate_llm_reasoning_node", END) # Added edge

# --- Memory & Compile ---
memory = MemorySaver()
app = workflow.compile(checkpointer=memory)

# --- Manual Test (Updated Check) ---
if __name__ == "__main__":
    from uuid import uuid4
    print("--- Testing Crypto Oracle Agent (with LLM Reasoning) ---")
    config = {"configurable": {"thread_id": str(uuid4())}}
    test_token_id = "3306" # e.g., Ethereum
    test_token_name = "ETH"
    test_input = {"token_id": test_token_id, "token_name": test_token_name}

    print(f"Invoking agent with input: {test_input} and config: {config}")

    try:
        result_state = app.invoke({"input": test_input}, config=config)
        print("--- Agent Execution Result State ---")
        # print(result_state) # Print full state if needed for debug
        print(f"Input: {result_state.get('input')}")
        print(f"Analysis Data: {result_state.get('analysis_data')}")
        print(f"LLM Reasoning: {result_state.get('llm_reasoning')}")

        # Check the final explanation
        final_output = result_state.get("llm_reasoning", "No LLM reasoning found in state.")
        print("--- Final LLM Explanation ---")
        print(final_output)
    except Exception as e:
        print(f"--- Error during agent execution ---")
        logger.exception("Agent invocation failed in main block")
        print(f"Error: {e}")

    print("--- Test Complete ---") 