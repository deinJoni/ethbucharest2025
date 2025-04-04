import logging
from typing import TypedDict, Annotated, Dict, Any, Optional
import operator
from datetime import datetime, timedelta
import statistics
import requests

from langchain_openai import ChatOpenAI
from langchain_core.agents import AgentAction
from langchain.agents import Tool
from langchain.tools import StructuredTool
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolExecutor
from langgraph.checkpoint.memory import MemorySaver
from langchain.prompts import PromptTemplate
from core.config import settings

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# --- SMA Tool ---
def sma_analysis(token_id: str, token_name: str) -> Dict[str, Any]:
    """
    Calculates SMA data for a crypto coin based on its Token Metrics ID.
    Uses the provided token_name in the output.
    Returns a dictionary containing: token_id, token_name, current_price, sma20, sma50, signal, and basic comparison info.
    Handles potential errors during data fetching or calculation.
    """
    logger.info(f"--- sma_analysis Tool ---")
    logger.info(f"Received token_id: {token_id}, token_name: {token_name}")

    analysis_data = {
        "token_id": token_id, 
        "token_name": token_name, 
        "error": None,
        "reasoning_components": {},  # Add reasoning_components field to match other agents
        "reason_string": None  # Add reason_string field for consistency
    } # Initialize result dict

    try:
        # Fetch data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=65)
        end_date_str = end_date.strftime('%Y-%m-%d')
        start_date_str = start_date.strftime('%Y-%m-%d')
        url = f"https://api.tokenmetrics.com/v2/daily-ohlcv?token_id={token_id}&startDate={start_date_str}&endDate={end_date_str}&limit=60&page=0"
        headers = {
            "accept": "application/json",
            "api_key": settings.TOKEN_METRICS_API_KEY
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()

        if not data.get("success", False) or not data.get("data"):
            error_msg = f"No data found for token_id {token_id}."
            analysis_data["error"] = error_msg
            analysis_data["reason_string"] = error_msg
            analysis_data["reasoning_components"]["error"] = error_msg
            return analysis_data

        # Sort data
        try:
            daily_data = sorted(data["data"], key=lambda x: x["DATE"], reverse=False)
        except KeyError:
             error_msg = f"Data format error for token_id {token_id}: Missing 'DATE' key."
             analysis_data["error"] = error_msg
             analysis_data["reason_string"] = error_msg
             analysis_data["reasoning_components"]["error"] = error_msg
             return analysis_data
        except Exception as e:
             logger.exception(f"Error sorting data for token_id {token_id}: {e}")
             error_msg = f"Failed to process data for token_id {token_id}: Error during sorting."
             analysis_data["error"] = error_msg
             analysis_data["reason_string"] = error_msg
             analysis_data["reasoning_components"]["error"] = error_msg
             return analysis_data

        # Check data length and extract closes
        if len(daily_data) < 50:
            error_msg = f"Insufficient data for token_id {token_id}. Needed 50 days, got {len(daily_data)}."
            analysis_data["error"] = error_msg
            analysis_data["reason_string"] = error_msg
            analysis_data["reasoning_components"]["error"] = error_msg
            return analysis_data
        relevant_data = daily_data[-50:]
        try:
            closes = [day["CLOSE"] for day in relevant_data]
        except KeyError:
            error_msg = f"Data format error for token_id {token_id}: Missing 'CLOSE' key."
            analysis_data["error"] = error_msg
            analysis_data["reason_string"] = error_msg
            analysis_data["reasoning_components"]["error"] = error_msg
            return analysis_data
        if len(closes) < 50: # Failsafe
             error_msg = f"Data processing error for token_id {token_id}: Could not extract 50 closing prices."
             analysis_data["error"] = error_msg
             analysis_data["reason_string"] = error_msg
             analysis_data["reasoning_components"]["error"] = error_msg
             return analysis_data

        # Calculate metrics
        current_price = closes[-1]
        analysis_data["current_price"] = current_price
        if len(closes) < 20: # Failsafe
           error_msg = f"Not enough data points ({len(closes)}) to calculate 20-day SMA for token_id {token_id}."
           analysis_data["error"] = error_msg
           analysis_data["reason_string"] = error_msg
           analysis_data["reasoning_components"]["error"] = error_msg
           return analysis_data
        sma20 = statistics.mean(closes[-20:])
        sma50 = statistics.mean(closes[-50:])
        analysis_data["sma20"] = sma20
        analysis_data["sma50"] = sma50

        # Store all values in reasoning_components too
        reasoning_comps = {
            "current_price": current_price,
            "sma20": sma20,
            "sma50": sma50
        }

        # Determine signal and basic comparison
        price = analysis_data["current_price"]
        if price > sma20 and price > sma50:
            signal = "BUY"
            comparison = f"Current price (${price:.2f}) > SMA20 (${sma20:.2f}) and > SMA50 (${sma50:.2f})"
            reasoning_comps["buy_check"] = True
            reasoning_comps["above_sma20"] = True
            reasoning_comps["above_sma50"] = True
        elif price < sma20 and price < sma50:
            signal = "SELL"
            comparison = f"Current price (${price:.2f}) < SMA20 (${sma20:.2f}) and < SMA50 (${sma50:.2f})"
            reasoning_comps["sell_check"] = True
            reasoning_comps["below_sma20"] = True
            reasoning_comps["below_sma50"] = True
        else:
            signal = "NO_SIGNAL"
            comparison = f"Current price (${price:.2f}) is not consistently above or below both SMAs (SMA20=${sma20:.2f}, SMA50=${sma50:.2f})"
            reasoning_comps["hold_reason"] = "mixed_signals"
            reasoning_comps["above_sma20"] = price > sma20
            reasoning_comps["above_sma50"] = price > sma50
            
        analysis_data["signal"] = signal
        analysis_data["comparison"] = comparison
        analysis_data["reason_string"] = comparison
        analysis_data["reasoning_components"] = reasoning_comps

        logger.info(f"Calculated analysis data for {token_id}: {analysis_data}")
        return analysis_data

    except requests.exceptions.RequestException as e:
         error_msg = f"API request failed for token_id {token_id}: {str(e)}"
         analysis_data["error"] = error_msg
         analysis_data["reason_string"] = error_msg
         analysis_data["reasoning_components"]["error"] = error_msg
         return analysis_data
    except statistics.StatisticsError as e:
         error_msg = f"Calculation error for token_id {token_id}: {str(e)}"
         analysis_data["error"] = error_msg
         analysis_data["reason_string"] = error_msg
         analysis_data["reasoning_components"]["error"] = error_msg
         return analysis_data
    except Exception as e:
        logger.exception(f"Unexpected error analyzing token_id {token_id}: {str(e)}")
        error_msg = f"Failed to analyze token_id {token_id}: An unexpected error occurred ({type(e).__name__})."
        analysis_data["error"] = error_msg
        analysis_data["reason_string"] = error_msg
        analysis_data["reasoning_components"]["error"] = error_msg
        return analysis_data

# --- Tool & Executor ---
sma_tool = StructuredTool.from_function(
    func=sma_analysis,
    name="sma_analysis_calculator",
    description="Calculates SMA (20-day, 50-day), current price, and determines a BUY/SELL/NO_SIGNAL based on the SMA Crossover strategy for a given Token Metrics ID (token_id) and token name (token_name). Returns a dictionary with calculated data or an error message.",
)
tool_executor = ToolExecutor([sma_tool])

# --- LLM for Reasoning ---
llm = ChatOpenAI(
    temperature=0.1,
    api_key=settings.OPENAI_API_KEY,
    model="gpt-4-0125-preview"
)

# --- Reasoning Prompt ---
reasoning_prompt = PromptTemplate.from_template(
    """You are a financial analyst assistant explaining the result of an SMA Crossover strategy calculation.

Based on the following data calculated for Token {token_name}:
- Current Price: ${current_price:.2f}
- SMA20 (20-day Simple Moving Average): ${sma20:.2f}
- SMA50 (50-day Simple Moving Average): ${sma50:.2f}
- Signal Determined: {signal}
- Comparison: {comparison}

Generate a concise explanation for a user. Your explanation should:
1. Start with "The signal determined for {token_name} is {signal}." - This exact format is critical.
2. Explain the reasoning based *only* on the provided comparison between the current price and the SMAs.
3. If the signal is BUY, mention it's generally considered a bullish sign suggesting potential upward momentum according to this strategy.
4. If the signal is SELL, mention it's generally considered a bearish sign suggesting potential downward momentum according to this strategy.
5. If the signal is NO SIGNAL, simply state the reasoning based on the comparison.
Do not add any information not present in the input data. Be factual and stick to the provided numbers and signal.

Explanation:"""
)

# --- LangGraph State (Updated for consistency) ---
class AgentState(TypedDict):
    input: Dict[str, str] # Expects {"token_id": "...", "token_name": "..."}
    action: Optional[AgentAction]
    analysis_data: Optional[Dict[str, Any]] # Result from sma_analysis tool
    reason_string: Optional[str] # Pre-LLM reason string from tool
    llm_reasoning: Optional[str] # Final explanation from LLM
    intermediate_steps: Annotated[list[tuple[AgentAction, Dict[str, Any]]], operator.add]

# --- Nodes (Renamed for consistency) ---
def prepare_tool_call(state: AgentState):
    logger.info("--- SMA Agent: Preparing Tool Call Node ---")
    input_data = state['input']
    token_id = input_data.get('token_id')
    token_name = input_data.get('token_name', 'Unknown Token') # Default name if missing
    logger.info(f"Input token_id: {token_id}, token_name: {token_name}")

    if not token_id:
        logger.error("Missing 'token_id' in input for prepare_tool_call node")
        # Return error state that skips tool execution
        return {
            "analysis_data": { # Store error info here
                 "token_id": token_id, 
                 "token_name": token_name, 
                 "error": "Missing 'token_id' in input.",
                 "reason_string": "Input error: Token ID was not provided.",
                 "reasoning_components": {"error": "Input error: Token ID was not provided."}
            }
        }

    tool_input = {"token_id": token_id, "token_name": token_name}
    action = AgentAction(tool="sma_analysis_calculator", tool_input=tool_input, log=f"Preparing SMA calculation for {token_name} (ID: {token_id})")
    logger.info(f"Prepared action: {action}")
    # Initialize intermediate_steps for consistency
    return {"action": action, "intermediate_steps": []}

def execute_tool(state: AgentState):
    logger.info("--- SMA Agent: Executing Tool Node ---")
    action = state.get("action")
    analysis_result_data = None
    token_name_for_error = state.get("input", {}).get("token_name", "Unknown Token")

    # Check if prepare_node already put an error in analysis_data
    if state.get("analysis_data") and state["analysis_data"].get("error"):
         logger.warning(f"Skipping tool execution due to error in prepare step: {state['analysis_data']['error']}")
         return {} # No changes needed, error already in analysis_data

    if not isinstance(action, AgentAction):
         logger.error(f"execute_tool_node received non-action: {action}")
         error_message = f"Internal error: Tool execution step received invalid action state."
         analysis_result_data = {
             "error": error_message,
             "reason_string": error_message,
             "token_id": state.get("input", {}).get("token_id"),
             "token_name": token_name_for_error,
             "reasoning_components": {"error": error_message} # Add error to reasoning_components
         }
         # Log a dummy action/error pair
         dummy_action = AgentAction(tool="error_state", tool_input={}, log=error_message)
         return {
             "analysis_data": analysis_result_data, 
             "reason_string": error_message,
             "intermediate_steps": [(dummy_action, analysis_result_data)]
         }

    try:
        output_dict = tool_executor.invoke(action)
        logger.info(f"Tool output dictionary: {output_dict}")
        analysis_result_data = output_dict

        if isinstance(output_dict, dict) and output_dict.get("error"):
            logger.warning(f"SMA calculation tool reported an error: {output_dict['error']}")

    except Exception as e:
        logger.exception(f"Error executing tool {action.tool}")
        error_message = f"Tool execution failed: {type(e).__name__}"
        analysis_result_data = {
             "error": error_message,
             "reason_string": f"Internal error during tool execution: {str(e)}",
             "token_id": action.tool_input.get("token_id"),
             "token_name": action.tool_input.get("token_name"),
             "reasoning_components": {"error": f"Internal error during tool execution: {str(e)}"} # Add error to reasoning_components
        }

    # Extract reason_string (for SMA, use comparison field as reason_string)
    reason_string = None
    if isinstance(analysis_result_data, dict):
        reason_string = analysis_result_data.get("reason_string") or analysis_result_data.get("comparison")
        # Also store the reason_string in the analysis_data for consistency if not already there
        if reason_string and "reason_string" not in analysis_result_data:
            analysis_result_data["reason_string"] = reason_string

    # Create intermediate_steps with the actual action/result
    intermediate_steps = [(action, analysis_result_data)]

    return {
        "analysis_data": analysis_result_data,
        "reason_string": reason_string,
        "intermediate_steps": intermediate_steps
    }

def generate_llm_reasoning(state: AgentState):
    logger.info("--- SMA Agent: Generating LLM Reasoning Node ---")
    analysis_data = state.get("analysis_data")
    reason_string = state.get("reason_string") # Get pre-calculated reason

    if not analysis_data:
        logger.error("No analysis data found in state for LLM reasoning.")
        return {"llm_reasoning": "Error: Analysis data was missing."}

    # Extract token information
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

    # Get data from reasoning_components if available
    reasoning_comps = analysis_data.get("reasoning_components", {})
    
    # Get values from reasoning_components if available, otherwise from analysis_data directly
    current_price = reasoning_comps.get("current_price") or analysis_data.get("current_price")
    sma20 = reasoning_comps.get("sma20") or analysis_data.get("sma20")
    sma50 = reasoning_comps.get("sma50") or analysis_data.get("sma50")
    signal = analysis_data.get("signal", "UNKNOWN")
    comparison = analysis_data.get("comparison") or reason_string

    # Check for required keys
    if current_price is None or sma20 is None or sma50 is None or signal is None or comparison is None:
        logger.error(f"Analysis data missing required values for LLM prompt: {analysis_data}")
        missing_values = []
        if current_price is None: missing_values.append("current_price")
        if sma20 is None: missing_values.append("sma20")
        if sma50 is None: missing_values.append("sma50")
        if signal is None: missing_values.append("signal")
        if comparison is None: missing_values.append("comparison")
        return {"llm_reasoning": f"Error: Analysis data incomplete, missing values: {missing_values}"}

    # Prepare prompt input
    prompt_input = {
        "token_name": token_name,
        "current_price": current_price,
        "sma20": sma20,
        "sma50": sma50,
        "signal": signal,
        "comparison": comparison
    }

    try:
        reasoning_chain = reasoning_prompt | llm
        logger.info(f"Invoking LLM with data for {token_name}: {prompt_input}")
        llm_response = reasoning_chain.invoke(prompt_input)

        if hasattr(llm_response, 'content'):
             reasoning_text = llm_response.content
        else:
             reasoning_text = str(llm_response)

        logger.info(f"LLM generated reasoning for {token_name}: {reasoning_text}")
        return {"llm_reasoning": reasoning_text.strip()}

    except Exception as e:
        logger.exception(f"Error invoking LLM for reasoning for {token_name}")
        return {"llm_reasoning": f"Error generating explanation for {token_name} (ID: {token_id}): {str(e)}"}

# --- Build Graph ---
workflow = StateGraph(AgentState)
workflow.add_node("prepare_tool_call", prepare_tool_call)
workflow.add_node("execute_tool", execute_tool)
workflow.add_node("generate_llm_reasoning", generate_llm_reasoning)
workflow.set_entry_point("prepare_tool_call")
workflow.add_edge("prepare_tool_call", "execute_tool")
workflow.add_edge("execute_tool", "generate_llm_reasoning")
workflow.add_edge("generate_llm_reasoning", END)

# --- Memory & Compile ---
memory = MemorySaver()
app = workflow.compile(checkpointer=memory)

# --- Manual Test ---
if __name__ == "__main__":
    from uuid import uuid4
    config = {"configurable": {"thread_id": str(uuid4())}}
    token_id_to_test = "3306" # Example Token ID for ETH on Token Metrics
    token_name_to_test = "Ethereum"
    test_input = {"token_id": token_id_to_test, "token_name": token_name_to_test}
    result = app.invoke({"input": test_input}, config=config)

    final_output = result.get("llm_reasoning", "No LLM reasoning found in state.")
    print(f"--- Final LLM Explanation for {token_name_to_test} (ID: {token_id_to_test}) ---")
    print(final_output)
    print("\n--- Full Final State ---")
    print(result) # Print the full state for debugging
