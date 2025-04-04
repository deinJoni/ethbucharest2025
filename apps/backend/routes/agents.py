from fastapi import APIRouter, HTTPException
from langchain_core.agents import AgentFinish, AgentAction
from core.config import settings
from agents.exampleagent import app as example_app # Rename to avoid conflict
from pydantic import BaseModel
import logging
from uuid import uuid4 # Import uuid for thread_id generation
from typing import List, Dict, Any, Optional # Import List, Dict, Any, Optional
from agents.sma_agent import app as crypto_graph_app
from agents.bounce_hunter import app as bounce_hunter_graph_app
from agents.crypto_oracle import app as crypto_oracle_app
from agents.manager_agent import app as manager_agent_app # Import the new manager app
from agents.momentum_quant_agent import app as momentum_quant_app # Import the new momentum quant agent

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix=f"{settings.API_V1_STR}/agents",
    tags=["agents"],
)


# --- New Models for SMA Agent ---
class SMARequest(BaseModel):
    token_id: str
    token_name: Optional[str] = None # Keep token_name optional for now

class SMAResponse(BaseModel):
    signal: Optional[str] = None # BUY, SELL, HOLD (from analysis_data)
    llm_reasoning: Optional[str] = None # Detailed explanation
    error: Optional[str] = None
    steps: Optional[List[Dict[str, Any]]] = None

# --- New Models for Crypto Oracle Agent ---
class OracleRequest(BaseModel):
    token_id: str # Input token ID
    token_name: Optional[str] = None # Input token name (optional, like SMA agent)

# Use a similar response structure
class OracleResponse(BaseModel):
    signal: Optional[str] = None # BUY, SELL, HOLD (from analysis_data)
    llm_reasoning: Optional[str] = None # Detailed explanation
    error: Optional[str] = None
    steps: Optional[List[Dict[str, Any]]] = None

# --- New Models for Momentum Quant Agent ---
class MomentumQuantRequest(BaseModel):
    token_id: str # Only requires token_id
    token_name: Optional[str] = None # Add optional token_name

# Updated response model to include LLM reasoning
class MomentumQuantResponse(BaseModel):
    signal: Optional[str] = None # BUY, SELL, HOLD (from analysis_data)
    llm_reasoning: Optional[str] = None # Detailed explanation
    error: Optional[str] = None
    steps: Optional[List[Dict[str, Any]]] = None

# --- New Models for Manager Agent ---
class ManagerRequest(BaseModel):
    token_id: str
    token_name: Optional[str] = None # User can provide a name, otherwise defaults are used

class ManagerResponse(BaseModel):
    final_summary: Optional[str] = None
    final_signal: Optional[str] = None  # Manager's derived recommendation (BUY, SELL, HOLD)
    sma_analysis: Optional[str] = None
    sma_signal: Optional[str] = None  # SMA agent's signal
    bounce_analysis: Optional[str] = None
    bounce_signal: Optional[str] = None  # Bounce hunter's signal
    oracle_analysis: Optional[str] = None
    oracle_signal: Optional[str] = None  # Oracle agent's signal
    momentum_analysis: Optional[str] = None  # New field for momentum analysis
    momentum_signal: Optional[str] = None  # New field for momentum signal
    error: Optional[str] = None # For overall errors or summary of sub-errors

# Update route to use new models and simplified logic
@router.post("/crypto_sma_agent/", response_model=SMAResponse)
@router.post("/crypto_sma_agent", response_model=SMAResponse)
async def ask_crypto_sma_agent(req: SMARequest): # Use SMARequest
    try:
        config = {"configurable": {"thread_id": str(uuid4())}}
        # Correctly structure the input for the graph
        input_data = {"input": {"token_id": req.token_id, "token_name": req.token_name or "Unknown"}}
        logger.info(f"Invoking crypto_sma_agent graph with input: {input_data}")

        final_state = crypto_graph_app.invoke(input_data, config=config)
        logger.info(f"Graph final state: {final_state}")

        # --- Format Steps (Updated for new graph) --- #
        formatted_steps = []
        analysis_data = final_state.get("analysis_data", {})
        llm_reasoning = final_state.get("llm_reasoning", "")

        # Extract signal from analysis_data
        signal = analysis_data.get("signal", "NO_SIGNAL") # SMA agent uses "NO_SIGNAL" instead of "HOLD"
        # Map "NO_SIGNAL" to "HOLD" for consistency with other agents
        if signal == "NO_SIGNAL":
            signal = "HOLD"

        # Step 1: Preparation (using the input)
        formatted_steps.append({
            "step": 1,
            "description": "Preparing calculation tool call",
            "input_token_id": req.token_id
        })

        # Step 2: Execution (from intermediate_steps)
        intermediate_steps = final_state.get("intermediate_steps", [])
        tool_output_data = "Not found"
        if intermediate_steps:
            action, tool_output_data = intermediate_steps[0] # Should be the calculator output dict
            if isinstance(action, AgentAction):
                formatted_steps.append({
                    "step": 2,
                    "description": "Executing calculation tool",
                    "action": getattr(action, 'tool', 'unknown_tool'),
                    "action_input": getattr(action, 'tool_input', 'unknown_input'),
                    "observation": tool_output_data # Store the dict
                })
            else:
                 formatted_steps.append({
                    "step": 2,
                    "description": "Calculation step format unexpected",
                    "raw_step_data": intermediate_steps[0]
                 })
        else:
            formatted_steps.append({
                "step": 2,
                "description": "Calculation step not found in state"
            })

        # Step 3: LLM Reasoning Generation
        formatted_steps.append({
            "step": 3,
            "description": "Generating final explanation (LLM)",
            "input_data_for_llm": analysis_data.get("reasoning_components", {}), # Show what LLM received from reasoning_components
            "llm_output": llm_reasoning
        })
        # --- End Format Steps --- #

        # Extract the final result from 'llm_reasoning' key
        analysis_result_text = final_state.get("llm_reasoning")

        # Check for error in analysis_data
        overall_error = None
        if analysis_data and analysis_data.get("error"):
            # Get error from reasoning_components if available, otherwise use regular fields
            overall_error = analysis_data.get("reasoning_components", {}).get("error") or analysis_data.get("reason_string") or analysis_data.get("error")
            logger.warning(f"SMA analysis reported an error: {overall_error}")

        if analysis_result_text:
            # Check if the final text indicates an error occurred upstream or during LLM generation
            if analysis_result_text.startswith("Error:") or \
               analysis_result_text.startswith("Failed to generate analysis:") or \
               analysis_result_text.startswith("Failed to analyze") or \
               analysis_result_text.startswith("Data format error") or \
               analysis_result_text.startswith("Insufficient data") or \
               analysis_result_text.startswith("No data found") or \
               analysis_result_text.startswith("API request failed") or \
               analysis_result_text.startswith("Calculation error") or \
               analysis_result_text.startswith("Analysis Error"):
                # Prioritize LLM error message over tool error
                overall_error = analysis_result_text
                logger.warning(f"Graph processing resulted in an error message: {analysis_result_text}")
                # Return error and steps
                return SMAResponse(signal=None, llm_reasoning=None, error=overall_error, steps=formatted_steps)
            else:
                # Return success and steps
                return SMAResponse(signal=signal, llm_reasoning=analysis_result_text, error=None, steps=formatted_steps)
        else:
            # Handle case where llm_reasoning key might be missing (should indicate a graph logic error)
            logger.error("Graph execution finished without 'llm_reasoning' in state.")
            # Prioritize any pre-existing error, or use a default message
            error_message = overall_error or "Graph execution failed to produce a final explanation."
            # Return error and steps
            return SMAResponse(signal=None, llm_reasoning=None, error=error_message, steps=formatted_steps)

    except Exception as e:
        logger.exception("Unhandled error processing crypto_sma_agent request") # Log full traceback
        # Return error in the new response format (no steps available here)
        return SMAResponse(signal=None, llm_reasoning=None, error=f"An unexpected server error occurred: {str(e)}", steps=None)

# Modified endpoint for Bounce Hunter
@router.post("/bounce_hunter_agent/", response_model=SMAResponse)
@router.post("/bounce_hunter_agent", response_model=SMAResponse) # Use SMAResponse model
async def ask_bounce_hunter_agent(req: SMARequest): # Use SMARequest
    # The agent graph now expects a dictionary input directly
    input_data = {"token_id": req.token_id, "token_name": req.token_name or "Unknown"}

    try:
        config = {"configurable": {"thread_id": str(uuid4())}}
        logger.info(f"Invoking bounce_hunter_agent graph with input: {input_data}")
        final_state = bounce_hunter_graph_app.invoke({"input": input_data}, config=config)
        logger.info(f"Bounce hunter graph final state: {final_state}")

        # --- Format Steps (Updated for LLM step) --- #
        formatted_steps = []
        intermediate_steps = final_state.get("intermediate_steps", [])
        # Get the raw tool output and the final LLM analysis
        raw_tool_output = final_state.get("analysis_data", "Error: Raw tool analysis result not found.")
        final_llm_analysis = final_state.get("llm_reasoning", "Error: Final LLM analysis not found.")
        
        # Extract signal if available
        signal = None
        if isinstance(raw_tool_output, dict):
            signal = raw_tool_output.get("signal")

        # Check if the final_llm_analysis indicates an error occurred upstream or during LLM generation
        overall_error = None
        if isinstance(final_llm_analysis, str) and \
           (final_llm_analysis.startswith("Error:") or \
            final_llm_analysis.startswith("Failed") or # Catches "Failed to analyze..."
            final_llm_analysis.startswith("LLM Error:")):
            overall_error = final_llm_analysis
            logger.warning(f"Bounce hunter graph processing resulted in an error message: {overall_error}")
        elif not isinstance(final_llm_analysis, str): # Handle case where it might be None or unexpected type
             overall_error = "Error: Final analysis was not generated or had an unexpected format."
             logger.error(f"{overall_error} State value: {final_llm_analysis}")

        # Log the steps (Tool Execution)
        step_count = 1
        if intermediate_steps:
            # Assuming the first step is the tool execution based on the bounce_hunter graph
            action, observation = intermediate_steps[0]
            # Ensure action is AgentAction before trying to access attributes
            if isinstance(action, AgentAction):
                formatted_steps.append({
                    "step": step_count,
                    "description": "Executing bounce hunter analysis tool",
                    "action": getattr(action, 'tool', 'unknown_tool'),
                    "action_input": getattr(action, 'tool_input', 'unknown_input'),
                    "observation": observation # This is the raw_tool_output
                })
            else:
                # Log unexpected step format
                formatted_steps.append({
                    "step": step_count,
                    "description": "Unexpected tool execution step format found",
                    "raw_step_data": (action, observation)
                })
            step_count += 1
        else:
             # Log if no steps were recorded (might indicate issue in prepare node or early error)
             formatted_steps.append({
                 "step": 1,
                 "description": "Tool execution intermediate step not found in state"
             })
             step_count += 1 # Increment step count even if step not found

        # Add the LLM generation step
        formatted_steps.append({
            "step": step_count,
            "description": "Generating final summary (LLM)",
            "input_to_llm": raw_tool_output.get("reasoning_components", {}) if isinstance(raw_tool_output, dict) else raw_tool_output, # Show reasoning_components if available
            "llm_output": final_llm_analysis # Show the final analysis string from the LLM node
        })
        # --- End Format Steps --- #

        # Return based on whether an error occurred
        if overall_error:
            # Return the error message from final_llm_analysis as the error field
            return SMAResponse(signal=None, llm_reasoning=None, error=overall_error, steps=formatted_steps)
        else:
            # Return the successful final_llm_analysis as the llm_reasoning field
            return SMAResponse(signal=signal, llm_reasoning=final_llm_analysis, error=None, steps=formatted_steps)

    except Exception as e:
        logger.exception("Unhandled error processing bounce_hunter_agent request")
        # Return error in the response format
        return SMAResponse(signal=None, llm_reasoning=None, error=f"An unexpected server error occurred: {str(e)}", steps=None)

# New endpoint for Crypto Oracle Agent
@router.post("/crypto_oracle_agent/", response_model=OracleResponse)
@router.post("/crypto_oracle_agent", response_model=OracleResponse)
async def ask_crypto_oracle_agent(req: OracleRequest):
    # Construct input data matching the agent state
    input_data = {"token_id": req.token_id, "token_name": req.token_name or "Unknown"}

    try:
        config = {"configurable": {"thread_id": str(uuid4())}}
        logger.info(f"Invoking crypto_oracle_agent graph with input: {input_data}")
        # The graph expects the input under an "input" key
        final_state = crypto_oracle_app.invoke({"input": input_data}, config=config)
        logger.info(f"Crypto Oracle graph final state: {final_state}")

        # --- Format Steps (Similar to Bounce Hunter) --- #
        formatted_steps = []
        intermediate_steps = final_state.get("intermediate_steps", [])
        analysis_data = final_state.get("analysis_data", {})
        # Get the final explanation from the LLM reasoning node
        final_explanation = final_state.get("llm_reasoning", "Error: LLM explanation not found in final state.")
        
        # Extract signal if available
        signal = None
        if isinstance(analysis_data, dict):
            signal = analysis_data.get("signal")

        # Check if the final explanation itself indicates an error occurred upstream
        tool_or_llm_error = None
        # Errors from the tool or LLM generation are now passed into llm_reasoning
        if final_explanation.startswith("Analysis Error") or \
           final_explanation.startswith("Error: Analysis data not found") or \
           final_explanation.startswith("Error generating explanation"):
            tool_or_llm_error = final_explanation
            logger.warning(f"Crypto Oracle graph processing resulted in an error message: {tool_or_llm_error}")

        # Log the steps (now contains action and the dict result from the tool)
        step_count = 1
        if intermediate_steps:
            # intermediate_steps is list[tuple[AgentAction, Dict[str, Any]]]
            for action, observation_dict in intermediate_steps:
                # Ensure action is AgentAction before trying to access attributes
                if isinstance(action, AgentAction):
                    formatted_steps.append({
                        "step": step_count,
                        "description": "Executing crypto oracle analysis tool",
                        "action": getattr(action, 'tool', 'unknown_tool'),
                        "action_input": getattr(action, 'tool_input', 'unknown_input'),
                        "observation": observation_dict # Log the dictionary
                    })
                else:
                    # Handle unexpected step format (e.g., the dummy error action)
                    formatted_steps.append({
                        "step": step_count,
                        "description": "Unexpected step format or error",
                        "raw_step_data": (action, observation_dict)
                    })
                step_count += 1

        # Add the LLM reasoning step
        formatted_steps.append({
            "step": step_count,
            "description": "Generating final explanation (LLM)",
            "input_data_for_llm": analysis_data.get("reasoning_components", {}), # Show what LLM used from reasoning_components
            "llm_output": final_explanation
        })
        # --- End Format Steps --- #

        # Return based on whether an error occurred
        if tool_or_llm_error:
            # Return the error message from llm_reasoning as the error field
            return OracleResponse(signal=None, llm_reasoning=None, error=tool_or_llm_error, steps=formatted_steps)
        else:
            # Return the successful explanation as the llm_reasoning field and signal
            return OracleResponse(signal=signal, llm_reasoning=final_explanation, error=None, steps=formatted_steps)

    except Exception as e:
        logger.exception("Unhandled error processing crypto_oracle_agent request")
        return OracleResponse(signal=None, llm_reasoning=None, error=f"An unexpected server error occurred: {str(e)}", steps=None)

# --- New Endpoint for Momentum Quant Agent ---
@router.post("/momentum_quant_agent/", response_model=MomentumQuantResponse)
@router.post("/momentum_quant_agent", response_model=MomentumQuantResponse)
async def ask_momentum_quant_agent(req: MomentumQuantRequest):
    """
    Runs the Momentum Quant agent, which analyzes momentum and quant grade,
    and generates a detailed explanation.
    """
    # Include token_name in the input dict if provided
    input_data = {
        "token_id": req.token_id,
        "token_name": req.token_name or f"Token ID {req.token_id}" # Use ID as fallback name
    }
    logger.info(f"Received request for token_id: {req.token_id}, token_name: {req.token_name}")

    try:
        config = {"configurable": {"thread_id": str(uuid4())}}
        # Pass the full input_data dictionary to the agent
        logger.info(f"Invoking momentum_quant_agent graph with input: {input_data}")
        final_state = momentum_quant_app.invoke({"input": input_data}, config=config)
        logger.info(f"Momentum Quant graph final state: {final_state}")

        # --- Extract results from the new state structure --- #
        analysis_data = final_state.get("analysis_data")
        llm_reasoning = final_state.get("llm_reasoning")
        intermediate_steps = final_state.get("intermediate_steps", [])

        overall_error = None
        signal = None

        if isinstance(analysis_data, dict):
            signal = analysis_data.get("signal") # Extract signal from dict
            if analysis_data.get("error"):
                # Error reported by the tool/calculation step
                overall_error = analysis_data.get("reasoning_components", {}).get("error") or analysis_data.get("reason_string") or analysis_data.get("error")
                logger.warning(f"Momentum Quant analysis reported an error: {overall_error}")

        # Check if LLM reasoning itself indicates an error (e.g., LLM call failed)
        if isinstance(llm_reasoning, str) and llm_reasoning.startswith("Analysis Error"):
             overall_error = llm_reasoning # Prioritize LLM/graph error message
             logger.warning(f"Momentum Quant LLM reasoning reported an error: {overall_error}")
        elif llm_reasoning is None and overall_error is None:
             # If no error reported yet, but LLM is missing, flag it
             overall_error = "Error: LLM reasoning was not generated."
             logger.error(overall_error)

        # --- Format Steps (Updated for dictionary observation and reasoning_components) --- #
        formatted_steps = []
        step_count = 1
        # intermediate_steps is List[Tuple[AgentAction, Dict]]
        if intermediate_steps:
            for action, observation_dict in intermediate_steps:
                step_info = {
                    "step": step_count,
                    "description": "Executing momentum quant analysis tool",
                    "observation": observation_dict # The result dictionary
                }
                if isinstance(action, AgentAction):
                    step_info["action"] = getattr(action, 'tool', 'unknown_tool')
                    step_info["action_input"] = getattr(action, 'tool_input', 'unknown_input')
                else:
                    # Handle cases like the dummy error action
                    step_info["description"] = "Graph execution step (potential error)"
                    step_info["raw_action"] = action

                formatted_steps.append(step_info)
                step_count += 1

        # Step for LLM generation (if successful)
        if llm_reasoning and not overall_error:
             formatted_steps.append({
                "step": step_count,
                "description": "Generating final explanation (LLM)",
                "input_data_for_llm": analysis_data.get("reasoning_components", {}), # Show what LLM used from reasoning_components
                "llm_output": llm_reasoning
             })
        elif overall_error:
             # If there was an error, add a step indicating LLM was skipped or failed
             formatted_steps.append({
                 "step": step_count,
                 "description": "LLM Reasoning Step",
                 "status": "Skipped or Failed due to Error",
                 "error_details": overall_error
             })

        # --- End Format Steps --- #

        return MomentumQuantResponse(
            signal=signal, # Return signal from analysis_data
            llm_reasoning=llm_reasoning, # Return LLM explanation
            error=overall_error, # Return overall error if any
            steps=formatted_steps
        )

    except Exception as e:
        logger.exception("Unhandled error processing momentum_quant_agent request")
        return MomentumQuantResponse(
            signal=None,
            llm_reasoning=None,
            error=f"An unexpected server error occurred: {type(e).__name__} - {str(e)}",
            steps=None
        )

# --- New Endpoint for Manager Agent ---
@router.post("/analysis_manager/", response_model=ManagerResponse)
@router.post("/analysis_manager", response_model=ManagerResponse)
async def ask_analysis_manager(req: ManagerRequest):
    """
    Orchestrates analysis by running SMA, Bounce Hunter, and Crypto Oracle agents,
    then synthesizes their results into a final recommendation using an LLM.
    Returns the final summary and the individual agent results for transparency.
    """
    # Construct input data matching the agent state's 'input' key
    input_data = {"token_id": req.token_id, "token_name": req.token_name or "Unknown Token"}

    try:
        # Use a unique thread_id for the manager session
        config = {"configurable": {"thread_id": f"manager_{str(uuid4())}"}}
        logger.info(f"Invoking analysis_manager graph with input: {input_data}")

        # Invoke the manager graph asynchronously
        # The graph itself expects the input nested under the "input" key
        final_state = await manager_agent_app.ainvoke({"input": input_data}, config=config)
        logger.info(f"Analysis Manager graph final state received.")
        # logger.debug(f"Final state details: {final_state}") # For detailed debugging

        # Extract results from the final state
        final_summary = final_state.get("final_summary")
        final_signal = final_state.get("final_signal")  # Get the signal directly from the state
        sma_result = final_state.get("sma_result")
        bounce_result = final_state.get("bounce_result")
        oracle_result = final_state.get("oracle_result")
        momentum_result = final_state.get("momentum_result")
        sub_errors = final_state.get("error_messages", [])

        # Extract signals from each agent's analysis
        sma_signal = None
        bounce_signal = None
        oracle_signal = None
        momentum_signal = None

        # Extract signals from individual analyses
        # SMA
        if sma_result and isinstance(sma_result, str):
            sma_upper = sma_result.upper()
            # New pattern for SMA agent
            if "THE SIGNAL DETERMINED" in sma_upper and "IS SELL" in sma_upper:
                sma_signal = "SELL"
            elif "THE SIGNAL DETERMINED" in sma_upper and "IS BUY" in sma_upper:
                sma_signal = "BUY"
            elif "THE SIGNAL DETERMINED" in sma_upper and "IS NO SIGNAL" in sma_upper:
                sma_signal = "HOLD"
            # Original patterns
            elif "BUY SIGNAL" in sma_upper or "RECOMMENDATION: BUY" in sma_upper:
                sma_signal = "BUY"
            elif "SELL SIGNAL" in sma_upper or "RECOMMENDATION: SELL" in sma_upper:
                sma_signal = "SELL"
            elif "HOLD SIGNAL" in sma_upper or "RECOMMENDATION: HOLD" in sma_upper or "NO SIGNAL" in sma_upper:
                sma_signal = "HOLD"

        # Bounce Hunter
        if bounce_result and isinstance(bounce_result, str):
            bounce_upper = bounce_result.upper()
            # New pattern for Bounce Hunter agent
            if "THE SIGNAL DETERMINED" in bounce_upper and "IS SELL" in bounce_upper:
                bounce_signal = "SELL"
            elif "THE SIGNAL DETERMINED" in bounce_upper and "IS BUY" in bounce_upper:
                bounce_signal = "BUY"
            elif "THE SIGNAL DETERMINED" in bounce_upper and "IS HOLD" in bounce_upper or "THE SIGNAL DETERMINED" in bounce_upper and "IS NO SIGNAL" in bounce_upper:
                bounce_signal = "HOLD"
            # Original patterns
            elif "BUY SIGNAL" in bounce_upper or "RECOMMENDATION: BUY" in bounce_upper:
                bounce_signal = "BUY"
            elif "SELL SIGNAL" in bounce_upper or "RECOMMENDATION: SELL" in bounce_upper:
                bounce_signal = "SELL"
            elif "HOLD SIGNAL" in bounce_upper or "RECOMMENDATION: HOLD" in bounce_upper or "NO SIGNAL" in bounce_upper:
                bounce_signal = "HOLD"

        # Oracle
        if oracle_result and isinstance(oracle_result, str):
            oracle_upper = oracle_result.upper()
            # Look for explicit final recommendation
            if "THE SIGNAL DETERMINED FOR" in oracle_upper and "IS SELL" in oracle_upper:
                oracle_signal = "SELL"
            elif "THE SIGNAL DETERMINED FOR" in oracle_upper and "IS BUY" in oracle_upper:
                oracle_signal = "BUY"
            elif "THE SIGNAL DETERMINED FOR" in oracle_upper and "IS HOLD" in oracle_upper or "THE SIGNAL DETERMINED FOR" in oracle_upper and "IS NO SIGNAL" in oracle_upper:
                oracle_signal = "HOLD"
            # Look for signal in quote marks or after "signal:"
            elif "**SELL**" in oracle_upper or "SIGNAL: **SELL**" in oracle_upper or "SIGNAL IS **SELL**" in oracle_upper:
                oracle_signal = "SELL"
            elif "**BUY**" in oracle_upper or "SIGNAL: **BUY**" in oracle_upper or "SIGNAL IS **BUY**" in oracle_upper:
                oracle_signal = "BUY"
            elif "**HOLD**" in oracle_upper or "SIGNAL: **HOLD**" in oracle_upper or "SIGNAL IS **HOLD**" in oracle_upper:
                oracle_signal = "HOLD"
            # Original patterns but with more context to avoid false positives
            elif (" BUY SIGNAL" in oracle_upper or "RECOMMENDATION: BUY" in oracle_upper) and not "NOT SATISFY" in oracle_upper and not "NOT MEET" in oracle_upper:
                oracle_signal = "BUY"
            elif (" SELL SIGNAL" in oracle_upper or "RECOMMENDATION: SELL" in oracle_upper) and not "NOT SATISFY" in oracle_upper and not "NOT MEET" in oracle_upper:
                oracle_signal = "SELL"
            elif (" HOLD SIGNAL" in oracle_upper or "RECOMMENDATION: HOLD" in oracle_upper or " NO SIGNAL" in oracle_upper):
                oracle_signal = "HOLD"
            # Final fallback - look for dominant signals
            elif oracle_upper.count("SELL") > oracle_upper.count("BUY") and oracle_upper.count("SELL") > oracle_upper.count("HOLD"):
                oracle_signal = "SELL"
            elif oracle_upper.count("BUY") > oracle_upper.count("SELL") and oracle_upper.count("BUY") > oracle_upper.count("HOLD"):
                oracle_signal = "BUY"
            elif oracle_upper.count("HOLD") > oracle_upper.count("SELL") and oracle_upper.count("HOLD") > oracle_upper.count("BUY"):
                oracle_signal = "HOLD"

        # Momentum
        if momentum_result and isinstance(momentum_result, str):
            momentum_upper = momentum_result.upper()
            # Look for explicit final recommendation
            if "THE SIGNAL DETERMINED FOR" in momentum_upper and "IS SELL" in momentum_upper:
                momentum_signal = "SELL"
            elif "THE SIGNAL DETERMINED FOR" in momentum_upper and "IS BUY" in momentum_upper:
                momentum_signal = "BUY"
            elif "THE SIGNAL DETERMINED FOR" in momentum_upper and "IS HOLD" in momentum_upper or "THE SIGNAL DETERMINED FOR" in momentum_upper and "IS NO SIGNAL" in momentum_upper:
                momentum_signal = "HOLD"
            # Look for signal at start of analysis
            elif momentum_upper.strip().startswith("THE HOLD SIGNAL FOR"):
                momentum_signal = "HOLD"
            elif momentum_upper.strip().startswith("THE BUY SIGNAL FOR"):
                momentum_signal = "BUY"
            elif momentum_upper.strip().startswith("THE SELL SIGNAL FOR"):
                momentum_signal = "SELL"
            # Original patterns but with more context to avoid false positives
            elif (" BUY SIGNAL" in momentum_upper or "RECOMMENDATION: BUY" in momentum_upper) and not "NOT SATISFY" in momentum_upper and not "NOT MEET" in momentum_upper:
                momentum_signal = "BUY"
            elif (" SELL SIGNAL" in momentum_upper or "RECOMMENDATION: SELL" in momentum_upper) and not "NOT SATISFY" in momentum_upper and not "NOT MEET" in momentum_upper:
                momentum_signal = "SELL"
            elif (" HOLD SIGNAL" in momentum_upper or "RECOMMENDATION: HOLD" in momentum_upper or " NO SIGNAL" in momentum_upper):
                momentum_signal = "HOLD"
            # Final fallback - look for dominant signals
            elif momentum_upper.count("SELL") > momentum_upper.count("BUY") and momentum_upper.count("SELL") > momentum_upper.count("HOLD"):
                momentum_signal = "SELL"
            elif momentum_upper.count("BUY") > momentum_upper.count("SELL") and momentum_upper.count("BUY") > momentum_upper.count("HOLD"):
                momentum_signal = "BUY"
            elif momentum_upper.count("HOLD") > momentum_upper.count("SELL") and momentum_upper.count("HOLD") > momentum_upper.count("BUY"):
                momentum_signal = "HOLD"

        overall_error = None
        # Report errors if any sub-agents failed or synthesis failed
        if sub_errors:
            error_summary = f"One or more sub-analyses encountered errors: {'; '.join(sub_errors)}"
            overall_error = error_summary
            logger.warning(f"Manager analysis finished with errors: {error_summary}")
        # Check if the final summary itself indicates a synthesis failure
        if final_summary and (final_summary.startswith("Error during final synthesis:") or final_summary.startswith("Analysis halted")):
             overall_error = final_summary # Prioritize synthesis/halt error message

        # Return the structured response
        return ManagerResponse(
            final_summary=final_summary,
            final_signal=final_signal,
            sma_analysis=sma_result,
            sma_signal=sma_signal,
            bounce_analysis=bounce_result,
            bounce_signal=bounce_signal,
            oracle_analysis=oracle_result,
            oracle_signal=oracle_signal,
            momentum_analysis=momentum_result,
            momentum_signal=momentum_signal,
            error=overall_error
        )

    except Exception as e:
        logger.exception("Unhandled error processing analysis_manager request")
        # Return a server error response
        return ManagerResponse(
            error=f"An unexpected server error occurred during manager execution: {type(e).__name__} - {str(e)}"
        )