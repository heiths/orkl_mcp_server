"""MCP server for the ORKL threat intelligence API."""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, TypeVar, AsyncIterator, cast

from mcp.server.fastmcp import Context, FastMCP

from orkl_mcp.api_client import OrklApiClient
from orkl_mcp.config import OrklConfig, load_config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("orkl_mcp")

# Type for context manager
T = TypeVar("T")

# Global API client for resources
_global_api_client: Optional[OrklApiClient] = None


class AppContext:
    """Application context for the MCP server."""

    def __init__(self, api_client: OrklApiClient, config: OrklConfig) -> None:
        """Initialize the application context.

        Args:
            api_client: ORKL API client.
            config: ORKL configuration.
        """
        self.api_client = api_client
        self.config = config


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """Manage the application lifespan.

    Args:
        server: FastMCP server instance.

    Yields:
        Application context.
    """
    config = load_config()

    # Create API client
    api_client = OrklApiClient(config)

    logger.info("ORKL MCP server starting up...")
    context = AppContext(api_client=api_client, config=config)

    # Initialize the API client and check connectivity
    try:
        await api_client.get_library_info(use_cache=False)
        logger.info("Successfully connected to ORKL API")
    except Exception as e:
        logger.warning(f"Failed to connect to ORKL API: {str(e)}")

    try:
        yield context
    finally:
        # Clean up
        logger.info("ORKL MCP server shutting down...")
        await api_client.close()


# Create FastMCP server
mcp = FastMCP(
    "ORKL Threat Intelligence",
    lifespan=app_lifespan,
    dependencies=["httpx", "pydantic"],
)


# Define MCP tools

@mcp.tool()
async def fetch_latest_threat_reports(
        ctx: Context,
        limit: Optional[int] = 10,
        order_by: str = "created_at",
        order: str = "desc",
) -> Dict[str, Any]:
    """Retrieve the most recent threat intelligence reports from the ORKL library.

    Args:
        ctx: MCP context.
        limit: Maximum number of reports to fetch (default: 10).
        order_by: Date field to order by (default: 'created_at').
            Valid values: 'created_at', 'updated_at', 'file_creation_date', 'file_modification_date'.
        order: Order direction (default: 'desc').
            Valid values: 'asc', 'desc'.

    Returns:
        A dictionary containing the threat reports.
    """
    # Validate inputs
    valid_order_by = ["created_at", "updated_at", "file_creation_date", "file_modification_date"]
    if order_by not in valid_order_by:
        raise ValueError(
            f"Invalid order_by value: {order_by}. Valid values: {', '.join(valid_order_by)}"
        )

    valid_order = ["asc", "desc"]
    if order not in valid_order:
        raise ValueError(
            f"Invalid order value: {order}. Valid values: {', '.join(valid_order)}"
        )

    # Get API client from context
    api_client = ctx.request_context.lifespan_context.api_client

    # Fetch data
    try:
        response = await api_client.get_library_entries(
            limit=limit,
            order_by=order_by,
            order=order,
        )
        return response["data"]
    except Exception as e:
        logger.error(f"Error fetching threat reports: {str(e)}")
        return {"error": str(e)}


@mcp.tool()
async def fetch_threat_report_details(ctx: Context, report_id: str) -> Dict[str, Any]:
    """Retrieve detailed information about a specific threat report by ID.

    Args:
        ctx: MCP context.
        report_id: The ID (UUID) of the threat report to fetch.

    Returns:
        A dictionary containing the detailed threat report.
    """
    if not report_id:
        raise ValueError("report_id is required")

    # Get API client from context
    api_client = ctx.request_context.lifespan_context.api_client

    # Fetch data
    try:
        response = await api_client.get_library_entry(report_id)
        return response["data"]
    except Exception as e:
        logger.error(f"Error fetching report {report_id}: {str(e)}")
        return {"error": str(e)}


@mcp.tool()
async def fetch_threat_report_by_hash(ctx: Context, sha1_hash: str) -> Dict[str, Any]:
    """Retrieve a specific threat report using its SHA1 hash.

    Args:
        ctx: MCP context.
        sha1_hash: The SHA1 hash of the threat report to fetch.

    Returns:
        A dictionary containing the detailed threat report.
    """
    if not sha1_hash:
        raise ValueError("sha1_hash is required")

    # Get API client from context
    api_client = ctx.request_context.lifespan_context.api_client

    # Fetch data
    try:
        response = await api_client.get_library_entry_by_sha1(sha1_hash)
        return response["data"]
    except Exception as e:
        logger.error(f"Error fetching report with hash {sha1_hash}: {str(e)}")
        return {"error": str(e)}


@mcp.tool()
async def search_threat_reports(
        ctx: Context, query: str, full: bool = False, limit: int = 1000
) -> Dict[str, Any]:
    """Search the ORKL library for threat reports matching specific criteria.

    Args:
        ctx: MCP context.
        query: Search query string (use quoted terms for exact matches).
        full: Whether to return the full report including plain-text (default: False).
        limit: Maximum number of reports to return (default: 1000).

    Returns:
        A dictionary containing the search results.
    """
    if not query:
        raise ValueError("query is required")

    # Get API client from context
    api_client = ctx.request_context.lifespan_context.api_client

    # Fetch data
    try:
        response = await api_client.search_library(query, full, limit)
        return response["data"]
    except Exception as e:
        logger.error(f"Error searching reports with query '{query}': {str(e)}")
        return {"error": str(e)}


@mcp.tool()
async def get_library_info(ctx: Context) -> Dict[str, Any]:
    """Retrieve general information about the ORKL threat intelligence library.

    Args:
        ctx: MCP context.

    Returns:
        A dictionary containing library statistics and information.
    """
    # Get API client from context
    api_client = ctx.request_context.lifespan_context.api_client

    # Fetch data
    try:
        response = await api_client.get_library_info()
        return response["data"]
    except Exception as e:
        logger.error(f"Error fetching library info: {str(e)}")
        return {"error": str(e)}


@mcp.tool()
async def get_library_version(ctx: Context) -> Dict[str, Any]:
    """Retrieve the latest version information for the ORKL library.

    Args:
        ctx: MCP context.

    Returns:
        A dictionary containing version details and metadata.
    """
    # Get API client from context
    api_client = ctx.request_context.lifespan_context.api_client

    # Fetch data
    try:
        response = await api_client.get_library_version()
        return response["data"]
    except Exception as e:
        logger.error(f"Error fetching library version: {str(e)}")
        return {"error": str(e)}


@mcp.tool()
async def fetch_threat_actors(ctx: Context) -> Dict[str, Any]:
    """Retrieve a list of all threat actors in the ORKL database.

    Args:
        ctx: MCP context.

    Returns:
        A dictionary containing threat actor profiles.
    """
    # Get API client from context
    api_client = ctx.request_context.lifespan_context.api_client

    # Fetch data
    try:
        response = await api_client.get_threat_actor_entries()
        return response["data"]
    except Exception as e:
        logger.error(f"Error fetching threat actors: {str(e)}")
        return {"error": str(e)}


@mcp.tool()
async def fetch_threat_actor_details(ctx: Context, actor_id: str) -> Dict[str, Any]:
    """Retrieve detailed information about a specific threat actor.

    Args:
        ctx: MCP context.
        actor_id: The ID (UUID) of the threat actor to fetch.

    Returns:
        A dictionary containing the detailed threat actor profile.
    """
    if not actor_id:
        raise ValueError("actor_id is required")

    # Get API client from context
    api_client = ctx.request_context.lifespan_context.api_client

    # Fetch data
    try:
        response = await api_client.get_threat_actor_entry(actor_id)
        return response["data"]
    except Exception as e:
        logger.error(f"Error fetching threat actor {actor_id}: {str(e)}")
        return {"error": str(e)}


@mcp.tool()
async def fetch_sources(ctx: Context) -> Dict[str, Any]:
    """Retrieve a list of all sources in the ORKL database.

    Args:
        ctx: MCP context.

    Returns:
        A dictionary containing source profiles.
    """
    # Get API client from context
    api_client = ctx.request_context.lifespan_context.api_client

    # Fetch data
    try:
        response = await api_client.get_source_entries()
        return response["data"]
    except Exception as e:
        logger.error(f"Error fetching sources: {str(e)}")
        return {"error": str(e)}


@mcp.tool()
async def fetch_source_details(ctx: Context, source_id: str, full: bool = False) -> Dict[str, Any]:
    """Retrieve detailed information about a specific source.

    Args:
        ctx: MCP context.
        source_id: The ID (UUID) of the source to fetch.
        full: Whether to return the full source including related reports (default: False).

    Returns:
        A dictionary containing the detailed source profile.
    """
    if not source_id:
        raise ValueError("source_id is required")

    # Get API client from context
    api_client = ctx.request_context.lifespan_context.api_client

    # Fetch data
    try:
        response = await api_client.get_source_entry(source_id, full)
        return response["data"]
    except Exception as e:
        logger.error(f"Error fetching source {source_id}: {str(e)}")
        return {"error": str(e)}


@mcp.tool()
async def clear_cache(
        ctx: Context, category: str = "all"
) -> Dict[str, str]:
    """Clear the server's cache for more up-to-date information retrieval.

    Args:
        ctx: MCP context.
        category: Resource category to clear (default: 'all').
            Valid values: 'threat_reports', 'threat_actors', 'sources', 'all'.

    Returns:
        A dictionary containing the operation result.
    """
    valid_categories = ["threat_reports", "threat_actors", "sources", "all"]
    if category not in valid_categories:
        raise ValueError(
            f"Invalid category: {category}. Valid values: {', '.join(valid_categories)}"
        )

    # Get API client from context
    api_client = ctx.request_context.lifespan_context.api_client

    # Clear cache
    try:
        api_client.clear_cache(category)
        return {"status": "success", "message": "Cache cleared"}
    except Exception as e:
        logger.error(f"Error clearing cache: {str(e)}")
        return {"error": str(e)}


# Define MCP resources
@mcp.resource("threat_reports://{report_id}")
async def get_threat_report_resource(
        report_id: str
) -> Dict[str, Any]:
    """Provide direct access to specific threat reports.

    Args:
        report_id: The ID of the threat report to fetch.

    Returns:
        The detailed threat report data.
    """
    # Use a global API client for resource access
    global _global_api_client
    if not _global_api_client:
        _global_api_client = OrklApiClient(load_config())

    # Fetch data
    try:
        response = await _global_api_client.get_library_entry(report_id)
        return response["data"]
    except Exception as e:
        logger.error(f"Error fetching report {report_id}: {str(e)}")
        return {"error": str(e)}


@mcp.resource("threat_actors://{actor_id}")
async def get_threat_actor_resource(
        actor_id: str
) -> Dict[str, Any]:
    """Provide direct access to specific threat actor profiles.

    Args:
        actor_id: The ID of the threat actor to fetch.

    Returns:
        The detailed threat actor information.
    """
    # Use a global API client for resource access
    global _global_api_client
    if not _global_api_client:
        _global_api_client = OrklApiClient(load_config())

    # Fetch data
    try:
        response = await _global_api_client.get_threat_actor_entry(actor_id)
        return response["data"]
    except Exception as e:
        logger.error(f"Error fetching threat actor {actor_id}: {str(e)}")
        return {"error": str(e)}


@mcp.resource("sources://{source_id}")
async def get_source_resource(
        source_id: str
) -> Dict[str, Any]:
    """Provide direct access to specific source information.

    Args:
        source_id: The ID of the source to fetch.

    Returns:
        The detailed source data.
    """
    # Use a global API client for resource access
    global _global_api_client
    if not _global_api_client:
        _global_api_client = OrklApiClient(load_config())

    # Fetch data
    try:
        response = await _global_api_client.get_source_entry(source_id)
        return response["data"]
    except Exception as e:
        logger.error(f"Error fetching source {source_id}: {str(e)}")
        return {"error": str(e)}


def main():
    """Entry point for the ORKL MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
