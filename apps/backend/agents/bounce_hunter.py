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

# --- Configuration ---
PROXIMITY_THRESHOLD = 0.05  # 5%

# --- Bounce Hunter Tool (Returns Dict) ---
def bounce_hunter_analysis(token_id: str, token_symbol: str) -> Dict[str, Any]:
    """
    Analyzes if a crypto token's current price is near historical support or resistance levels.
    Returns a dictionary containing detected levels, signals, and reasoning components, or an error.
    """
    symbol_cleaned = token_symbol.strip().upper()
    logger.info(f"Starting bounce hunter analysis for symbol: '{symbol_cleaned}' (ID: {token_id})")
    
    # Initialize result dictionary
    analysis_result: Dict[str, Any] = {
        "token_id": token_id,
        "token_symbol": symbol_cleaned,
        "current_price": None,
        "nearby_levels": [],
        "signal": "NO SIGNAL",  # Default signal
        "reasoning_components": {},
        "reason_string": "Analysis did not complete.",
        "error": None
    }

    # --- Check API Key ---
    api_key = settings.TOKEN_METRICS_API_KEY
    if not api_key or api_key == "YOUR_TOKEN_METRICS_API_KEY":
        logger.error("Token Metrics API key not configured.")
        analysis_result["error"] = "API key missing"
        analysis_result["reasoning_components"]["error"] = "Internal configuration error: API key missing."
        return analysis_result

    if not token_id:
        logger.error(f"Missing token_id for analysis of symbol '{symbol_cleaned}'")
        analysis_result["error"] = "Missing token_id input"
        analysis_result["reasoning_components"]["error"] = "Input error: Token ID was not provided."
        return analysis_result

    # Fetch current price from Token Metrics API
    headers = {"accept": "application/json", "api_key": api_key}
    price_url = f"https://api.tokenmetrics.com/v2/price?token_id={token_id}"
    current_price = None
    
    try:
        price_response = requests.get(price_url, headers=headers, timeout=10)
        price_response.raise_for_status()
        price_data = price_response.json()
        
        if price_data.get("success") and price_data.get("data"):
            if price_data["data"]:
                # Extract the current price from the API response
                current_price = float(price_data["data"][0].get("CURRENT_PRICE", 0))
                logger.info(f"Successfully fetched current price for {symbol_cleaned} (ID: {token_id}): ${current_price:.2f}")
            else:
                analysis_result["error"] = "No price data found"
                analysis_result["reasoning_components"]["error"] = "No price data found in API response."
                analysis_result["reason_string"] = f"Could not retrieve current price for {symbol_cleaned}."
                return analysis_result
        else:
            api_msg = price_data.get('message', 'Unknown API error')
            analysis_result["error"] = f"API Error: {api_msg}"
            analysis_result["reasoning_components"]["error"] = f"API Error: Could not fetch price data ({api_msg})."
            analysis_result["reason_string"] = f"Failed to retrieve current price for {symbol_cleaned} from Token Metrics API."
            return analysis_result
    except requests.exceptions.RequestException as req_e:
        logger.exception(f"API Request error fetching price for {symbol_cleaned} (ID: {token_id}): {req_e}")
        analysis_result["error"] = "API request failed"
        analysis_result["reasoning_components"]["error"] = f"Network error: Failed to connect to the price API ({type(req_e).__name__})."
        analysis_result["reason_string"] = f"Failed to connect to Token Metrics API to fetch current price for {symbol_cleaned}."
        return analysis_result
    except Exception as e:
        logger.exception(f"Unexpected error processing price data for {symbol_cleaned} (ID: {token_id}): {e}")
        analysis_result["error"] = "Price data processing failed"
        analysis_result["reasoning_components"]["error"] = f"Internal error: Failed processing price data ({type(e).__name__})."
        analysis_result["reason_string"] = f"An error occurred while retrieving current price for {symbol_cleaned}."
        return analysis_result
        
    analysis_result["current_price"] = current_price

    # --- Fetch Historical Levels from Token Metrics API ---
    headers = {"accept": "application/json", "api_key": api_key}
    url = f"https://api.tokenmetrics.com/v2/resistance-support?token_id={token_id}&limit=100&page=0"
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        response_data = response.json()
        
        if response_data.get("success") and response_data.get("data"):
            if response_data["data"]:
                token_data = response_data["data"][0]
                raw_levels = token_data.get("HISTORICAL_RESISTANCE_SUPPORT_LEVELS", [])
                historical_levels = [{"level": float(lvl["level"]), "date": lvl["date"]} 
                                     for lvl in raw_levels if "level" in lvl and "date" in lvl]
                logger.info(f"Successfully fetched {len(historical_levels)} levels for {symbol_cleaned} (ID: {token_id})")
                
                if not historical_levels:
                    analysis_result["error"] = "No historical levels found"
                    analysis_result["reasoning_components"]["error"] = "No historical support/resistance levels found for this token."
                    analysis_result["reason_string"] = f"No historical support/resistance levels found for {symbol_cleaned}."
                    return analysis_result
                
                # Store all historical levels in reasoning components
                analysis_result["reasoning_components"]["historical_levels"] = historical_levels
                analysis_result["reasoning_components"]["proximity_threshold"] = PROXIMITY_THRESHOLD
                
                # Find nearby levels
                nearby_levels = []
                bounce_levels = []  # Support levels (price above)
                breakout_levels = []  # Resistance levels (price below)
                
                for level_data in historical_levels:
                    level = level_data["level"]
                    level_date = level_data["date"]
                    price_diff = abs(current_price - level)
                    proximity_percent = (price_diff / level) if level != 0 else 0
                    
                    if proximity_percent <= PROXIMITY_THRESHOLD:
                        distance_str = f"${price_diff:.2f} ({proximity_percent:.2%})"
                        level_info = {
                            "level": level,
                            "date": level_date,
                            "distance": price_diff,
                            "proximity_percent": proximity_percent,
                            "distance_str": distance_str
                        }
                        
                        if current_price > level:
                            level_info["type"] = "support"
                            bounce_levels.append(level_info)
                        else:
                            level_info["type"] = "resistance"
                            breakout_levels.append(level_info)
                        
                        nearby_levels.append(level_info)
                
                # Store nearby levels in result
                analysis_result["nearby_levels"] = nearby_levels
                analysis_result["reasoning_components"]["bounce_levels"] = bounce_levels
                analysis_result["reasoning_components"]["breakout_levels"] = breakout_levels
                
                # Determine signal based on nearby levels
                if bounce_levels and breakout_levels:
                    # If both support and resistance are nearby, the one closest to price takes precedence
                    closest_bounce = min(bounce_levels, key=lambda x: x["proximity_percent"])
                    closest_breakout = min(breakout_levels, key=lambda x: x["proximity_percent"])
                    
                    if closest_bounce["proximity_percent"] <= closest_breakout["proximity_percent"]:
                        analysis_result["signal"] = "BUY"
                        analysis_result["reason_string"] = (
                            f"Price (${current_price:.2f}) is {closest_bounce['distance_str']} above support at "
                            f"${closest_bounce['level']:.2f} from {closest_bounce['date']}. "
                            f"A potential bounce may be forming."
                        )
                    else:
                        analysis_result["signal"] = "SELL"
                        analysis_result["reason_string"] = (
                            f"Price (${current_price:.2f}) is {closest_breakout['distance_str']} below resistance at "
                            f"${closest_breakout['level']:.2f} from {closest_breakout['date']}. "
                            f"A potential breakout may be forming."
                        )
                
                elif bounce_levels:
                    analysis_result["signal"] = "BUY"
                    closest_bounce = min(bounce_levels, key=lambda x: x["proximity_percent"])
                    analysis_result["reason_string"] = (
                        f"Price (${current_price:.2f}) is {closest_bounce['distance_str']} above support at "
                        f"${closest_bounce['level']:.2f} from {closest_bounce['date']}. "
                        f"A potential bounce may be forming."
                    )
                
                elif breakout_levels:
                    analysis_result["signal"] = "SELL"
                    closest_breakout = min(breakout_levels, key=lambda x: x["proximity_percent"])
                    analysis_result["reason_string"] = (
                        f"Price (${current_price:.2f}) is {closest_breakout['distance_str']} below resistance at "
                        f"${closest_breakout['level']:.2f} from {closest_breakout['date']}. "
                        f"A potential breakout may be forming."
                    )
                
                else:
                    analysis_result["signal"] = "HOLD"
                    analysis_result["reason_string"] = (
                        f"Current price (${current_price:.2f}) is not within {PROXIMITY_THRESHOLD:.1%} "
                        f"of any historical support or resistance levels for {symbol_cleaned}."
                    )
            
            else:
                analysis_result["error"] = "No data found"
                analysis_result["reasoning_components"]["error"] = "No token data found in API response."
                analysis_result["reason_string"] = f"No data found for {symbol_cleaned} in Token Metrics API response."
                return analysis_result
        
        else:
            api_msg = response_data.get('message', 'Unknown API error')
            analysis_result["error"] = f"API Error: {api_msg}"
            analysis_result["reasoning_components"]["error"] = f"API Error: Could not fetch support/resistance data ({api_msg})."
            analysis_result["reason_string"] = f"Failed to retrieve support/resistance data for {symbol_cleaned} from Token Metrics API."
            return analysis_result
    
    except requests.exceptions.RequestException as req_e:
        logger.exception(f"API Request error fetching levels for {symbol_cleaned} (ID: {token_id}): {req_e}")
        analysis_result["error"] = "API request failed"
        analysis_result["reasoning_components"]["error"] = f"Network error: Failed to connect to the support/resistance API ({type(req_e).__name__})."
        analysis_result["reason_string"] = f"Failed to connect to Token Metrics API to fetch support/resistance data for {symbol_cleaned}."
        return analysis_result
    
    except Exception as e:
        logger.exception(f"Unexpected error processing data for {symbol_cleaned} (ID: {token_id}): {e}")
        analysis_result["error"] = "Data processing failed"
        analysis_result["reasoning_components"]["error"] = f"Internal error: Failed processing support/resistance data ({type(e).__name__})."
        analysis_result["reason_string"] = f"An error occurred while analyzing support/resistance levels for {symbol_cleaned}."
        return analysis_result
    
    logger.info(f"Bounce Hunter analysis complete for {symbol_cleaned} (ID: {token_id}): Signal={analysis_result['signal']}")
    return analysis_result


# --- Tool & Executor ---
bounce_hunter_tool = StructuredTool.from_function(
    func=bounce_hunter_analysis,
    name="bounce_hunter_analyzer",
    description="Analyzes if a token's current price is near historical support or resistance levels (within 5% proximity) using Token Metrics data. Returns a dictionary with detected levels, signal, and reasoning components or an error.",
)
tool_executor = ToolExecutor([bounce_hunter_tool])

# --- LLM and Prompt ---
llm = ChatOpenAI(
    temperature=0.1,
    api_key=settings.OPENAI_API_KEY,
    model="gpt-4-0125-preview"
)

reasoning_prompt = PromptTemplate.from_template(
    """You are a crypto analysis assistant explaining the result of the Bounce Hunter strategy for {token_symbol}.

    The analysis relies on detecting when price approaches historically significant support or resistance levels:
    * Current Price: ${current_price_str}
    * Proximity Threshold: {proximity_threshold:.1%} (How close price must be to a level to trigger a signal)
    * Found nearby levels: {level_count} (Number of historical levels within the proximity threshold)

    Strategy Signals:
    * BUY: Price is above and near a historical support level, suggesting a potential bounce upward.
    * SELL: Price is below and near a historical resistance level, suggesting a potential breakout or decline.
    * HOLD: Price is not near any significant historical levels, indicating no clear technical signal.

    **Analysis Summary:**

    Based on the Bounce Hunter strategy analysis for {token_symbol}, the resulting signal is **{signal}**.

    The primary reason derived from the calculation is: "{reason_string}"

    **Explanation:**

    Start your explanation with "The signal determined for {token_symbol} is {signal}." - This exact format is critical.
    
    Then provide clear, concise reasoning for this signal using a methodical approach:
    1. First, discuss the current price position (${current_price_str}) relative to key support/resistance levels.
    2. If nearby levels were detected, explain which level is most significant and why (focus only on the closest/most relevant level, not all historical levels).
    3. Explain how the proximity to this level ({proximity_threshold:.1%} threshold) triggered the specific signal.
    4. Discuss the practical trading implications of this signal based on technical analysis principles.
    
    Make sure your explanation is clear, logical, and focuses on the key metrics that led to the {signal} decision.
    
    Before concluding, restate the final signal recommendation in this exact format:
    "FINAL RECOMMENDATION: {signal}"
    """
)

# --- LangGraph State ---
class AgentState(TypedDict):
    input: Dict[str, str]  # Expects {"token_id": "...", "token_name": "..."}
    action: AgentAction | None
    analysis_data: Optional[Dict[str, Any]]  # Result from bounce_hunter_analysis tool
    reason_string: Optional[str]  # Pre-LLM reason string from tool
    llm_reasoning: Optional[str]  # Final explanation from LLM
    intermediate_steps: Annotated[list[tuple[AgentAction, Dict[str, Any]]], operator.add]


# --- Nodes ---
def prepare_tool_call_node(state: AgentState):
    logger.info("--- Bounce Hunter: Preparing Tool Call Node ---")
    input_data = state['input']
    token_id = input_data.get('token_id')
    token_name = input_data.get('token_name', 'UnknownSymbol')
    logger.info(f"Input token_id: {token_id}, token_name/symbol: {token_name}")

    if not token_id:
        logger.error("Missing 'token_id' in input for prepare_tool_call_node")
        # Return error state that skips tool execution
        return {
            "analysis_data": {
                 "token_id": token_id, "token_symbol": token_name, "error": "Missing 'token_id' in input.",
                 "reasoning_components": {"error": "Input error: Token ID was not provided."}
            }
        }

    tool_input = {"token_id": token_id, "token_symbol": token_name}
    action = AgentAction(
        tool="bounce_hunter_analyzer",
        tool_input=tool_input,
        log=f"Preparing Bounce Hunter analysis for {token_name} (ID: {token_id})"
    )
    logger.info(f"Prepared action: {action}")
    return {"action": action, "intermediate_steps": []}


def execute_tool_node(state: AgentState):
    logger.info("--- Bounce Hunter: Executing Tool Node ---")
    action = state.get("action")
    analysis_result_data = None

    # Check if prepare_node already put an error in analysis_data
    if state.get("analysis_data") and state["analysis_data"].get("error"):
         logger.warning(f"Skipping tool execution due to error in prepare step: {state['analysis_data']['error']}")
         return {}  # No changes needed

    if not isinstance(action, AgentAction):
         logger.error(f"execute_tool_node received non-action: {action}")
         error_message = f"Internal error: Tool execution step received invalid action state."
         analysis_result_data = {
             "error": error_message,
             "reasoning_components": {"error": error_message}
         }
         dummy_action = AgentAction(tool="error_state", tool_input={}, log=error_message)
         return {"analysis_data": analysis_result_data, "intermediate_steps": [(dummy_action, analysis_result_data)]}
    else:
        logger.info(f"Executing tool: {action.tool} with input {action.tool_input}")
        try:
            output_dict = tool_executor.invoke(action)
            logger.info(f"Tool output dictionary: {output_dict}")
            analysis_result_data = output_dict

            if isinstance(output_dict, dict) and output_dict.get("error"):
                 logger.warning(f"Bounce Hunter tool reported an error: {output_dict['error']}")

        except Exception as e:
            logger.exception(f"Error executing tool {action.tool}: {e}")
            error_message = f"Tool execution failed: {type(e).__name__}"
            analysis_result_data = {
                 "error": error_message,
                 "reasoning_components": {"error": f"Internal error during tool execution: {str(e)}"},
                 "token_id": action.tool_input.get("token_id"),
                 "token_symbol": action.tool_input.get("token_symbol")
            }

    # Log the actual action and the dictionary result
    intermediate_steps = state.get("intermediate_steps", [])
    intermediate_steps.append((action, analysis_result_data))

    # Extract reason_string and store in state
    reason_string = analysis_result_data.get("reason_string") if isinstance(analysis_result_data, dict) else None

    return {
        "analysis_data": analysis_result_data,
        "reason_string": reason_string,
        "intermediate_steps": intermediate_steps
    }


def generate_llm_reasoning_node(state: AgentState):
    logger.info("--- Bounce Hunter: Generating LLM Reasoning Node ---")
    analysis_data = state.get("analysis_data")
    reason_string = state.get("reason_string")
    final_explanation = "Error: Analysis data not found in state."

    if not analysis_data:
        logger.error("No analysis data found in state for LLM reasoning.")
        return {"llm_reasoning": final_explanation}

    if analysis_data.get("error"):
        error_msg = analysis_data["error"]
        reasoning_error = reason_string or analysis_data.get("reasoning_components", {}).get("error", "Unknown calculation error")
        logger.warning(f"Skipping LLM reasoning due to previous error: {error_msg}")
        final_explanation = f"Analysis Error for {analysis_data.get('token_symbol', 'token')}: {reasoning_error}"
        return {"llm_reasoning": final_explanation}

    # Prepare data for prompt
    signal = analysis_data.get("signal", "UNKNOWN")
    current_price = analysis_data.get("current_price")
    nearby_levels = analysis_data.get("nearby_levels", [])
    
    if current_price is None or reason_string is None:
         logger.error(f"LLM Node: Missing required data (price or reason string) in state")
         final_explanation = f"Analysis Error: Could not generate explanation due to missing core data."
         return {"llm_reasoning": final_explanation}

    # Format values for prompt
    current_price_str = f"{current_price:.2f}" if current_price is not None else "N/A"
    level_count = len(nearby_levels)

    # Prepare final input for the prompt
    prompt_input = {
        "token_symbol": analysis_data.get("token_symbol", "this token"),
        "current_price_str": current_price_str,
        "proximity_threshold": PROXIMITY_THRESHOLD,
        "level_count": level_count,
        "signal": signal,
        "reason_string": reason_string,
    }

    # Log the input data for the LLM (similar to crypto_oracle.py's step 3)
    logger.info(f"Input data for LLM reasoning: {prompt_input}")

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


# --- Build Graph ---
workflow = StateGraph(AgentState)
workflow.add_node("prepare_tool_call_node", prepare_tool_call_node)
workflow.add_node("execute_tool_node", execute_tool_node)
workflow.add_node("generate_llm_reasoning_node", generate_llm_reasoning_node)
workflow.set_entry_point("prepare_tool_call_node")
workflow.add_edge("prepare_tool_call_node", "execute_tool_node")
workflow.add_edge("execute_tool_node", "generate_llm_reasoning_node")
workflow.add_edge("generate_llm_reasoning_node", END)

# --- Memory & Compile ---
memory = MemorySaver()
app = workflow.compile(checkpointer=memory)

# --- Manual Test ---
if __name__ == "__main__":
    from uuid import uuid4
    print("--- Testing Bounce Hunter Agent (with LLM Reasoning) ---")
    config = {"configurable": {"thread_id": str(uuid4())}}
    test_token_id = "3306"  # e.g., Ethereum
    test_token_name = "ETH"
    test_input = {"token_id": test_token_id, "token_name": test_token_name}

    print(f"Invoking agent with input: {test_input} and config: {config}")

    try:
        result_state = app.invoke({"input": test_input}, config=config)
        print("--- Agent Execution Result State ---")
        print(f"Input: {result_state.get('input')}")
        print(f"Analysis Data: {result_state.get('analysis_data')}")
        print(f"LLM Reasoning: {result_state.get('llm_reasoning')}")

        final_output = result_state.get("llm_reasoning", "No LLM reasoning found in state.")
        print("--- Final LLM Explanation ---")
        print(final_output)
    except Exception as e:
        print(f"--- Error during agent execution ---")
        logger.exception("Agent invocation failed in main block")
        print(f"Error: {e}")

    print("--- Test Complete ---") 