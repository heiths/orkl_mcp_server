#!/usr/bin/env python
"""Run the ORKL MCP server."""
import logging
import sys
from typing import NoReturn

from dotenv import load_dotenv

from orkl_mcp.config import load_config
from orkl_mcp.server import mcp

logger = logging.getLogger("orkl_mcp")


def setup_environment() -> None:
    """Configure environment and logging for the application."""
    # Load environment variables from .env file
    load_dotenv()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def main() -> None:
    """Run the MCP server with proper configuration."""
    logger.info("Loading ORKL MCP configuration...")
    config = load_config()

    logger.info("Starting ORKL MCP server...")
    try:
        # Call mcp.run directly as it handles its own async execution
        mcp.run()
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        raise


def run_server() -> NoReturn:
    """Entry point function that handles the server lifecycle."""
    setup_environment()

    try:
        # Run main as a regular function since mcp.run manages its own async operations
        main()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Server error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    run_server()
