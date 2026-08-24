"""Thin HTTP client for a FHIR R4 server.

Defaults to the public HAPI FHIR test server (https://hapi.fhir.org/baseR4),
a sandbox the HL7 community runs specifically for demos and automated
testing — no authentication and no real patient data. The base URL is
configurable via the FHIR_BASE_URL environment variable so the same client
can point at a different R4-compliant server (a local HAPI FHIR Docker
image, a vendor sandbox, etc.) without touching test code.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import requests

DEFAULT_BASE_URL = "https://hapi.fhir.org/baseR4"
FHIR_HEADERS = {
    "Content-Type": "application/fhir+json",
    "Accept": "application/fhir+json",
}


@dataclass
class FhirResponse:
    status_code: int
    body: dict[str, Any]


class FhirClient:
    """Small wrapper around `requests` for FHIR resource CRUD + search."""

    def __init__(self, base_url: str | None = None, timeout: float = 20.0):
        self.base_url = (base_url or os.environ.get("FHIR_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()

    def create(self, resource_type: str, payload: dict[str, Any]) -> FhirResponse:
        resp = self.session.post(
            f"{self.base_url}/{resource_type}",
            json=payload,
            headers=FHIR_HEADERS,
            timeout=self.timeout,
        )
        return FhirResponse(status_code=resp.status_code, body=self._safe_json(resp))

    def read(self, resource_type: str, resource_id: str) -> FhirResponse:
        resp = self.session.get(
            f"{self.base_url}/{resource_type}/{resource_id}",
            headers=FHIR_HEADERS,
            timeout=self.timeout,
        )
        return FhirResponse(status_code=resp.status_code, body=self._safe_json(resp))

    def search(self, resource_type: str, **params: str) -> FhirResponse:
        resp = self.session.get(
            f"{self.base_url}/{resource_type}",
            params=params,
            headers=FHIR_HEADERS,
            timeout=self.timeout,
        )
        return FhirResponse(status_code=resp.status_code, body=self._safe_json(resp))

    def delete(self, resource_type: str, resource_id: str) -> FhirResponse:
        resp = self.session.delete(
            f"{self.base_url}/{resource_type}/{resource_id}",
            headers=FHIR_HEADERS,
            timeout=self.timeout,
        )
        body = self._safe_json(resp) if resp.content else {}
        return FhirResponse(status_code=resp.status_code, body=body)

    @staticmethod
    def _safe_json(resp: requests.Response) -> dict[str, Any]:
        try:
            return resp.json()
        except ValueError:
            return {"raw": resp.text}
