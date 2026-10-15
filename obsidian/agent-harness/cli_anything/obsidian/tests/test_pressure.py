import requests
import pytest
from unittest.mock import MagicMock, patch

from cli_anything.obsidian.utils.obsidian_backend import api_get


def test_http_error_does_not_echo_bearer_token():
    token = "synthetic-bearer-secret-9f31"
    response = MagicMock()
    response.status_code = 401
    response.text = f'{{"message":"bad authorization Bearer {token}"}}'
    response.raise_for_status.side_effect = requests.exceptions.HTTPError("401 Unauthorized")
    with patch("cli_anything.obsidian.utils.obsidian_backend.requests.get", return_value=response):
        with pytest.raises(RuntimeError) as caught:
            api_get("https://vault.example", "/vault/", token)

    assert token not in str(caught.value)
    assert "redacted" in str(caught.value).lower()
