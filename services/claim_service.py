import hashlib
import os
import uuid

import cv2
import numpy as np
from werkzeug.utils import secure_filename

from database import db
from models import AugmentedPhoto, Claim, DamageAssessment
from modules.augmenter import augment_claim_image
from modules.classifier import classify_damage_description


class ClaimService:
    @staticmethod
    def process_claim(file_storage, notes, vehicle_type, upload_folder, selected_preset=""):
        image_bytes = file_storage.read()
        if not image_bytes:
            raise ValueError("Uploaded image is empty.")

        image_buffer = np.frombuffer(image_bytes, dtype=np.uint8)
        decoded_image = cv2.imdecode(image_buffer, cv2.IMREAD_COLOR)
        if decoded_image is None:
            raise ValueError("Could not read uploaded image.")

        source_hash = hashlib.sha256(image_bytes).hexdigest()
        claim_uuid = str(uuid.uuid4())
        unique_prefix = claim_uuid[:8]
        clean_name = secure_filename(file_storage.filename or "")
        unique_filename = f"{unique_prefix}_{clean_name}"
        saved_path = os.path.join(upload_folder, unique_filename)

        file_storage.stream.seek(0)
        file_storage.save(saved_path)
        claim_serial = f"CLM-2026-{unique_prefix.upper()}"

        try:
            ai_assessment = classify_damage_description(notes, saved_path, selected_preset)
            if ai_assessment["review_recommended"]:
                review_details = "; ".join(ai_assessment["review_reasons"]) or (
                    "Please verify the visual assessment."
                )
                ai_assessment["summary"] = (
                    f"{ai_assessment['summary']} Adjuster review required: {review_details}"
                )

            augmented_results = augment_claim_image(saved_path, upload_folder)
            augmented_files = [
                {
                    "effect": item["effect"],
                    "filename": item["filename"],
                    "url": f"/uploads/{item['filename']}",
                }
                for item in augmented_results
            ]
            financials = ai_assessment.get("financial_breakdown", {})

            claim = Claim(
                id=claim_uuid,
                claim_number=claim_serial,
                status="COMPLETED",
                adjuster_notes=notes,
                source_image_hash=source_hash,
                source_image_path=unique_filename,
            )
            db.session.add(claim)
            db.session.flush()

            db.session.add(DamageAssessment(
                claim_id=claim.id,
                damage_type=ai_assessment.get("damage_type", "OTHER"),
                severity=ai_assessment.get("severity", "MODERATE"),
                estimated_action=ai_assessment.get("estimated_action", "REPAIR"),
                confidence_score=float(ai_assessment.get("confidence_score", 0.9)),
                total_cost=financials.get("total_cost", "$0.00"),
                labor_hours=financials.get("labor_hours", "0.0 hrs"),
                parts_cost=financials.get("parts_cost", "$0.00"),
                total_loss_probability=financials.get("total_loss_probability", "0%"),
                summary=ai_assessment.get("summary", ""),
            ))

            for item in augmented_results:
                db.session.add(AugmentedPhoto(
                    claim_id=claim.id,
                    effect_type=item["effect"],
                    filename=item["filename"],
                ))

            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        return {
            "status": "success",
            "data": {
                "claim_id": claim.id,
                "claim_number": claim.claim_number,
                "source_image_hash": source_hash,
                "original_image": {
                    "filename": unique_filename,
                    "url": f"/uploads/{unique_filename}",
                },
                "augmented_images": augmented_files,
                "ai_assessment": ai_assessment,
            },
        }

    @staticmethod
    def list_claims():
        claims = Claim.query.order_by(Claim.created_at.desc()).limit(50).all()
        return [claim.to_dict() for claim in claims]

    @staticmethod
    def get_claim_by_id(claim_id):
        claim = Claim.query.filter(
            (Claim.id == claim_id) | (Claim.claim_number == claim_id)
        ).first()
        return claim.to_dict() if claim else None
