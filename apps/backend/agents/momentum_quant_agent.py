import logging
from typing import TypedDict, Annotated, Dict, Any, Optional
import operator
from datetime import datetime, timedelta
from uuid import uuid4
import requests

# Added imports for LLM
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate

from langchain_core.agents import AgentAction
from langchain.tools import StructuredTool
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolExecutor
from langgraph.checkpoint.memory import MemorySaver
from core.config import settings

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# --- Configuration ---
MOMENTUM_THRESHOLD = 0.005 # 0.5% change threshold
QUANT_GRADE_THRESHOLD = 55 # Minimum quant grade for BUY signal

# --- Momentum Quant Tool (Returns Dict) ---
def momentum_quant_analysis(token_id: str, token_name: str = None) -> Dict[str, Any]:
    """
    Analyzes momentum (Trader Grade % change) and quantitative factors (Quant Grade)
    for a crypto token based on Token Metrics data. Requires the token ID.
    Optional token_name parameter for consistency with other agents.
    Returns a dictionary containing calculated metrics, the signal (BUY/SELL/HOLD),
    reason string, and error field.
    """
    # Clean the symbol if provided, use as token_name in result
    token_name_clean = token_name.strip() if token_name else f"Token ID {token_id}"
    logger.info(f"Starting momentum/quant analysis for {token_name_clean} (ID: {token_id})")
    
    # Initialize result dictionary with token_name included
    analysis_result: Dict[str, Any] = {
        "token_id": token_id,
        "token_name": token_name_clean, # Add token_name directly
        "latest_tg": None,
        "previous_tg": None,
        "pct_change_tg": None,
        "quant_grade": None,
        "signal": "HOLD", # Default signal
        "reason_string": "Analysis did not complete.", # Default reason
        "reasoning_components": {}, # Add reasoning_components to match bounce_hunter
        "error": None
    }

    # --- Fetch API Key ---
    api_key = settings.TOKEN_METRICS_API_KEY
    if not api_key or api_key == "YOUR_TOKEN_METRICS_API_KEY":
         logger.error("Token Metrics API key not configured.")
         analysis_result["error"] = "API key missing"
         analysis_result["reason_string"] = "Internal configuration error: API key missing."
         analysis_result["reasoning_components"]["error"] = "Internal configuration error: API key missing."
         return analysis_result

    if not token_id:
        logger.error("Missing token_id for momentum/quant analysis")
        analysis_result["error"] = "Missing token_id input"
        analysis_result["reason_string"] = "Input error: Token ID was not provided."
        analysis_result["reasoning_components"]["error"] = "Input error: Token ID was not provided."
        return analysis_result

    headers = {
        "accept": "application/json",
        "api_key": api_key
    }

    # --- Fetch Trader Grades Data (Last 5 days) ---
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=5) # Fetch last 5 days to ensure we have 2 comparable points
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')

    trader_grades_url = f"https://api.tokenmetrics.com/v2/trader-grades?token_id={token_id}&startDate={start_date_str}&endDate={end_date_str}"
    logger.info(f"Fetching trader grades from {trader_grades_url}")

    latest_grade = None
    previous_grade = None
    pct_change = None
    quant_grade = None

    try:
        grades_response = requests.get(trader_grades_url, headers=headers, timeout=15)
        grades_response.raise_for_status()
        grades_data = grades_response.json()

        if grades_data.get("success") and isinstance(grades_data.get("data"), list):
            sorted_grades = sorted(grades_data["data"], key=lambda x: datetime.fromisoformat(x['DATE'].replace('Z', '+00:00')) if x.get('DATE') else datetime.min, reverse=True)

            if len(sorted_grades) >= 2:
                latest_entry = sorted_grades[0]
                previous_entry = sorted_grades[1]

                latest_grade_raw = latest_entry.get("TM_TRADER_GRADE")
                previous_grade_raw = previous_entry.get("TM_TRADER_GRADE")
                latest_quant_grade_raw = latest_entry.get("QUANT_GRADE")

                # Process Quant Grade
                if latest_quant_grade_raw is not None:
                    try:
                        quant_grade = float(latest_quant_grade_raw)
                        analysis_result["quant_grade"] = quant_grade
                        logger.info(f"Latest Quant Grade (from Trader Grades): {quant_grade:.2f} (on {latest_entry.get('DATE')})")
                    except (ValueError, TypeError):
                        logger.warning(f"Could not parse QUANT_GRADE '{latest_quant_grade_raw}' from trader grades.")
                else:
                    logger.warning(f"QUANT_GRADE field missing in latest trader grade entry for token {token_id}.")

                # Process Trader Grades & Momentum
                if latest_grade_raw is not None and previous_grade_raw is not None:
                    try:
                        latest_grade = float(latest_grade_raw)
                        previous_grade = float(previous_grade_raw)
                        analysis_result["latest_tg"] = latest_grade
                        analysis_result["previous_tg"] = previous_grade
                        if previous_grade != 0:
                            pct_change = (latest_grade - previous_grade) / previous_grade
                            analysis_result["pct_change_tg"] = pct_change
                            logger.info(f"Trader Grades: Latest={latest_grade:.2f}, Previous={previous_grade:.2f}, Change={pct_change:.4f}")
                        else:
                            logger.warning("Previous trader grade is 0, cannot calculate percent change.")
                    except (ValueError, TypeError):
                        logger.warning("Could not parse latest/previous trader grade to float.")
                else:
                    logger.warning("Latest or previous trader grade missing, cannot calculate momentum.")

            elif len(sorted_grades) == 1:
                 logger.warning(f"Only 1 day of trader grade data found for token {token_id}. Cannot calculate momentum.")
                 latest_entry = sorted_grades[0]
                 latest_grade_raw = latest_entry.get("TM_TRADER_GRADE")
                 latest_quant_grade_raw = latest_entry.get("QUANT_GRADE")
                 # Try to get grades even with one entry
                 if latest_grade_raw is not None:
                      try: analysis_result["latest_tg"] = float(latest_grade_raw)
                      except: pass
                 if latest_quant_grade_raw is not None:
                     try:
                         quant_grade = float(latest_quant_grade_raw)
                         analysis_result["quant_grade"] = quant_grade
                         logger.info(f"Latest Quant Grade (from single Trader Grade entry): {quant_grade:.2f}")
                     except (ValueError, TypeError): pass
            else:
                logger.warning(f"No trader grade data found for token {token_id} in the last 5 days.")
        else:
            api_msg = grades_data.get('message', 'Unknown API error')
            logger.error(f"Failed to fetch or parse trader grades data for token {token_id}. Message: {api_msg}")
            analysis_result["error"] = f"API Error: {api_msg}"
            analysis_result["reason_string"] = f"API Error: Could not fetch trader grade data ({api_msg})."
            return analysis_result

    except requests.exceptions.RequestException as req_e:
         logger.exception(f"API Request error fetching trader grades for {token_id}: {req_e}")
         analysis_result["error"] = "API request failed"
         analysis_result["reason_string"] = f"Network error: Failed to connect to the trader grade API ({type(req_e).__name__})."
         return analysis_result
    except Exception as e:
        logger.exception(f"Unexpected error processing trader grade data for {token_id}: {e}")
        analysis_result["error"] = "Data processing failed"
        analysis_result["reason_string"] = f"Internal error: Failed processing trader grade data ({type(e).__name__})."
        return analysis_result

    # --- Decision Logic ---
    signal = "HOLD" # Default
    reason_str = ""

    # Check if necessary data is available
    if pct_change is None or quant_grade is None:
         logger.warning(f"Cannot make decision due to missing data: pct_change={pct_change}, quant_grade={quant_grade}")
         reason_str = "Insufficient data: Could not determine momentum change or quant grade."
         if analysis_result["latest_tg"] is None: reason_str += " Missing latest Trader Grade."
         if analysis_result["previous_tg"] is None: reason_str += " Missing previous Trader Grade."
         if analysis_result["quant_grade"] is None: reason_str += " Missing Quant Grade."
         analysis_result["signal"] = "HOLD"
         analysis_result["reason_string"] = reason_str
         analysis_result["reasoning_components"]["error"] = reason_str # Add to reasoning_components
         analysis_result["error"] = "Insufficient data" # Flag error for LLM skip if needed
         return analysis_result

    # Populate reasoning_components
    reasoning_comps = {
        "latest_tg": analysis_result["latest_tg"],
        "previous_tg": analysis_result["previous_tg"],
        "pct_change_tg": pct_change,
        "quant_grade": quant_grade,
        "momentum_threshold": MOMENTUM_THRESHOLD,
        "quant_grade_threshold": QUANT_GRADE_THRESHOLD
    }
    
    # BUY Signal: Positive momentum AND strong quant grade
    if pct_change > MOMENTUM_THRESHOLD and quant_grade > QUANT_GRADE_THRESHOLD:
        signal = "BUY"
        reason_str = f"BUY signal triggered: Momentum ({pct_change:.2%}) > {MOMENTUM_THRESHOLD:.1%} threshold AND Quant Grade ({quant_grade:.1f}) > {QUANT_GRADE_THRESHOLD} threshold."
        reasoning_comps["buy_check"] = True
        logger.info(reason_str)

    # SELL Signal: Negative momentum (significant drop)
    elif pct_change < -MOMENTUM_THRESHOLD:
        signal = "SELL"
        reason_str = f"SELL signal triggered: Momentum ({pct_change:.2%}) < {-MOMENTUM_THRESHOLD:.1%} threshold."
        reasoning_comps["sell_check"] = True
        logger.info(reason_str)

    # HOLD Signal: Default if neither BUY nor SELL conditions are met
    else:
        signal = "HOLD"
        reason_str = f"HOLD signal: Conditions not met. Momentum ({pct_change:.2%}) did not meet BUY/SELL thresholds OR Quant Grade ({quant_grade:.1f}) was not above BUY threshold ({QUANT_GRADE_THRESHOLD})."
        reasoning_comps["hold_reason"] = "thresholds_not_met"
        logger.info(reason_str)

    analysis_result["signal"] = signal
    analysis_result["reason_string"] = reason_str
    analysis_result["reasoning_components"] = reasoning_comps
    logger.info(f"Momentum Quant analysis complete for {token_name_clean}: Signal={signal}")
    return analysis_result

# --- Tool & Executor ---
momentum_quant_tool = StructuredTool.from_function(
    func=momentum_quant_analysis,
    name="momentum_quant_analyzer", # Renamed for consistency
    description=(
        "Analyzes momentum (Trader Grade % change) and quantitative factors (Quant Grade) for a token using its Token Metrics ID. "
        "Requires 'token_id'. Optional 'token_name' for display. Returns a dictionary with metrics, signal (BUY/SELL/HOLD), reasoning, and error status."
    ),
)

tool_executor = ToolExecutor([momentum_quant_tool])

# --- LLM and Prompt ---
llm = ChatOpenAI(
    temperature=0.1,
    api_key=settings.OPENAI_API_KEY,
    model="gpt-4-0125-preview"
)

momentum_reasoning_prompt = PromptTemplate.from_template(
    """You are a crypto analysis assistant explaining the result of the Momentum Quant strategy for {token_name} (ID: {token_id}).

    The analysis uses these key metrics:
    *   Momentum (Trader Grade % Change): {pct_change_tg_str}
    *   Latest Quant Grade: {quant_grade_str}

    Strategy Rules Used:
    *   BUY: If Momentum > {momentum_threshold:.1%} AND Quant Grade > {quant_grade_threshold}.
    *   SELL: If Momentum < -{momentum_threshold:.1%}.
    *   HOLD: Otherwise.

    **Analysis Summary:**

    Based on the Momentum Quant strategy analysis for {token_name} (ID: {token_id}), the resulting signal is **{signal}**.

    The primary reason derived from the calculation is: "{reason_string}"

    **Explanation:**

    Start your explanation with "The signal determined for {token_name} is {signal}." - This exact format is critical.
    
    Then rephrase the calculated reason into a concise, user-friendly explanation for why the signal is {signal}. Stick strictly to the provided reason and metrics. Mention the thresholds involved ({momentum_threshold:.1%}, {quant_grade_threshold}). Maintain a professional and objective tone.
    
    Before concluding, restate the final signal recommendation in this exact format:
    "FINAL RECOMMENDATION: {signal}"
    """
)

# --- LangGraph State (Updated) ---
class MomentumQuantAgentState(TypedDict):
    # Update input type hint to include optional token_name
    input: Dict[str, Optional[str]] # Expects {"token_id": "...", "token_name": "..."}
    action: Optional[AgentAction]
    analysis_data: Optional[Dict[str, Any]] # Result from momentum_quant_analysis tool
    reason_string: Optional[str] # Pre-LLM reason string from tool
    llm_reasoning: Optional[str] # Final explanation from LLM
    # Update intermediate_steps annotation to match other agents
    intermediate_steps: Annotated[list[tuple[AgentAction, Dict[str, Any]]], operator.add]

# --- Nodes (Added generate_llm_reasoning_node) ---
def prepare_tool_call_node(state: MomentumQuantAgentState):
    logger.info("--- Momentum Quant: Preparing Tool Call Node ---")
    input_data = state['input']
    token_id = input_data.get('token_id')
    # Log token_name if available, use fallback if not
    token_name = input_data.get('token_name') or f"Token ID {token_id}"
    logger.info(f"Input token_id: {token_id}, token_name: {token_name}")

    if not token_id:
        logger.error("Missing 'token_id' in input for prepare_tool_call_node")
        # Return error state that skips tool execution
        return {
            "analysis_data": { # Store error info here now
                 "token_id": token_id,
                 "token_name": token_name, # Include name in error data
                 "error": "Missing 'token_id' in input.",
                 "reason_string": "Input error: Token ID was not provided."
            }
        }

    # Prepare tool input dictionary matching momentum_quant_analysis args
    # Include token_name in the tool input
    tool_input = {"token_id": token_id, "token_name": token_name}

    action = AgentAction(
        tool="momentum_quant_analyzer", # Use updated tool name
        tool_input=tool_input,
        # Update log message to include token_name
        log=f"Preparing momentum/quant analysis for {token_name} (ID: {token_id})"
    )
    logger.info(f"Prepared action: {action}")
    # Initialize intermediate_steps if it doesn't exist (standard practice)
    return {"action": action, "intermediate_steps": []}


def execute_tool_node(state: MomentumQuantAgentState):
    logger.info("--- Momentum Quant: Executing Tool Node ---")
    action = state.get("action")
    analysis_result_data = None # Default result
    token_name_for_error = state.get("input", {}).get("token_name") or f"Token ID {state.get('input', {}).get('token_id', 'N/A')}"

    # Check if prepare_node already put an error in analysis_data
    if state.get("analysis_data") and state["analysis_data"].get("error"):
         logger.warning(f"Skipping tool execution for {token_name_for_error} due to error in prepare step: {state['analysis_data']['error']}")
         # Keep existing analysis_data with error
         return {} # No changes needed

    if not isinstance(action, AgentAction):
         logger.error(f"execute_tool_node received non-action for {token_name_for_error}: {action}")
         error_message = f"Internal error: Tool execution step received invalid action state."
         analysis_result_data = {
             "error": error_message,
             "reason_string": error_message,
             "token_id": state.get("input", {}).get("token_id"), # Try to get token_id
             "token_name": token_name_for_error, # Add name
             "reasoning_components": {"error": error_message} # Add error to reasoning_components
         }
         # Log a dummy action/error pair
         dummy_action = AgentAction(tool="error_state", tool_input={}, log=error_message)
         return {
             "analysis_data": analysis_result_data,
             "reason_string": error_message, # Populate reason_string too
             "intermediate_steps": [(dummy_action, analysis_result_data)]
         }
    else:
        logger.info(f"Executing tool: {action.tool} with input {action.tool_input} for {token_name_for_error}")
        try:
            # Tool function now handles token_name directly
            output_dict = tool_executor.invoke(action)
            logger.info(f"Tool output dictionary for {token_name_for_error}: {output_dict}")
            analysis_result_data = output_dict

            if isinstance(output_dict, dict) and output_dict.get("error"):
                 logger.warning(f"Momentum Quant tool reported an error for {token_name_for_error}: {output_dict['error']}")

        except Exception as e:
            logger.exception(f"Error executing tool {action.tool} for {token_name_for_error}: {e}")
            error_message = f"Tool execution failed: {type(e).__name__}"
            analysis_result_data = {
                 "error": error_message,
                 "reason_string": f"Internal error during tool execution: {str(e)}",
                 "token_id": action.tool_input.get("token_id"), # Try to preserve context
                 "token_name": token_name_for_error,
                 "reasoning_components": {"error": f"Internal error during tool execution: {str(e)}"} # Add error to reasoning_components
            }

    # Log the actual action and the dictionary result
    # state.get("intermediate_steps", []) isn't needed here as we overwrite
    intermediate_steps_list = [(action, analysis_result_data)]

    # Extract reason_string and store in state
    reason_string = analysis_result_data.get("reason_string") if isinstance(analysis_result_data, dict) else None

    return {
        "analysis_data": analysis_result_data,
        "reason_string": reason_string, # Populate reason_string in state
        "intermediate_steps": intermediate_steps_list # Return the list with the single step
    }

def generate_llm_reasoning_node(state: MomentumQuantAgentState):
    logger.info("--- Momentum Quant: Generating LLM Reasoning Node ---")
    analysis_data = state.get("analysis_data")
    reason_string = state.get("reason_string") # Get pre-calculated reason
    final_explanation = "Error: Analysis data not found in state." # Default error

    if not analysis_data:
        logger.error("No analysis data found in state for LLM reasoning.")
        return {"llm_reasoning": final_explanation}

    # Extract token data directly from analysis_data
    token_id = analysis_data.get("token_id", "N/A")
    token_name = analysis_data.get("token_name", f"Token ID {token_id}")

    # If tool execution resulted in an error stored in analysis_data
    if analysis_data.get("error"):
        error_msg = analysis_data["error"]
        # Use the reason_string which should contain the error details now
        reasoning_error = reason_string or analysis_data.get("reason_string", "Unknown calculation error")
        # Also check reasoning_components for error message
        if reasoning_error == "Unknown calculation error" and isinstance(analysis_data.get("reasoning_components"), dict):
            reasoning_error = analysis_data["reasoning_components"].get("error", reasoning_error)
        logger.warning(f"Skipping LLM reasoning due to previous error: {error_msg}")
        final_explanation = f"Analysis Error for {token_name} (ID: {token_id}): {reasoning_error}"
        return {"llm_reasoning": final_explanation}

    # --- Prepare data for prompt ---
    signal = analysis_data.get("signal", "UNKNOWN")
    reasoning_comps = analysis_data.get("reasoning_components", {})
    
    # Get values from reasoning_components if available, otherwise from analysis_data
    latest_tg = reasoning_comps.get("latest_tg") or analysis_data.get("latest_tg")
    previous_tg = reasoning_comps.get("previous_tg") or analysis_data.get("previous_tg")
    pct_change_tg = reasoning_comps.get("pct_change_tg") or analysis_data.get("pct_change_tg")
    quant_grade = reasoning_comps.get("quant_grade") or analysis_data.get("quant_grade")

    # Check required values exist
    if pct_change_tg is None or quant_grade is None or reason_string is None:
         logger.error(f"LLM Node: Missing required data (pct_change, quant_grade, or reason_string) in state for {token_name}: {state}")
         # Use the existing reason_string if available, otherwise a generic message
         final_explanation = f"Analysis Error for {token_name} (ID: {token_id}): {reason_string or 'Could not generate explanation due to missing core metrics or reason.'}"
         return {"llm_reasoning": final_explanation}

    # Format values for prompt
    latest_tg_str = f"{latest_tg:.2f}" if latest_tg is not None else "N/A"
    previous_tg_str = f"{previous_tg:.2f}" if previous_tg is not None else "N/A"
    pct_change_tg_str = f"{pct_change_tg:.2%}" if pct_change_tg is not None else "N/A"
    quant_grade_str = f"{quant_grade:.1f}" if quant_grade is not None else "N/A"

    # Prepare final input for the prompt, including token_name
    prompt_input = {
        "token_id": token_id, # Keep ID for context
        "token_name": token_name, # Add token_name
        "latest_tg_str": latest_tg_str,
        "previous_tg_str": previous_tg_str,
        "pct_change_tg_str": pct_change_tg_str,
        "quant_grade_str": quant_grade_str,
        "signal": signal,
        "reason_string": reason_string,
        "momentum_threshold": MOMENTUM_THRESHOLD,
        "quant_grade_threshold": QUANT_GRADE_THRESHOLD,
    }

    try:
        reasoning_chain = momentum_reasoning_prompt | llm
        logger.info(f"Invoking LLM with data for {token_name}: {prompt_input}")
        llm_response = reasoning_chain.invoke(prompt_input)

        if hasattr(llm_response, 'content'):
             final_explanation = llm_response.content
        else:
             final_explanation = str(llm_response)

        logger.info(f"LLM generated reasoning for {token_name}: {final_explanation}")
        return {"llm_reasoning": final_explanation.strip()}

    except Exception as e:
        logger.exception(f"Error invoking LLM for reasoning for {token_name}")
        final_explanation = f"Error generating explanation for {token_name} (ID: {token_id}): {str(e)}"
        return {"llm_reasoning": final_explanation}

# --- Build Graph (Updated) ---
workflow = StateGraph(MomentumQuantAgentState)

# Use standardized node names
workflow.add_node("prepare_tool_call", prepare_tool_call_node)
workflow.add_node("execute_tool", execute_tool_node)
workflow.add_node("generate_llm_reasoning", generate_llm_reasoning_node)

workflow.set_entry_point("prepare_tool_call")

# Add edges to define the flow
workflow.add_edge("prepare_tool_call", "execute_tool")
workflow.add_edge("execute_tool", "generate_llm_reasoning")
workflow.add_edge("generate_llm_reasoning", END)

# --- Memory & Compile ---
memory = MemorySaver()
# Allow instrumentation for LangSmith tracing
app = workflow.compile(checkpointer=memory)

# --- Manual Test (Updated Check) ---
if __name__ == "__main__":
    print("--- Testing Momentum Quant Agent (with LLM Reasoning) ---")
    config = {"configurable": {"thread_id": str(uuid4())}}

    # --- Test Cases (Add token_name) ---
    test_cases = [
        {"token_id": "3306", "token_name": "Ethereum", "description": "Ethereum (Likely valid)"},
        {"token_id": "1", "token_name": "Bitcoin", "description": "Bitcoin (Likely valid)"},
        {"token_id": "999999", "token_name": "Invalid Token 999999", "description": "Invalid Token ID"},
        {"token_id": "", "token_name": None, "description": "Missing Token ID"},
        # Add more specific cases if you know tokens likely to trigger BUY/SELL
    ]

    for case in test_cases:
        token_id_to_test = case["token_id"]
        token_name_to_test = case["token_name"]
        print(f"\n--- Running Test: {case['description']} (ID: {token_id_to_test}, Name: {token_name_to_test}) ---")
        # Include token_name in the test input
        test_input = {"token_id": token_id_to_test, "token_name": token_name_to_test}

        print(f"Invoking agent with input: {test_input} and config: {config}")

        try:
            # Execute the agent graph
            result_state = app.invoke({"input": test_input}, config=config)

            print("--- Agent Execution Result State ---")
            # print(result_state) # Print full state for debugging if needed
            print(f"Input: {result_state.get('input')}")
            # Verify the structure of the output
            analysis_data_output = result_state.get('analysis_data')
            llm_reasoning_output = result_state.get('llm_reasoning')
            print(f"Analysis Data (Dict): {analysis_data_output}")
            print(f"LLM Reasoning (Str): {llm_reasoning_output}")

            # Extract the final LLM explanation
            final_output = llm_reasoning_output or "No LLM reasoning found in state."
            print(f"\n--- Final LLM Explanation for {case['description']} (ID: {token_id_to_test}) ---")
            print(final_output)

        except Exception as e:
            print(f"--- Error during agent execution for {case['description']} (ID: {token_id_to_test}) ---")
            logger.exception(f"Agent invocation failed in main block for {token_id_to_test}")
            print(f"Error: {type(e).__name__} - {e}")

    print("\n--- Test Complete ---") 