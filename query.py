#!/usr/bin/env python3
"""Ad hoc query runner for Recipe Recommendation Agent.

Run queries directly without starting the full API server.

Usage:
    make query "What can I make with chicken and rice?"
    python query.py "What are some vegetarian recipes?"

Features:
- Direct agent execution via arun()
- Single query input with response output
- Clean exit after completion
"""

import asyncio
import sys

from src.utils.config import config
from src.utils.logger import logger
from src.agents.agent import initialize_recipe_agent


async def run_query(query: str) -> None:
    """Execute a single ad hoc query and print the response.
    
    Args:
        query: The user query to send to the agent.
    """
    try:
        logger.info("Initializing agent...")
        agent = await initialize_recipe_agent()
        
        logger.info(f"Running query: {query}")
        logger.info("---")
        
        # Run the query and get response
        response = await agent.arun(input=query)
        
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
