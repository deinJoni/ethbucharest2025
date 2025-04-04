from langchain_community.tools import tool
import logging
# import re # No longer needed

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@tool
def multiply(query: str) -> str: # Return string for consistency, including errors
    """Multiply two integers. Input must be two integers separated by a space (e.g., '5 3')."""
    logger.info(f"Multiply tool called with: '{query}'")

    try:
        # Split the input string and convert to integers
        parts = query.split()
        if len(parts) != 2:
            raise ValueError("Input must contain exactly two numbers separated by a space.")

        a = int(parts[0])
        b = int(parts[1])

        result = a * b
        logger.info(f"Multiply result: {result}")
        return str(result) # Return result as a string

    except ValueError as ve:
        logger.error(f"Value error in multiply tool: {ve}")
        return f"Error: {ve}"
    except Exception as e:
        logger.error(f"Unexpected error in multiply tool: {e}", exc_info=True)
        return f"Error: An unexpected error occurred."

# Removed the 'tools' list export as it's not typically used this way
# If needed elsewhere, import the tool directly: from tools.exampletool import multiply