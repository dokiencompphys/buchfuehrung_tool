"""Ende-zu-Ende über HTTP: so, wie die App das Backend benutzt."""

from datetime import date

import pytest
from fastapi.testclient import TestClient

from buchfuehrung.api.app import create_app
from buchfuehrung.config import Settings


@pytest.fixture
def client(tmp_path):
    settings = Settings(data_dir=tmp_path, default_ocr_engine="fake", cors_origins=("*",))
    return TestClient(create_app(settings, today=lambda: date(2026, 11, 8)))


def test_manual_month_flow(client):
    draft = client.get("/api/drafts/blank", params={"year": 2026, "month": 11, "region": "BY"})
    assert draft.status_code == 200
    ledger = draft.json()
    assert len(ledger["entries"]) == 30
    assert ledger["entries"][0]["closed"]["name"] == "Allerheiligen"

    ledger["entries"][1]["income"] = "250.00"
    ledger["entries"][1]["expense"] = "40.10"
    saved = client.put("/api/months/2026/11", json=ledger)
    assert saved.status_code == 200
    assert saved.json()["created"] is True
    assert saved.json()["ledger"]["totals"] == {
        "income": "250.00",
        "expense": "40.10",
        "balance": "209.90",
    }

    again = client.put("/api/months/2026/11", json=ledger)
    assert again.json()["created"] is False

    archive = client.get("/api/months").json()
    assert [(i["year"], i["month"]) for i in archive] == [(2026, 11)]

    export = client.get("/api/months/2026/11/export", params={"format": "xlsx"})
    assert export.status_code == 200
    assert 'filename="buchfuehrung_2026-11.xlsx"' in export.headers["content-disposition"]

    metrics = client.get("/api/analytics").json()
    assert metrics["income_ytd"] == "250.00"


def test_photo_flow_with_demo_engine(client):
    response = client.post(
        "/api/drafts/photo",
        data={"region": "BE"},
        files={"photo": ("seite.jpg", b"\xff\xd8fake", "image/jpeg")},
    )
    assert response.status_code == 200
    body = response.json()
    assert (body["ledger"]["year"], body["ledger"]["month"]) == (2026, 11)
    assert body["recognized_days"] == 4
    photo_id = body["ledger"]["photo_id"]
    assert client.get(f"/api/photos/{photo_id}").content == b"\xff\xd8fake"


def test_missing_ocr_model_is_reported(client):
    response = client.post(
        "/api/drafts/photo",
        data={"region": "BE", "engine": "does-not-exist"},
        files={"photo": ("seite.jpg", b"x", "image/jpeg")},
    )
    assert response.status_code == 503


def test_incomplete_month_is_rejected(client):
    ledger = client.get(
        "/api/drafts/blank", params={"year": 2026, "month": 2, "region": "BE"}
    ).json()
    ledger["entries"] = ledger["entries"][:-1]
    assert client.put("/api/months/2026/2", json=ledger).status_code == 422


def test_unknown_region(client):
    r = client.get("/api/drafts/blank", params={"year": 2026, "month": 2, "region": "XX"})
    assert r.status_code == 422


def test_photo_path_traversal_is_blocked(client):
    assert client.get("/api/photos/..%2Fbuchfuehrung.sqlite3").status_code == 404
