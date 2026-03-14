"""Schema navigation and QC example tools."""

from .mcp_instance import mcp


@mcp.tool()
def get_top_level_nodes() -> list:
    """
    This tool exposes the top level nodes of the data schema. In order to access any of the fields using
    tools like get_records/aggregation retrieval, you would just have to call the field name like "_id".
    Note that most of the fields have further nesting. So in order to call a field within the nesting sturcture,
    you would have to use something like "subject.subject_id". Use this tool as a resource. To find out more
    about the nesting structure of the fields, you can access the relevant get_<field_name>_example tools in this server.
    """

    top_level_nodes = {
        "_id": "Unique identifier for data asset assigned by MongoDB, usually a series of numbers",
        "name": "Name of data asset, combines subject_id and creation_time",
        "quality_control": "A collection of quality control metrics evaluated on a data asset. Has further nesting",
        "acquisition": "Single episode of data collection that creates one data asset. Contains data_streams, stimulus_epochs, manipulations. Has further nesting",
        "data_description": "Tracks administrative information about a data asset, including affiliated researchers/organizations, projects, data modalities, dates of collection. Has further nesting",
        "instrument": "Information about the components/devices used to collect data. Has a single 'components' list. Has further nesting",
        "procedures": "Information about anything done to the subject or specimen prior to data collection. Has further nesting",
        "processing": "Captures the data processing and analysis steps, with data_processes, pipelines, and dependency_graph. Has further nesting",
        "subject": "Describes the subject from which data was obtained. Has subject_id and subject_details (MouseSubject/HumanSubject/CalibrationObject). Has further nesting",
        "model": "Description of a machine learning model including architecture, training, and evaluation details. Has further nesting",
        "other_identifiers": "Links to the data asset on secondary platforms",
        "location": "Current location of the data asset (e.g., S3 path)",
    }
    return top_level_nodes


@mcp.tool()
def get_additional_schema_help():
    """
    Advice to follow for creating MongoDB aggregations for the metadata
    """
    return """

Key Requirements when creating MongoDB queries:
Always unwind procedures field
Use data_description.modalities.name for modality queries
For questions on modalities, always unwind the modalities field.
Use $regex over $elemMatch

Handle duration queries carefully:
To find the duration of an acquisition, strictly follow the following aggregation stage -
{{
    $addFields: {{
      acquisition_duration_ms: {{
        $subtract: [
          {{ $dateFromString: {{ dateString: "$acquisition.acquisition_end_time" }} }},
          {{ $dateFromString: {{ dateString: "$acquisition.acquisition_start_time" }} }}
        ]
      }}
    }}
  }}

All data collection metadata is under 'acquisition' regardless of modality
(imaging or physiology). The 'acquisition' field contains data_streams,
stimulus_epochs, and subject_details.
"""


@mcp.tool()
def get_modality_types():
    """
    Exposes how to access data modality information within data assets
    """
    return """
Here are the different modality types:
Access them through data_description.modalities.name or data_description.modalities.abbreviation
1.
    name: "Behavior"
    abbreviation: "behavior"
2.
    name: "Behavior videos"
    abbreviation: "behavior-videos"
3.
    name: "Confocal microscopy"
    abbreviation: "confocal"
4.
    name: "Electromyography"
    abbreviation: "EMG"
5.
    name: "Extracellular electrophysiology"
    abbreviation: "ecephys"
6.
    name: "Fiber photometry"
    abbreviation: "fib"
7.
    name: "Fluorescence micro-optical sectioning tomography"
    abbreviation: "fMOST"
8.
    name: "Intracellular electrophysiology"
    abbreviation: "icephys"
9.
    name: "Intrinsic signal imaging"
    abbreviation: "ISI"
10.
    name: "Magnetic resonance imaging"
    abbreviation: "MRI"
11.
    name: "Multiplexed error-robust fluorescence in situ hybridization"
    abbreviation: "merfish"
12.
    name: "Planar optical physiology"
    abbreviation: "pophys"
13.
    name: "Scanned line projection imaging"
    abbreviation: "slap"
14.
    name: "Selective plane illumination microscopy"
    abbreviation: "SPIM"
"""


@mcp.tool()
def get_quality_control_example() -> dict:
    """
    Example of the quality_control schema.
    Each metric has modality, stage, tags, status_history, and reference.
    """
    return """
    The quality_control schema defines how quality metrics are organized
    and evaluated for data assets:

- Each data asset has an array of "metrics"
- Each metric contains:
  - modality: The type of data (SPIM, ecephys, behavior, etc.)
  - stage: When quality was assessed (Raw data, Processing, Analysis, Multi-asset)
  - tags: List of string tags for grouping
  - status_history: Array of status entries with timestamp and status value
  - reference: Optional reference link or description
- Top-level fields: default_grouping, allow_tag_failures

Important quality_control query patterns:
1. To query metrics by modality:
   {{"quality_control.metrics": {{"\\$elemMatch": {{"modality.abbreviation": "SPIM"}}}}}}

2. To unwind and query individual metrics:
   [{{"\\$unwind": "$quality_control.metrics"}}, {{"\\$match": {{"quality_control.metrics.<field>": <value>}}}}]

3. To query latest status (check status_history array):
   [{{"\\$unwind": "$quality_control.metrics"}},
    {{"\\$unwind": "$quality_control.metrics.status_history"}},
    {{"\\$match": {{"quality_control.metrics.status_history.status": "Pass"}}}}]

4. For aggregating QC statistics by modality:
   [{{"\\$unwind": "$quality_control.metrics"}},
    {{"\\$group": {{"_id": "$quality_control.metrics.modality.abbreviation", "count": {{"\\$sum": 1}}}}}}]

Example queries:
- Find assets with failed QC metrics:
  {{"quality_control.metrics.status_history.status": "Fail"}}
- Find SPIM data with pending QC:
  {{"quality_control.metrics": {{"\\$elemMatch": {{"modality.abbreviation": "SPIM", "status_history.status": "Pending"}}}}}}
- Count metrics per asset:
  {{"\\$project": {{"metricCount": {{"\\$size": "$quality_control.metrics"}}}}}}

"""


