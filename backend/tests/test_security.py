import pytest
from app import config
from app.config import redact_sensitive
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_redact_sensitive_removes_configured_api_key():
    # Temporarily set a dummy key to verify scrubbing
    original_key = config.GNANI_API_KEY
    try:
        config.GNANI_API_KEY = "gnani_dummy_test_placeholder_token"
        raw_text = "Error calling endpoint with key gnani_dummy_test_placeholder_token: connection refused"
        sanitized = redact_sensitive(raw_text)
        assert "gnani_dummy_test_placeholder_token" not in sanitized
        assert "[REDACTED_API_KEY]" in sanitized
    finally:
        config.GNANI_API_KEY = original_key


def test_redact_sensitive_removes_auth_header_patterns():
    raw_header_str = "Request failed: X-API-Key-ID: my-api-token-998811 at https://api.vachana.ai"
    sanitized = redact_sensitive(raw_header_str)
    assert "my-api-token-998811" not in sanitized
    assert "[REDACTED_KEY]" in sanitized

    bearer_str = "Authorization: Bearer secret_bearer_token_xyz12345"
    sanitized_bearer = redact_sensitive(bearer_str)
    assert "secret_bearer_token_xyz12345" not in sanitized_bearer
    assert "[REDACTED_TOKEN]" in sanitized_bearer


def test_cors_preflight_headers():
    response = client.options(
        "/api/chat",
        headers={
            "Origin": "http://localhost:5174",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5174"
