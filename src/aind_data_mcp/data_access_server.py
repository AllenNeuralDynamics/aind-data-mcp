"""MCP server for AIND data access."""

from pathlib import Path

# Import tool modules — side-effect registers all @mcp.tool() decorators
from .mcp_instance import mcp  # noqa: F401
from . import example_tools  # noqa: F401
from . import nwb_tools  # noqa: F401
from . import query_tools  # noqa: F401
from . import schema_tools  # noqa: F401
from . import squirrel_tools  # noqa: F401


@mcp.resource("resource://aind_api")
def get_aind_data_access_api() -> str:
    """
    Get context on how to use the AIND data access api to show users how to
    wrap tool calls
    """
    resource_path = Path(__file__).parent / "resources" / "aind_api_prompt.txt"
    with open(resource_path, "r") as file:
        file_content = file.read()
    return file_content


@mcp.resource("resource://load_nwbfile")
def get_nwbfile_download_script() -> str:
    """
    Get context on how to return an NWBfile from the /data folder in current repository
    """
    resource_path = Path(__file__).parent / "resources" / "load_nwbfile.txt"
    with open(resource_path, "r") as file:
        file_content = file.read()
    return file_content


@mcp.resource("resource://squirrel_tables")
def get_squirrel_tables() -> str:
    """
    Schema for the zombie_squirrel cached tables (title and description for
    every column in every table). Use this resource to understand what data
    is available in the fast S3-backed tables before deciding whether to use
    squirrel tools or fall back to MongoDB queries.
    """
    resource_path = Path(__file__).parent / "resources" / "squirrel.json"
    with open(resource_path, "r") as file:
        file_content = file.read()
    return file_content


@mcp.resource("resource://squirrel_api")
def get_squirrel_api_prompt() -> str:
    """
    Guidance on how to use zombie_squirrel in Python scripts alongside
    aind-data-access-api. Covers the fast-table-first pattern, $in query
    batching for large result sets, and example scripts.
    """
    resource_path = (
        Path(__file__).parent / "resources" / "squirrel_api_prompt.txt"
    )
    with open(resource_path, "r") as file:
        file_content = file.read()
    return file_content


def main():
    """Main entry point for the MCP server."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
