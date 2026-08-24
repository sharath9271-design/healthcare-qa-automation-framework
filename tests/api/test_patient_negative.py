"""Negative-path API tests: malformed input and missing resources."""

from __future__ import annotations

import uuid
from typing import Any

from fhir_client import FhirClient


def test_create_patient_missing_resource_type_is_rejected(
    fhir_client: FhirClient, synthetic_patients: dict[str, Any]
):
    response = fhir_client.create("Patient", synthetic_patients["missing_resource_type"])

    assert response.status_code == 400


def test_create_patient_with_invalid_birth_date_is_rejected(
    fhir_client: FhirClient, synthetic_patients: dict[str, Any]
):
    response = fhir_client.create("Patient", synthetic_patients["invalid_birth_date"])

    assert response.status_code == 400


def test_get_nonexistent_patient_returns_404(fhir_client: FhirClient):
    bogus_id = f"qa-does-not-exist-{uuid.uuid4().hex}"

    response = fhir_client.read("Patient", bogus_id)

    assert response.status_code == 404


def test_search_with_no_matches_returns_empty_bundle(fhir_client: FhirClient):
    response = fhir_client.search("Patient", family=f"NoSuchFamily{uuid.uuid4().hex[:12]}")

    assert response.status_code == 200
    assert response.body["resourceType"] == "Bundle"
    assert response.body.get("total", 0) == 0
