"""Compact schema navigation for AIND metadata queries."""

from typing import Any, Literal

from .mcp_instance import mcp

_SCHEMA_PATHS: dict[str, dict[str, Any]] = {
    "_id": {"description": "MongoDB data asset identifier", "paths": ["_id"]},
    "name": {"description": "Data asset name", "paths": ["name"]},
    "quality_control": {
        "description": "Quality metrics evaluated on a data asset",
        "paths": [
            "quality_control.metrics.modality.abbreviation",
            "quality_control.metrics.stage",
            "quality_control.metrics.status_history.status",
        ],
    },
    "acquisition": {
        "description": "Data collection episode and streams",
        "paths": [
            "acquisition.acquisition_start_time",
            "acquisition.acquisition_end_time",
            "acquisition.data_streams.stream_start_time",
            "acquisition.data_streams.stream_end_time",
            "acquisition.data_streams.modalities.abbreviation",
            "acquisition.data_streams.modalities.name",
            "acquisition.data_streams.active_devices",
        ],
    },
    "data_description": {
        "description": "Administrative, project, modality, and level metadata",
        "paths": [
            "data_description.project_name",
            "data_description.data_level",
            "data_description.modalities.abbreviation",
            "data_description.modalities.name",
            "data_description.creation_time",
            "data_description.subject_id",
        ],
    },
    "instrument": {
        "description": "Devices and components used for collection",
        "paths": [
            "instrument.instrument_id",
            "instrument.modalities.abbreviation",
            "instrument.components.name",
            "instrument.components.object_type",
        ],
    },
    "procedures": {
        "description": "Procedures performed before data collection",
        "paths": [
            "procedures.subject_procedures.start_date",
            "procedures.subject_procedures.procedures.object_type",
            "procedures.subject_procedures.procedures.injection_materials.name",
            "procedures.subject_procedures.procedures.targeted_structure.name",
        ],
    },
    "processing": {
        "description": "Processing steps, pipelines, and dependencies",
        "paths": [
            "processing.data_processes.name",
            "processing.data_processes.process_type",
            "processing.data_processes.pipeline_name",
            "processing.pipelines.name",
        ],
    },
    "subject": {
        "description": "Subject identity and biological metadata",
        "paths": [
            "subject.subject_id",
            "subject.subject_details.sex",
            "subject.subject_details.date_of_birth",
            "subject.subject_details.strain.name",
            "subject.subject_details.species.name",
            "subject.subject_details.genotype",
            "subject.subject_details.breeding_info.maternal_id",
            "subject.subject_details.breeding_info.maternal_genotype",
            "subject.subject_details.breeding_info.paternal_id",
            "subject.subject_details.breeding_info.paternal_genotype",
            "subject.sex",
        ],
    },
    "model": {
        "description": "Machine learning model metadata",
        "paths": [
            "model.name",
            "model.version",
            "model.architecture",
            "model.software_framework.name",
        ],
    },
    "other_identifiers": {
        "description": "Links to secondary platforms",
        "paths": ["other_identifiers"],
    },
    "location": {
        "description": "Current data asset location",
        "paths": ["location"],
    },
}

_SCHEMA_EXAMPLES = {
    "acquisition": {
        "acquisition": {
            "acquisition_start_time": "2023-04-25T02:35:00-07:00",
            "acquisition_end_time": "2023-04-25T03:16:00-07:00",
            "data_streams": [
                {
                    "stream_start_time": "2023-04-25T02:45:00-07:00",
                    "stream_end_time": "2023-04-25T03:16:00-07:00",
                    "modalities": [{"abbreviation": "ecephys"}],
                }
            ],
        }
    },
    "data_description": {
        "data_description": {
            "project_name": "Example project",
            "data_level": "raw",
            "modalities": [{"name": "Behavior", "abbreviation": "behavior"}],
        }
    },
    "instrument": {
        "instrument": {
            "instrument_id": "EPHYS1",
            "modalities": [{"abbreviation": "ecephys"}],
            "components": [{"object_type": "Camera", "name": "Face Camera"}],
        }
    },
    "procedures": {
        "procedures": {
            "subject_procedures": [
                {
                    "start_date": "2022-07-12",
                    "procedures": [
                        {
                            "object_type": "Brain injection",
                            "injection_materials": [
                                {"name": "AAV2-Flex-ChrimsonR"}
                            ],
                        }
                    ],
                }
            ]
        }
    },
    "processing": {
        "processing": {
            "data_processes": [
                {"name": "File format conversion", "pipeline_name": "Imaging"}
            ],
            "pipelines": [{"name": "Imaging"}],
        }
    },
    "subject": {
        "subject": {
            "subject_id": "123456",
            "subject_details": {
                "sex": "Male",
                "date_of_birth": "2022-11-22",
                "strain": {"name": "C57BL/6J"},
                "genotype": "wt",
                "breeding_info": {
                    "maternal_id": "546543",
                    "maternal_genotype": "wt",
                    "paternal_id": "232323",
                    "paternal_genotype": "wt",
                },
            },
        }
    },
    "quality_control": {
        "quality_control": {
            "metrics": [
                {
                    "modality": {"abbreviation": "SPIM"},
                    "stage": "Raw data",
                    "status_history": [{"status": "Pass"}],
                }
            ]
        }
    },
    "model": {
        "model": {
            "name": "Example model",
            "version": "1.0",
            "architecture": "ResNet",
        }
    },
}


@mcp.tool()
def get_schema_context(
    node: str = "top_level",
    path: str | None = None,
    detail: Literal["paths", "example"] = "paths",
) -> dict[str, Any]:
    """Return compact V2 schema paths or an opt-in small example.

    Use this single hierarchy entry point before calling ``get_records`` or
    ``aggregation_retrieval``. ``node`` is a top-level node such as
    ``subject``, ``data_description``, ``acquisition``, or ``procedures``;
    use ``top_level`` to list all nodes. ``path`` filters the returned paths,
    for example ``subject_details.breeding_info``. ``detail`` is ``paths``
    by default and can be ``example`` when a compact synthetic example is
    needed. Examples are intentionally small and omit unrelated fields.
    """
    if detail not in {"paths", "example"}:
        raise ValueError("detail must be 'paths' or 'example'")

    if node == "top_level":
        if detail == "example":
            raise ValueError("choose a schema node when detail='example'")
        return {
            "nodes": {
                name: value["description"]
                for name, value in _SCHEMA_PATHS.items()
            }
        }

    if node not in _SCHEMA_PATHS:
        valid_nodes = ", ".join(sorted(_SCHEMA_PATHS))
        raise ValueError(
            f"unknown node '{node}'; choose one of: {valid_nodes}"
        )

    if detail == "example":
        example = _SCHEMA_EXAMPLES.get(node)
        if example is None:
            raise ValueError(f"no compact example is available for '{node}'")
        return {"node": node, "path": path, "example": example}

    node_paths = _SCHEMA_PATHS[node]["paths"]
    if path:
        path_prefix = (
            f"{node}.{path}" if not path.startswith(f"{node}.") else path
        )
        node_paths = [
            schema_path
            for schema_path in node_paths
            if schema_path == path_prefix
            or schema_path.startswith(f"{path_prefix}.")
        ]
    return {"node": node, "path": path, "paths": node_paths}


@mcp.tool()
def get_modality_types():
    """List modality names and abbreviations used in data asset metadata."""
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
