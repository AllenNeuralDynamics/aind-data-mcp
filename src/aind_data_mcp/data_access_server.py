"""MCP server for AIND data access."""

from importlib.resources import files

# Import tool modules — side-effect registers all @mcp.tool() decorators.
from .mcp_instance import mcp  # noqa: F401
from . import nwb_tools  # noqa: F401
from . import query_tools  # noqa: F401
from . import schema_tools  # noqa: F401
from . import cache_tools  # noqa: F401


@mcp.resource("resource://aind_api")
def get_aind_data_access_api() -> str:
    """
    Get context on how to use the AIND data access api to show users how to
    wrap tool calls
    """
    return (
        files("aind_data_mcp.resources")
        .joinpath("aind_api_prompt.txt")
        .read_text(encoding="utf-8")
    )


@mcp.resource("resource://load_nwbfile")
def get_nwbfile_download_script() -> str:
    """
    Get context on how to return an NWBfile from the /data folder in current repository
    """
    return (
        files("aind_data_mcp.resources")
        .joinpath("load_nwbfile.txt")
        .read_text(encoding="utf-8")
    )


@mcp.resource("resource://cache_tables")
def get_cache_tables() -> str:
    """
    Schema for the biodata_cache cached tables (title and description for
    every column in every table). Use this resource to understand what data
    is available in the fast S3-backed tables before deciding whether to use
    cache tools or fall back to MongoDB queries.
    """
    from biodata_cache import get_cache_registry

    registry = get_cache_registry()
    return registry.model_dump_json(indent=2)


@mcp.resource("resource://cache_api")
def get_cache_api_prompt() -> str:
    """
    Guidance on how to use biodata_cache in Python scripts alongside
    aind-data-access-api. Covers the fast-table-first pattern, $in query
    batching for large result sets, and example scripts.
    """
    return (
        files("aind_data_mcp.resources")
        .joinpath("cache_api_prompt.txt")
        .read_text(encoding="utf-8")
    )


def main():
    """Main entry point for the MCP server."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
