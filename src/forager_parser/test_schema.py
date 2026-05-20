"""
Validate that all profile.yaml and variant YAMLs in merchants/ conform to
schema/merchant-profile.v1.json.
"""
import json
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator, ValidationError

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = REPO_ROOT / "schema" / "merchant-profile.v1.json"
PROFILES_DIR = REPO_ROOT / "merchants"


def _all_profile_files():
    """Find all profile.yaml + variants/*.yaml under merchants/."""
    files = []
    for p in PROFILES_DIR.rglob("profile.yaml"):
        files.append(p)
    for p in PROFILES_DIR.rglob("variants/*.yaml"):
        files.append(p)
    return sorted(files)


@pytest.fixture(scope="module")
def validator():
    with SCHEMA_PATH.open() as f:
        schema = json.load(f)
    return Draft202012Validator(schema)


@pytest.mark.parametrize("profile_path", _all_profile_files(),
                         ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_profile_schema_valid(profile_path, validator):
    """Each profile/variant must validate against the schema."""
    with profile_path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)

    errors = list(validator.iter_errors(data))
    if errors:
        msg = f"\nProfile {profile_path.relative_to(REPO_ROOT)} has schema errors:\n"
        for err in errors:
            path_str = "/".join(str(p) for p in err.absolute_path) or "<root>"
            msg += f"  at {path_str}: {err.message}\n"
        pytest.fail(msg)
