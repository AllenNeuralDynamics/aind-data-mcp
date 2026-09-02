"""MongoDB query tools."""

from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Dict, NoReturn, Optional, Union

from fastmcp.exceptions import ToolError

from .mcp_instance import mcp, setup_mongodb_client


def _raise_tool_error(tool_name: str, ex: Exception) -> NoReturn:
    raise ToolError(f"{tool_name} failed: {type(ex).__name__}: {ex}") from ex


def _result_metadata(result: list[dict]) -> dict[str, str]:
    serialized = json.dumps(
        result, sort_keys=True, separators=(",", ":"), default=str
    )
    marker = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    return {
        "snapshot_marker": f"query-result-sha256:{marker}",
        "snapshot_scope": "returned query result; the upstream API exposes no global database revision",
        "api_version": "v2",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
    }


def _with_metadata(result: list[dict], include_metadata: bool):
    if not include_metadata:
        return result
    return {"records": result, "metadata": _result_metadata(result)}


@mcp.tool()
def get_records(
    filter: Optional[dict] = None,
    projection: Optional[dict] = None,
    limit: int = 5,
    include_metadata: bool = False,
):
    """Retrieve metadata documents with a simple MongoDB filter and projection.

    Use this for straightforward dataset and asset lookups. Common V2 leaf
    paths are ``subject.subject_id``, ``subject.subject_details.sex`` (legacy
    alias ``subject.sex``), ``subject.subject_details.date_of_birth``,
    ``subject.subject_details.strain.name``,
    ``subject.subject_details.genotype``,
    ``subject.subject_details.breeding_info.maternal_genotype``,
    ``subject.subject_details.breeding_info.paternal_genotype``,
    ``data_description.project_name``, ``data_description.data_level``,
    ``data_description.modalities.abbreviation``,
    ``acquisition.acquisition_start_time``, and
    ``acquisition.acquisition_end_time``.

    Use leaf paths instead of parent projections. For example, projecting
    ``procedures: 1`` or ``acquisition: 1`` returns the entire nested object.
    A compact procedures projection is
    ``{"procedures.subject_procedures.procedures.injection_materials.name": 1,
    "_id": 0}``.

    Args:
        filter: MongoDB query filter. For example,
            ``{"subject.subject_details.sex": "Male"}``. An empty filter
            returns all documents.
        projection: Fields to include or exclude. Use 1 to include a field
            and 0 to exclude it. An empty projection returns all fields.
        limit: Maximum number of records to retrieve. Keep this at or below
            100 when possible.
        include_metadata: If true, return ``{"records": [...], "metadata":
            {...}}`` with a reproducible marker for the exact result set and
            the AIND API version.

    Returns:
        A list of matching documents, or a dictionary containing ``records``
        and ``metadata`` when ``include_metadata`` is true.

    Do not use this for grouping, calculations across documents, joins, or
    full data-asset retrievals. Use ``aggregation_retrieval`` for those cases.
    """

    try:
        docdb_api_client = setup_mongodb_client()
        records = docdb_api_client.retrieve_docdb_records(
            filter_query=filter or {}, projection=projection or {}, limit=limit
        )
        return _with_metadata(records, include_metadata)

    except Exception as ex:
        _raise_tool_error("get_records", ex)


@mcp.tool()
def aggregation_retrieval(
    agg_pipeline: list,
    field_aliases: Optional[dict[str, list[str]]] = None,
    include_metadata: bool = False,
):
    """Run a MongoDB aggregation pipeline for transformed metadata queries.

    Use ``get_schema_context`` for compact V2 field paths. Common grouping
    fields are ``data_description.project_name``,
    ``data_description.data_level``,
    ``data_description.modalities.abbreviation``, and
    ``subject.subject_details.sex``. Parent projections such as
    ``{"acquisition": 1}`` return the entire nested object, so project only
    required leaf paths.

    Direct recipes:
    - Project counts: group by ``$data_description.project_name``, sum 1,
      sort by ``count`` descending, and limit to 10.
    - Data-level counts: group by ``$data_description.data_level`` and sum 1.
    - Subject-sex counts: group by
      ``$subject.subject_details.sex``. To include legacy ``$subject.sex``
      values in one call, use ``field_aliases`` with the logical name
      ``subject_sex`` and group by ``$_aind_aliases.subject_sex``.

    Args:
        agg_pipeline: MongoDB aggregation stages such as ``$match``,
            ``$project``, ``$group``, ``$sort``, and ``$unwind``.
        field_aliases: Map a logical field name to ordered MongoDB paths. The
            tool creates ``_aind_aliases`` using the first non-null value.
            For legacy sex data, use ``{"subject_sex":
            ["subject.subject_details.sex", "subject.sex"]}`` and group by
            ``$_aind_aliases.subject_sex``.
        include_metadata: If true, return ``{"records": [...], "metadata":
            {...}}`` with a reproducible result marker, API version, and
            retrieval time. The upstream API exposes no global database
            revision.

    Returns:
        A list of aggregation documents, or a dictionary containing
        ``records`` and ``metadata`` when ``include_metadata`` is true.
        Tool failures raise ``ToolError``.

    Include a ``$project`` stage early to reduce data transfer. Avoid
    ``$map`` in ``$project`` stages unless the input is an array.
    """
    try:
        docdb_api_client = setup_mongodb_client()
        if field_aliases:
            alias_fields = {}
            for logical_name, paths in field_aliases.items():
                if not paths:
                    raise ValueError(
                        f"field alias '{logical_name}' must include at least one path"
                    )
                expression: str | dict = f"${paths[-1]}"
                for path in reversed(paths[:-1]):
                    expression = {"$ifNull": [f"${path}", expression]}
                alias_fields[logical_name] = expression
            agg_pipeline = [
                {"$set": {"_aind_aliases": alias_fields}},
                *agg_pipeline,
            ]
        result = docdb_api_client.aggregate_docdb_records(
            pipeline=agg_pipeline
        )
        return _with_metadata(result, include_metadata)

    except Exception as ex:
        _raise_tool_error("aggregation_retrieval", ex)


@mcp.tool()
def count_records(filter: dict | None = None):
    """
    Retrieves number of documents from MongoDB database using
    a simple MongoDB filter

    WHEN TO USE THIS FUNCTION:
    - For counting number of documents  based on a straightforward criteria

    NOT RECOMMENDED FOR:
    - Complex data transformations (use aggregation_retrieval instead)

    Parameters
    ----------
    filter : dict, optional
        MongoDB query filter to narrow down the documents to retrieve.
        Example: {"subject.subject_details.sex": "Male"}
        If empty dict object, returns all documents.

    Returns
    -------
    dict
        Object containing ``total_record_count`` and
        ``filtered_record_count``.

    """
    try:
        docdb_api_client = setup_mongodb_client()
        count = docdb_api_client._count_records(filter_query=filter or {})
        return count

    except Exception as ex:
        _raise_tool_error("count_records", ex)


@mcp.tool()
def get_summary(_id: str):
    """
    Get an LLM-generated summary for a data asset, based on the _id field
    """
    try:
        docdb_api_client = setup_mongodb_client()
        result = docdb_api_client.generate_data_summary(_id)
        return result

    except Exception as ex:
        _raise_tool_error("get_summary", ex)


def _flatten_dict(
    d: Union[Dict, list],
    parent_key: str = "",
    sep: str = ".",
    depth: Optional[int] = None,
    current_depth: int = 0,
) -> Dict[str, Any]:
    """
    Recursively flattens a nested dict/list into dot-notation up to `depth`.
    If depth=None, fully flatten.
    """
    items = []
    if isinstance(d, dict) and (depth is None or current_depth < depth):
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            items.extend(
                _flatten_dict(
                    v, new_key, sep, depth, current_depth + 1
                ).items()
            )
    elif isinstance(d, list) and (depth is None or current_depth < depth):
        for i, v in enumerate(d):
            new_key = f"{parent_key}{sep}{i}"
            items.extend(
                _flatten_dict(
                    v, new_key, sep, depth, current_depth + 1
                ).items()
            )
    else:
        items.append((parent_key, d))
    return dict(items)


@mcp.tool()
def flatten_records(
    records: list[dict],
    depth: Optional[int] = None,
) -> list[dict]:
    """
    Flatten a list of records into dot-notation.

    Args:
        records (list): List of dicts.
        depth (int, optional): How deep to flatten.

    Returns:
        list[dict]: Each record flattened.
    """

    try:
        return [_flatten_dict(record, depth=depth) for record in records]

    except Exception as ex:
        _raise_tool_error("flatten_records", ex)


@mcp.tool()
def get_project_names() -> list:
    """
    Exposes project names in database
    """
    try:
        docdb_api_client = setup_mongodb_client()
        return docdb_api_client.aggregate_docdb_records(
            pipeline=[
                {
                    "$match": {
                        "data_description.project_name": {
                            "$exists": True,
                            "$ne": None,
                        }
                    }
                },
                {"$group": {"_id": "$data_description.project_name"}},
                {"$sort": {"_id": 1}},
                {"$project": {"_id": 0, "project_name": "$_id"}},
            ]
        )
    except Exception as ex:
        _raise_tool_error("get_project_names", ex)
