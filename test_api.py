import os
import io
import json
from app import app

def test_api_endpoints():
    print("=" * 60)
    print("🌐 CLAIM-AUGMENT AI: PRODUCTION HTTP INTEGRATION TEST")
    print("=" * 60)

    # 1. Initialize Flask's in-memory test client
    client = app.test_client()

    # -------------------------------------------------------------
    # TEST 1: Health Check / Home Route (GET /)
    # -------------------------------------------------------------
    print("\n[Test 1/4] Verifying Home / Health Endpoint (GET /)...")
    res = client.get("/")
    assert res.status_code == 200, f"Expected 200 OK, got {res.status_code}"
    print("   -> Status: 200 OK ✅")

    # -------------------------------------------------------------
    # TEST 2: Defensive Validation - Missing Photo (POST /api/process-claim)
    # -------------------------------------------------------------
    print("\n[Test 2/4] Testing Missing File Rejection (400 Bad Request)...")
    res_no_photo = client.post("/api/process-claim", data={"notes": "Scratched bumper"})
    assert res_no_photo.status_code == 400, f"Expected 400, got {res_no_photo.status_code}"
    json_data = res_no_photo.get_json()
    assert json_data["status"] == "error"
    print(f"   -> Successfully rejected: {json_data['message']} ✅")

    # -------------------------------------------------------------
    # TEST 3: Security Validation - Invalid File Extension (POST /api/process-claim)
    # -------------------------------------------------------------
    print("\n[Test 3/4] Testing Invalid File Extension Rejection (Security)...")
    fake_exe = (io.BytesIO(b"malicious executable content"), "virus.exe")
    res_bad_ext = client.post(
        "/api/process-claim",
        data={"photo": fake_exe, "notes": "Checking security"},
        content_type="multipart/form-data"
    )
    assert res_bad_ext.status_code == 400
    print(f"   -> Malicious file rejected: {res_bad_ext.get_json()['message']} ✅")

    # -------------------------------------------------------------
    # TEST 4: Happy Path - Real Image Upload & Processing (POST /api/process-claim)
    # -------------------------------------------------------------
    print("\n[Test 4/4] Testing End-to-End Claim Processing Pipeline...")
    
    # Create a small valid mock JPEG image in memory (BytesIO)
    import cv2
    import numpy as np
    mock_img = np.full((100, 100, 3), 128, dtype=np.uint8)
    _, img_encoded = cv2.imencode(".jpg", mock_img)
    image_bytes = io.BytesIO(img_encoded.tobytes())

    res_success = client.post(
        "/api/process-claim",
        data={
            "photo": (image_bytes, "claim_car.jpg"),
            "notes": "Severe front bumper collision with bent frame and shattered headlight."
        },
        content_type="multipart/form-data"
    )

    assert res_success.status_code == 200, f"Processing failed: {res_success.get_data(as_text=True)}"
    payload = res_success.get_json()
    
    assert payload["status"] == "success"
    data = payload["data"]
    
    # Assert original image URL was returned
    assert "original_image" in data
    assert data["original_image"]["url"].startswith("/uploads/")
    
    # Assert all 5 augmented images were generated and returned
    assert len(data["augmented_images"]) == 5
    print(f"   -> Generated {len(data['augmented_images'])} augmented URLs ✅")
    
    # Assert AI assessment contract
    ai = data["ai_assessment"]
    print(f"   -> AI Detected: {ai.get('damage_type')} | Severity: {ai.get('severity')} | Action: {ai.get('estimated_action')}")
    assert "damage_type" in ai
    assert "severity" in ai
    assert "estimated_action" in ai

    print("\n" + "=" * 60)
    print("✨ ALL 4 PRODUCTION HTTP INTEGRATION TESTS PASSED!")
    print("=" * 60)

if __name__ == "__main__":
    test_api_endpoints()