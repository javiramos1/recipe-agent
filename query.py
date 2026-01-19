#!/usr/bin/env python3
"""Ad hoc query runner for Recipe Recommendation Agent.

Run queries directly without starting the full API server.

Usage:
    make query Q="What can I make with chicken and rice?"
    python query.py "What are some vegetarian recipes?"

Features:
- Direct agent execution via arun()
- Single query input with response output
- Clean exit after completion
"""

import asyncio
import json
import sys

from src.utils.config import config
from src.utils.logger import logger
from src.agents.agent import initialize_recipe_agent


async def run_query(query: str) -> None:
    """Execute a single ad hoc query and print the response.
    
    Args:
        query: The user query to send to the agent (plain text or JSON).
    """
    try:
        logger.info("Initializing agent...")
        agent = await initialize_recipe_agent()
        
        logger.info(f"Running query: {query}")
        logger.info("---")
        
        # Try to parse as JSON, otherwise treat as a text query with extracted ingredients
        try:
            request_data = json.loads(query)
        except json.JSONDecodeError:
            # If not JSON, extract ingredients from natural language or treat as a plain query
            # For now, send as a simple list of ingredients extracted from common patterns
            # e.g., "chicken and rice" -> ["chicken", "rice"]
            import re
            # Simple extraction: split by "and", commas, etc.
            parts = re.split(r'\s+(?:and|or|,)\s+|\s*,\s*', query.lower())
            ingredients = [p.strip() for p in parts if p.strip()]
            request_data = {"ingredients": ingredients}
        
        # Run the query and get response
        response = await agent.arun(input=json.dumps(request_data))
        
        logger.info("---")
        print(response.content)
        
    except KeyboardInterrupt:
        logger.info("\nQuery interrupted by user.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Query execution failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python query.py \"<your query>\"")
        print("Example: python query.py \"What can I make with chicken and rice?\"")
        sys.exit(1)
    
    # Join all arguments after script name as the query (handles queries with spaces)
    query = " ".join(sys.argv[1:])
    
    # Run the async query function
    asyncio.run(run_query(query))
