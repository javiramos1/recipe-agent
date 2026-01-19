#!/usr/bin/env python3
"""Ad hoc query runner for Recipe Recommendation Agent.

Run queries directly without starting the full API server.

Usage:
    make query Q="What can I make with chicken and rice?"
    python query.py "What are some vegetarian recipes?"
    python query.py --debug "Your query"  # Show full JSON response
    python query.py --stateless "Your query"  # No session history (clear memory)

Features:
- Direct agent execution via arun()
- Single query input with formatted markdown response
- Debug mode to display full JSON with all fields
- Stateless mode to run without session history or memory
- Clean exit after completion
"""

import asyncio
import json
import sys
import tempfile
from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown

from src.utils.config import config
from src.utils.logger import logger
from src.agents.agent import initialize_recipe_agent

console = Console()


def run_query(query: str, debug: bool = False, stateless: bool = False) -> None:
    """Execute a single ad hoc query and print the response.
    
    Args:
        query: The user query to send to the agent (plain text or JSON).
        debug: If True, display full JSON response with all fields.
        stateless: If True, use a temporary database (clears memory between queries).
    """
    try:
        logger.info(f"Initializing agent (stateless={stateless})...")
        
        # For stateless mode, temporarily override DATABASE_URL to use a temp database
        original_db_url = config.DATABASE_URL
        if stateless:
            temp_db = Path(tempfile.gettempdir()) / f"query_stateless_{id(asyncio)}.db"
            config.DATABASE_URL = f"sqlite:///{temp_db}"
            logger.info(f"Using temporary database: {temp_db}")
        
        try:
            agent = initialize_recipe_agent()
        finally:
            # Restore original DATABASE_URL
            if stateless:
                config.DATABASE_URL = original_db_url
        
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
        print("Usage: python query.py [--debug] [--stateless] \"<your query>\"")
        print("Example: python query.py \"What can I make with chicken and rice?\"")
        print("Debug:   python query.py --debug \"What can I make with chicken and rice?\"")
        print("Stateless: python query.py --stateless \"What can I make with chicken and rice?\"")
        sys.exit(1)
    
    # Check for debug and stateless flags
    debug_mode = False
    stateless_mode = False
    argv_start = 1
    
    while argv_start < len(sys.argv) and sys.argv[argv_start].startswith("--"):
        if sys.argv[argv_start] == "--debug":
            debug_mode = True
            argv_start += 1
        elif sys.argv[argv_start] == "--stateless":
            stateless_mode = True
            argv_start += 1
        else:
            print(f"Unknown flag: {sys.argv[argv_start]}")
            sys.exit(1)
    
    if argv_start >= len(sys.argv):
        print("Error: No query provided")
        print("Usage: python query.py [--debug] [--stateless] \"<your query>\"")
        sys.exit(1)
    
    # Join all arguments after flags as the query (handles queries with spaces)
    query = " ".join(sys.argv[argv_start:])
    
    # Run the query function
    run_query(query, debug=debug_mode, stateless=stateless_mode)
