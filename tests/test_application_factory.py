import hashlib
import io
import json
import uuid
import zipfile

import cv2
import numpy as np

from app import create_app
from database import db
from models import Claim


def test_factory_registers_api_and_request_middleware(tmp_path):
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite://",
        "UPLOAD_FOLDER": str(tmp_path),
    })

    response = app.test_client().get("/api/claims")

    assert response.status_code == 200
    assert response.get_json() == {"status": "success", "count": 0, "data": []}
    assert uuid.UUID(response.headers["X-Request-ID"]).version == 4
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["X-Response-Time"].endswith("ms")

    health_response = app.test_client().get("/healthz")
    assert health_response.status_code == 200
    assert health_response.get_json() == {"status": "ok"}


def test_factory_keeps_unknown_routes_json(tmp_path):
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite://",
        "UPLOAD_FOLDER": str(tmp_path),
    })

    response = app.test_client().get("/missing")

    assert response.status_code == 404
    assert response.get_json()["status"] == "error"


def test_factory_uses_configured_upload_directory(tmp_path, monkeypatch):
    upload_folder = tmp_path / "persistent-uploads"
    monkeypatch.setenv("UPLOAD_FOLDER", str(upload_folder))
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite://",
    })

    assert app.config["UPLOAD_FOLDER"] == str(upload_folder)
    assert upload_folder.is_dir()


def test_processing_persists_claim_and_export_contains_provenance(tmp_path, monkeypatch):
    import services.claim_service as claim_service

    def fake_augment(image_path, output_folder):
        results = []
        for effect in ("rain", "low_light", "glare", "fog", "sensor_noise"):
            filename = f"fixture_{effect}.jpg"
            (tmp_path / filename).write_bytes(effect.encode())
            results.append({"effect": effect, "filename": filename, "path": str(tmp_path / filename)})
        return results

    monkeypatch.setattr(claim_service, "augment_claim_image", fake_augment)
    monkeypatch.setattr(claim_service, "classify_damage_description", lambda notes, image_path, selected_preset: {
        "damage_type": "DENT",
        "severity": "MODERATE",
        "estimated_action": "REPAIR",
        "confidence_score": 0.9,
        "summary": "Test assessment.",
        "visual_findings": ["Door panel is dented."],
        "preset_conflict": True,
        "notes_conflict": False,
        "review_recommended": True,
        "review_reasons": ["Visible damage conflicts with the Door Scratch preset."],
        "inference": {"provider": "groq", "model": "qwen/qwen3.8-27b", "request_id": "req-test"},
    })
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite://",
        "UPLOAD_FOLDER": str(tmp_path),
    })
    _, encoded = cv2.imencode(".jpg", np.full((16, 16, 3), 128, dtype=np.uint8))
    image_bytes = encoded.tobytes()
    client = app.test_client()

    response = client.post(
        "/api/process-claim",
        data={
            "photo": (io.BytesIO(image_bytes), "fixture.jpg"),
            "notes": "Door dent",
            "preset": "door_scratch",
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["source_image_hash"] == hashlib.sha256(image_bytes).hexdigest()
    assert len(data["augmented_images"]) == 5
    assert (tmp_path / data["original_image"]["filename"]).read_bytes() == image_bytes
    assert data["ai_assessment"]["review_recommended"] is True
    assert "Adjuster review required" in data["ai_assessment"]["summary"]
    assert data["ai_assessment"]["inference"]["request_id"] == "req-test"

    claims_response = client.get("/api/claims")
    assert claims_response.get_json()["count"] == 1
    claim = claims_response.get_json()["data"][0]
    assert claim["id"] == data["claim_id"]

    detail_response = client.get(f"/api/claims/{data['claim_number']}")
    assert detail_response.status_code == 200
    assert detail_response.get_json()["data"]["assessment"]["damage_type"] == "DENT"

    export_response = client.post("/api/export-zip", json={
        "images": [data["original_image"], *data["augmented_images"]],
        "ai_assessment": data["ai_assessment"],
    })
    with zipfile.ZipFile(io.BytesIO(export_response.data)) as archive:
        assert "claim_report.json" in archive.namelist()
        assert f"dataset/{data['original_image']['filename']}" in archive.namelist()
        report = json.loads(archive.read("claim_report.json"))
        assert report["ai_assessment"]["damage_type"] == "DENT"

    with app.app_context():
        assert db.session.query(Claim).count() == 1


def test_vision_provider_failure_is_reported_without_creating_a_claim(tmp_path, monkeypatch):
    import services.claim_service as claim_service
    from modules.classifier import DamageClassificationError

    def fail_classification(notes, image_path, selected_preset):
        raise DamageClassificationError("Vision service is busy; please retry shortly.")

    monkeypatch.setattr(claim_service, "classify_damage_description", fail_classification)
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite://",
        "UPLOAD_FOLDER": str(tmp_path),
    })
    _, encoded = cv2.imencode(".jpg", np.full((16, 16, 3), 128, dtype=np.uint8))

    response = app.test_client().post(
        "/api/process-claim",
        data={"photo": (io.BytesIO(encoded.tobytes()), "fixture.jpg"), "preset": "door_scratch"},
        content_type="multipart/form-data",
    )

    assert response.status_code == 503
    assert response.get_json()["message"] == "Vision service is busy; please retry shortly."
    assert not list(tmp_path.glob("*_rain.jpg"))
    with app.app_context():
        assert db.session.query(Claim).count() == 0
