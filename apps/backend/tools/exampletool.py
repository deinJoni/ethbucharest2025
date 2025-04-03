from langchain_community.tools import tool
import logging
import re

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@tool
def multiply(query: str) -> int:
    """Multiply two integers together.
    
    Args:
        query: A string in the format 'a=5 b=3' where a and b are integers to multiply
        
    Returns:
        The product of a and b
    """
    logger.info(f"Multiply tool called with: {query}")
    
    # Parse the input
    try:
        # Extract a and b values using regex
        a_match = re.search(r'a=(\d+)', query)
        b_match = re.search(r'b=(\d+)', query)
        
        if not a_match or not b_match:
            return "Error: Input must be in the format 'a=5 b=3'"
            
        a = int(a_match.group(1))
        b = int(b_match.group(1))
        
        result = a * b
        logger.info(f"Multiply result: {result}")
        return result
    except Exception as e:
        logger.error(f"Error in multiply tool: {e}")
        return f"Error: {str(e)}"

tools = [multiply]