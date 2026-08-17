import os
os.environ.setdefault("FLASK_SECRET_KEY", "test-secret")
os.environ.setdefault("APP_ENV", "development")

import pytest
from app import app as flask_app


@pytest.fixture
def client():
    flask_app.config.update(TESTING=True)
    with flask_app.test_client() as client:
        yield client


def test_health_live(client):
    resp = client.get("/health/live")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"


def test_health_ready(client):
    resp = client.get("/health/ready")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"
    assert data["db"] == "ok"


def test_login_page_accessible(client):
    resp = client.get("/login")
    assert resp.status_code == 200


def test_dashboard_redirects_when_not_authenticated(client):
    resp = client.get("/", follow_redirects=False)
    assert resp.status_code in (301, 302)
    assert "/login" in resp.headers["Location"]
