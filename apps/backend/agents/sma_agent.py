import logging
from typing import TypedDict, Annotated, Dict, Any
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

    analysis_data = {"token_id": token_id, "token_name": token_name, "error": None} # Initialize result dict

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
            analysis_data["error"] = f"No data found for token_id {token_id}."
            return analysis_data

        # Sort data
        try:
            daily_data = sorted(data["data"], key=lambda x: x["DATE"], reverse=False)
        except KeyError:
             analysis_data["error"] = f"Data format error for token_id {token_id}: Missing 'DATE' key."
             return analysis_data
        except Exception as e:
             logger.exception(f"Error sorting data for token_id {token_id}: {e}")
             analysis_data["error"] = f"Failed to process data for token_id {token_id}: Error during sorting."
             return analysis_data

        # Check data length and extract closes
        if len(daily_data) < 50:
            analysis_data["error"] = f"Insufficient data for token_id {token_id}. Needed 50 days, got {len(daily_data)}."
            return analysis_data
        relevant_data = daily_data[-50:]
        try:
            closes = [day["CLOSE"] for day in relevant_data]
        except KeyError:
            analysis_data["error"] = f"Data format error for token_id {token_id}: Missing 'CLOSE' key."
            return analysis_data
        if len(closes) < 50: # Failsafe
             analysis_data["error"] = f"Data processing error for token_id {token_id}: Could not extract 50 closing prices."
             return analysis_data

        # Calculate metrics
        analysis_data["current_price"] = closes[-1]
        if len(closes) < 20: # Failsafe
           analysis_data["error"] = f"Not enough data points ({len(closes)}) to calculate 20-day SMA for token_id {token_id}."
           return analysis_data
        analysis_data["sma20"] = statistics.mean(closes[-20:])
        analysis_data["sma50"] = statistics.mean(closes[-50:])

        # Determine signal and basic comparison
        price = analysis_data["current_price"]
        sma20 = analysis_data["sma20"]
        sma50 = analysis_data["sma50"]
        if price > sma20 and price > sma50:
            analysis_data["signal"] = "BUY"
            analysis_data["comparison"] = f"Current price (${price:.2f}) > SMA20 (${sma20:.2f}) and > SMA50 (${sma50:.2f})"
        elif price < sma20 and price < sma50:
            analysis_data["signal"] = "SELL"
            analysis_data["comparison"] = f"Current price (${price:.2f}) < SMA20 (${sma20:.2f}) and < SMA50 (${sma50:.2f})"
        else:
            analysis_data["signal"] = "NO_SIGNAL"
            analysis_data["comparison"] = f"Current price (${price:.2f}) is not consistently above or below both SMAs (SMA20=${sma20:.2f}, SMA50=${sma50:.2f})"

        logger.info(f"Calculated analysis data for {token_id}: {analysis_data}")
        return analysis_data

    except requests.exceptions.RequestException as e:
         analysis_data["error"] = f"API request failed for token_id {token_id}: {str(e)}"
         return analysis_data
    except statistics.StatisticsError as e:
         analysis_data["error"] = f"Calculation error for token_id {token_id}: {str(e)}"
         return analysis_data
    except Exception as e:
        logger.exception(f"Unexpected error analyzing token_id {token_id}: {str(e)}")
        analysis_data["error"] = f"Failed to analyze token_id {token_id}: An unexpected error occurred ({type(e).__name__})."
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
1. State the signal clearly (BUY, SELL, or NO SIGNAL).
2. Explain the reasoning based *only* on the provided comparison between the current price and the SMAs.
3. If the signal is BUY, mention it's generally considered a bullish sign suggesting potential upward momentum according to this strategy.
4. If the signal is SELL, mention it's generally considered a bearish sign suggesting potential downward momentum according to this strategy.
5. If the signal is NO SIGNAL, simply state the reasoning based on the comparison.
Do not add any information not present in the input data. Be factual and stick to the provided numbers and signal.

Explanation:"""
)

# --- LangGraph State ---
class AgentState(TypedDict):
    input: Dict[str, str] # Expects {"token_id": "...", "token_name": "..."}
    action: AgentAction | None
    analysis_data: Dict[str, Any] | None
    llm_reasoning: str | None
    intermediate_steps: Annotated[list[tuple[AgentAction, Dict[str, Any]]], operator.add]

# --- Nodes ---
def prepare_tool_call_node(state: AgentState):
    logger.info("--- Preparing Tool Call Node ---")
    input_data = state['input']
    token_id = input_data.get('token_id')
    token_name = input_data.get('token_name', 'Unknown Token') # Default name if missing
    logger.info(f"Input token_id: {token_id}, token_name: {token_name}")

    if not token_id:
        logger.error("Missing 'token_id' in input for prepare_tool_call_node")
        # How to handle this? Maybe raise error or return a state indicating failure?
        # For now, let's allow it to proceed but the tool call will likely fail.
        tool_input = {"token_id": None, "token_name": token_name} # Or handle error state
    else:
        tool_input = {"token_id": token_id, "token_name": token_name}

    action = AgentAction(tool="sma_analysis_calculator", tool_input=tool_input, log=f"Preparing SMA calculation for {token_name} ({token_id})")
    logger.info(f"Prepared action: {action}")
    return {"action": action}

def execute_tool_node(state: AgentState):
    logger.info("--- Executing Calculation Tool Node ---")
    action = state.get("action")
    logger.info(f"Action to execute: {action}")
    analysis_result_data = None
    error_message = None

    if not isinstance(action, AgentAction):
         logger.error(f"execute_tool_node received non-action: {action}")
         error_message = f"Error: execute_tool_node received non-action: {action}"
         analysis_result_data = {"error": error_message}
         return {"analysis_data": analysis_result_data, "intermediate_steps": [(action, analysis_result_data)]}

    try:
        output_dict = tool_executor.invoke(action)
        logger.info(f"Calculation tool raw output: {output_dict}")
        analysis_result_data = output_dict

        if isinstance(output_dict, dict) and output_dict.get("error"):
            logger.warning(f"SMA calculation tool reported an error: {output_dict['error']}")

    except Exception as e:
        logger.error(f"Error executing tool {action.tool}: {e}", exc_info=True)
        error_message = f"Error during tool execution {action.tool}: {str(e)}"
        analysis_result_data = {"error": error_message}

    return {"analysis_data": analysis_result_data, "intermediate_steps": [(action, analysis_result_data)]}

def generate_llm_reasoning_node(state: AgentState):
    logger.info("--- Generating LLM Reasoning Node ---")
    analysis_data = state.get("analysis_data")

    if not analysis_data:
        logger.error("No analysis data found in state for LLM reasoning.")
        return {"llm_reasoning": "Error: Analysis data was missing."}

    if analysis_data.get("error"):
        error_msg = analysis_data["error"]
        logger.warning(f"Skipping LLM reasoning due to previous error: {error_msg}")
        return {"llm_reasoning": f"Failed to generate analysis: {error_msg}"}

    required_keys = ["token_name", "current_price", "sma20", "sma50", "signal", "comparison"]
    if not all(key in analysis_data for key in required_keys):
        logger.error(f"Analysis data missing required keys for LLM prompt: {analysis_data}")
        missing_keys = [key for key in required_keys if key not in analysis_data]
        return {"llm_reasoning": f"Error: Analysis data incomplete, missing keys: {missing_keys}"}

    try:
        reasoning_chain = reasoning_prompt | llm
        logger.info(f"Invoking LLM with data: {analysis_data}")
        llm_response = reasoning_chain.invoke(analysis_data)

        if hasattr(llm_response, 'content'):
             reasoning_text = llm_response.content
        else:
             reasoning_text = str(llm_response)

        logger.info(f"LLM generated reasoning: {reasoning_text}")
        return {"llm_reasoning": reasoning_text.strip()}

    except Exception as e:
        logger.exception("Error invoking LLM for reasoning")
        return {"llm_reasoning": f"Error generating explanation: {str(e)}"}

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
