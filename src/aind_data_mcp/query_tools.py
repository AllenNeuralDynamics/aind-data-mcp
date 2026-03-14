"""MongoDB query tools."""

from typing import Any, Dict, Optional, Union

from .mcp_instance import mcp, setup_mongodb_client


@mcp.tool()
def get_records(filter: dict = {}, projection: dict = {}, limit: int = 5):
    """
    Retrieves documents from MongoDB database using simple filters
    and projections.

    WHEN TO USE THIS FUNCTION:
    - For straightforward document retrieval based on specific criteria
    - When you need only a subset of fields from documents
    - When the query logic doesn't require multi-stage processing
    - For better performance with simpler queries

    NOT RECOMMENDED FOR:
    - Complex data transformations (use aggregation_retrieval instead)
    - Grouping operations or calculations across documents
    - Joining or relating data across collections
    - Trying to fetch an entire data asset (data assets are long and
    will clog up the context window)

    Parameters
    ----------
    filter : dict
        MongoDB query filter to narrow down the documents to retrieve.
        Example: {"subject.sex": "Male"}
        If empty dict object, returns all documents.

    projection : dict
        Fields to include or exclude in the returned documents.
        Use 1 to include a field, 0 to exclude.
        Example: {"subject.genotype": 1, "_id": 0}
        will return only the genotype field.
        If empty dict object, returns all documents.

    limit: int
        Limit retrievals to a reasonable number, try to not exceed 100

    Returns
    -------
    list
        List of dictionary objects representing the matching documents.
        Each dictionary contains the requested fields based on the projection.

    """

    docdb_api_client = setup_mongodb_client()

    try:
        records = docdb_api_client.retrieve_docdb_records(
            filter_query=filter, projection=projection, limit=limit
        )
        return records

    except Exception as ex:
        template = "An exception of type {0} occurred. Arguments:\n{1!r}"
        message = template.format(type(ex).__name__, ex.args)
        return message



@mcp.tool()
def aggregation_retrieval(agg_pipeline: list):
    """
    Executes a MongoDB aggregation pipeline for complex data transformations
    and analysis.

    For additional context on how to create filters and projections,
    use the retrieve_schema_context tool.

    WHEN TO USE THIS FUNCTION:
    - When you need to perform multi-stage data processing operations
    - For complex queries requiring grouping, filtering, sorting in sequence
    - When you need to calculate aggregated values (sums, averages, counts)
    - For data transformation operations that can't be done with simple queries

    NOT RECOMMENDED FOR:
    - Simple document retrieval (use get_records instead)
    - When you only need to filter data without transformations

    Parameters
    ----------
    agg_pipeline : list
        A list of dictionary objects representing MongoDB aggregation stages.
        Each stage should be a valid MongoDB aggregation operator.
        Common stages include: $match, $project, $group, $sort, $unwind.

    Returns
    -------
    list
        Returns a list of documents resulting from the aggregation pipeline.
        If an error occurs, returns an error message string describing
        the exception.

    Notes
    -----
    - Include a $project stage early in the pipeline to reduce data transfer
    - Avoid using $map operator in $project stages as it requires array inputs
    """
    docdb_api_client = setup_mongodb_client()

    try:
        result = docdb_api_client.aggregate_docdb_records(
            pipeline=agg_pipeline
        )
        return result

    except Exception as ex:
        template = "An exception of type {0} occurred. Arguments:\n{1!r}"
        message = template.format(type(ex).__name__, ex.args)
        return message



@mcp.tool()
def count_records(filter: dict):
    """
    Retrieves number of documents from MongoDB database using
    a simple MongoDB filter

    WHEN TO USE THIS FUNCTION:
    - For counting number of documents  based on a straightforward criteria

    NOT RECOMMENDED FOR:
    - Complex data transformations (use aggregation_retrieval instead)

    Parameters
    ----------
    filter : dict
        MongoDB query filter to narrow down the documents to retrieve.
        Example: {"subject.sex": "Male"}
        If empty dict object, returns all documents.

    Returns
    -------
    int
        number of records retrieved

    """
    docdb_api_client = setup_mongodb_client()
    try:
        count = docdb_api_client._count_records(filter_query=filter)
        return count

    except Exception as ex:
        template = "An exception of type {0} occurred. Arguments:\n{1!r}"
        message = template.format(type(ex).__name__, ex.args)
        return message



@mcp.tool()
def get_summary(_id: str):
    """
    Get an LLM-generated summary for a data asset, based on the _id field
    """
    docdb_api_client = setup_mongodb_client()

    try:
        result = docdb_api_client.generate_data_summary(_id)
        return result

    except Exception as ex:
        template = "An exception of type {0} occurred. Arguments:\n{1!r}"
        message = template.format(type(ex).__name__, ex.args)
        return message



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
    filter,
    limit,
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

    docdb_api_client = setup_mongodb_client()

    try:
        records = docdb_api_client.retrieve_docdb_records(
            filter_query=filter, limit=limit
        )
        return [_flatten_dict(record, depth=depth) for record in records]

    except Exception as ex:
        template = "An exception of type {0} occurred. Arguments:\n{1!r}"
        message = template.format(type(ex).__name__, ex.args)
        return message


@mcp.tool()
def get_project_names() -> list:
    """
    Exposes project names in database
    """
    docdb_api_client = setup_mongodb_client()
    names = docdb_api_client.aggregate_docdb_records(
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
    return names


