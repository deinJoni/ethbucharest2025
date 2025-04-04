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

        # --- Placeholder Data ---
        # TODO: Fetch current price from OHLCV endpoint or other real-time source
        current_price = 2950.00 # Dummy data for ETH
        # --- End Placeholder Data ---

        # --- Fetch Historical Levels from Token Metrics API ---
        api_key = settings.TOKEN_METRICS_API_KEY
        if not api_key or api_key == "YOUR_TOKEN_METRICS_API_KEY": # Basic check
             logger.error("Token Metrics API key not configured.")
             # Use cleaned symbol in error message
             return f"Failed to analyze {symbol_cleaned}: Token Metrics API key missing."

        # Use the provided token_id directly, no mapping needed
        # Use cleaned symbol for the 'symbol' parameter in the URL
        url = f"https://api.tokenmetrics.com/v2/resistance-support?token_id={token_id}&limit=100&page=0"
        headers = {
            "accept": "application/json",
            "api_key": api_key
        }

        historical_levels = []
        try:
            response = requests.get(url, headers=headers, timeout=10) # Added timeout
            print(f"Response: {response}")
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            response_data = response.json()
            print(f"Response Data: {response_data}")

            if response_data.get("success") and response_data.get("data"):
                # Since we query by token_id, the list should contain only our token.
                # Take the first item directly instead of filtering by symbol.
                if response_data["data"]:
                    token_data = response_data["data"][0]
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
                logger.error(f"Token Metrics API call failed or returned no data for {symbol_cleaned} (ID: {token_id}). Message: {response_data.get('message')}")
                return f"Failed to fetch data for {symbol_cleaned} from Token Metrics: {response_data.get('message', 'Unknown API error')}"

        except requests.exceptions.RequestException as e:
            logger.exception(f"Error fetching data from Token Metrics for {symbol_cleaned} (ID: {token_id}): {e}")
            return f"Failed to analyze {symbol_cleaned}: Could not connect to Token Metrics API ({type(e).__name__})."
        except (ValueError, KeyError) as e: # Handle JSON parsing or key errors
             logger.exception(f"Error processing Token Metrics response for {symbol_cleaned} (ID: {token_id}): {e}")
             return f"Failed to analyze {symbol_cleaned}: Invalid data format received from Token Metrics ({type(e).__name__})."
        # --- End API Fetch ---

        # Check if historical_levels were successfully populated (token_data was found and valid)
        if not historical_levels:
            # The warning about "No data found for symbol..." is removed as we don't filter by symbol now
            # If levels list is empty, it means either token_data was None or HISTORICAL_RESISTANCE_SUPPORT_LEVELS was missing/empty
            logger.warning(f"Could not extract historical levels for {symbol_cleaned} (ID: {token_id}) from Token Metrics response.")
            return f"{symbol_cleaned}: No historical support/resistance levels found or extracted via Token Metrics."

        nearby_signals = []
        for level_data in historical_levels:
            level = level_data["level"]
            level_date = level_data["date"]
            price_diff = abs(current_price - level)
            proximity_percent = (price_diff / level) if level != 0 else 0

            if proximity_percent <= PROXIMITY_THRESHOLD:
                distance_str = f"${price_diff:.2f} ({proximity_percent:.2%})"
                if current_price > level:
                    signal = "Bounce Watch"
                    signal_desc = f"{signal} (Price above support {level:.2f} from {level_date}, Distance: {distance_str})"
                else: # current_price <= level
                    signal = "Breakout Watch"
                    signal_desc = f"{signal} (Price below resistance {level:.2f} from {level_date}, Distance: {distance_str})"
                nearby_signals.append(signal_desc)

        if not nearby_signals:
            result = f"{symbol_cleaned}: Current Price=${current_price:.2f}. No nearby key levels within {PROXIMITY_THRESHOLD:.1%} — no signal."
        else:
            signals_formatted = "\n".join(f"- {s}" for s in nearby_signals)
            result = f"{symbol_cleaned}: Current Price=${current_price:.2f}.\nNearby Key Levels & Signals:\n{signals_formatted}"

        logger.info(f"Bounce hunter analysis result for {symbol_cleaned}: {result}")
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
