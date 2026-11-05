"""
Unit and Integration Tests for CORS Origins and WebSocket Origin Security
"""
import pytest
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.main import app
from app import config
from app.config import is_allowed_origin, CORS_ORIGINS


@pytest.fixture
def client():
    return TestClient(app)


def test_default_cors_origins_include_render_and_localhost():
    """Verify default CORS origins include Render staging and local development ports."""
    assert "https://fertobot-staging.onrender.com" in CORS_ORIGINS
    assert "http://localhost:5173" in CORS_ORIGINS
    assert "http://127.0.0.1:5173" in CORS_ORIGINS
    assert "http://localhost:5174" in CORS_ORIGINS
    assert "http://testserver" in CORS_ORIGINS


def test_wildcard_origin_is_rejected_for_credentials_safety():
    """Verify that wildcard '*' is stripped to prevent insecure credentials configuration."""
    assert "*" not in CORS_ORIGINS


def test_is_allowed_origin_matching():
    """Verify exact match, trailing slash normalization, and rejection of unauthorized domains."""
    # Allowed origins (with or without trailing slash)
    assert is_allowed_origin("https://fertobot-staging.onrender.com") is True
    assert is_allowed_origin("https://fertobot-staging.onrender.com/") is True
    assert is_allowed_origin("http://localhost:5173") is True
    assert is_allowed_origin("http://127.0.0.1:5174") is True

    # Empty or None origin (native mobile / CLI client) permitted
    assert is_allowed_origin(None) is True
    assert is_allowed_origin("") is True

    # Unauthorized domains rejected
    assert is_allowed_origin("https://malicious-phishing.com") is False
    assert is_allowed_origin("http://attacker-site.org") is False


def test_cors_origin_regex_matching(monkeypatch):
    """Verify dynamic Vercel preview domain regex matching."""
    monkeypatch.setattr(config, "CORS_ORIGIN_REGEX", r"^https:\/\/.*\.vercel\.app$")

    # Matching Vercel domains
    assert is_allowed_origin("https://fertobot-ai.vercel.app") is True
    assert is_allowed_origin("https://fertobot-git-preview-branch.vercel.app") is True

    # Non-matching domains rejected
    assert is_allowed_origin("https://evil-site.com") is False
    assert is_allowed_origin("https://vercel.app.malicious.com") is False


def test_http_cors_preflight_and_headers_allowed_origin(client):
    """Verify HTTP CORS response headers for allowed origins."""
    headers = {
        "Origin": "https://fertobot-staging.onrender.com",
        "Access-Control-Request-Method": "POST",
    }
    # Preflight OPTIONS
    response = client.options("/api/chat", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "https://fertobot-staging.onrender.com"
    assert response.headers.get("access-control-allow-credentials") == "true"


def test_http_cors_unauthorized_origin_does_not_return_allow_header(client):
    """Verify unauthorized origin does not receive access-control-allow-origin header."""
    headers = {
        "Origin": "https://unauthorized-domain.com",
    }
    response = client.get("/api/config", headers=headers)
    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


def test_websocket_origin_allowed_connection_succeeds(client):
    """Verify WebSocket handshake succeeds when origin is in allowed CORS list."""
    with client.websocket_connect(
        "/api/ws/stt",
        headers={"origin": "https://fertobot-staging.onrender.com"}
    ) as ws:
        msg = ws.receive_json()
        assert "type" in msg


def test_websocket_origin_no_origin_header_succeeds(client):
    """Verify WebSocket handshake succeeds for clients without Origin header (native CLI/mobile)."""
    with client.websocket_connect("/api/ws/stt") as ws:
        msg = ws.receive_json()
        assert "type" in msg


def test_websocket_origin_unauthorized_is_rejected(client):
    """Verify WebSocket handshake with unauthorized origin is rejected with policy violation (1008)."""
    with pytest.raises(WebSocketDisconnect) as excinfo:
        with client.websocket_connect(
            "/api/ws/stt",
            headers={"origin": "https://malicious-domain.com"}
        ) as ws:
            ws.receive_json()

    assert excinfo.value.code == 1008
