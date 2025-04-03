# agent.py
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, Tool, create_react_agent
from tools.exampletool import multiply
from core.config import settings
from langchain.prompts import PromptTemplate
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create tools list with descriptions
tools = [
    Tool(
        name="multiply",
        func=multiply,
        description="Multiply two numbers. You can provide parameters in one of these formats: 1) a=5 b=3 or 2) {\"a\": 5, \"b\": 3}",
    )
]

# Initialize LLM with API key
llm = ChatOpenAI(
    temperature=0,  # Reduced temperature for more deterministic responses
    api_key=settings.OPENAI_API_KEY,
    model="gpt-3.5-turbo"
)

# Define ReAct prompt template for the agent
template = """Answer the following questions as best you can. You have access to the following tools:

{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action

IMPORTANT NOTE FOR MULTIPLY TOOL:
For the multiply tool, you can provide the input in one of these two formats:
1. Simple format: a=5 b=3
2. Or directly (no JSON): a=5 b=3

DO NOT use JSON format or quotes for the Action Input. Just use simple key-value pairs.

Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {input}
Thought:{agent_scratchpad}"""

prompt = PromptTemplate.from_template(template)

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
