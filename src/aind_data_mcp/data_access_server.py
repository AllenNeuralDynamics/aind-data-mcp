"""MCP server for AIND data access."""

from pathlib import Path

# Import tool modules — side-effect registers all @mcp.tool() decorators
from .mcp_instance import mcp  # noqa: F401
from . import example_tools  # noqa: F401
from . import nwb_tools  # noqa: F401
from . import query_tools  # noqa: F401
from . import schema_tools  # noqa: F401


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


def main():
    """Main entry point for the MCP server."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
