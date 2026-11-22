import os
import sys
import time
import json
import cv2
import numpy as np

# Add project root to sys.path so we can import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from modules.augmenter import augment_claim_image
from modules.classifier import classify_damage_description

# =====================================================================
# PRODUCTION RATE LIMITER & CACHE CONFIGURATION
# =====================================================================
RATE_LIMIT_DELAY_SECONDS = 2.0  # Guarantees maximum ~30 req/min (Groq Free Tier safe)
AI_CACHE = {}                    # In-memory deduplication cache

def generate_sample_dataset(dataset_dir: str, num_samples: int = 3):
    """Generates a small mock dataset of vehicle damage photos for testing."""
    os.makedirs(dataset_dir, exist_ok=True)
    sample_manifest = []

    samples = [
        {"name": "claim_01_bumper_dent.jpg", "notes": "Rear bumper dented with paint cracking after reversing into pillar.", "color": (120, 120, 120)},
        {"name": "claim_02_door_scratch.jpg", "notes": "Superficial 5-inch key scratch on driver door panel.", "color": (180, 150, 150)},
        {"name": "claim_03_headlight_shatter.jpg", "notes": "Crushed passenger headlight and warped fender from highway debris.", "color": (100, 100, 130)},
    ]

    for item in samples[:num_samples]:
        img_path = os.path.join(dataset_dir, item["name"])
        # Create a synthetic vehicle panel with damage marks
        canvas = np.full((300, 300, 3), item["color"], dtype=np.uint8)
        cv2.line(canvas, (40, 50), (260, 250), (20, 20, 180), 5)
        cv2.imwrite(img_path, canvas)
        sample_manifest.append({"path": img_path, "notes": item["notes"]})

    return sample_manifest

def run_batch_pipeline(input_manifest, output_dir: str):
    """
    Processes a batch of damage photos with:
    1. OpenCV Augmentation (Free, Local)
    2. Rate-limited & Cached Groq Classification (Safe, Low-Token)
    3. JSON Manifest Generation
    """
    os.makedirs(output_dir, exist_ok=True)
    print("=" * 65)
    print("🚀 STARTING TOP 1% BATCH DATASET PROCESSING PIPELINE")
    print(f"   Rate Limit Buffer: {RATE_LIMIT_DELAY_SECONDS}s between AI calls")
    print("=" * 65)

    final_dataset = []
    total_images = len(input_manifest)

    for idx, claim in enumerate(input_manifest, start=1):
        print(f"\n[{idx}/{total_images}] Processing: {os.path.basename(claim['path'])}")
        
        # 1. Image Augmentation (100% Local - 0 API cost)
        print("   -> Running 5-point Computer Vision augmentation...")
        augmented = augment_claim_image(claim["path"], output_dir)
        print(f"   -> Created {len(augmented)} transformed variations on disk.")

        # 2. AI Classification with Caching & Rate Limiting
        notes = claim["notes"]
        if notes in AI_CACHE:
            print("   -> ⚡ CACHE HIT! Using cached AI assessment (Saved 1 Groq API Call, 0 tokens).")
            ai_result = AI_CACHE[notes]
        else:
            print("   -> 🌐 Calling Groq LPU (openai/gpt-oss-20b)...")
            ai_result = classify_damage_description(notes)
            AI_CACHE[notes] = ai_result  # Save to cache
            
            # Paced Worker Sleep (Rate Limiter)
            if idx < total_images:
                print(f"   -> ⏱️ Sleeping {RATE_LIMIT_DELAY_SECONDS}s to respect Groq free tier limit...")
                time.sleep(RATE_LIMIT_DELAY_SECONDS)

        # 3. Compile Record
        record = {
            "source_image": claim["path"],
            "claims_notes": notes,
            "ai_damage_assessment": ai_result,
            "augmented_variations": augmented
        }
        final_dataset.append(record)

    # 4. Save Final Manifest
    manifest_path = os.path.join(output_dir, "dataset_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(final_dataset, f, indent=2)

    print("\n" + "=" * 65)
    print(f"✨ BATCH PROCESSING COMPLETE!")
    print(f"   Total Source Images:      {total_images}")
    print(f"   Total Augmented Images:   {total_images * 5}")
    print(f"   Combined Dataset Size:    {total_images * 6} photos")
    print(f"   ML Manifest Written To:   {manifest_path}")
    print("=" * 65)

if __name__ == "__main__":
    test_batch_folder = "uploads/batch_input"
    test_output_folder = "uploads/batch_output"
    
    print("📦 Generating 3 sample damage photos for batch test...")
    manifest = generate_sample_dataset(test_batch_folder, num_samples=3)
    
    run_batch_pipeline(manifest, test_output_folder)