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

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix=f"{settings.API_V1_STR}/agents",
    tags=["agents"],
)

# Original AgentRequest (keep for other agents for now)
class AgentRequest(BaseModel):
    input: str

# Original AgentResponse (keep for other agents for now)
class AgentResponse(BaseModel):
    answer: str
    steps: List[Dict[str, Any]] | None = None
    error: str | None = None

# --- New Models for SMA Agent ---
class SMARequest(BaseModel):
    token_id: str
    token_name: Optional[str] = None # Keep token_name optional for now

class SMAResponse(BaseModel):
    analysis: str | None = None
    error: str | None = None
    steps: List[Dict[str, Any]] | None = None # Add steps field
# ------------------------------

# --- New Model for Bounce Hunter Agent ---
# class BounceHunterRequest(BaseModel): # Replaced by SMARequest
#     symbol: str

# ---------------------------------------

@router.post("/example_agent")
async def ask_example_agent(req: AgentRequest):
    # Placeholder for the existing example agent logic
    # You might want to implement this similarly if needed
    # For now, return a placeholder or raise NotImplementedError
    # raise NotImplementedError("Example agent endpoint is not implemented.")
    return {"message": "Example agent endpoint not fully implemented yet"}

# Update route to use new models and simplified logic
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
            "input_data_for_llm": analysis_data, # Show what LLM received
            "llm_output": llm_reasoning
        })
        # --- End Format Steps --- #

        # Extract the final result from 'llm_reasoning' key
        analysis_result_text = final_state.get("llm_reasoning")

        if analysis_result_text:
            # Check if the final text indicates an error occurred upstream
            # Errors from sma_analysis or LLM generation are passed into llm_reasoning
            if analysis_result_text.startswith("Error:") or \
               analysis_result_text.startswith("Failed to generate analysis:") or \
               analysis_result_text.startswith("Failed to analyze") or \
               analysis_result_text.startswith("Data format error") or \
               analysis_result_text.startswith("Insufficient data") or \
               analysis_result_text.startswith("No data found") or \
               analysis_result_text.startswith("API request failed") or \
               analysis_result_text.startswith("Calculation error"):
                logger.warning(f"Graph processing resulted in an error message: {analysis_result_text}")
                # Return error and steps
                return SMAResponse(analysis=None, error=analysis_result_text, steps=formatted_steps)
            else:
                # Return success and steps
                return SMAResponse(analysis=analysis_result_text, error=None, steps=formatted_steps)
        else:
            # Handle case where llm_reasoning key might be missing (should indicate a graph logic error)
            logger.error("Graph execution finished without 'llm_reasoning' in state.")
            # Return error and steps
            return SMAResponse(analysis=None, error="Graph execution failed to produce a final explanation.", steps=formatted_steps)

    except Exception as e:
        logger.exception("Unhandled error processing crypto_sma_agent request") # Log full traceback
        # Return error in the new response format (no steps available here)
        return SMAResponse(analysis=None, error=f"An unexpected server error occurred: {str(e)}", steps=None)

# Modified endpoint for Bounce Hunter
@router.post("/bounce_hunter_agent", response_model=SMAResponse) # Use SMAResponse model
async def ask_bounce_hunter_agent(req: SMARequest): # Use SMARequest
    # The agent graph now expects a dictionary input directly
    input_data = {"token_id": req.token_id, "token_name": req.token_name or "Unknown"}

    try:
        config = {"configurable": {"thread_id": str(uuid4())}}
        logger.info(f"Invoking bounce_hunter_agent graph with input: {input_data}")
        final_state = bounce_hunter_graph_app.invoke({"input": input_data}, config=config)
        logger.info(f"Bounce hunter graph final state: {final_state}")

        # --- Format Steps (Simplified for direct tool call) --- #
        formatted_steps = []
        intermediate_steps = final_state.get("intermediate_steps", [])
        analysis_result_text = final_state.get("analysis_result", "Error: Analysis result not found in final state.")

        # Check if the analysis_result itself indicates an error from the tool
        tool_error = None
        if isinstance(analysis_result_text, str) and \
           (analysis_result_text.startswith("Error:") or analysis_result_text.startswith("Failed to")):
            tool_error = analysis_result_text
            logger.warning(f"Bounce hunter tool reported an error: {tool_error}")

        # Log the steps (Preparation and Execution)
        step_count = 1
        if intermediate_steps:
            for action, observation in intermediate_steps:
                # Ensure action is AgentAction before trying to access attributes
                if isinstance(action, AgentAction):
                    formatted_steps.append({
                        "step": step_count,
                        "description": "Executing bounce hunter analysis tool", # Simplified description
                        "action": getattr(action, 'tool', 'unknown_tool'),
                        "action_input": getattr(action, 'tool_input', 'unknown_input'),
                        "observation": observation
                    })
                else:
                    # Log unexpected step format
                    formatted_steps.append({
                        "step": step_count,
                        "description": "Unexpected step format found",
                        "raw_step_data": (action, observation)
                    })
                step_count += 1
        else:
             # Log if no steps were recorded (might indicate issue in prepare node)
             formatted_steps.append({
                 "step": 1,
                 "description": "Intermediate steps not found in state"
             })
        # --- End Format Steps --- #

        # Return based on whether an error occurred
        if tool_error:
            return SMAResponse(analysis=None, error=tool_error, steps=formatted_steps)
        else:
            return SMAResponse(analysis=analysis_result_text, error=None, steps=formatted_steps)

    except Exception as e:
        logger.exception("Unhandled error processing bounce_hunter_agent request")
        return SMAResponse(analysis=None, error=f"An unexpected server error occurred: {str(e)}", steps=None)