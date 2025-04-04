# apps/backend/agents/manager_agent.py
import logging
import asyncio
from typing import TypedDict, Annotated, Dict, Any, List, Optional
import operator
from uuid import uuid4

from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

# Import the compiled apps from the other agents
from .sma_agent import app as sma_app
from .bounce_hunter import app as bounce_hunter_app
from .crypto_oracle import app as crypto_oracle_app
from .momentum_quant_agent import app as momentum_quant_app
from core.config import settings

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# --- LLM for Final Synthesis ---
llm = ChatOpenAI(
    temperature=0.1,
    api_key=settings.OPENAI_API_KEY,
    model="gpt-4-0125-preview" # Or your preferred model
)

# --- Synthesis Prompt ---
synthesis_prompt = PromptTemplate.from_template(
    """You are a senior financial analyst synthesizing analyses from specialist agents for {token_name} (ID: {token_id}). Provide a final recommendation (Strong Buy, Buy, Hold, Sell, Strong Sell) based on their insights and your own expertise.

**Agent Analyses:**

1.  **SMA Crossover Analysis:**
    *   Result: {sma_result}

2.  **Bounce Hunter Analysis (Support/Resistance):**
    *   Result: {bounce_result}

3.  **Crypto Oracle Analysis (Trader Grade & Momentum):**
    *   Result: {oracle_result}

4.  **Momentum Quant Analysis (Trader Grade % Change & Quant Grade):**
    *   Result: {momentum_result}

**Your Task:**

1.  **Summarize:** Briefly state the signal/key finding from each agent.
2.  **Compare:** Note agreements or disagreements in signals/reasoning.
3.  **Synthesize:** Weigh the evidence. Do signals reinforce or conflict?
4.  **Form Your Opinion:** Using your expertise, add your own assessment of {token_name}'s outlook.
5.  **Conclude:** State your final recommendation (Strong Buy, Buy, Hold, Sell, Strong Sell).
6.  **Explain:** Justify your recommendation by referencing specific findings about {token_name} and how they collectively support your conclusion. Address any conflicting signals and your reasoning for weighing them.

Your response MUST include a clear final signal in this format at the end:
"FINAL RECOMMENDATION: [Strong Buy/Buy/Hold/Sell/Strong Sell]"

**Final Synthesized Analysis for {token_name}:**
"""
)

# --- LangGraph State ---
class ManagerAgentState(TypedDict):
    input: Dict[str, str] # {"token_id": "...", "token_name": "..."}
    sma_result: Optional[str]
    bounce_result: Optional[str]
    oracle_result: Optional[str]
    momentum_result: Optional[str]
    error_messages: List[str] # Collect errors from sub-agents
    final_summary: Optional[str]
    final_signal: Optional[str] # Added field to store the final signal

# --- Nodes ---

# Helper Function to invoke a sub-agent asynchronously
async def invoke_sub_agent(agent_app, input_data: Dict[str, Any], agent_name: str) -> str:
    """Invokes a sub-agent graph and returns its final analysis string or an error message."""
    logger.info(f"--- Manager: Invoking {agent_name} ---")
    
    max_retries = 3
    retry_count = 0
    retry_delay = 2  # Initial delay in seconds
    
    while retry_count < max_retries:
        try:
            if retry_count > 0:
                logger.info(f"--- Manager: Retry #{retry_count} for {agent_name} ---")
                
            # Use a unique thread_id for each sub-invocation
            config = {"configurable": {"thread_id": f"sub_{agent_name}_{str(uuid4())}"}}
            # Prepare input for the sub-agent
            sub_input = {"input": input_data}
            final_state = await agent_app.ainvoke(sub_input, config=config)

            # Extract result based on the agent's known output key
            if agent_name == "sma_agent":
                result = final_state.get("llm_reasoning")
            elif agent_name == "bounce_hunter_agent":
                result = final_state.get("llm_reasoning")
            elif agent_name == "crypto_oracle_agent":
                result = final_state.get("llm_reasoning")
            elif agent_name == "momentum_quant_agent":
                # Try multiple potential keys for momentum agent
                result = None
                potential_keys = ["llm_reasoning", "final_analysis", "analysis_result", "result", "explanation"]
                for key in potential_keys:
                    if key in final_state and isinstance(final_state[key], str):
                        result = final_state[key]
                        logger.info(f"Found momentum result in key: {key}")
                        break
                
                # If still not found, check if there's any dict with a text/string result
                if result is None:
                    for key, value in final_state.items():
                        if isinstance(value, dict) and "result" in value and isinstance(value["result"], str):
                            result = value["result"]
                            logger.info(f"Found momentum result in nested dict: {key}.result")
                            break
                
                # Last resort: try to extract and summarize from analysis_data if available
                if result is None and "analysis_data" in final_state:
                    analysis_data = final_state["analysis_data"]
                    if isinstance(analysis_data, dict):
                        # Try to create a basic summary from the analysis data
                        summary_parts = []
                        
                        # Signal
                        if "signal" in analysis_data:
                            summary_parts.append(f"Signal: {analysis_data['signal']}")
                        
                        # Trader grade
                        if "trader_grade" in analysis_data:
                            summary_parts.append(f"Trader Grade: {analysis_data['trader_grade']}")
                        
                        # Percent change
                        if "percent_change" in analysis_data:
                            summary_parts.append(f"Percent Change: {analysis_data['percent_change']}%")
                            
                        # Quant grade
                        if "quant_grade" in analysis_data:
                            summary_parts.append(f"Quant Grade: {analysis_data['quant_grade']}")
                            
                        # Additional metrics
                        for key in ["momentum", "volatility", "trend", "volume"]:
                            if key in analysis_data:
                                summary_parts.append(f"{key.capitalize()}: {analysis_data[key]}")
                                
                        # Put together a basic fallback summary
                        if summary_parts:
                            result = f"Momentum Quant Analysis (Fallback Summary):\n" + "\n".join(summary_parts)
                            logger.info(f"Created fallback summary for momentum agent from analysis_data")
            else:
                result = None # Should not happen

            if result is None:
                # Handle missing key case - retry
                error_msg = f"{agent_name}: Critical error - Expected result key not found in final state."
                logger.error(error_msg)
                logger.error(f"Final state keys: {final_state.keys()}")
                
                # Check if we should retry
                if retry_count < max_retries - 1:
                    retry_count += 1
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                    continue
                else:
                    return f"{agent_name} Error: {error_msg} (After {max_retries} attempts)"
                    
            elif not isinstance(result, str):
                # Handle unexpected type - retry
                error_msg = f"Unexpected result type ({type(result).__name__}) received."
                logger.error(f"{agent_name}: {error_msg}")
                
                # Check if we should retry
                if retry_count < max_retries - 1:
                    retry_count += 1
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                    continue
                else:
                    return f"{agent_name} Error: {error_msg} (After {max_retries} attempts)"
                    
            elif result.startswith("Error:") or result.startswith("Failed") or result.startswith("Analysis Error"):
                # Handle errors reported by the sub-agent itself - retry
                logger.warning(f"{agent_name} reported an error: {result}")
                
                # Check if we should retry
                if retry_count < max_retries - 1:
                    retry_count += 1
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                    continue
                else:
                    return f"{agent_name} Error: {result} (After {max_retries} attempts)"
                    
            else:
                # Successful result
                logger.info(f"--- Manager: {agent_name} Completed Successfully ---")
                return result

        except Exception as e:
            logger.exception(f"Manager: Unhandled error invoking {agent_name}")
            
            # Check if we should retry
            if retry_count < max_retries - 1:
                retry_count += 1
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
                continue
            else:
                return f"{agent_name} Invocation Error: {type(e).__name__} - {str(e)} (After {max_retries} attempts)"
    
    # Should never reach here, but just in case
    return f"{agent_name} Error: Maximum retries reached with no successful response"

# Node to run sub-agents in parallel
async def run_sub_agents_node(state: ManagerAgentState):
    logger.info("--- Manager: Running Sub-Agents Node ---")
    input_data = state['input']
    token_id = input_data.get('token_id')
    token_name = input_data.get('token_name', 'Unknown') # Use input name

    if not token_id:
         logger.error("Manager agent cannot proceed: Missing token_id.")
         # Update state to reflect this fatal error
         return {
             "error_messages": ["Input Error: Missing token_id for analysis."],
             "sma_result": "Skipped - Missing token_id",
             "bounce_result": "Skipped - Missing token_id",
             "oracle_result": "Skipped - Missing token_id",
             "final_summary": "Analysis halted due to missing token ID." # Prevent synthesis
         }

    # Define tasks for asyncio.gather
    tasks = [
        invoke_sub_agent(sma_app, input_data, "sma_agent"),
        invoke_sub_agent(bounce_hunter_app, input_data, "bounce_hunter_agent"),
        invoke_sub_agent(crypto_oracle_app, input_data, "crypto_oracle_agent"),
        invoke_sub_agent(momentum_quant_app, input_data, "momentum_quant_agent")
    ]

    # Run tasks concurrently
    results = await asyncio.gather(*tasks)
    sma_result, bounce_result, oracle_result, momentum_result = results

    # Collect errors from results
    errors = [res for res in results if "Error:" in res]

    logger.info(f"Manager: Sub-agent results collected. Found {len(errors)} errors.")
    return {
        "sma_result": sma_result,
        "bounce_result": bounce_result,
        "oracle_result": oracle_result,
        "momentum_result": momentum_result,
        "error_messages": errors # Store collected error strings
    }


# Node to synthesize results using LLM
async def synthesize_results_node(state: ManagerAgentState):
    logger.info("--- Manager: Synthesizing Results Node ---")

    # If run_sub_agents_node already set a final_summary due to input error, skip synthesis
    if state.get("final_summary"):
        logger.warning("Skipping synthesis node due to prior fatal error (e.g., missing token_id).")
        return {} # No changes needed

    sma_result = state.get("sma_result", "Analysis unavailable.")
    bounce_result = state.get("bounce_result", "Analysis unavailable.")
    oracle_result = state.get("oracle_result", "Analysis unavailable.")
    momentum_result = state.get("momentum_result", "Analysis unavailable.")
    errors = state.get("error_messages", [])
    token_id = state['input'].get('token_id', 'N/A')
    token_name = state['input'].get('token_name', 'N/A')

    if errors:
        logger.warning(f"Synthesizing results based on potentially incomplete data due to {len(errors)} sub-agent errors.")
        # LLM will see the errors embedded within the result strings

    # Prepare prompt input
    prompt_input = {
        "token_id": token_id,
        "token_name": token_name,
        "sma_result": sma_result,
        "bounce_result": bounce_result,
        "oracle_result": oracle_result,
        "momentum_result": momentum_result,
    }

    try:
        synthesis_chain = synthesis_prompt | llm
        logger.info("Manager: Invoking LLM for final synthesis...")
        # Use async invoke
        llm_response = await synthesis_chain.ainvoke(prompt_input)

        if hasattr(llm_response, 'content'):
             summary = llm_response.content
        else:
             summary = str(llm_response)

        logger.info("Manager: LLM synthesis complete.")
        
        # Extract the final signal from the LLM's response
        final_signal = None
        # Look for our explicitly requested format
        if "FINAL RECOMMENDATION:" in summary:
            recommendation_line = [line for line in summary.split('\n') if "FINAL RECOMMENDATION:" in line]
            if recommendation_line:
                # Extract the signal from the line "FINAL RECOMMENDATION: [Signal]"
                recommendation_text = recommendation_line[0].split("FINAL RECOMMENDATION:")[1].strip()
                if "STRONG BUY" in recommendation_text.upper():
                    final_signal = "STRONG BUY"
                elif "BUY" in recommendation_text.upper():
                    final_signal = "BUY"
                elif "STRONG SELL" in recommendation_text.upper():
                    final_signal = "STRONG SELL"
                elif "SELL" in recommendation_text.upper():
                    final_signal = "SELL"
                elif "HOLD" in recommendation_text.upper():
                    final_signal = "HOLD"
        
        # If we couldn't find the explicit format, try to infer from the text
        if not final_signal:
            summary_upper = summary.upper()
            if "STRONG BUY" in summary_upper:
                final_signal = "STRONG BUY"
            elif "BUY" in summary_upper:
                final_signal = "BUY"
            elif "STRONG SELL" in summary_upper:
                final_signal = "STRONG SELL"
            elif "SELL" in summary_upper:
                final_signal = "SELL"
            elif "HOLD" in summary_upper:
                final_signal = "HOLD"
            
        logger.info(f"Manager: Extracted final signal: {final_signal}")
        return {"final_summary": summary.strip(), "final_signal": final_signal}

    except Exception as e:
        logger.exception("Manager: Error invoking LLM for synthesis")
        # Return an error summary, but also keep individual results
        return {"final_summary": f"Error during final synthesis: {type(e).__name__} - {str(e)}", "final_signal": None}


# --- Build Graph ---
workflow = StateGraph(ManagerAgentState)
workflow.add_node("run_sub_agents", run_sub_agents_node)
workflow.add_node("synthesize_results", synthesize_results_node)

workflow.set_entry_point("run_sub_agents")
workflow.add_edge("run_sub_agents", "synthesize_results")
workflow.add_edge("synthesize_results", END)

# --- Memory & Compile ---
# Checkpointing can be useful if sub-agent calls are long/costly
memory = MemorySaver()
app = workflow.compile(checkpointer=memory)
