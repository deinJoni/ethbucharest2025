# agent.py
import logging
from typing import TypedDict, Annotated
import operator

from langchain_openai import ChatOpenAI
from langchain.agents import Tool
from langchain_core.agents import AgentAction, AgentFinish
from langchain.prompts import PromptTemplate
# LangGraph imports: StateGraph for building, END for the final node
from langgraph.graph import StateGraph, END
# ToolExecutor helps run LangChain tools within the graph
from langgraph.prebuilt import ToolExecutor
# MemorySaver allows the graph state to be persisted (here, just in memory)
from langgraph.checkpoint.memory import MemorySaver
# Import the specific function for creating the ReAct agent logic
from langchain.agents import create_react_agent

from tools.exampletool import multiply # Import the simplified tool
from core.config import settings

# --- Basic Setup ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Tool Definition ---
# Define the tools the agent can use.
# We use the simplified multiply tool.
math_tools = [
    Tool(
        name="multiply",
        func=multiply.run,
        description="Multiply two integers. Input must be two integers separated by a space (e.g., '5 3')."
    )
]
# The ToolExecutor takes the list of tools and handles calling them
tool_executor = ToolExecutor(math_tools)

# --- Agent Setup ---
# Initialize the LLM (Language Model)
llm = ChatOpenAI(
    temperature=0,
    api_key=settings.OPENAI_API_KEY,
    model="gpt-3.5-turbo"
)

# Define the prompt template for the ReAct agent
# This tells the agent how to think, act, and format its response.
# It includes placeholders for input, tools, and scratchpad (agent's internal thoughts).
prompt = PromptTemplate.from_template(
    """You are a helpful assistant that can answer questions and perform calculations.

Available tools: {tools}

Use the following format:
Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action (e.g., for multiply: 5 3)
Observation: the result of the action
... (this Thought/Action/Action Input/Observation sequence can repeat)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {input}
{agent_scratchpad}"""
)

# Create the core agent logic using the ReAct framework.
# This combines the LLM, the prompt, and the tools.
# The output is a Runnable that decides the next step (Action or Finish).
agent_runnable = create_react_agent(llm=llm, tools=math_tools, prompt=prompt)

# --- LangGraph State Definition ---
# This defines the structure of the data that flows through the graph.
# Think of it as the "memory" of the agent during its execution run.
class AgentState(TypedDict):
    # The initial question or input from the user.
    input: str
    # The decision made by the agent in the current step (either to call a tool or finish).
    agent_decision: AgentAction | AgentFinish | None
    # A list to keep track of the sequence of tool calls and their results.
    # `operator.add` means new steps are appended to this list.
    intermediate_steps: Annotated[list[tuple[AgentAction, str]], operator.add]


# --- LangGraph Node Definitions ---
# Nodes are functions that perform actions based on the current state.

# Node 1: Agent Logic - Decides the next step (tool call or finish)
def run_agent_node(state: AgentState):
    """Runs the agent runnable to determine the next action or if we are done."""
    logger.info("--- Running Agent Node ---")
    # Pass the input and previous steps to the agent runnable
    agent_decision = agent_runnable.invoke(
        {
            "input": state["input"],
            "intermediate_steps": state["intermediate_steps"],
        }
    )
    logger.info(f"Agent decision: {agent_decision}")
    # Return the decision to be added to the state
    return {"agent_decision": agent_decision}

# Node 2: Tool Execution - Calls the chosen tool
def execute_tool_node(state: AgentState):
    """Executes the tool chosen by the agent and returns the result."""
    logger.info("--- Executing Tool Node ---")
    agent_action = state['agent_decision']
    # Ensure the decision is an action, not the final finish signal
    if not isinstance(agent_action, AgentAction):
         raise ValueError("Agent decision is not an action, cannot execute tool.")

    # Use the ToolExecutor to run the tool with the provided input
    output = tool_executor.invoke(agent_action)
    logger.info(f"Tool output: {output}")
    # Return the action and its output to be added to intermediate_steps
    return {"intermediate_steps": [(agent_action, str(output))]} # Appends this tuple

# --- LangGraph Edge Definitions ---
# Edges define the flow of control between nodes.

# Conditional Edge: Checks the agent's decision to route to the next step
def should_continue_edge(state: AgentState):
    """Determines the next node based on the agent's decision."""
    logger.info("--- Evaluating Conditional Edge ---")
    # Check if the agent's last decision was to finish
    if isinstance(state['agent_decision'], AgentFinish):
        logger.info("Agent decided to finish. Routing to END.")
        return END # Special value indicating the graph should stop
    else:
        # Otherwise, the agent decided to call a tool
        logger.info("Agent decided to use a tool. Routing to execute_tool_node.")
        return "execute_tool_node" # Name of the next node to run

# --- Construct the Graph ---
# Initialize a new state graph with our defined AgentState
workflow = StateGraph(AgentState)

# Add the nodes to the graph
workflow.add_node("agent_node", run_agent_node)
workflow.add_node("execute_tool_node", execute_tool_node)

# Set the starting point of the graph
workflow.set_entry_point("agent_node")

# Add the conditional edge:
# From agent_node, call should_continue_edge to decide where to go next.
# If it returns "execute_tool_node", go there. If it returns END, stop.
workflow.add_conditional_edges(
    "agent_node",
    should_continue_edge,
    {
        "execute_tool_node": "execute_tool_node",
        END: END
    }
)

# Add a regular edge:
# After execute_tool_node runs, always go back to agent_node to decide the next step.
workflow.add_edge("execute_tool_node", "agent_node")

# Add simple in-memory checkpointing (state persistence)
memory = MemorySaver()

# Compile the graph into a runnable application
# The checkpointer allows the state to be saved/loaded (useful for longer interactions)
app = workflow.compile(checkpointer=memory)

# --- Example Usage (when run directly) ---
if __name__ == "__main__":
    from uuid import uuid4
    # Configuration for stateful execution (each thread_id gets its own state)
    config = {"configurable": {"thread_id": str(uuid4())}}

    inputs = {"input": "What is 6 multiplied by 7?"}
    print(f"\n--- Running Graph ---")
    print(f"Input: {inputs['input']}")

    # Use stream to see the output of each node/step as it happens
    for event in app.stream(inputs, config=config):
        for node_name, output in event.items():
            # Print the output of each node, excluding the final END marker
            if node_name != "__end__":
                 print(f"\nOutput from node '{node_name}':")
                 print(output)

    # Optionally, get the final state directly using invoke
    # final_state = app.invoke(inputs, config=config)
    # print("\n--- Final State ---")
    # print(final_state)
    # agent_finish = final_state.get('agent_decision') # Use updated state key
    # if isinstance(agent_finish, AgentFinish):
    #     print("\n--- Final Answer ---")
    #     print(agent_finish.return_values['output'])
