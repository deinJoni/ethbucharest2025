import logging
from typing import TypedDict, Annotated, Dict, Any
import operator
from datetime import datetime
from uuid import uuid4
import requests

from langchain_openai import ChatOpenAI # Keep for potential future use? Or remove? Let's remove for now.
# from langchain.agents import Tool, create_react_agent # Remove ReAct
from langchain.tools import StructuredTool # Use StructuredTool
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolExecutor
from langgraph.checkpoint.memory import MemorySaver
# from langchain.prompts import PromptTemplate # Remove ReAct Prompt
from langchain_core.agents import AgentAction # Keep for state/nodes
from core.config import settings

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# --- Configuration ---
PROXIMITY_THRESHOLD = 0.05 # 5%

# --- Bounce Hunter Tool ---
# Modified to accept token_id and symbol directly
def bounce_hunter_analysis(token_id: str, symbol: str) -> str:
    """
    Analyzes if a crypto token's current price is near historical support or resistance levels.
    Requires the token ID (e.g., 3306) and symbol (e.g., 'ETH').
    Fetches current price and historical levels from Token Metrics API using the token_id.
    Uses the symbol for the API call parameter and filtering results.
    Compares price to levels within a configurable threshold (5%).
    Flags 'Bounce Watch' if price is above a nearby level (support).
    Flags 'Breakout Watch' if price is below a nearby level (resistance).
    """
    try:
        # Clean the input symbol (used for API param and filtering)
        symbol_cleaned = symbol.strip().upper()
        logger.info(f"Starting bounce hunter analysis for symbol: '{symbol_cleaned}' (using token_id: {token_id})")

        # --- Fetch API Key ---
        api_key = settings.TOKEN_METRICS_API_KEY
        if not api_key or api_key == "YOUR_TOKEN_METRICS_API_KEY": # Basic check
             logger.error("Token Metrics API key not configured.")
             return f"Failed to analyze {symbol_cleaned}: Token Metrics API key missing."

        headers = {
            "accept": "application/json",
            "api_key": api_key
        }

        # --- Fetch Current Price from Token Metrics API ---
        current_price = None
        price_url = f"https://api.tokenmetrics.com/v2/price?token_id={token_id}"
        try:
            logger.info(f"Fetching current price for {symbol_cleaned} (ID: {token_id}) from {price_url}")
            price_response = requests.get(price_url, headers=headers, timeout=10)
            price_response.raise_for_status()
            price_data = price_response.json()

            if price_data.get("success") and price_data.get("data"):
                if price_data["data"]:
                    # Assuming the first item in the data list corresponds to the token_id
                    token_price_info = price_data["data"][0]
                    if token_price_info.get("TOKEN_ID") == int(token_id): # Verify token ID match
                        current_price = token_price_info.get("CURRENT_PRICE")
                        if current_price is not None:
                            current_price = float(current_price) # Ensure it's a float
                            logger.info(f"Successfully fetched current price for {symbol_cleaned} (ID: {token_id}): {current_price}")
                        else:
                            logger.error(f"CURRENT_PRICE field missing in Token Metrics price response for {symbol_cleaned} (ID: {token_id}).")
                    else:
                        logger.error(f"Token ID mismatch in price response. Expected {token_id}, got {token_price_info.get('TOKEN_ID')}")
                else:
                     logger.error(f"Token Metrics price response data list is empty for {symbol_cleaned} (ID: {token_id}).")
            else:
                logger.error(f"Token Metrics price API call failed or returned no data for {symbol_cleaned} (ID: {token_id}). Message: {price_data.get('message')}")

        except requests.exceptions.RequestException as e:
            logger.exception(f"Error fetching current price from Token Metrics for {symbol_cleaned} (ID: {token_id}): {e}")
            # Decide how to handle price fetch failure: return error or continue without price? Returning error is safer.
            return f"Failed to analyze {symbol_cleaned}: Could not fetch current price from Token Metrics ({type(e).__name__})."
        except (ValueError, KeyError, TypeError) as e: # Handle JSON parsing, key errors, or type conversion issues
             logger.exception(f"Error processing Token Metrics price response for {symbol_cleaned} (ID: {token_id}): {e}")
             return f"Failed to analyze {symbol_cleaned}: Invalid price data format received from Token Metrics ({type(e).__name__})."

        # Check if current_price was successfully obtained before proceeding
        if current_price is None:
            # If price fetch failed for any reason noted above, return an error message.
            return f"Failed to analyze {symbol_cleaned}: Could not determine current price from Token Metrics."

        # --- Fetch Historical Levels from Token Metrics API ---
        # Use the provided token_id directly, no mapping needed
        # Use cleaned symbol for the 'symbol' parameter in the URL (though maybe not needed if endpoint ignores it?)
        levels_url = f"https://api.tokenmetrics.com/v2/resistance-support?token_id={token_id}&limit=100&page=0"
        # headers are already defined above

        historical_levels = []
        try:
            logger.info(f"Fetching historical levels for {symbol_cleaned} (ID: {token_id}) from {levels_url}")
            levels_response = requests.get(levels_url, headers=headers, timeout=10) # Added timeout
            # print(f"Response: {levels_response}") # Debug print
            levels_response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            levels_response_data = levels_response.json()
            # print(f"Response Data: {levels_response_data}") # Debug print

            if levels_response_data.get("success") and levels_response_data.get("data"):
                # Since we query by token_id, the list should contain only our token.
                # Take the first item directly instead of filtering by symbol.
                if levels_response_data["data"]:
                    token_data = levels_response_data["data"][0]
                    # Optional: Verify the symbol if needed, though filtering is removed.
                    # actual_symbol = token_data.get("TOKEN_SYMBOL")
                    # if actual_symbol != symbol_cleaned:
                    #    logger.warning(f"Symbol mismatch: Input gave '{symbol_cleaned}', API returned '{actual_symbol}'")

                    raw_levels = token_data.get("HISTORICAL_RESISTANCE_SUPPORT_LEVELS", [])
                    historical_levels = [{"level": float(lvl["level"]), "date": lvl["date"]} for lvl in raw_levels if "level" in lvl and "date" in lvl]
                    logger.info(f"Successfully fetched {len(historical_levels)} levels for {symbol_cleaned} (ID: {token_id}) from Token Metrics.")
                else:
                    # This case means success=True, data is present, but the list is empty - unlikely
                    logger.warning(f"Token Metrics response indicated success but data list was empty for {symbol_cleaned} (ID: {token_id}).")
                    token_data = None # Ensure token_data is None
            else:
                logger.error(f"Token Metrics API call failed or returned no data for {symbol_cleaned} (ID: {token_id}). Message: {levels_response_data.get('message')}")
                return f"Failed to fetch data for {symbol_cleaned} from Token Metrics: {levels_response_data.get('message', 'Unknown API error')}"

        except requests.exceptions.RequestException as e:
            logger.exception(f"Error fetching data from Token Metrics for {symbol_cleaned} (ID: {token_id}): {e}")
            return f"Failed to analyze {symbol_cleaned}: Could not connect to Token Metrics API ({type(e).__name__})."
        except (ValueError, KeyError) as e: # Handle JSON parsing or key errors
             logger.exception(f"Error processing Token Metrics response for {symbol_cleaned} (ID: {token_id}): {e}")
             return f"Failed to analyze {symbol_cleaned}: Invalid data format received from Token Metrics ({type(e).__name__})."
        # --- End API Fetch ---

        # Check if historical_levels were successfully populated (token_data was found and valid)
        if not historical_levels:
            logger.warning(f"Could not extract historical levels for {symbol_cleaned} (ID: {token_id}) from Token Metrics response.")
            # Return HOLD if no levels are found
            return f"Decision: HOLD — Reason: No historical support/resistance levels found or extracted for {symbol_cleaned} (ID: {token_id}) via Token Metrics."

        # --- Decision Logic ---
        decision = "HOLD" # Default decision
        reason = f"Price (${current_price:.2f}) is not within {PROXIMITY_THRESHOLD:.1%} of any known historical support/resistance levels."

        # Sort levels by proximity to potentially prioritize the closest?
        # Or just take the first signal found? Let's take the first signal for now.
        for level_data in historical_levels:
            level = level_data["level"]
            level_date = level_data["date"]
            price_diff = abs(current_price - level)
            proximity_percent = (price_diff / level) if level != 0 else float('inf') # Avoid division by zero

            if proximity_percent <= PROXIMITY_THRESHOLD:
                distance_str = f"${price_diff:.2f} ({proximity_percent:.2%})"
                if current_price > level:
                    # Price is above a nearby level (Support) -> BUY signal
                    decision = "BUY"
                    reason = f"Price (${current_price:.2f}) is within {proximity_percent:.2%} above support level {level:.2f} (from {level_date}). Expecting a bounce."
                    logger.info(f"BUY signal triggered for {symbol_cleaned} near support level {level:.2f}")
                    break # Stop after finding the first significant level signal
                else: # current_price <= level
                    # Price is below a nearby level (Resistance) -> SELL signal
                    decision = "SELL"
                    reason = f"Price (${current_price:.2f}) is within {proximity_percent:.2%} below resistance level {level:.2f} (from {level_date}). Expecting rejection."
                    logger.info(f"SELL signal triggered for {symbol_cleaned} near resistance level {level:.2f}")
                    break # Stop after finding the first significant level signal

        # Format the final output
        result = f"Decision: {decision} — Reason: {reason}"

        logger.info(f"Bounce hunter analysis result for {symbol_cleaned} (ID: {token_id}): {result}")
        return result

    except Exception as e:
        # Log original symbol in case cleaning caused issues upstream
        logger.exception(f"Error during bounce hunter analysis for symbol '{symbol}' (token_id: {token_id}): {str(e)}")
        # Use cleaned symbol in user-facing error
        return f"Failed to analyze {symbol.strip().upper()} for bounce/breakout: An unexpected error occurred ({type(e).__name__})."

# --- Tool & LLM ---
# Use StructuredTool as function takes multiple args
bounce_hunter_tool = StructuredTool.from_function(
    func=bounce_hunter_analysis,
    name="bounce_hunter_analysis",
    description=(
        "Analyzes if a token's current price is near historical support or resistance levels (within 5% proximity) "
        "using its Token Metrics ID (token_id) and symbol. Flags potential bounces or breakouts. "
        "Returns a string analysis."
    ),
    # args_schema=... # Optional: Define Pydantic model for args if needed for validation
)

tool_executor = ToolExecutor([bounce_hunter_tool])

# Remove LLM used for ReAct agent decisions
# llm = ChatOpenAI(...)

# Remove ReAct Prompt
# prompt = PromptTemplate.from_template(...)

# Remove ReAct runnable
# agent_runnable = create_react_agent(...)

# --- LangGraph State ---
# Modified state to match sma_agent structure (input dict, explicit action, result)
class AgentState(TypedDict):
    input: Dict[str, str] # Expects {"token_id": "...", "token_name": "..."}
    action: AgentAction | None # Action prepared for the tool
    analysis_result: str | None # String result from the tool
    # Remove ReAct specific state keys
    # agent_decision: AgentAction | AgentFinish | None
    intermediate_steps: Annotated[list[tuple[AgentAction, str]], operator.add] # Keep for logging/tracing if needed

# --- Nodes ---
# New node to prepare tool call, similar to sma_agent
def prepare_tool_call_node(state: AgentState):
    logger.info("--- Bounce Hunter: Preparing Tool Call Node ---")
    input_data = state['input']
    token_id = input_data.get('token_id')
    # Use token_name as the basis for the symbol, default if missing
    # The bounce_hunter_analysis tool needs *a* symbol, even if just for the API param.
    # Assuming token_name can be used as symbol (e.g., "Ethereum" or "ETH")
    symbol = input_data.get('token_name', 'UnknownSymbol')
    logger.info(f"Input token_id: {token_id}, derived symbol: {symbol}")

    if not token_id:
        logger.error("Missing 'token_id' in input for prepare_tool_call_node")
        # Handle error state: Set result directly to prevent tool call
        return {"analysis_result": "Error: Missing 'token_id' in input."}

    # Prepare tool input dictionary matching bounce_hunter_analysis args
    tool_input = {"token_id": token_id, "symbol": symbol}

    action = AgentAction(
        tool="bounce_hunter_analysis",
        tool_input=tool_input,
        log=f"Preparing bounce hunter analysis for {symbol} (ID: {token_id})"
    )
    logger.info(f"Prepared action: {action}")
    # Initialize intermediate_steps if it doesn't exist
    return {"action": action, "intermediate_steps": []}


# Modified execute_tool_node for structured tool and new state
def execute_tool_node(state: AgentState):
    logger.info("--- Bounce Hunter: Executing Tool Node ---")
    action = state.get("action")
    analysis_result = None
    error_occurred = False

    if not isinstance(action, AgentAction):
        logger.error(f"execute_tool_node received non-action: {action}")
        analysis_result = f"Error: Tool execution step received invalid action state: {action}"
        error_occurred = True
        action = AgentAction(tool="error", tool_input={}, log=analysis_result) # Dummy action for logging
    else:
        logger.info(f"Executing tool: {action.tool} with input {action.tool_input}")
        try:
            # Execute the tool and get the output string
            output_str = tool_executor.invoke(action)
            logger.info(f"Tool output string: {output_str}")
            analysis_result = output_str
        except Exception as e:
            logger.exception(f"Error executing tool {action.tool}: {e}")
            analysis_result = f"Error executing tool {action.tool}: {str(e)}"
            error_occurred = True

    # Store result and log the step
    intermediate_steps = state.get("intermediate_steps", [])
    intermediate_steps.append((action, analysis_result))

    return {"analysis_result": analysis_result, "intermediate_steps": intermediate_steps}


# Remove ReAct specific nodes
# def run_agent_node(state: AgentState): ...
# def should_continue_edge(state: AgentState): ...

# --- Build Graph ---
workflow = StateGraph(AgentState)

# Add the nodes to the graph
workflow.add_node("prepare_tool_call_node", prepare_tool_call_node)
workflow.add_node("execute_tool_node", execute_tool_node)

# Set the entry point
workflow.set_entry_point("prepare_tool_call_node")

# Define the linear graph flow
workflow.add_edge("prepare_tool_call_node", "execute_tool_node")
workflow.add_edge("execute_tool_node", END) # End after tool execution

# --- Memory & Compile ---
memory = MemorySaver()
app = workflow.compile(checkpointer=memory)

# --- Manual Test ---
# Updated test block for new structure
if __name__ == "__main__":
    print("--- Testing Bounce Hunter Agent (Structured Flow) ---")
    config = {"configurable": {"thread_id": str(uuid4())}}
    # Define the user input for the agent (dictionary)
    token_id_to_test = "3306" # Example Token ID for ETH on Token Metrics
    # Test with both 'Ethereum' and 'ETH' as potential token_name inputs
    # token_name_to_test = "Ethereum"
    token_name_to_test = "ETH"
    test_input = {"token_id": token_id_to_test, "token_name": token_name_to_test}

    print(f"Invoking agent with input: {test_input} and config: {config}")

    try:
        # Execute the agent graph with the input dictionary
        result_state = app.invoke({"input": test_input}, config=config)

        print("\n--- Agent Execution Result State ---")
        print(result_state)

        # Extract the final analysis result from the state
        final_output = result_state.get("analysis_result", "No analysis result found in state.")

        print("\n--- Final Analysis Result ---")
        print(final_output)

    except Exception as e:
        # Catch any exceptions during the invocation
        print(f"\n--- Error during agent execution ---")
        logger.exception("Agent invocation failed in main block")
        print(f"Error: {e}")

    print("\n--- Test Complete ---")
