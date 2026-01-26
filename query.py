#!/usr/bin/env python3
"""Ad hoc query runner for Recipe Recommendation Agent.

Run queries directly without starting the full API server.

Usage:
    make query Q="What can I make with chicken and rice?"
    python query.py "What are some vegetarian recipes?"
    python query.py --debug "Your query"  # Show full JSON response
    python query.py --stateless "Your query"  # No session history (clear memory)
    python query.py --image images/pasta.png "What can I make?"  # With image detection

Features:
- Direct agent execution via arun()
- Single query input with formatted markdown response
- Debug mode to display full JSON with all fields
- Stateless mode to run without session history or memory
- Image support for ingredient detection
- Clean exit after completion
"""

import asyncio
import base64
import json
import sys
from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown

from src.utils.config import config
from src.utils.logger import logger
from src.agents.agent import initialize_recipe_agent

console = Console()

# Note: Image compression now handled by pre-hook in src/mcp_tools/ingredients.py
# This keeps compression centralized and works for both query and run modes


def extract_response_text(response) -> str:
    """Extract markdown response text from agent response object.
    
    Handles multiple response formats:
    - RecipeResponse with 'response' field
    - Response with 'content' containing 'response' field
    - Dict responses with 'response' key
    - Fallback to string representation
    
    Args:
        response: Agent response object (RecipeResponse, dict, or other)
    
    Returns:
        Extracted response text or empty string if not found
    """
    # Try RecipeResponse object with response field
    if hasattr(response, 'response') and response.response:
        return response.response
    
    # Try response.content with nested response field
    if hasattr(response, 'content') and response.content:
        if hasattr(response.content, 'response'):
            return response.content.response
        elif isinstance(response.content, dict) and 'response' in response.content:
            return response.content['response']
        elif isinstance(response.content, str):
            return response.content
    
    # Fallback to string representation
    return str(response) if response else ""


def run_query(query: str, debug: bool = False, stateless: bool = False, image_path: str = None) -> None:
    """Execute a single ad hoc query and print the response.
    
    Args:
        query: The user query to send to the agent (plain text or JSON).
        debug: If True, display full JSON response with all fields.
        stateless: If True, disable persistence (no session memory).
        image_path: Optional path to an image file to include in the query.
    """
    try:
        logger.info(f"Initializing agent (stateless={stateless})...")
        
        # Initialize agent with persistence disabled for stateless queries
        # initialize_recipe_agent is async and returns (agent, tracing_db, knowledge) tuple
        agent, _, _ = asyncio.run(initialize_recipe_agent(use_db=not stateless))
        
        logger.info(f"Running query: {query}")
        if image_path:
            logger.info(f"Image: {image_path}")
        logger.info("---")
        
        # Try to parse as JSON, otherwise treat as a text message
        try:
            request_data = json.loads(query)
            # If it's valid JSON, ensure it has a 'message' field
            if "message" not in request_data:
                request_data = {"message": query}
        except json.JSONDecodeError:
            # If not JSON, treat the entire input as a message
            request_data = {"message": query}
        
        # Add image if provided
        if image_path:
            image_file = Path(image_path)
            if not image_file.exists():
                console.print(f"[red]✗ Error: Image file not found: {image_path}[/red]")
                sys.exit(1)
            
            # Read and encode image (compression handled by pre-hook)
            logger.info(f"Loading image: {image_file.name}...")
            with open(image_file, "rb") as f:
                image_bytes = f.read()
            
            image_data = base64.b64encode(image_bytes).decode("utf-8")
            
            # Determine MIME type based on extension
            ext = image_file.suffix.lower()
            mime_types = {
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".png": "image/png",
                ".gif": "image/gif",
                ".webp": "image/webp"
            }
            mime_type = mime_types.get(ext, "image/jpeg")
            
            # Add image to request
            if "images" not in request_data:
                request_data["images"] = []
            request_data["images"].append(f"data:{mime_type};base64,{image_data}")
            logger.info(f"✓ Loaded image: {image_file.name} ({len(image_data) / 1024:.1f} KB base64)")
        
        # Run the query and get response (async call)
        response = asyncio.run(agent.arun(input=json.dumps(request_data)))
        
        logger.info("---")
        console.print()  # Blank line for separation
        
        # Display debug info if requested
        if debug:
            console.print("[bold cyan]Debug Mode: Full Response[/bold cyan]")
            console.print("[dim]" + "=" * 60 + "[/dim]")
            response_dict = response.model_dump() if hasattr(response, 'model_dump') else response.__dict__
            console.print_json(data=response_dict)
            console.print("[dim]" + "=" * 60 + "[/dim]")
            console.print()
        
        # Display response with proper markdown formatting and colors
        response_text = extract_response_text(response)
        
        if response_text:
            # Render as markdown with rich formatting (colors, bold, etc.)
            console.print(Markdown(response_text))
        else:
            # Fallback: print the response as-is
            console.print("[yellow]No response text found[/yellow]")
        
    except KeyboardInterrupt:
        logger.info("\nQuery interrupted by user.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Query execution failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python query.py [--debug] [--stateless] [--image PATH] \"<your query>\"")
        print("")
        print("Examples:")
        print("  python query.py \"What can I make with chicken and rice?\"")
        print("  python query.py --debug \"What can I make with chicken and rice?\"")
        print("  python query.py --stateless \"What can I make with chicken and rice?\"")
        print("  python query.py --image images/pasta.png \"What can I make with these ingredients?\"")
        print("  python query.py --image images/pasta.png --debug \"What can I make with these ingredients?\"")
        sys.exit(1)
    
    # Check for debug, stateless, and image flags
    debug_mode = False
    stateless_mode = False
    image_path = None
    argv_start = 1
    
    while argv_start < len(sys.argv) and sys.argv[argv_start].startswith("--"):
        if sys.argv[argv_start] == "--debug":
            debug_mode = True
            argv_start += 1
        elif sys.argv[argv_start] == "--stateless":
            stateless_mode = True
            argv_start += 1
        elif sys.argv[argv_start] == "--image":
            argv_start += 1
            if argv_start >= len(sys.argv):
                print("Error: --image flag requires a file path")
                sys.exit(1)
            image_path = sys.argv[argv_start]
            argv_start += 1
        else:
            print(f"Unknown flag: {sys.argv[argv_start]}")
            sys.exit(1)
    
    if argv_start >= len(sys.argv):
        print("Error: No query provided")
        print("Usage: python query.py [--debug] [--stateless] [--image PATH] \"<your query>\"")
        sys.exit(1)
    
    # Join all arguments after flags as the query (handles queries with spaces)
    query = " ".join(sys.argv[argv_start:])
    
    # Run the query function
    run_query(query, debug=debug_mode, stateless=stateless_mode, image_path=image_path)
