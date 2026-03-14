# AIND Data MCP Server

[![License](https://img.shields.io/badge/license-MIT-brightgreen)](LICENSE)
![Code Style](https://img.shields.io/badge/code%20style-black-black)
[![semantic-release: angular](https://img.shields.io/badge/semantic--release-angular-e10079?logo=semantic-release)](https://github.com/semantic-release/semantic-release)
![Interrogate](https://img.shields.io/badge/interrogate-100.0%25-brightgreen)
![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen)
![Python](https://img.shields.io/badge/python->=3.11-blue?logo=python)

An MCP (Model Context Protocol) server that provides access to AIND (Allen Institute for Neural Dynamics) metadata and data assets through a comprehensive set of tools and resources. This server targets the **V2 aind-data-schema** format.

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

## Installation

Install uv if you haven't already — see [uv installation docs](https://docs.astral.sh/uv/getting-started/installation/).

Install the MCP server using uv:

```bash
uv tool install aind-data-mcp
```

Or using pip:

```bash
pip install aind-data-mcp
```

## Configuration

### For Cline (VSCode Extension)

In order to ensure that the MCP server runs in your preferred client, you will have to download the `aind-data-mcp` package to your console. If space is an issue, please set `UV_CACHE_DIR` and `UV_TOOL_DIR` to locations that have capacity before proceeding with the next step.

1. Simpler version of install
   Run `uv tool install aind-data-mcp` on your terminal and proceed below to configuring your MCP clients.
2. If the above step didn't work:

Create virtual environment with python 3.11 in IDE

```bash
# Instructions for Conda
conda create -n <my_env> python=3.11
conda activate <my_env>

# Instructions for virtual environment
py -3.11 -m venv .venv
# Windows startup
.venv\Scripts\Activate.ps1
# Mac/ Linux startup
source .venv/bin/activate
```

Run the following commands in your IDE terminal.

```bash
pip install uv
uvx aind-data-mcp
```

If all goes well, and you see the following notice - `Starting MCP server 'aind_data_mcp' with transport 'stdio'` -, you should be good for the set up in your client of choice!

### Cursor IDE

1. Install the MCP server:
   ```bash
   uv tool install aind-data-mcp
   ```

2. Create the MCP configuration file:
   ```bash
   mkdir -p ~/.cursor
   ```

3. Create `~/.cursor/mcp.json` with the following content:
   ```json
   {
     "mcpServers": {
       "aind-data-access": {
         "command": "aind-data-mcp",
         "args": [],
         "env": {}
       }
     }
   }
   ```

4. **Important**: Replace `aind-data-mcp` with the full path if needed:
   ```bash
   which aind-data-mcp
   ```
   Use the full path (e.g., `/Users/username/.local/bin/aind-data-mcp`) in the `command` field.

5. Restart Cursor completely (Cmd+Q then reopen)

**Note**: Cursor uses a different MCP configuration system than VSCode. The configuration must be in `~/.cursor/mcp.json`, not in the main settings.json file.

## Instructions for use in MCP clients

JSON Config files to add MCP servers in clients should be structured like this

```json
{
    "mcpServers": {

    }
}
```

Insert the following lines into the mcpServers dictionary

```json
"aind_data_mcp": {
      "disabled": false,
      "timeout": 300,
      "type": "stdio",
      "command": "aind-data-mcp"
}
```

Note that after configuring the JSON files, it will take a few minutes for the server to populate in the client.

### Claude Desktop App

- Click the three lines at the top left of the screen.
- File > Settings > Developer > Edit config

### Cline in VSCode

- Ensure that Cline is downloaded to VSCode
- Click the three stacked rectangles at the top right of the Cline window
- Installed > Configure MCP Servers
- Close and reopen VSCode

### Github Copilot in VSCode

- Command palette (ctrl shift p)
- Search for MCP: Add server
- Select `Manual Install` / `stdio`
- When prompted for a command, input `uvx aind-data-mcp`
- Name your server
- Close and reopen VSCode
- In Copilot chat -> Select agent mode -> Click the three stacked rectangles to configure tools
- API context and NWB loading patterns are served automatically as MCP resources (`resource://aind_api` and `resource://load_nwbfile`) — no manual file setup required

### For use in Code Ocean

* Refer to the [code ocean MCP server](https://github.com/codeocean/codeocean-mcp-server) for additional support

## Development

To develop the code, run

```bash
uv sync --group dev
```

To run tests:

```bash
uv run coverage run -m unittest discover && uv run coverage report
```

To run linting:

```bash
uv run flake8 . && uv run interrogate --verbose .
```
