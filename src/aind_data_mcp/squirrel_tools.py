"""
MCP tools backed by zombie_squirrel cached tables.

These tools query pre-built Parquet tables hosted on S3 for fast lookups
of commonly-needed fields. They are significantly faster than the MongoDB
API for filtering by project, subject, modality, data level, or dates.

Use these tools FIRST whenever the query only needs fields available in
the tables. Fetch full MongoDB records afterwards only when richer metadata
is required.
"""

from typing import Optional

import pandas as pd
from zombie_squirrel import (
    asset_basics,
    assets_smartspim,
    qc,
    raw_to_derived,
    source_data,
    unique_project_names,
    unique_subject_ids,
)

from .mcp_instance import mcp


def _to_serialisable(value):
    """Recursively convert numpy/pandas types to plain Python types."""
    import math

    import numpy as np

    if isinstance(value, np.ndarray):
        return [_to_serialisable(v) for v in value.tolist()]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if np.isnan(value) else float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


def _df_to_records(df: pd.DataFrame) -> list[dict]:
    """Convert a DataFrame to a JSON-serializable list of dicts."""
    raw = df.to_dict("records")
    return [
        {k: _to_serialisable(v) for k, v in row.items()} for row in raw
    ]


@mcp.tool()
def get_asset_basics(
    subject_id: Optional[str] = None,
    project_name: Optional[str] = None,
    modality: Optional[str] = None,
    data_level: Optional[str] = None,
    name_contains: Optional[str] = None,
    limit: int = 200,
) -> list[dict] | str:
    """
    Query the zombie_squirrel asset_basics cached table.

    Returns one row per data asset with lightweight metadata. Covers every
    asset in the database and is updated incrementally, so it is always
    nearly current.

    WHEN TO USE THIS TOOL FIRST:
    - Discovering assets for a subject, project, modality, or data level
    - Counting or listing assets before deciding whether to fetch full records
    - Getting asset names / _ids for use in downstream MongoDB queries

    NOT A REPLACEMENT FOR get_records / aggregation_retrieval when:
    - Richer nested fields are required (e.g. full subject, procedures, etc.)
    - The query involves fields not present in this table

    Available columns (see resource://squirrel_tables for full schema):
        _id, name, modalities, project_name, data_level, subject_id,
        acquisition_start_time, acquisition_end_time, code_ocean,
        process_date, genotype, location

    Parameters
    ----------
    subject_id : str, optional
        Filter to assets belonging to this subject ID (exact match).
    project_name : str, optional
        Filter to assets with this project name (exact match).
    modality : str, optional
        Filter to assets whose modalities string contains this substring,
        e.g. "ecephys", "behavior", "ophys". Case-insensitive.
    data_level : str, optional
        Filter by data level, e.g. "raw" or "derived".
    name_contains : str, optional
        Filter to assets whose name contains this substring. Case-insensitive.
    limit : int
        Maximum number of rows to return (default 200).

    Returns
    -------
    list[dict]
        Matching asset rows, each containing the columns listed above.
    """
    try:
        df = asset_basics()

        if subject_id is not None:
            df = df[df["subject_id"] == str(subject_id)]
        if project_name is not None:
            df = df[df["project_name"] == project_name]
        if modality is not None:
            df = df[
                df["modalities"].str.contains(
                    modality, case=False, na=False
                )
            ]
        if data_level is not None:
            df = df[df["data_level"] == data_level]
        if name_contains is not None:
            df = df[
                df["name"].str.contains(
                    name_contains, case=False, na=False
                )
            ]

        df = df.head(limit)
        return _df_to_records(df)

    except Exception as ex:
        return f"Error in get_asset_basics: {type(ex).__name__}: {ex}"


@mcp.tool()
def get_unique_project_names() -> list[str] | str:
    """
    Return all unique project names across the data asset database.

    Use this tool to:
    - Discover what projects exist before filtering with get_asset_basics
    - Validate the exact spelling of a project name

    Returns
    -------
    list[str]
        Sorted list of unique project name strings.
    """
    try:
        return sorted(p for p in unique_project_names() if p is not None)
    except Exception as ex:
        return f"Error in get_unique_project_names: {type(ex).__name__}: {ex}"


@mcp.tool()
def get_unique_subject_ids() -> list[str] | str:
    """
    Return all unique subject IDs across the data asset database.

    Use this tool to:
    - Check whether a subject ID exists before deeper queries
    - Enumerate all subjects for a bulk analysis

    Returns
    -------
    list[str]
        List of unique subject ID strings.
    """
    try:
        return [str(s) for s in unique_subject_ids() if pd.notna(s)]
    except Exception as ex:
        return f"Error in get_unique_subject_ids: {type(ex).__name__}: {ex}"


@mcp.tool()
def get_source_data_table(
    source_asset_name: Optional[str] = None,
    pipeline_name: Optional[str] = None,
    limit: int = 200,
) -> list[dict] | str:
    """
    Query the zombie_squirrel source_data cached table.

    Returns one row per derived asset per source data entry, mapping each
    derived asset back to the raw asset it was generated from, along with
    the pipeline name and processing timestamp.

    Columns: name, source_data, pipeline_name, processing_time

    Parameters
    ----------
    source_asset_name : str, optional
        Filter to rows where the source_data column matches this raw asset
        name exactly (the raw asset that was processed).
    pipeline_name : str, optional
        Filter to rows from a specific pipeline (substring match,
        case-insensitive).
    limit : int
        Maximum number of rows to return (default 200).

    Returns
    -------
    list[dict]
        Matching rows with name, source_data, pipeline_name,
        processing_time columns.
    """
    try:
        df = source_data()

        if source_asset_name is not None:
            df = df[df["source_data"] == source_asset_name]
        if pipeline_name is not None:
            df = df[
                df["pipeline_name"].str.contains(
                    pipeline_name, case=False, na=False
                )
            ]

        df = df.head(limit)
        return _df_to_records(df)

    except Exception as ex:
        return f"Error in get_source_data_table: {type(ex).__name__}: {ex}"


@mcp.tool()
def get_raw_to_derived(
    asset_name: str,
    latest: bool = False,
) -> list[str] | str:
    """
    Return the derived asset names produced from a given raw asset.

    Use this tool to trace which processed/derived assets were generated
    from a specific raw data asset.

    Parameters
    ----------
    asset_name : str
        The raw asset name to look up (e.g.
        "ecephys_716870_2024-07-09_15-39-28").
    latest : bool
        If True, for each unique pipeline_name return only the most recent
        derived asset by processing_time. Useful when a raw asset has been
        re-processed multiple times and you only want the latest result.
        Default False (return all derived assets).

    Returns
    -------
    list[str]
        List of derived asset names, or an empty list if none found.
    """
    try:
        return raw_to_derived(asset_name, latest=latest)
    except Exception as ex:
        return f"Error in get_raw_to_derived: {type(ex).__name__}: {ex}"


@mcp.tool()
def get_qc_metrics(
    subject_id: str,
    asset_names: Optional[list[str]] = None,
) -> list[dict] | str:
    """
    Fetch quality control metrics for all assets belonging to a subject.

    Returns one row per QC metric per asset. Metrics are cached per
    subject_id; a cache miss (no prior data for this subject) will return
    an empty list — in that case the data may simply not yet be cached.

    Columns: name, stage, modality, value, status, asset_name

    Parameters
    ----------
    subject_id : str
        The subject ID to fetch QC data for (maps to subject.subject_id in
        the full metadata document).
    asset_names : list[str], optional
        Optional list of asset names to restrict results to. If omitted,
        returns QC metrics for all assets of the subject.

    Returns
    -------
    list[dict]
        QC metric rows for the requested subject / assets.
    """
    try:
        result = qc(subject_id, asset_names=asset_names)
        if isinstance(result, str) or (
            isinstance(result, pd.DataFrame) and result.empty
        ):
            return []
        return _df_to_records(result)
    except Exception as ex:
        return f"Error in get_qc_metrics: {type(ex).__name__}: {ex}"


@mcp.tool()
def get_assets_smartspim(
    subject_id: Optional[str] = None,
    genotype: Optional[str] = None,
    limit: int = 100,
) -> list[dict] | str:
    """
    Query the zombie_squirrel SmartSPIM assets cached table.

    Returns one row per SmartSPIM asset with processing status and
    Neuroglancer visualisation links for each channel.

    Columns: subject_id, genotype, institution, acquisition_start_time,
    processing_end_time, stitched_link, processed, name, channel_1,
    segmentation_link_1, quantification_link_1, channel_2, ..., channel_3,
    segmentation_link_3, quantification_link_3

    Parameters
    ----------
    subject_id : str, optional
        Filter to a specific subject ID (exact match).
    genotype : str, optional
        Filter to assets whose genotype contains this substring
        (case-insensitive).
    limit : int
        Maximum number of rows to return (default 100).

    Returns
    -------
    list[dict]
        Matching SmartSPIM asset rows.
    """
    try:
        df = assets_smartspim()

        if subject_id is not None:
            df = df[df["subject_id"] == str(subject_id)]
        if genotype is not None:
            df = df[
                df["genotype"].str.contains(
                    genotype, case=False, na=False
                )
            ]

        df = df.head(limit)
        return _df_to_records(df)

    except Exception as ex:
        return f"Error in get_assets_smartspim: {type(ex).__name__}: {ex}"
