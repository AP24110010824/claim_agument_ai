import os
import cv2
import numpy as np
from modules.augmenter import augment_claim_image

def test_pipeline():
    print("🚗 [1/4] Generating a synthetic test car-panel image...")
    # Create a 400x400 gray vehicle panel
    test_img = np.full((400, 400, 3), 180, dtype=np.uint8)

    # Draw a simulated red/black scratch across the panel
    cv2.line(test_img, (50, 80), (350, 320), (30, 30, 200), 4)

    test_input_path = "uploads/test_scratch.jpg"
    cv2.imwrite(test_input_path, test_img)
    print(f"✅ Saved test input to: {test_input_path}")

    print("⚡ [2/4] Running augmentation pipeline across 5 conditions...")
    results = augment_claim_image(test_input_path, "uploads")

    print(f"🎉 [3/4] Successfully generated {len(results)} augmented photos:")
    for res in results:
        print(f"   - Effect: {res['effect']:<12} -> File: {res['filename']}")

    print("🔍 [4/4] Verifying generated files exist on disk...")
    for res in results:
        assert os.path.exists(res["path"]), f"Missing file: {res['path']}"
    print("✨ ALL TESTS PASSED! Augmentation engine is production ready.")

if __name__ == "__main__":
    test_pipeline()