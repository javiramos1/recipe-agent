#!/usr/bin/env python3
"""Ad hoc query runner for Recipe Recommendation Agent.

Run queries directly without starting the full API server.

Usage:
    make query Q="What can I make with chicken and rice?"
    python query.py "What are some vegetarian recipes?"
    python query.py --debug "Your query"  # Show full JSON response

Features:
- Direct agent execution via arun()
- Single query input with formatted markdown response
- Debug mode to display full JSON with all fields
- Clean exit after completion
"""

import asyncio
import json
import sys

from rich.console import Console
from rich.markdown import Markdown

from src.utils.config import config
from src.utils.logger import logger
from src.agents.agent import initialize_recipe_agent

console = Console()


def run_query(query: str, debug: bool = False) -> None:
    """Execute a single ad hoc query and print the response.
    
    Args:
        query: The user query to send to the agent (plain text or JSON).
        debug: If True, display full JSON response with all fields.
    """
    try:
        logger.info("Initializing agent...")
        agent = initialize_recipe_agent()
        
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
        
        # Run the query and get response (async call)
        response = asyncio.run(agent.arun(input=json.dumps(request_data)))
        
        logger.info("---")
        
        # Display response
        if debug:
            # Debug mode: show full JSON with all fields
            console.print("[bold cyan]Debug Mode: Full Response[/bold cyan]")
            console.print("[dim]" + "=" * 60 + "[/dim]")
            response_dict = response.model_dump() if hasattr(response, 'model_dump') else response.__dict__
            console.print_json(data=response_dict)
            console.print("[dim]" + "=" * 60 + "[/dim]")
            console.print()
        
        # Formatted markdown output
        if hasattr(response, 'content'):
            markdown_content = Markdown(response.content)
            console.print(markdown_content)
        else:
            console.print(response)
        
    except KeyboardInterrupt:
        logger.info("\nQuery interrupted by user.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Query execution failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python query.py [--debug] \"<your query>\"")
        print("Example: python query.py \"What can I make with chicken and rice?\"")
        print("Debug:   python query.py --debug \"What can I make with chicken and rice?\"")
        sys.exit(1)
    
    # Check for debug flag
    debug_mode = False
    argv_start = 1
    
    if sys.argv[1] == "--debug":
        debug_mode = True
        argv_start = 2
        if len(sys.argv) < 3:
            print("Usage: python query.py --debug \"<your query>\"")
            sys.exit(1)
    
    # Join all arguments after script name as the query (handles queries with spaces)
    query = " ".join(sys.argv[argv_start:])
    
    # Run the query function
    run_query(query, debug=debug_mode)
