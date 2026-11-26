import io
import tempfile
from unittest.mock import patch

import cv2
import numpy as np

from app import create_app


def test_api_endpoints():
    print("=" * 60)
    print("CLAIMAUGMENT AI: HTTP INTEGRATION TEST")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as upload_dir:
        app = create_app({
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite://",
            "UPLOAD_FOLDER": upload_dir,
        })
        client = app.test_client()

        print("\n[Test 1/4] Home route...")
        response = client.get("/")
        assert response.status_code == 200
        print("   -> Status: 200 OK")

        print("\n[Test 2/4] Missing-photo validation...")
        response = client.post("/api/process-claim", data={"notes": "Scratched bumper"})
        assert response.status_code == 400
        assert response.get_json()["status"] == "error"
        print("   -> Missing photo rejected")

        print("\n[Test 3/4] Invalid-file validation...")
        response = client.post(
            "/api/process-claim",
            data={"photo": (io.BytesIO(b"malicious executable content"), "virus.exe")},
            content_type="multipart/form-data",
        )
        assert response.status_code == 400
        print("   -> Invalid file rejected")

        print("\n[Test 4/4] Claim processing with mocked Groq inference...")
        mock_image = np.full((100, 100, 3), 128, dtype=np.uint8)
        _, encoded_image = cv2.imencode(".jpg", mock_image)
        fake_assessment = {
            "damage_type": "DENT",
            "severity": "SEVERE",
            "estimated_action": "REPLACE",
            "confidence_score": 0.9,
            "summary": "Mocked test assessment.",
            "components": ["bumper"],
            "visual_findings": ["The bumper is visibly dented."],
            "preset_conflict": False,
            "notes_conflict": False,
            "review_recommended": False,
            "review_reasons": [],
            "inference": {
                "provider": "groq",
                "model": "qwen/qwen3.8-27b",
                "request_id": "req-test-api",
                "prompt_tokens": 10,
                "completion_tokens": 5,
            },
            "financial_breakdown": {
                "total_cost": "$1,000.00",
                "labor_hours": "2.0 hrs",
                "parts_cost": "$800.00",
                "total_loss_probability": "7%",
            },
        }
        with patch(
            "services.claim_service.classify_damage_description",
            return_value=fake_assessment,
        ):
            response = client.post(
                "/api/process-claim",
                data={
                    "photo": (io.BytesIO(encoded_image.tobytes()), "claim_car.jpg"),
                    "notes": "Front bumper collision.",
                    "preset": "frontal_collision",
                },
                content_type="multipart/form-data",
            )

        assert response.status_code == 200, response.get_data(as_text=True)
        payload = response.get_json()
        assert payload["status"] == "success"
        data = payload["data"]
        assert data["original_image"]["url"].startswith("/uploads/")
        assert len(data["augmented_images"]) == 5
        assert data["ai_assessment"]["inference"]["request_id"] == "req-test-api"
        print("   -> Claim processed with 5 augmentations and inference metadata")

    print("\nHTTP integration tests passed.")


if __name__ == "__main__":
    test_api_endpoints()
