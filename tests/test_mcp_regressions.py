import asyncio
import unittest
from unittest.mock import Mock, patch

import numpy as np
import pandas as pd
from fastmcp.exceptions import ToolError

import aind_data_mcp.cache_tools as cache_tools
import aind_data_mcp.query_tools as query_tools
import aind_data_mcp.schema_tools as schema_tools
from aind_data_mcp.data_access_server import (
    get_aind_data_access_api,
    get_cache_api_prompt,
    get_nwbfile_download_script,
    mcp,
)


class TestMcpRegressions(unittest.TestCase):
    def setUp(self):
        self.asset_frame = pd.DataFrame(
            [
                {
                    "name": "a[1]",
                    "subject_id": "1",
                    "project_name": "Project",
                    "modalities": "SPIM",
                    "data_level": "raw",
                    "acquisition_start_time": "2023-01-01T00:00:00-08:00",
                    "acquisition_end_time": "2023-01-01T01:00:00-08:00",
                    "genotype": pd.NA,
                },
                {
                    "name": "b",
                    "subject_id": "2",
                    "project_name": "Project",
                    "modalities": "ecephys",
                    "data_level": "derived",
                    "acquisition_start_time": "2025-01-01T00:00:00Z",
                    "acquisition_end_time": "2025-01-01T01:00:00Z",
                    "genotype": "wt",
                },
            ]
        )

    def test_resources_are_available(self):
        self.assertIn("MetadataDbClient", get_aind_data_access_api())
        self.assertIn("NWBZarrIO", get_nwbfile_download_script())
        self.assertIn("asset_basics", get_cache_api_prompt())

    def test_get_records_uses_fresh_defaults(self):
        client = Mock()
        client.retrieve_docdb_records.return_value = []

        with patch.object(
            query_tools, "setup_mongodb_client", return_value=client
        ):
            self.assertEqual(query_tools.get_records(), [])
            self.assertEqual(query_tools.get_records(), [])

        calls = client.retrieve_docdb_records.call_args_list
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0].kwargs["filter_query"], {})
        self.assertEqual(calls[0].kwargs["projection"], {})

    def test_flatten_records_flattens_supplied_records(self):
        records = [{"subject": {"subject_id": "1"}}]

        with patch.object(query_tools, "setup_mongodb_client") as setup_client:
            result = query_tools.flatten_records(records)

        self.assertEqual(result, [{"subject.subject_id": "1"}])
        setup_client.assert_not_called()

    def test_query_setup_errors_are_tool_errors(self):
        with patch.object(
            query_tools,
            "setup_mongodb_client",
            side_effect=RuntimeError("database unavailable"),
        ):
            with self.assertRaises(ToolError):
                query_tools.get_records()

    def test_schema_context_returns_paths_and_small_examples(self):
        top_level = schema_tools.get_schema_context(detail="paths")
        subject_paths = schema_tools.get_schema_context(
            "subject", path="subject_details.breeding_info", detail="paths"
        )
        subject_example = schema_tools.get_schema_context(
            "subject", detail="example"
        )
        quality_control_example = schema_tools.get_schema_context(
            "quality_control", detail="example"
        )

        self.assertIn("subject", top_level["nodes"])
        self.assertEqual(
            subject_paths["paths"],
            [
                "subject.subject_details.breeding_info.maternal_id",
                "subject.subject_details.breeding_info.maternal_genotype",
                "subject.subject_details.breeding_info.paternal_id",
                "subject.subject_details.breeding_info.paternal_genotype",
            ],
        )
        self.assertEqual(
            subject_example["example"]["subject"]["subject_details"][
                "breeding_info"
            ]["maternal_id"],
            "546543",
        )
        self.assertEqual(
            quality_control_example["example"]["quality_control"]["metrics"][
                0
            ]["modality"]["abbreviation"],
            "SPIM",
        )

    def test_schema_context_rejects_invalid_requests(self):
        with self.assertRaises(ValueError):
            schema_tools.get_schema_context(detail="example")
        with self.assertRaises(ValueError):
            schema_tools.get_schema_context("location", detail="example")
        with self.assertRaises(ValueError):
            schema_tools.get_schema_context("unknown")
        with self.assertRaises(ValueError):
            schema_tools.get_schema_context(detail="invalid")

    def test_schema_context_reveals_only_requested_depth(self):
        root_tree = schema_tools.get_schema_context()
        branch_tree = schema_tools.get_schema_context(
            path="Acquisition.data_streams", max_depth=1
        )

        self.assertIn("- **Acquisition**", root_tree)
        self.assertIn("`data_streams` (", root_tree)
        self.assertNotIn("- **DataStream**", root_tree)
        self.assertIn("- **DataStream**", branch_tree)
        self.assertIn("- **ExternalDataStream**", branch_tree)
        self.assertNotIn("`protocol_id` (", branch_tree)

    def test_schema_context_requires_path_for_expansion(self):
        with self.assertRaisesRegex(ValueError, "path is required"):
            schema_tools.get_schema_context(max_depth=1)

    def test_schema_context_rejects_unknown_path(self):
        with self.assertRaisesRegex(ValueError, "unknown schema path"):
            schema_tools.get_schema_context(path="Acquisition.no_such_field")

    def test_schema_context_rejects_negative_depth(self):
        with self.assertRaises(ValueError):
            schema_tools.get_schema_context(max_depth=-1)

    def test_aggregation_aliases_and_metadata_are_opt_in(self):
        client = Mock()
        client.aggregate_docdb_records.return_value = [
            {"_id": "Male", "count": 2}
        ]

        with patch.object(
            query_tools, "setup_mongodb_client", return_value=client
        ):
            result = query_tools.aggregation_retrieval(
                agg_pipeline=[
                    {"$group": {"_id": "$_aind_aliases.subject_sex"}}
                ],
                field_aliases={
                    "subject_sex": [
                        "subject.subject_details.sex",
                        "subject.sex",
                    ]
                },
                include_metadata=True,
            )

        pipeline = client.aggregate_docdb_records.call_args.kwargs["pipeline"]
        self.assertEqual(
            pipeline[0],
            {
                "$set": {
                    "_aind_aliases": {
                        "subject_sex": {
                            "$ifNull": [
                                "$subject.subject_details.sex",
                                "$subject.sex",
                            ]
                        }
                    }
                }
            },
        )
        self.assertEqual(result["records"], [{"_id": "Male", "count": 2}])
        self.assertTrue(
            result["metadata"]["snapshot_marker"].startswith(
                "query-result-sha256:"
            )
        )
        self.assertEqual(result["metadata"]["api_version"], "v2")

    def test_aggregation_rejects_empty_aliases(self):
        client = Mock()
        with patch.object(
            query_tools, "setup_mongodb_client", return_value=client
        ):
            with self.assertRaises(ToolError):
                query_tools.aggregation_retrieval(
                    agg_pipeline=[], field_aliases={"subject_sex": []}
                )

    def test_server_publishes_compact_initialized_manifest(self):
        tool_names = {tool.name for tool in asyncio.run(mcp.list_tools())}
        self.assertIn("get_schema_context", tool_names)
        self.assertNotIn("get_schema_tree", tool_names)
        self.assertNotIn("get_subject_example", tool_names)
        self.assertIn("get_schema_context", mcp.instructions)

    def test_asset_basics_filters_dates_pages_and_reports_total(self):
        backend_results = [
            (self.asset_frame.iloc[[0]], 1),
            self.asset_frame.iloc[[1]],
            self.asset_frame.iloc[[0]],
        ]
        with patch.object(
            cache_tools, "asset_basics", side_effect=backend_results
        ) as asset_basics_mock:
            result = cache_tools.get_asset_basics(
                project_name="Project",
                acquisition_start_before="2024-01-01T00:00:00Z",
                include_total=True,
                limit=500,
            )
            page = cache_tools.get_asset_basics(
                project_name="Project", offset=1, limit=1
            )
            literal = cache_tools.get_asset_basics(name_contains="[")

        self.assertEqual(result["total_matches"], 1)
        self.assertEqual(result["limit"], cache_tools.MAX_LIMIT)
        self.assertFalse(result["has_more"])
        self.assertEqual(result["records"][0]["name"], "a[1]")
        self.assertEqual(page[0]["name"], "b")
        self.assertEqual([row["name"] for row in literal], ["a[1]"])
        first_call = asset_basics_mock.call_args_list[0].kwargs
        self.assertEqual(first_call["project_name"], "Project")
        self.assertEqual(
            first_call["acquisition_start_before"], "2024-01-01T00:00:00Z"
        )
        self.assertEqual(first_call["limit"], cache_tools.MAX_LIMIT)
        self.assertEqual(first_call["offset"], 0)
        self.assertTrue(first_call["include_total"])
        self.assertIn("instrument_id", first_call["columns"])
        self.assertIn("experimenters_normalized", first_call["columns"])
        self.assertIn("investigators_normalized", first_call["columns"])

    def test_smartspim_adds_subject_metadata_and_filters_subject(self):
        smartspim_frame = pd.DataFrame(
            [
                {
                    "name": "stitched",
                    "raw_name": "a[1]",
                    "processed": True,
                    "channel": None,
                }
            ]
        )

        with (
            patch.object(
                cache_tools, "assets_smartspim", return_value=smartspim_frame
            ),
            patch.object(
                cache_tools, "asset_basics", return_value=self.asset_frame
            ),
        ):
            result = cache_tools.get_assets_smartspim(subject_id="1")

        self.assertEqual(result[0]["subject_id"], "1")
        self.assertIsNone(result[0]["genotype"])

    def test_serialization_handles_numpy_and_pandas_values(self):
        result = cache_tools._to_serialisable(
            {
                "timestamp": pd.Timestamp("2024-01-01"),
                "numpy_timestamp": np.datetime64("2024-01-02"),
                "missing": pd.NA,
                "values": np.array([np.int64(2), np.nan]),
            }
        )

        self.assertEqual(
            result,
            {
                "timestamp": "2024-01-01T00:00:00",
                "numpy_timestamp": "2024-01-02T00:00:00",
                "missing": None,
                "values": [2, None],
            },
        )

    def test_qc_lazy_path_is_not_reported_as_empty(self):
        with patch.object(cache_tools, "qc", return_value="s3://cache/qc/1"):
            with self.assertRaises(ToolError):
                cache_tools.get_qc_metrics("1")

    def test_negative_cache_limit_is_rejected(self):
        with patch.object(
            cache_tools, "asset_basics", return_value=self.asset_frame
        ):
            with self.assertRaises(ToolError):
                cache_tools.get_asset_basics(limit=-1)


if __name__ == "__main__":
    unittest.main()
