# AIND Data MCP Server

[![License](https://img.shields.io/badge/license-MIT-brightgreen)](LICENSE)
![Code Style](https://img.shields.io/badge/code%20style-black-black)
[![semantic-release: angular](https://img.shields.io/badge/semantic--release-angular-e10079?logo=semantic-release)](https://github.com/semantic-release/semantic-release)
![Interrogate](https://img.shields.io/badge/interrogate-100.0%25-brightgreen)
![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen)
![Python](https://img.shields.io/badge/python->=3.11-blue?logo=python)

An MCP (Model Context Protocol) server that provides access to AIND (Allen Institute for Neural Dynamics) metadata and data assets through a comprehensive set of tools and resources. This server targets the **V2 aind-data-schema** format.

## Installation

Each IDE/client has its own configuration method, look at their documentation for instructions on MCP configuration/setup.

You can either use the command `uvx aind-data-mcp` to launch the server, or install it locally with `uv tool install aind-data-mcp` and then launch it with just `aind-data-mcp`.

### For use in Code Ocean

* Refer to the [code ocean MCP server](https://github.com/codeocean/codeocean-mcp-server) for additional support

## Features

This MCP server provides the following tools:

**Data Retrieval & Querying**
- `get_records` — Query MongoDB collections using filters and projections
- `aggregation_retrieval` — Execute complex MongoDB aggregation pipelines
- `count_records` — Count documents matching a filter
- `flatten_records` — Retrieve and flatten records into dot-notation for easier inspection
- `get_project_names` — List all project names in the database
- `get_summary` — Generate an AI-powered summary for a specific data asset

**Schema Navigation**
- `get_top_level_nodes` — Explore the top-level fields of the V2 metadata schema
- `get_additional_schema_help` — Query-writing guidance for V2 aggregations
- `get_modality_types` — List all available data modality names and abbreviations

**Schema Examples** (one tool per document type)
- `get_acquisition_example`, `get_data_description_example`, `get_instrument_example`, `get_procedures_example`, `get_subject_example`, `get_processing_example`, `get_model_example`, `get_quality_control_example`

**NWB File Access**
- `identify_nwb_contents_in_code_ocean` — Load an NWB file from the `/data` directory in a Code Ocean capsule
- `identify_nwb_contents_with_s3_link` — Load an NWB file from an S3 path

**Resources** (accessible via the MCP protocol)
- `resource://aind_api` — Context and usage patterns for the AIND data access API
- `resource://load_nwbfile` — Reference script for loading NWB files

## Development

To develop the code, run

```bash
uv sync --extra dev
```

To run tests:

```bash
uv run coverage run -m unittest discover && uv run coverage report
```

To run linting:

```bash
uv run flake8 . && uv run interrogate --verbose .
```
