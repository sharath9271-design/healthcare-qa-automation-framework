"""Offline unit tests for FhirClient itself (no network calls).

The rest of the suite exercises a real FHIR server; these tests just pin
down FhirClient's request-building behaviour with a mocked session so it
can be verified in any environment, including one with no internet access.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from fhir_client import DEFAULT_BASE_URL, FhirClient


def _mock_response(status_code=200, json_body=None, content=b"{}"):
    resp = MagicMock()
    resp.status_code = status_code
    resp.content = content
    resp.json.return_value = json_body if json_body is not None else {}
    return resp


def test_defaults_to_public_hapi_fhir_server():
    client = FhirClient()
    assert client.base_url == DEFAULT_BASE_URL


def test_base_url_can_be_overridden():
    client = FhirClient(base_url="https://example.org/fhir/")
    assert client.base_url == "https://example.org/fhir"


def test_create_posts_to_resource_collection_endpoint():
    client = FhirClient(base_url="https://example.org/fhir")
    with patch.object(client.session, "post", return_value=_mock_response(201, {"id": "abc"})) as mock_post:
        result = client.create("Patient", {"resourceType": "Patient"})

    mock_post.assert_called_once()
    called_url = mock_post.call_args.args[0]
    assert called_url == "https://example.org/fhir/Patient"
    assert result.status_code == 201
    assert result.body["id"] == "abc"


def test_read_builds_resource_id_url():
    client = FhirClient(base_url="https://example.org/fhir")
    with patch.object(client.session, "get", return_value=_mock_response(200, {"id": "42"})) as mock_get:
        result = client.read("Patient", "42")

    called_url = mock_get.call_args.args[0]
    assert called_url == "https://example.org/fhir/Patient/42"
    assert result.body["id"] == "42"


def test_search_passes_query_params():
    client = FhirClient(base_url="https://example.org/fhir")
    with patch.object(client.session, "get", return_value=_mock_response(200, {"resourceType": "Bundle"})) as mock_get:
        client.search("Patient", family="Smith")

    assert mock_get.call_args.kwargs["params"] == {"family": "Smith"}


def test_delete_handles_empty_response_body():
    client = FhirClient(base_url="https://example.org/fhir")
    with patch.object(client.session, "delete", return_value=_mock_response(204, content=b"")) as mock_delete:
        result = client.delete("Patient", "42")

    mock_delete.assert_called_once()
    assert result.status_code == 204
    assert result.body == {}
