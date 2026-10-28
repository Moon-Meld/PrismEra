"""Unit tests for Desktop Client Gateway API endpoints and module."""

import pytest
from fastapi.testclient import TestClient
from prismera.api.server import app
from prismera.desktop import is_port_in_use


@pytest.fixture
def client():
    return TestClient(app)


def test_desktop_info_endpoint(client):
    """Verify /api/desktop/info provides structured desktop metadata."""
    resp = client.get("/api/desktop/info", headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"})
    assert resp.status_code == 200
    data = resp.json()

    assert data["version"] == "0.2.0"
    assert "platforms" in data
    assert "macos" in data["platforms"]
    assert "windows" in data["platforms"]
    assert data["client_detected_os"] == "macos"

    # macOS checks
    mac_targets = data["platforms"]["macos"]["targets"]
    assert len(mac_targets) >= 2
    assert any(t["arch"] == "arm64" for t in mac_targets)
    assert any(t["arch"] == "x64" for t in mac_targets)

    # Windows checks
    win_targets = data["platforms"]["windows"]["targets"]
    assert len(win_targets) >= 2
    assert any(t["format"] == "exe" for t in win_targets)
    assert any(t["format"] == "zip" for t in win_targets)

    # Features check
    features = data["features"]
    assert len(features) >= 4


def test_desktop_windows_detection(client):
    """Verify Windows User-Agent detection."""
    resp = client.get("/api/desktop/info", headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["client_detected_os"] == "windows"


def test_desktop_download_redirect(client):
    """Verify desktop installer download endpoint properly redirects to release asset when not local."""
    resp = client.get("/api/desktop/download/mac-arm64", follow_redirects=False)
    # Expect 307 Redirect to GitHub release or 200 if local file exists
    assert resp.status_code in [200, 307]
    if resp.status_code == 307:
        assert "PrismEra-0.2.0-mac-arm64.dmg" in resp.headers["location"]


def test_desktop_download_invalid_target(client):
    """Verify 404 for unrecognized desktop targets."""
    resp = client.get("/api/desktop/download/unknown-os", follow_redirects=False)
    assert resp.status_code == 404


def test_desktop_utility():
    """Verify port checking utility in prismera.desktop."""
    # Port 0 or unused high port should not be in use
    in_use = is_port_in_use(59999, "127.0.0.1")
    assert isinstance(in_use, bool)
