import unittest
from unittest.mock import Mock, patch

import numpy as np
import pandas as pd
from fastmcp.exceptions import ToolError

import aind_data_mcp.cache_tools as cache_tools
import aind_data_mcp.query_tools as query_tools
from aind_data_mcp.data_access_server import (
    get_aind_data_access_api,
    get_cache_api_prompt,
    get_nwbfile_download_script,
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

        with patch.object(query_tools, "setup_mongodb_client", return_value=client):
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

    def test_asset_basics_filters_dates_pages_and_reports_total(self):
        with patch.object(cache_tools, "asset_basics", return_value=self.asset_frame):
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

        with patch.object(
            cache_tools, "assets_smartspim", return_value=smartspim_frame
        ), patch.object(cache_tools, "asset_basics", return_value=self.asset_frame):
            result = cache_tools.get_assets_smartspim(subject_id="1")

        self.assertEqual(result[0]["subject_id"], "1")
        self.assertIsNone(result[0]["genotype"])

    def test_serialization_handles_numpy_and_pandas_values(self):
        result = cache_tools._to_serialisable(
            {
                "timestamp": pd.Timestamp("2024-01-01"),
                "missing": pd.NA,
                "values": np.array([np.int64(2), np.nan]),
            }
        )

        self.assertEqual(
            result,
            {
                "timestamp": "2024-01-01T00:00:00",
                "missing": None,
                "values": [2, None],
            },
        )

    def test_qc_lazy_path_is_not_reported_as_empty(self):
        with patch.object(cache_tools, "qc", return_value="s3://cache/qc/1"):
            with self.assertRaises(ToolError):
                cache_tools.get_qc_metrics("1")

    def test_negative_cache_limit_is_rejected(self):
        with patch.object(cache_tools, "asset_basics", return_value=self.asset_frame):
            with self.assertRaises(ToolError):
                cache_tools.get_asset_basics(limit=-1)


if __name__ == "__main__":
    unittest.main()
