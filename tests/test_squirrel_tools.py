"""Tests for squirrel_tools MCP tools.

Run directly with:  python tests/test_squirrel_tools.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from aind_data_mcp.squirrel_tools import (
    get_asset_basics,
    get_unique_project_names,
    get_unique_subject_ids,
    get_source_data_table,
    get_raw_to_derived,
    get_qc_metrics,
    get_assets_smartspim,
)

# ── get_unique_project_names ─────────────────────────────────────────────────


def test_unique_project_names():
    result = get_unique_project_names()
    assert isinstance(result, list), f"Expected list, got {type(result)}"
    assert len(result) > 0, "Expected non-empty project names list"
    assert all(
        isinstance(p, str) for p in result
    ), "All project names should be strings"
    assert result == sorted(result), "Result should be sorted"
    print(f"  [PASS] get_unique_project_names: {len(result)} projects")
    print(f"         Sample: {result[:3]}")


# ── get_unique_subject_ids ──────────────────────────────────────────────────


def test_unique_subject_ids():
    result = get_unique_subject_ids()
    assert isinstance(result, list), f"Expected list, got {type(result)}"
    assert len(result) > 0, "Expected non-empty subject IDs list"
    assert all(
        isinstance(s, str) for s in result
    ), "All subject IDs should be strings"
    print(f"  [PASS] get_unique_subject_ids: {len(result)} subjects")
    print(f"         Sample: {result[:3]}")
    return result


# ── get_asset_basics ─────────────────────────────────────────────────────────


def test_asset_basics_no_filter():
    result = get_asset_basics(limit=5)
    assert isinstance(result, list), f"Expected list, got {type(result)}"
    assert len(result) == 5, f"Expected 5 rows, got {len(result)}"
    expected_cols = {
        "_id", "name", "modalities", "project_name",
        "data_level", "subject_id",
    }
    assert expected_cols.issubset(
        result[0].keys()
    ), f"Missing columns. Got: {list(result[0].keys())}"
    print(f"  [PASS] get_asset_basics (no filter): {len(result)} rows")
    return result


def test_asset_basics_subject_filter(subject_id: str):
    result = get_asset_basics(subject_id=subject_id, limit=50)
    assert isinstance(result, list)
    assert all(
        r["subject_id"] == subject_id for r in result
    ), "All rows should match the subject_id filter"
    print(
        f"  [PASS] get_asset_basics (subject_id={subject_id}): "
        f"{len(result)} rows"
    )
    return result


def test_asset_basics_data_level_filter():
    raw_result = get_asset_basics(data_level="raw", limit=20)
    assert isinstance(raw_result, list)
    assert all(
        r["data_level"] == "raw" for r in raw_result
    ), "All rows should have data_level='raw'"
    print(
        f"  [PASS] get_asset_basics (data_level=raw): {len(raw_result)} rows"
    )

    derived_result = get_asset_basics(data_level="derived", limit=20)
    assert all(
        r["data_level"] == "derived" for r in derived_result
    ), "All rows should have data_level='derived'"
    print(
        f"  [PASS] get_asset_basics (data_level=derived): "
        f"{len(derived_result)} rows"
    )


def test_asset_basics_modality_filter():
    result = get_asset_basics(modality="ecephys", limit=10)
    assert isinstance(result, list)
    assert all(
        "ecephys" in r["modalities"].lower() for r in result
    ), "All rows should contain 'ecephys' in modalities"
    print(
        f"  [PASS] get_asset_basics (modality=ecephys): {len(result)} rows"
    )


def test_asset_basics_name_contains():
    result = get_asset_basics(name_contains="sorted", limit=10)
    assert isinstance(result, list)
    assert all(
        "sorted" in r["name"].lower() for r in result
    ), "All asset names should contain 'sorted'"
    print(
        f"  [PASS] get_asset_basics (name_contains=sorted): {len(result)} rows"
    )


def test_asset_basics_combined_filter():
    result = get_asset_basics(
        modality="behavior", data_level="raw", limit=10
    )
    assert isinstance(result, list)
    assert all(r["data_level"] == "raw" for r in result)
    assert all("behavior" in r["modalities"].lower() for r in result)
    print(
        f"  [PASS] get_asset_basics (combined: behavior+raw): "
        f"{len(result)} rows"
    )


# ── get_source_data_table ────────────────────────────────────────────────────


def test_source_data_no_filter():
    result = get_source_data_table(limit=5)
    assert isinstance(result, list)
    assert len(result) == 5
    expected_cols = {"name", "source_data", "pipeline_name", "processing_time"}
    assert expected_cols.issubset(result[0].keys()), (
        f"Missing columns. Got: {list(result[0].keys())}"
    )
    print(f"  [PASS] get_source_data_table (no filter): {len(result)} rows")
    return result


def test_source_data_filter_by_source(source_name: str):
    result = get_source_data_table(source_asset_name=source_name, limit=20)
    assert isinstance(result, list)
    assert all(
        r["source_data"] == source_name for r in result
    ), "All rows should match source_asset_name filter"
    print(
        f"  [PASS] get_source_data_table (source={source_name}): "
        f"{len(result)} derived assets"
    )
    return result


def test_source_data_pipeline_filter():
    result = get_source_data_table(
        pipeline_name="Processing Pipeline", limit=10
    )
    assert isinstance(result, list)
    assert all(
        "processing pipeline" in r["pipeline_name"].lower() for r in result
    ), "All rows should match pipeline_name filter"
    print(
        f"  [PASS] get_source_data_table (pipeline=Processing Pipeline): "
        f"{len(result)} rows"
    )


# ── get_raw_to_derived ───────────────────────────────────────────────────────


def test_raw_to_derived_known(source_name: str):
    result = get_raw_to_derived(source_name)
    assert isinstance(result, list), f"Expected list, got {type(result)}"
    assert len(result) > 0, (
        f"Expected at least one derived asset for {source_name}"
    )
    assert all(isinstance(s, str) for s in result)
    # Every derived name should start with the raw asset prefix
    assert all(result[i].startswith(source_name) for i in range(len(result)))
    print(f"  [PASS] get_raw_to_derived({source_name}): {result}")


def test_raw_to_derived_latest(source_name: str):
    all_derived = get_raw_to_derived(source_name, latest=False)
    latest_derived = get_raw_to_derived(source_name, latest=True)
    assert isinstance(latest_derived, list)
    # latest should return <= all
    assert len(latest_derived) <= len(all_derived), (
        "latest=True should return <= number of results from latest=False"
    )
    print(
        f"  [PASS] get_raw_to_derived latest=True: {len(latest_derived)} "
        f"(vs {len(all_derived)} total)"
    )


def test_raw_to_derived_unknown():
    result = get_raw_to_derived("nonexistent_asset_xyz_123")
    assert result == [], f"Expected empty list for unknown asset, got {result}"
    print("  [PASS] get_raw_to_derived (unknown asset): []")


# ── get_qc_metrics ──────────────────────────────────────────────────────────


def test_qc_no_cache_returns_empty(subject_id: str):
    """qc() returns an empty DataFrame when cache is not populated."""
    result = get_qc_metrics(subject_id)
    assert isinstance(result, list), f"Expected list, got {type(result)}"
    # Empty is acceptable — cache miss is not an error
    print(
        f"  [PASS] get_qc_metrics({subject_id}): "
        f"{len(result)} rows (cache may be empty)"
    )


# ── get_assets_smartspim ─────────────────────────────────────────────────────


def test_assets_smartspim_no_filter():
    result = get_assets_smartspim(limit=5)
    assert isinstance(result, list), f"Expected list, got {type(result)}"
    if result:
        expected_cols = {"subject_id", "name", "genotype"}
        assert expected_cols.issubset(result[0].keys()), (
            f"Missing columns. Got: {list(result[0].keys())}"
        )
    print(
        f"  [PASS] get_assets_smartspim (no filter): {len(result)} rows"
    )


def test_assets_smartspim_subject_filter(subject_id: str):
    result = get_assets_smartspim(subject_id=subject_id, limit=20)
    assert isinstance(result, list)
    assert all(
        r["subject_id"] == subject_id for r in result
    ), "All rows should match subject_id"
    print(
        f"  [PASS] get_assets_smartspim (subject={subject_id}): "
        f"{len(result)} rows"
    )


# ── Serialisation sanity check ───────────────────────────────────────────────


def test_json_serialisable():
    """All tools should return JSON-serialisable data."""
    import json

    results = {
        "get_asset_basics": get_asset_basics(limit=3),
        "get_unique_project_names": get_unique_project_names(),
        "get_unique_subject_ids": get_unique_subject_ids(),
        "get_source_data_table": get_source_data_table(limit=3),
    }
    for name, data in results.items():
        try:
            json.dumps(data)
            print(f"  [PASS] JSON serialisable: {name}")
        except (TypeError, ValueError) as e:
            raise AssertionError(
                f"{name} is not JSON-serialisable: {e}"
            ) from e


# ── Runner ───────────────────────────────────────────────────────────────────


def run_all():
    print("\n=== zombie_squirrel MCP tool tests ===\n")

    # Discover live data to use as fixtures
    subjects = get_unique_subject_ids()
    assert subjects, "No subjects returned — cannot run all tests"
    sample_subject = subjects[0]

    sd_rows = get_source_data_table(limit=10)
    sample_source = sd_rows[0]["source_data"] if sd_rows else None

    print("--- get_unique_project_names ---")
    test_unique_project_names()

    print("\n--- get_unique_subject_ids ---")
    test_unique_subject_ids()

    print("\n--- get_asset_basics ---")
    test_asset_basics_no_filter()
    test_asset_basics_data_level_filter()
    test_asset_basics_modality_filter()
    test_asset_basics_name_contains()
    test_asset_basics_combined_filter()
    test_asset_basics_subject_filter(sample_subject)

    print("\n--- get_source_data_table ---")
    test_source_data_no_filter()
    test_source_data_pipeline_filter()
    if sample_source:
        test_source_data_filter_by_source(sample_source)

    print("\n--- get_raw_to_derived ---")
    if sample_source:
        test_raw_to_derived_known(sample_source)
        test_raw_to_derived_latest(sample_source)
    test_raw_to_derived_unknown()

    print("\n--- get_qc_metrics ---")
    test_qc_no_cache_returns_empty(sample_subject)

    print("\n--- get_assets_smartspim ---")
    smartspim_rows = get_assets_smartspim(limit=5)
    test_assets_smartspim_no_filter()
    if smartspim_rows:
        spim_subject = smartspim_rows[0]["subject_id"]
        test_assets_smartspim_subject_filter(spim_subject)

    print("\n--- JSON serialisability ---")
    test_json_serialisable()

    print("\n=== All tests passed ===\n")


if __name__ == "__main__":
    run_all()
