"""Compact schema navigation for AIND metadata queries."""

import json
from importlib.resources import files
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

_SCHEMA_TREE = json.loads(
    files("aind_data_mcp.resources")
    .joinpath("schema_tree.json")
    .read_text(encoding="utf-8")
)
_SCHEMA_MODELS = _SCHEMA_TREE["models"]


def _schema_tree_path(node: str, path: str | None) -> str:
    if node == "top_level":
        return path or ""
    if not path:
        return node

    node_prefix = f"{node}."
    if path.casefold() in {node.casefold(), node_prefix.casefold()}:
        return node
    if path.casefold().startswith(node_prefix.casefold()):
        return path
    return f"{node}.{path}"


def _render_compact_schema_context(
    node: str, path: str | None, detail: Literal["paths", "example"]
) -> dict[str, Any]:
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
def get_schema_context(
    node: str = "top_level",
    path: str | None = None,
    detail: Literal["tree", "paths", "example"] = "tree",
    max_depth: int = 0,
) -> dict[str, Any] | str:
    """Reveal the complete schema or opt into compact query-oriented views.

    The default tree is complete and shallow. Use a dot-separated ``path``
    such as ``Acquisition.data_streams`` and increase ``max_depth`` to expand
    one branch. Use ``detail='paths'`` for compact query paths or
    ``detail='example'`` for a small synthetic example.
    """
    if detail not in {"tree", "paths", "example"}:
        raise ValueError("detail must be 'tree', 'paths', or 'example'")

    if detail == "tree":
        return _render_schema_tree(_schema_tree_path(node, path), max_depth)

    if max_depth:
        raise ValueError("max_depth is only valid when detail='tree'")
    return _render_compact_schema_context(node, path, detail)


def _find_model(name: str) -> str | None:
    name = name.casefold()
    return next(
        (
            model_name
            for model_name in _SCHEMA_MODELS
            if model_name.casefold() == name
        ),
        None,
    )


def _find_field(model_name: str, name: str) -> dict[str, Any] | None:
    name = name.casefold()
    return next(
        (
            field
            for field in _SCHEMA_MODELS[model_name]["fields"]
            if field["name"].casefold() == name
        ),
        None,
    )


def _append_field(
    lines: list[str],
    field: dict[str, Any],
    indent: str,
    max_depth: int,
    seen: frozenset[str],
) -> None:
    required = ", required" if field["required"] else ""
    detail = field["title"]
    if field["description"]:
        detail += f": {field['description']}"
    lines.append(
        f"{indent}- `{field['name']}` "
        f"({field['type']}{required}) — {detail}"
    )
    if max_depth > 0:
        for child_name in field["children"]:
            if child_name not in seen:
                _append_model(
                    lines,
                    child_name,
                    indent,
                    max_depth - 1,
                    seen,
                )


def _append_model(
    lines: list[str],
    model_name: str,
    indent: str,
    max_depth: int,
    seen: frozenset[str] = frozenset(),
    fields: list[dict[str, Any]] | None = None,
) -> None:
    if model_name in seen:
        return
    model = _SCHEMA_MODELS[model_name]
    lines.append(f"{indent}- **{model_name}** — {model['description']}")
    model_seen = seen | {model_name}
    for field in fields or model["fields"]:
        _append_field(
            lines,
            field,
            indent + "  ",
            max_depth,
            model_seen,
        )


def _resolve_schema_path(
    path: str,
) -> tuple[str | None, list[tuple[str, dict[str, Any]]] | None]:
    parts = [part for part in path.split(".") if part]
    model_name = _find_model(parts[0]) if parts else None
    if model_name is None:
        valid_models = ", ".join(_SCHEMA_TREE["roots"])
        raise ValueError(
            f"unknown schema path '{path}'; choose a root model: "
            f"{valid_models}"
        )
    if len(parts) == 1:
        return model_name, None

    current_models = [model_name]
    for index, part in enumerate(parts[1:]):
        is_last = index == len(parts) - 2
        field_matches = []
        child_models = []
        for current_model in current_models:
            field = _find_field(current_model, part)
            if field is None:
                continue
            if is_last:
                field_matches.append((current_model, field))
            child_models.extend(field["children"])
        if is_last and field_matches:
            return None, field_matches
        current_models = list(dict.fromkeys(child_models))
        if not current_models:
            break

    raise ValueError(
        f"unknown schema path '{path}'; use a model and dot-separated "
        "field names"
    )


def _render_schema_tree(path: str = "", max_depth: int = 0) -> str:
    """Render the bundled schema tree for one optional branch.

    The default returns every root model and its direct fields. Use a
    dot-separated path such as ``Acquisition.data_streams`` to inspect one
    branch, and increase ``max_depth`` to reveal nested model fields below
    that branch.
    """
    if max_depth < 0:
        raise ValueError("max_depth must be non-negative")
    if not isinstance(path, str):
        raise ValueError("path must be a dot-separated schema path")

    path = path.strip()
    if path in {"", "top_level"}:
        if max_depth:
            raise ValueError(
                "path is required when max_depth is greater than zero"
            )
        lines: list[str] = []
        for model_name in _SCHEMA_TREE["roots"]:
            _append_model(lines, model_name, "", max_depth)
        return "\n".join(lines)

    selected_model, field_matches = _resolve_schema_path(path)
    lines = []
    if selected_model is not None:
        _append_model(lines, selected_model, "", max_depth)
    else:
        for parent_model, field in field_matches or []:
            _append_model(
                lines,
                parent_model,
                "",
                max_depth,
                fields=[field],
            )
    return "\n".join(lines)


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
