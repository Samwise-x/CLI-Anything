"""Obsidian Local REST API wrapper — the single module that makes network requests.

Obsidian Local REST API plugin runs an HTTPS server (default: https://localhost:27124).
Authentication is via Bearer token configured in the plugin settings.
Loopback accepts the plugin's self-signed certificate; remote hosts verify TLS.
"""

import os
from urllib.parse import urlsplit

import requests
from typing import Any

# Default Obsidian Local REST API URL
DEFAULT_BASE_URL = "https://localhost:27124"


def _headers(api_key: str, accept: str = "application/json",
             content_type: str | None = None) -> dict:
    """Build request headers with Bearer auth."""
    h = {"Authorization": f"Bearer {api_key}", "Accept": accept}
    if content_type:
        h["Content-Type"] = content_type
    return h


def _safe_error_body(resp: requests.Response, api_key: str) -> str:
    """Keep API diagnostics useful without echoing the Bearer credential."""
    body = resp.text
    return body.replace(api_key, "[redacted]") if api_key else body


def _verify_tls(base_url: str) -> bool | str:
    """Verify remote certificates; allow the plugin's self-signed loopback cert."""
    parsed = urlsplit(base_url)
    hostname = (parsed.hostname or "").lower()
    is_loopback = hostname in {"localhost", "127.0.0.1", "::1"}
    if not is_loopback and parsed.scheme.lower() != "https":
        raise ValueError("Obsidian API credentials require HTTPS for non-loopback hosts")
    ca_bundle = os.environ.get("OBSIDIAN_CA_BUNDLE")
    if ca_bundle:
        return ca_bundle
    if is_loopback:
        return False
    return True


def api_get(base_url: str, endpoint: str, api_key: str,
            params: dict | None = None, timeout: int = 30) -> Any:
    """Perform a GET request against the Obsidian REST API."""
    url = f"{base_url.rstrip('/')}{endpoint}"
    try:
        resp = requests.get(url, headers=_headers(api_key),
                           params=params, timeout=timeout, verify=_verify_tls(base_url))
        resp.raise_for_status()
        if resp.status_code == 204 or not resp.content:
            return {"status": "ok"}
        content_type = resp.headers.get("content-type", "")
        if "application/json" in content_type:
            return resp.json()
        return {"content": resp.text}
    except requests.exceptions.ConnectionError as e:
        raise RuntimeError(
            f"Cannot connect to Obsidian REST API at {base_url}. "
            "Is Obsidian running with the Local REST API plugin enabled?"
        ) from e
    except requests.exceptions.HTTPError as e:
        raise RuntimeError(
            f"Obsidian API error {resp.status_code} on GET {endpoint}: {_safe_error_body(resp, api_key)}"
        ) from e
    except requests.exceptions.Timeout as e:
        raise RuntimeError(
            f"Request to Obsidian timed out: GET {endpoint}"
        ) from e


def api_post(base_url: str, endpoint: str, api_key: str,
             data: dict | None = None, params: dict | None = None,
             timeout: int = 30) -> Any:
    """Perform a POST request against the Obsidian REST API."""
    url = f"{base_url.rstrip('/')}{endpoint}"
    try:
        resp = requests.post(url, headers=_headers(api_key),
                            json=data, params=params,
                            timeout=timeout, verify=_verify_tls(base_url))
        resp.raise_for_status()
        if resp.status_code == 204 or not resp.content:
            return {"status": "ok"}
        content_type = resp.headers.get("content-type", "")
        if "application/json" in content_type:
            return resp.json()
        return {"content": resp.text}
    except requests.exceptions.ConnectionError as e:
        raise RuntimeError(
            f"Cannot connect to Obsidian REST API at {base_url}. "
            "Is Obsidian running with the Local REST API plugin enabled?"
        ) from e
    except requests.exceptions.HTTPError as e:
        raise RuntimeError(
            f"Obsidian API error {resp.status_code} on POST {endpoint}: {_safe_error_body(resp, api_key)}"
        ) from e
    except requests.exceptions.Timeout as e:
        raise RuntimeError(
            f"Request to Obsidian timed out: POST {endpoint}"
        ) from e


def api_post_raw(base_url: str, endpoint: str, api_key: str,
                 body: str, content_type: str,
                 params: dict | None = None, timeout: int = 30) -> Any:
    """POST a raw body with a caller-provided Content-Type.

    Used for Obsidian endpoints that require vendor-specific media types
    (e.g. ``application/vnd.olrapi.dataview.dql+txt`` for the search endpoint),
    where the standard ``api_post`` JSON path would be rejected with
    ``40012 Unknown or invalid Content-Type``.
    """
    url = f"{base_url.rstrip('/')}{endpoint}"
    try:
        headers = _headers(api_key, content_type=content_type)
        resp = requests.post(url, headers=headers,
                             data=body.encode("utf-8"), params=params,
                             timeout=timeout, verify=_verify_tls(base_url))
        resp.raise_for_status()
        if resp.status_code == 204 or not resp.content:
            return {"status": "ok"}
        resp_ct = resp.headers.get("content-type", "")
        if "application/json" in resp_ct:
            return resp.json()
        return {"content": resp.text}
    except requests.exceptions.ConnectionError as e:
        raise RuntimeError(
            f"Cannot connect to Obsidian REST API at {base_url}. "
            "Is Obsidian running with the Local REST API plugin enabled?"
        ) from e
    except requests.exceptions.HTTPError as e:
        raise RuntimeError(
            f"Obsidian API error {resp.status_code} on POST {endpoint}: {_safe_error_body(resp, api_key)}"
        ) from e
    except requests.exceptions.Timeout as e:
        raise RuntimeError(
            f"Request to Obsidian timed out: POST {endpoint}"
        ) from e


def api_put(base_url: str, endpoint: str, api_key: str,
            content: str = "", content_type: str = "text/markdown",
            timeout: int = 30) -> Any:
    """Perform a PUT request (sends raw text, not JSON)."""
    url = f"{base_url.rstrip('/')}{endpoint}"
    try:
        headers = _headers(api_key, content_type=content_type)
        resp = requests.put(url, headers=headers, data=content.encode("utf-8"),
                           timeout=timeout, verify=_verify_tls(base_url))
        resp.raise_for_status()
        if resp.status_code == 204 or not resp.content:
            return {"status": "ok"}
        ct = resp.headers.get("content-type", "")
        if "application/json" in ct:
            return resp.json()
        return {"status": "ok"}
    except requests.exceptions.ConnectionError as e:
        raise RuntimeError(
            f"Cannot connect to Obsidian REST API at {base_url}. "
            "Is Obsidian running with the Local REST API plugin enabled?"
        ) from e
    except requests.exceptions.HTTPError as e:
        raise RuntimeError(
            f"Obsidian API error {resp.status_code} on PUT {endpoint}: {_safe_error_body(resp, api_key)}"
        ) from e
    except requests.exceptions.Timeout as e:
        raise RuntimeError(
            f"Request to Obsidian timed out: PUT {endpoint}"
        ) from e


def api_delete(base_url: str, endpoint: str, api_key: str,
               timeout: int = 30) -> Any:
    """Perform a DELETE request."""
    url = f"{base_url.rstrip('/')}{endpoint}"
    try:
        resp = requests.delete(url, headers=_headers(api_key),
                              timeout=timeout, verify=_verify_tls(base_url))
        resp.raise_for_status()
        if resp.status_code == 204 or not resp.content:
            return {"status": "ok"}
        ct = resp.headers.get("content-type", "")
        if "application/json" in ct:
            return resp.json()
        return {"status": "ok"}
    except requests.exceptions.ConnectionError as e:
        raise RuntimeError(
            f"Cannot connect to Obsidian REST API at {base_url}. "
            "Is Obsidian running with the Local REST API plugin enabled?"
        ) from e
    except requests.exceptions.HTTPError as e:
        raise RuntimeError(
            f"Obsidian API error {resp.status_code} on DELETE {endpoint}: {_safe_error_body(resp, api_key)}"
        ) from e
    except requests.exceptions.Timeout as e:
        raise RuntimeError(
            f"Request to Obsidian timed out: DELETE {endpoint}"
        ) from e


def is_available(api_key: str, base_url: str = DEFAULT_BASE_URL) -> bool:
    """Check if Obsidian REST API is reachable."""
    try:
        resp = requests.get(
            f"{base_url.rstrip('/')}/",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=5,
            verify=_verify_tls(base_url),
        )
        return resp.status_code == 200
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        return False
