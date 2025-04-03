from langchain_community.tools import tool
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@tool
def multiply(a: str, b: str) -> int:
    """Multiply two integers together.
    
    Args:
        a: The first integer
        b: The second integer
        
    Returns:
        The product of a and b
    """
    logger.info(f"Multiply tool called with: a={a}, b={b}")
    result = int(a) * int(b)
    logger.info(f"Multiply result: {result}")
    return result

tools = [multiply]