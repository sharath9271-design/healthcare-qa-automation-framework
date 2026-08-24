"""Positive-path API tests against a FHIR R4 Patient endpoint.

These run against the public HAPI FHIR test server by default (see
fhir_client.py). Each test creates its own resource with a unique,
synthetic surname and deletes it afterwards, so the suite is safe to run
repeatedly against a shared public sandbox.
"""

from __future__ import annotations

from typing import Any

from fhir_client import FhirClient


def test_create_patient_returns_201_with_id(fhir_client: FhirClient, valid_patient_payload: dict[str, Any]):
    response = fhir_client.create("Patient", valid_patient_payload)

    assert response.status_code == 201
    assert response.body["resourceType"] == "Patient"
    assert "id" in response.body

    fhir_client.delete("Patient", response.body["id"])


def test_created_patient_can_be_read_back(fhir_client: FhirClient, valid_patient_payload: dict[str, Any]):
    created = fhir_client.create("Patient", valid_patient_payload)
    patient_id = created.body["id"]

    try:
        fetched = fhir_client.read("Patient", patient_id)

        assert fetched.status_code == 200
        assert fetched.body["id"] == patient_id
        assert fetched.body["name"][0]["family"] == valid_patient_payload["name"][0]["family"]
        assert fetched.body["birthDate"] == valid_patient_payload["birthDate"]
    finally:
        fhir_client.delete("Patient", patient_id)


def test_search_patient_by_family_name(
    fhir_client: FhirClient, valid_patient_payload: dict[str, Any], unique_family_name: str
):
    created = fhir_client.create("Patient", valid_patient_payload)
    patient_id = created.body["id"]

    try:
        results = fhir_client.search("Patient", family=unique_family_name)

        assert results.status_code == 200
        assert results.body["resourceType"] == "Bundle"
        assert results.body.get("total", 0) >= 1
        returned_ids = [entry["resource"]["id"] for entry in results.body.get("entry", [])]
        assert patient_id in returned_ids
    finally:
        fhir_client.delete("Patient", patient_id)


def test_patient_resource_has_required_fhir_fields(fhir_client: FhirClient, valid_patient_payload: dict[str, Any]):
    created = fhir_client.create("Patient", valid_patient_payload)
    patient_id = created.body["id"]

    try:
        assert created.body["resourceType"] == "Patient"
        assert created.body["id"]
        assert "meta" in created.body
        assert "versionId" in created.body["meta"]
    finally:
        fhir_client.delete("Patient", patient_id)
