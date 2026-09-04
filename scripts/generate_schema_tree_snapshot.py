"""Generate the bundled AIND schema tree from aind-data-schema."""

import json
import sys
import typing
from pathlib import Path

from aind_data_schema.utils import schema_tree
from aind_data_schema.utils.schema_tree import DataCoreModel


OUTPUT_PATH = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "aind_data_mcp"
    / "resources"
    / "schema_tree.json"
)


def collect_models() -> dict[type, None]:
    models: dict[type, None] = {}
    pending = list(
        sorted(
            DataCoreModel.__subclasses__(), key=lambda model: model.__name__
        )
    )
    while pending:
        model = pending.pop(0)
        if model in models:
            continue
        models[model] = None
        try:
            hints = typing.get_type_hints(model, include_extras=True)
        except Exception:
            continue
        for field_name, field_info in model.model_fields.items():
            if field_name in schema_tree._SKIP_FIELDS:
                continue
            annotation = hints.get(field_name, field_info.annotation)
            pending.extend(schema_tree._extract_expandable_types(annotation))
    return models


def serialize_model(model: type) -> dict:
    fields = []
    try:
        hints = typing.get_type_hints(model, include_extras=True)
    except Exception:
        hints = {}
    for field_name, field_info in model.model_fields.items():
        if field_name in schema_tree._SKIP_FIELDS:
            continue
        annotation = hints.get(field_name, field_info.annotation)
        fields.append(
            {
                "name": field_name,
                "type": schema_tree._annotation_to_str(annotation),
                "title": field_info.title or field_name,
                "description": field_info.description or "",
                "required": field_info.is_required(),
                "children": [
                    child.__name__
                    for child in schema_tree._extract_expandable_types(
                        annotation
                    )
                ],
            }
        )
    return {
        "description": (model.__doc__ or "").strip().split("\n")[0],
        "fields": fields,
    }


def main() -> None:
    models = collect_models()
    model_names = [model.__name__ for model in models]
    if len(model_names) != len(set(model_names)):
        raise RuntimeError("schema model names must be unique")
    snapshot = {
        "source": "aind-data-schema",
        "roots": [
            model.__name__
            for model in sorted(
                DataCoreModel.__subclasses__(),
                key=lambda model: model.__name__,
            )
        ],
        "models": {
            model.__name__: serialize_model(model)
            for model in sorted(models, key=lambda model: model.__name__)
        },
    }
    OUTPUT_PATH.write_text(
        json.dumps(snapshot, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(models)} models to {OUTPUT_PATH}")


if __name__ == "__main__":
    sys.exit(main())
