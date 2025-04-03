from fastapi import APIRouter
from core.config import settings
from agents.exampleagent import agent_executor
from pydantic import BaseModel
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix=f"{settings.API_V1_STR}/agents",
    tags=["agents"],
)

class AgentRequest(BaseModel):
    question: str

@router.post("/example_agent")
async def ask_agent(req: AgentRequest):
    if not req.question or req.question.strip() == "":
        return {"answer": "Please provide a question to answer."}
    
    try:
        logger.info(f"Processing agent request: {req.question}")
        
        # Check for multiplication keywords
        question = req.question.strip()
        
        # Process the request with the agent
        result = agent_executor.invoke({"input": question})
        logger.info(f"Agent result: {result}")
        
        # Extract the output from the result
        answer = result.get("output", "I couldn't process that request.")
        
        # Return the answer
        return {"answer": answer}
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}", exc_info=True)
        return {"error": str(e)}