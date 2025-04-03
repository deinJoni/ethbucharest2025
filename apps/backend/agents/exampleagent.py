# agent.py
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, Tool, create_react_agent
from langchain.prompts import PromptTemplate
from tools.exampletool import multiply
from core.config import settings
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create tools list with descriptions
tools = [
    Tool(
        name="multiply",
        func=multiply,
        description="Multiply two numbers. Input should be in the format: 'a=5 b=3'",
    )
]

# Initialize LLM with API key
llm = ChatOpenAI(
    temperature=0,  # Reduced temperature for more deterministic responses
    api_key=settings.OPENAI_API_KEY,
    model="gpt-3.5-turbo"
)

# Create prompt template
prompt = PromptTemplate(
    template="""
You are a helpful assistant that can answer questions and perform calculations.

You have access to the following tools:
{tools}

Use the following format:
Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Question: {input}
{agent_scratchpad}
""",
    input_variables=["input", "agent_scratchpad", "tools", "tool_names"]
)

# Create ReAct agent
agent = create_react_agent(
    llm=llm,
    tools=tools,
    prompt=prompt
)

# Create agent executor
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True,
    max_iterations=3,
    return_intermediate_steps=True,
    handle_parsing_errors=True
)
