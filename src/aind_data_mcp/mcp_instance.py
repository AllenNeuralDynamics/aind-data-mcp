"""Central MCP instance and MongoDB client factory."""

from aind_data_access_api.document_db import MetadataDbClient
from fastmcp import FastMCP

mcp = FastMCP("aind_data_mcp")


def setup_mongodb_client():
    """Set up and return the MongoDB client"""

    return MetadataDbClient(
        host="api.allenneuraldynamics.org",
        version="v2",
    )

