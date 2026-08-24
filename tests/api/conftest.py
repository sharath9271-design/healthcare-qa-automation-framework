from __future__ import annotations

import copy
import json
import pathlib
import uuid
from typing import Any

import pytest

from fhir_client import FhirClient

FIXTURES_PATH = pathlib.Path(__file__).resolve().parents[2] / "fixtures" / "synthetic_patients.json"


@pytest.fixture(scope="session")
def fhir_client() -> FhirClient:
    return FhirClient()


@pytest.fixture()
def synthetic_patients() -> dict[str, Any]:
    with FIXTURES_PATH.open() as f:
        return json.load(f)


@pytest.fixture()
def unique_family_name() -> str:
    """A per-test-run unique surname so search tests don't collide with
    other automated runs hitting the same shared public sandbox."""
    return f"QaFramework{uuid.uuid4().hex[:10]}"


@pytest.fixture()
def valid_patient_payload(synthetic_patients: dict[str, Any], unique_family_name: str) -> dict[str, Any]:
    payload = copy.deepcopy(synthetic_patients["valid_patient_template"])
    payload["name"][0]["family"] = unique_family_name
    return payload
