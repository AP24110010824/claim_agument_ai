import base64
import io
import json
import logging
import mimetypes
import os

from dotenv import load_dotenv
from groq import APIConnectionError, APIStatusError, Groq, RateLimitError
from PIL import Image, ImageOps

load_dotenv()

logger = logging.getLogger(__name__)
MODEL_NAME = os.getenv("GROQ_VISION_MODEL", "qwen/qwen3.8-27b")

CERTIFIED_LABOR_RATE_PER_HOUR = 95.00
PAINT_FINISH_RATE_PER_HOUR = 65.00
OEM_PARTS_CATALOG = {
    "radiator": {"part_cost": 485.00, "labor_hours": 3.5, "paint_hours": 0.0},
    "bumper": {"part_cost": 650.00, "labor_hours": 2.5, "paint_hours": 3.0},
    "hood": {"part_cost": 820.00, "labor_hours": 2.0, "paint_hours": 3.5},
    "headlight": {"part_cost": 420.00, "labor_hours": 1.2, "paint_hours": 0.0},
    "fender": {"part_cost": 380.00, "labor_hours": 2.2, "paint_hours": 2.8},
    "door": {"part_cost": 950.00, "labor_hours": 3.5, "paint_hours": 4.0},
    "frame": {"part_cost": 2800.00, "labor_hours": 14.0, "paint_hours": 2.0},
    "windshield": {"part_cost": 550.00, "labor_hours": 2.5, "paint_hours": 0.0},
}

DAMAGE_TYPES = {"SCRATCH", "DENT", "CRACK", "SHATTER", "STRUCTURAL", "OTHER"}
SEVERITIES = {"MINOR", "MODERATE", "SEVERE"}
ESTIMATED_ACTIONS = {"REPAIR", "REPLACE", "FURTHER_INSPECTION"}
PRESETS = {
    "frontal_collision": "Frontal Collision",
    "door_scratch": "Door Scratch",
    "hail_glass": "Hail & Glass",
}
MAX_ENCODED_IMAGE_BYTES = 14_000_000

SYSTEM_INSTRUCTION = """You are an assistant that triages visible vehicle damage from a photo.
The photo is the primary evidence. Adjuster notes and the selected preset are context only;
never let them override visible contradictory evidence. Explicitly flag a conflict when the
photo does not match the selected preset or notes. Assess only visible damage: do not claim
hidden frame, radiator, or other internal damage from an exterior photo. Use FURTHER_INSPECTION
when the image cannot support a reliable assessment. Confidence is an estimate, not a calibrated
insurance decision. Return only a JSON object with exactly these fields:
{
  "damage_type": "SCRATCH|DENT|CRACK|SHATTER|STRUCTURAL|OTHER",
  "severity": "MINOR|MODERATE|SEVERE",
  "estimated_action": "REPAIR|REPLACE|FURTHER_INSPECTION",
  "confidence_score": 0.0,
  "components": ["bumper|hood|radiator|headlight|fender|door|frame|windshield"],
  "visual_findings": ["short observation grounded in the photo"],
  "preset_conflict": false,
  "notes_conflict": false,
  "review_recommended": false,
  "review_reasons": ["reason, if needed"],
  "summary": "Brief summary of visible evidence"
}
"""


class DamageClassificationError(RuntimeError):
    status_code = 503


def _get_client():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or api_key == "your_groq_api_key_here":
        raise DamageClassificationError("Groq API is not configured.")
    return Groq(api_key=api_key)


def _encode_image(image_path):
    mime_type, _ = mimetypes.guess_type(image_path)
    if mime_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise ValueError("Unsupported image type for damage classification.")

    with open(image_path, "rb") as image_file:
        image_bytes = image_file.read()

    if len(image_bytes) > MAX_ENCODED_IMAGE_BYTES:
        with Image.open(io.BytesIO(image_bytes)) as source_image:
            image = ImageOps.exif_transpose(source_image).convert("RGB")
            image.thumbnail((3072, 3072))
            for quality in (90, 82, 74, 66):
                compressed = io.BytesIO()
                image.save(compressed, format="JPEG", quality=quality, optimize=True)
                image_bytes = compressed.getvalue()
                if len(image_bytes) <= MAX_ENCODED_IMAGE_BYTES:
                    mime_type = "image/jpeg"
                    break
            else:
                raise ValueError("Image is too large to send for classification.")

    encoded = base64.b64encode(image_bytes).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def calculate_actuarial_financials(severity: str, components: list) -> dict:
    detected_parts = set()

    for part in OEM_PARTS_CATALOG:
        if part in components:
            detected_parts.add(part)

    if not detected_parts:
        if severity == "SEVERE":
            detected_parts.update(["bumper", "hood", "radiator"])
        elif severity == "MODERATE":
            detected_parts.update(["bumper", "headlight"])
        else:
            detected_parts.add("fender")

    total_parts_cost = sum(OEM_PARTS_CATALOG[part]["part_cost"] for part in detected_parts)
    total_labor_hours = sum(OEM_PARTS_CATALOG[part]["labor_hours"] for part in detected_parts)
    total_paint_hours = sum(OEM_PARTS_CATALOG[part]["paint_hours"] for part in detected_parts)
    labor_cost = (
        total_labor_hours * CERTIFIED_LABOR_RATE_PER_HOUR
        + total_paint_hours * PAINT_FINISH_RATE_PER_HOUR
    )
    total_cost = total_parts_cost + labor_cost
    total_loss_pct = min(98, max(5, int((total_cost / 14000.0) * 100)))

    return {
        "total_cost": f"${total_cost:,.2f}",
        "labor_hours": f"{(total_labor_hours + total_paint_hours):.1f} hrs",
        "parts_cost": f"${total_parts_cost:,.2f}",
        "total_loss_probability": f"{total_loss_pct}%",
        "identified_components": sorted(detected_parts),
    }


def _validate_assessment(parsed_data, selected_preset):
    damage_type = parsed_data.get("damage_type")
    severity = parsed_data.get("severity")
    estimated_action = parsed_data.get("estimated_action")
    confidence = parsed_data.get("confidence_score")

    if damage_type not in DAMAGE_TYPES:
        raise ValueError("Invalid damage_type returned by model.")
    if severity not in SEVERITIES:
        raise ValueError("Invalid severity returned by model.")
    if estimated_action not in ESTIMATED_ACTIONS:
        raise ValueError("Invalid estimated_action returned by model.")
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        raise ValueError("Invalid confidence_score returned by model.")
    if not 0.0 <= float(confidence) <= 1.0:
        raise ValueError("Invalid confidence_score returned by model.")

    components = parsed_data.get("components")
    visual_findings = parsed_data.get("visual_findings")
    review_reasons = parsed_data.get("review_reasons")
    for field_name, values in (
        ("components", components),
        ("visual_findings", visual_findings),
        ("review_reasons", review_reasons),
    ):
        if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
            raise ValueError(f"Invalid {field_name} returned by model.")
    if any(component not in OEM_PARTS_CATALOG for component in components):
        raise ValueError("Unsupported component returned by model.")
    for field_name in ("preset_conflict", "notes_conflict", "review_recommended"):
        if not isinstance(parsed_data.get(field_name), bool):
            raise ValueError(f"Invalid {field_name} returned by model.")
    if not isinstance(parsed_data.get("summary"), str) or not parsed_data["summary"].strip():
        raise ValueError("Invalid summary returned by model.")

    preset_conflict = parsed_data["preset_conflict"]
    if selected_preset == "door_scratch":
        preset_conflict = preset_conflict or damage_type != "SCRATCH" or severity != "MINOR"

    review_recommended = (
        parsed_data["review_recommended"]
        or preset_conflict
        or parsed_data["notes_conflict"]
        or float(confidence) < 0.65
    )
    review_reasons = [reason.strip() for reason in review_reasons if reason.strip()]
    if (
        preset_conflict
        and selected_preset
        and not any("preset" in reason.lower() for reason in review_reasons)
    ):
        review_reasons.append(
            f"Visible damage conflicts with the {PRESETS[selected_preset]} preset."
        )
    if parsed_data["notes_conflict"] and not any("notes" in reason.lower() for reason in review_reasons):
        review_reasons.append("Visible damage conflicts with the adjuster notes.")
    if float(confidence) < 0.65 and not any("confidence" in reason.lower() for reason in review_reasons):
        review_reasons.append("Low model confidence; adjuster review is recommended.")

    return {
        "damage_type": damage_type,
        "severity": severity,
        "estimated_action": estimated_action,
        "confidence_score": float(confidence),
        "components": sorted(set(components)),
        "visual_findings": [finding.strip() for finding in visual_findings if finding.strip()],
        "preset_conflict": preset_conflict,
        "notes_conflict": parsed_data["notes_conflict"],
        "review_recommended": review_recommended,
        "review_reasons": review_reasons,
        "selected_preset": selected_preset or None,
        "summary": parsed_data["summary"].strip(),
    }


def classify_damage_description(description_text: str, image_path: str, selected_preset: str = "") -> dict:
    if not os.path.isfile(image_path):
        raise ValueError("A valid damage photo is required for classification.")
    if selected_preset and selected_preset not in PRESETS:
        raise ValueError("Unknown damage preset.")

    preset_label = PRESETS.get(selected_preset, "None")
    notes = description_text.strip() or "No adjuster notes provided."
    image_data_url = _encode_image(image_path)
    user_prompt = (
        f"Selected preset (context only): {preset_label}.\n"
        f"Adjuster notes (context only): {notes}\n"
        "Inspect the attached photo independently. Compare what is visibly present with the "
        "preset and notes. Return the required JSON assessment."
    )

    try:
        completion = _get_client().chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_INSTRUCTION},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt},
                        {"type": "image_url", "image_url": {"url": image_data_url}},
                    ],
                },
            ],
            temperature=0.1,
            max_completion_tokens=1024,
            response_format={"type": "json_object"},
        )
    except RateLimitError as error:
        logger.warning("Groq vision request rate limited.")
        raise DamageClassificationError("Vision service is busy; please retry shortly.") from error
    except APIConnectionError as error:
        logger.error("Groq vision service could not be reached.")
        raise DamageClassificationError("Vision service is temporarily unreachable.") from error
    except APIStatusError as error:
        logger.error("Groq vision request failed with status %s.", error.status_code)
        raise DamageClassificationError("Vision service could not complete the assessment.") from error

    try:
        raw_response = completion.choices[0].message.content
        if not raw_response:
            raise ValueError("Model returned an empty assessment.")
        parsed_data = json.loads(raw_response)
        assessment = _validate_assessment(parsed_data, selected_preset)
    except (AttributeError, IndexError, TypeError, ValueError, json.JSONDecodeError) as error:
        logger.error("Groq vision response failed schema validation: %s", error)
        raise DamageClassificationError("Vision service returned an invalid assessment.") from error

    usage = completion.usage
    request_id = getattr(completion, "_request_id", None) or completion.id
    assessment["financial_breakdown"] = calculate_actuarial_financials(
        assessment["severity"], assessment["components"]
    )
    assessment["inference"] = {
        "provider": "groq",
        "model": completion.model or MODEL_NAME,
        "request_id": request_id,
        "prompt_tokens": usage.prompt_tokens if usage else None,
        "completion_tokens": usage.completion_tokens if usage else None,
    }
    logger.info(
        "Groq vision inference succeeded model=%s request_id=%s prompt_tokens=%s completion_tokens=%s",
        assessment["inference"]["model"],
        request_id,
        assessment["inference"]["prompt_tokens"],
        assessment["inference"]["completion_tokens"],
    )
    return assessment
