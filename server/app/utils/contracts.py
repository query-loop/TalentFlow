from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from jsonschema import Draft202012Validator, RefResolver


# Resolve to repo root: .../server/app/utils -> parents[3] = repo root
REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMAS_DIR = REPO_ROOT / "contracts" / "schemas"


def load_schema(name: str) -> dict[str, Any]:
    """
    Load a JSON schema by filename from contracts/schemas.
    Example: load_schema('generate_response.json')
    """
    path = (SCHEMAS_DIR / name).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Schema not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def make_validator(root_schema: dict[str, Any]) -> Draft202012Validator:
    # Provide a resolver rooted at SCHEMAS_DIR so $ref with relative paths resolves
    resolver = RefResolver(base_uri=SCHEMAS_DIR.as_uri() + "/", referrer=root_schema)
    return Draft202012Validator(root_schema, resolver=resolver)


def validate_against(schema_file: str, data: Any) -> Optional[list[str]]:
    """
    Validate data against the given schema file. Returns a list of error strings
    if invalid, or None if valid.
    """
    schema = load_schema(schema_file)
    validator = make_validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda e: e.path)
    if errors:
        return [f"{'/'.join(map(str, e.path))}: {e.message}" for e in errors]
    return None
