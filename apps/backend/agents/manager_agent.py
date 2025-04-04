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
    """You are a senior financial analyst synthesizing analyses from three specialist agents for the token {token_name} (ID: {token_id}). Provide a final recommendation (Strong Buy, Buy, Hold, Sell, Strong Sell) based on their combined insights.

**Agent Analyses:**

1.  **SMA Crossover Analysis:**
    *   Result: {sma_result}

2.  **Bounce Hunter Analysis (Support/Resistance):**
    *   Result: {bounce_result}

3.  **Crypto Oracle Analysis (Trader Grade & Momentum):**
    *   Result: {oracle_result}

**Your Task:**

1.  **Summarize:** Briefly state the signal/key finding from each agent.
2.  **Compare:** Note agreements or disagreements in signals/reasoning.
3.  **Synthesize:** Weigh the evidence. Do signals reinforce or conflict?
4.  **Conclude:** State your final recommendation (Strong Buy, Buy, Hold, Sell, Strong Sell).
5.  **Explain:** Justify your recommendation by referencing specific agent findings and how they collectively support your conclusion. Address any conflicting signals and your reasoning for weighing them.

**Final Synthesized Analysis for {token_name}:**
"""
)

# --- LangGraph State ---
class ManagerAgentState(TypedDict):
    input: Dict[str, str] # {"token_id": "...", "token_name": "..."}
    sma_result: Optional[str]
    bounce_result: Optional[str]
    oracle_result: Optional[str]
    error_messages: List[str] # Collect errors from sub-agents
    final_summary: Optional[str]

# --- Nodes ---

# Helper Function to invoke a sub-agent asynchronously
async def invoke_sub_agent(agent_app, input_data: Dict[str, Any], agent_name: str) -> str:
    """Invokes a sub-agent graph and returns its final analysis string or an error message."""
    logger.info(f"--- Manager: Invoking {agent_name} ---")
    try:
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
        else:
            result = None # Should not happen

        if result is None:
            # Handle missing key case
             error_msg = f"{agent_name}: Critical error - Expected result key not found in final state."
             logger.error(error_msg)
             return f"{agent_name} Error: {error_msg}"
        elif not isinstance(result, str):
            # Handle unexpected type
            error_msg = f"Unexpected result type ({type(result).__name__}) received."
            logger.error(f"{agent_name}: {error_msg}")
            return f"{agent_name} Error: {error_msg}"
        elif result.startswith("Error:") or result.startswith("Failed") or result.startswith("Analysis Error"):
            # Handle errors reported by the sub-agent itself
            logger.warning(f"{agent_name} reported an error: {result}")
            return f"{agent_name} Error: {result}" # Pass the error string through
        else:
            # Successful result
            logger.info(f"--- Manager: {agent_name} Completed Successfully ---")
            return result

    except Exception as e:
        logger.exception(f"Manager: Unhandled error invoking {agent_name}")
        return f"{agent_name} Invocation Error: {type(e).__name__} - {str(e)}"

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
        invoke_sub_agent(crypto_oracle_app, input_data, "crypto_oracle_agent")
    ]

    # Run tasks concurrently
    results = await asyncio.gather(*tasks)
    sma_result, bounce_result, oracle_result = results

    # Collect errors from results
    errors = [res for res in results if "Error:" in res]

    logger.info(f"Manager: Sub-agent results collected. Found {len(errors)} errors.")
    return {
        "sma_result": sma_result,
        "bounce_result": bounce_result,
        "oracle_result": oracle_result,
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
        return {"final_summary": summary.strip()}

    except Exception as e:
        logger.exception("Manager: Error invoking LLM for synthesis")
        # Return an error summary, but also keep individual results
        return {"final_summary": f"Error during final synthesis: {type(e).__name__} - {str(e)}"}


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

# --- Manual Test ---
if __name__ == "__main__":
    print("--- Testing Manager Agent ---")
    test_token_id = "3306" # Example: Ethereum
    test_token_name = "Ethereum"
    test_input = {"token_id": test_token_id, "token_name": test_token_name}

    async def run_test():
        config = {"configurable": {"thread_id": f"manager_test_{str(uuid4())}"}}
        print(f"Invoking manager agent with input: {test_input}")
        try:
            # Use async invoke for testing async nodes
            result_state = await app.ainvoke({"input": test_input}, config=config)
            print("\n--- Manager Agent Final State ---")
            # print(result_state) # Print full state if needed
            print(f"Input: {result_state.get('input')}")
            print(f"SMA Result: {result_state.get('sma_result')}")
            print(f"Bounce Result: {result_state.get('bounce_result')}")
            print(f"Oracle Result: {result_state.get('oracle_result')}")
            print(f"Errors: {result_state.get('error_messages')}")
            print(f"\nFinal Summary:\n{result_state.get('final_summary')}")

        except Exception as e:
            print(f"\n--- Error during manager agent test execution ---")
            logger.exception("Manager agent test invocation failed")
            print(f"Error: {type(e).__name__} - {e}")

    # Run the async test function
    asyncio.run(run_test())
    print("\n--- Test Complete ---")
