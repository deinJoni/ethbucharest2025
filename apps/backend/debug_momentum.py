import asyncio
import logging
from uuid import uuid4
from agents.momentum_quant_agent import app as momentum_quant_app

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_momentum_agent():
    # Prepare input data
    input_data = {
        "token_id": "1",  # Bitcoin
        "token_name": "Bitcoin"
    }
    
    config = {"configurable": {"thread_id": f"debug_test_{str(uuid4())}"}}
    logger.info(f"Invoking momentum_quant_agent with input: {input_data}")
    
    try:
        # Use async invoke
        final_state = await momentum_quant_app.ainvoke({"input": input_data}, config=config)
        logger.info("Momentum agent execution complete")
        
        # Inspect the state
        logger.info(f"Final state keys: {list(final_state.keys())}")
        
        # Check for llm_reasoning
        if "llm_reasoning" in final_state:
            logger.info(f"llm_reasoning type: {type(final_state['llm_reasoning'])}")
            logger.info(f"llm_reasoning content: {final_state['llm_reasoning']}")
        else:
            logger.error("'llm_reasoning' key not found in final state")
            # Inspect other keys that might be present
            for key, value in final_state.items():
                logger.info(f"Key: {key}, Type: {type(value)}")
                if isinstance(value, dict) and value.get("result"):
                    logger.info(f"Found result in {key}: {value['result']}")
                    
    except Exception as e:
        logger.exception(f"Error during test: {e}")

if __name__ == "__main__":
    asyncio.run(test_momentum_agent()) 