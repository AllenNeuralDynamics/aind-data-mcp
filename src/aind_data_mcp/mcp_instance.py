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

Routing rules:
- Use get_asset_basics for asset-level filters, fields, dates, paging, and
    totals. It pushes predicates to the cache and returns a compact projection.
- Use get_records for a small exact lookup or nested leaf fields; use
    aggregation_retrieval for grouping, distinct values, counts, or unwinding
    arrays. Do not fetch records or call count_records when one aggregation
    already answers the question.
- Canonical aggregation paths include
    data_description.data_level, data_description.project_name,
    data_description.modalities.abbreviation, and
    subject.subject_details.sex. Use field_aliases only when combining a
    legacy path such as subject.sex with its V2 replacement.
- Use get_schema_context only when the needed path is not listed above or in
    a tool description. Request detail="example" only when a concrete shape
    is necessary.

Use the NWB tools only when an asset file must be inspected.
"""

mcp = FastMCP("aind_data_mcp", instructions=SERVER_INSTRUCTIONS)


def setup_mongodb_client():
    """Set up and return the MongoDB client"""

    return MetadataDbClient(
        host="api.allenneuraldynamics.org",
        version="v2",
    )
