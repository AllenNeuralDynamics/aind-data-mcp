"""
MCP tools backed by biodata_cache cached tables.

These tools query pre-built Parquet tables hosted on S3 for fast lookups
of commonly-needed fields. They are significantly faster than the MongoDB
API for filtering by project, subject, modality, data level, or dates.

Use these tools FIRST whenever the query only needs fields available in
the tables. Fetch full MongoDB records afterwards only when richer metadata
is required.
"""

import os
from typing import Optional

import pandas as pd

# Must be set before importing biodata_cache — the registry reads this env var
# at module-import time and selects the backend (S3 vs in-memory) accordingly.
os.environ["BIODATA_CACHE_BACKEND"] = "S3"

from biodata_cache import (  # noqa: E402
    asset_basics,
    assets_smartspim,
    behavior_curriculum,
    metadata_upgrade,
    platform_dynamic_foraging_events,
    platform_dynamic_foraging_sessions,
    platform_dynamic_foraging_trials,
    platform_exaspim,
    platform_fib,
    platform_qc,
    qc,
    raw_to_derived,
    scientist_rl_fib,
    source_data,
    time_to_qc,
    unique_genotypes,
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
    Query the biodata_cache asset_basics cached table.

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
        process_date, genotype, age, acquisition_type, location,
        experimenters, experimenters_normalized, instrument_id,
        instrument_id_normalized, investigators, investigators_normalized

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
    Query the biodata_cache source_data cached table.

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
    raw_name_contains: Optional[str] = None,
    channel: Optional[str] = None,
    processed: Optional[bool] = None,
    limit: int = 100,
) -> list[dict] | str:
    """
    Query the biodata_cache SmartSPIM assets cached table.

    Returns one row per (asset, channel) with processing status and
    Neuroglancer visualisation links. Join with get_asset_basics on the
    raw_name column to get subject_id, genotype, or other metadata.

    Columns: name, raw_name, processed, processing_end_time, stitched_link,
    raw_link, channel, segmentation_link, quantification_link

    Parameters
    ----------
    raw_name_contains : str, optional
        Filter rows whose raw_name contains this substring (case-insensitive).
        Useful for filtering by subject ID embedded in the asset name.
    channel : str, optional
        Filter to a specific channel (substring match, case-insensitive).
    processed : bool, optional
        If True, return only assets with a stitched derived asset.
        If False, return only unprocessed assets.
    limit : int
        Maximum number of rows to return (default 100).

    Returns
    -------
    list[dict]
        Matching SmartSPIM rows, one per (asset, channel).
    """
    try:
        df = assets_smartspim()

        if raw_name_contains is not None:
            df = df[
                df["raw_name"].str.contains(
                    raw_name_contains, case=False, na=False
                )
            ]
        if channel is not None:
            df = df[
                df["channel"].str.contains(
                    channel, case=False, na=False
                )
            ]
        if processed is not None:
            df = df[df["processed"] == processed]

        df = df.head(limit)
        return _df_to_records(df)

    except Exception as ex:
        return f"Error in get_assets_smartspim: {type(ex).__name__}: {ex}"


@mcp.tool()
def get_unique_genotypes() -> list[str] | str:
    """
    Return all unique genotypes across the data asset database.

    Use this tool to:
    - Discover what genotypes exist before filtering with get_asset_basics
    - Validate the exact spelling of a genotype string

    Returns
    -------
    list[str]
        Sorted list of unique genotype strings.
    """
    try:
        return sorted(g for g in unique_genotypes() if g is not None)
    except Exception as ex:
        return f"Error in get_unique_genotypes: {type(ex).__name__}: {ex}"


@mcp.tool()
def get_platform_qc(
    platform: str,
    asset_name: Optional[str] = None,
    tag: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 200,
) -> list[dict] | str:
    """
    Query the biodata_cache platform_qc table for tag-level QC statuses.

    Returns one row per (asset, tag) combination for the given platform.
    Cached per platform; use for quick QC status summaries without needing
    to pull per-metric quality_control data.

    Columns: asset_name, tag, status, timestamp,
    instrument_id_normalized, experimenters_normalized

    Parameters
    ----------
    platform : str
        Required. One of: 'spim', 'fib', 'vr', 'dynamic_foraging'.
    asset_name : str, optional
        Filter to a specific asset name (exact match).
    tag : str, optional
        Filter to rows whose tag contains this substring (case-insensitive).
    status : str, optional
        Filter by QC status, e.g. 'pass', 'fail', 'pending'.
    limit : int
        Maximum number of rows to return (default 200).

    Returns
    -------
    list[dict]
        Matching platform QC rows.
    """
    try:
        df = platform_qc(platform)

        if asset_name is not None:
            df = df[df["asset_name"] == asset_name]
        if tag is not None:
            df = df[
                df["tag"].str.contains(tag, case=False, na=False)
            ]
        if status is not None:
            df = df[df["status"] == status]

        df = df.head(limit)
        return _df_to_records(df)

    except Exception as ex:
        return f"Error in get_platform_qc: {type(ex).__name__}: {ex}"


@mcp.tool()
def get_assets_exaspim(
    raw_name_contains: Optional[str] = None,
    processed: Optional[bool] = None,
    limit: int = 100,
) -> list[dict] | str:
    """
    Query the biodata_cache ExaSPIM assets cached table.

    Returns one row per ExaSPIM asset with processing status and
    Neuroglancer visualisation links.

    Columns: name, raw_name, processed, raw_link, fused_link

    Parameters
    ----------
    raw_name_contains : str, optional
        Filter rows whose raw_name contains this substring (case-insensitive).
    processed : bool, optional
        If True, return only assets with a fused derived asset.
        If False, return only unprocessed assets.
    limit : int
        Maximum number of rows to return (default 100).

    Returns
    -------
    list[dict]
        Matching ExaSPIM asset rows.
    """
    try:
        df = platform_exaspim()

        if raw_name_contains is not None:
            df = df[
                df["raw_name"].str.contains(
                    raw_name_contains, case=False, na=False
                )
            ]
        if processed is not None:
            df = df[df["processed"] == processed]

        df = df.head(limit)
        return _df_to_records(df)

    except Exception as ex:
        return f"Error in get_assets_exaspim: {type(ex).__name__}: {ex}"


@mcp.tool()
def get_assets_fib(
    asset_name: Optional[str] = None,
    fiber: Optional[str] = None,
    channel: Optional[str] = None,
    targeted_structure: Optional[str] = None,
    limit: int = 200,
) -> list[dict] | str:
    """
    Query the biodata_cache fiber photometry (fib) assets table.

    Returns one row per (asset, fiber, channel) combination.

    Columns: asset_name, fiber, patch_cord, channel,
    intended_measurement, targeted_structure

    Parameters
    ----------
    asset_name : str, optional
        Filter to a specific asset name (exact match).
    fiber : str, optional
        Filter to a specific fiber (substring match, case-insensitive).
    channel : str, optional
        Filter to a specific channel (substring match, case-insensitive).
    targeted_structure : str, optional
        Filter by targeted brain structure (substring match,
        case-insensitive).
    limit : int
        Maximum number of rows to return (default 200).

    Returns
    -------
    list[dict]
        Matching fiber photometry rows.
    """
    try:
        df = platform_fib()

        if asset_name is not None:
            df = df[df["asset_name"] == asset_name]
        if fiber is not None:
            df = df[
                df["fiber"].str.contains(fiber, case=False, na=False)
            ]
        if channel is not None:
            df = df[
                df["channel"].str.contains(channel, case=False, na=False)
            ]
        if targeted_structure is not None:
            df = df[
                df["targeted_structure"].str.contains(
                    targeted_structure, case=False, na=False
                )
            ]

        df = df.head(limit)
        return _df_to_records(df)

    except Exception as ex:
        return f"Error in get_assets_fib: {type(ex).__name__}: {ex}"


@mcp.tool()
def get_foraging_sessions(
    subject_id: Optional[str] = None,
    task: Optional[str] = None,
    curriculum_name: Optional[str] = None,
    limit: int = 200,
) -> list[dict] | str:
    """
    Query the biodata_cache dynamic foraging session table.

    Returns one row per dynamic foraging session with key performance
    metrics. Backed by platform_dynamic_foraging_sessions (~160 columns).

    Key columns: _session_id, subject_id, session_date, nwb_suffix, task,
    total_trials, finished_trials, finished_rate, foraging_eff,
    foraging_performance, bias_naive, curriculum_name,
    curriculum_version, current_stage_actual, foraging_eff_random_seed,
    reaction_time_median, early_lick_rate, hardware, rig_type,
    data_source, institute

    Parameters
    ----------
    subject_id : str, optional
        Filter to a specific subject ID (exact match).
    task : str, optional
        Filter to sessions with this task (substring match,
        case-insensitive).
    curriculum_name : str, optional
        Filter to sessions with this curriculum (substring match,
        case-insensitive).
    limit : int
        Maximum number of rows to return (default 200).

    Returns
    -------
    list[dict]
        Matching foraging session rows.
    """
    try:
        df = platform_dynamic_foraging_sessions()

        if subject_id is not None:
            df = df[df["subject_id"] == str(subject_id)]
        if task is not None:
            df = df[
                df["task"].str.contains(task, case=False, na=False)
            ]
        if curriculum_name is not None:
            df = df[
                df["curriculum_name"].str.contains(
                    curriculum_name, case=False, na=False
                )
            ]

        df = df.head(limit)
        return _df_to_records(df)

    except Exception as ex:
        return f"Error in get_foraging_sessions: {type(ex).__name__}: {ex}"


@mcp.tool()
def get_behavior_curriculum(
    asset_name: Optional[str] = None,
    curriculum_name: Optional[str] = None,
    stage_name: Optional[str] = None,
    limit: int = 200,
) -> list[dict] | str:
    """
    Query the biodata_cache behavior_curriculum table.

    Returns one row per behavior asset with its curriculum name and
    training stage.

    Columns: asset_name, curriculum_name, stage_name, stage_node_id

    Parameters
    ----------
    asset_name : str, optional
        Filter to a specific asset name (exact match).
    curriculum_name : str, optional
        Filter by curriculum name (substring match, case-insensitive).
    stage_name : str, optional
        Filter by stage name (substring match, case-insensitive).
    limit : int
        Maximum number of rows to return (default 200).

    Returns
    -------
    list[dict]
        Matching behavior curriculum rows.
    """
    try:
        df = behavior_curriculum()

        if asset_name is not None:
            df = df[df["asset_name"] == asset_name]
        if curriculum_name is not None:
            df = df[
                df["curriculum_name"].str.contains(
                    curriculum_name, case=False, na=False
                )
            ]
        if stage_name is not None:
            df = df[
                df["stage_name"].str.contains(
                    stage_name, case=False, na=False
                )
            ]

        df = df.head(limit)
        return _df_to_records(df)

    except Exception as ex:
        return f"Error in get_behavior_curriculum: {type(ex).__name__}: {ex}"


@mcp.tool()
def get_time_to_qc(
    name_contains: Optional[str] = None,
    limit: int = 200,
) -> list[dict] | str:
    """
    Query the biodata_cache time_to_qc table.

    Returns one row per derived asset with timestamps for processing
    completion and QC completion. Useful for monitoring QC throughput
    and identifying bottlenecks.

    Columns: name, process_end_time, qc_time

    Parameters
    ----------
    name_contains : str, optional
        Filter to assets whose name contains this substring
        (case-insensitive).
    limit : int
        Maximum number of rows to return (default 200).

    Returns
    -------
    list[dict]
        Matching time-to-QC rows.
    """
    try:
        df = time_to_qc()

        if name_contains is not None:
            df = df[
                df["name"].str.contains(
                    name_contains, case=False, na=False
                )
            ]

        df = df.head(limit)
        return _df_to_records(df)

    except Exception as ex:
        return f"Error in get_time_to_qc: {type(ex).__name__}: {ex}"


@mcp.tool()
def get_metadata_upgrade(
    project_name: Optional[str] = None,
    data_level: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 200,
) -> list[dict] | str:
    """
    Query the biodata_cache metadata_upgrade table.

    Returns one row per asset showing its metadata upgrade status across
    schema versions. Useful for tracking which assets have been migrated
    to newer metadata schemas.

    Columns: _id, name, project_name, data_level, v2_id,
    upgrader_version, last_modified, status, upgrade_datetime

    Parameters
    ----------
    project_name : str, optional
        Filter to a specific project name (exact match).
    data_level : str, optional
        Filter by data level, e.g. 'raw' or 'derived'.
    status : str, optional
        Filter by upgrade status, e.g. 'success', 'failed', 'pending'.
    limit : int
        Maximum number of rows to return (default 200).

    Returns
    -------
    list[dict]
        Matching metadata upgrade rows.
    """
    try:
        df = metadata_upgrade()

        if project_name is not None:
            df = df[df["project_name"] == project_name]
        if data_level is not None:
            df = df[df["data_level"] == data_level]
        if status is not None:
            df = df[df["status"] == status]

        df = df.head(limit)
        return _df_to_records(df)

    except Exception as ex:
        return f"Error in get_metadata_upgrade: {type(ex).__name__}: {ex}"


@mcp.tool()
def get_foraging_trials(
    subject_id: str,
    limit: int = 500,
) -> list[dict] | str:
    """
    Fetch dynamic foraging trial-level data for a single subject.

    Returns one row per trial from the hive-partitioned trial table in the
    upstream aind-dynamic-foraging-database. Requires a subject_id; data is
    cached per subject and fetched from upstream on a cache miss.

    Key columns: _session_id, subject_id, session_date, trial_index,
    animal_response, rewarded_historyL, rewarded_historyR,
    reward_outcome_color, go_cue_time, reaction_time, ...

    Parameters
    ----------
    subject_id : str
        The subject ID to fetch trial data for (required).
    limit : int
        Maximum number of rows to return (default 500).

    Returns
    -------
    list[dict]
        Trial rows for the subject.
    """
    try:
        df = platform_dynamic_foraging_trials(str(subject_id))
        df = df.head(limit)
        return _df_to_records(df)
    except Exception as ex:
        return f"Error in get_foraging_trials: {type(ex).__name__}: {ex}"


@mcp.tool()
def get_foraging_events(
    subject_id: str,
    limit: int = 1000,
) -> list[dict] | str:
    """
    Fetch dynamic foraging event-level data for a single subject.

    Returns one row per behavioral event from the hive-partitioned event
    table in the upstream aind-dynamic-foraging-database. Requires a
    subject_id; data is cached per subject and fetched from upstream on
    a cache miss.

    Key columns: _session_id, subject_id, session_date, event_type,
    event_time, value, ...

    Parameters
    ----------
    subject_id : str
        The subject ID to fetch event data for (required).
    limit : int
        Maximum number of rows to return (default 1000).

    Returns
    -------
    list[dict]
        Event rows for the subject.
    """
    try:
        df = platform_dynamic_foraging_events(str(subject_id))
        df = df.head(limit)
        return _df_to_records(df)
    except Exception as ex:
        return f"Error in get_foraging_events: {type(ex).__name__}: {ex}"


@mcp.tool()
def get_scientist_rl_fib(
    targeted_structure: Optional[str] = None,
    indicator: Optional[str] = None,
) -> list[dict] | str:
    """
    Query the biodata_cache scientist_rl_fib cohort summary table.

    Returns one row per (fiber_targeted_structure, virus/indicator)
    combination, collapsed across all qualifying subjects that have both
    behavior and fiber photometry data at a STAGE_FINAL or GRADUATED
    training stage.

    Columns: targeted_structure, coordinates, indicator, mouse_ids,
    mouse_count, session_count

    Parameters
    ----------
    targeted_structure : str, optional
        Filter to rows whose targeted_structure contains this substring
        (case-insensitive).
    indicator : str, optional
        Filter to rows whose indicator (virus/reporter) contains this
        substring (case-insensitive).

    Returns
    -------
    list[dict]
        Matching cohort summary rows.
    """
    try:
        df = scientist_rl_fib()

        if targeted_structure is not None:
            df = df[
                df["targeted_structure"].str.contains(
                    targeted_structure, case=False, na=False
                )
            ]
        if indicator is not None:
            df = df[
                df["indicator"].str.contains(
                    indicator, case=False, na=False
                )
            ]

        return _df_to_records(df)

    except Exception as ex:
        return f"Error in get_scientist_rl_fib: {type(ex).__name__}: {ex}"
