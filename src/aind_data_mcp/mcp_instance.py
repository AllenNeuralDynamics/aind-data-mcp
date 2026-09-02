"""Central MCP instance and MongoDB client factory."""

from aind_data_access_api.document_db import MetadataDbClient
from fastmcp import FastMCP

SERVER_INSTRUCTIONS = """AIND data MCP ready tool manifest. This manifest is published with the MCP
initialize response; use these tools after initialization.

Query tools:
- get_records(filter, projection, limit, include_metadata): retrieve a small
    set of metadata records using exact leaf paths.
- aggregation_retrieval(agg_pipeline, field_aliases, include_metadata): run
    grouped, sorted, or otherwise transformed MongoDB queries.
- count_records(filter): count records matching a simple filter.
- flatten_records(records, depth): flatten returned nested records.

Schema and discovery:
- get_schema_context(node, path, detail): list compact V2 paths by default;
    request detail="example" for a small opt-in example.
- get_modality_types(): list modality names and abbreviations.

Cache tools should be preferred for asset-basics, project, subject, and
modality lookups when their descriptions match the request. Use the NWB tools
only when an asset file must be inspected.
"""

mcp = FastMCP("aind_data_mcp", instructions=SERVER_INSTRUCTIONS)


def setup_mongodb_client():
    """Set up and return the MongoDB client"""

    return MetadataDbClient(
        host="api.allenneuraldynamics.org",
        version="v2",
    )
