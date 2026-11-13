"""Turn model text into a dict. Models sometimes wrap JSON in markdown."""

import json
import re

REQUIRED_KEYS = ("damage_type", "severity", "part", "summary")
DAMAGE_TYPES = {"SCRATCH", "DENT", "CRACK", "PAINT", "BROKEN", "OTHER"}
SEVERITIES = {"MINOR", "MODERATE", "SEVERE"}

_FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)
_OBJECT = re.compile(r"\{.*\}", re.DOTALL)


class ModelOutputError(ValueError):
    """The model replied, but the text was not the JSON we asked for."""


def parse_model_json(raw: str) -> dict:
    text = (raw or "").strip()
    if not text:
        raise ModelOutputError("Model returned an empty message.")

    fenced = _FENCE.search(text)
    candidate = fenced.group(1).strip() if fenced else text

    try:
        payload = json.loads(candidate)
    except json.JSONDecodeError:
        match = _OBJECT.search(candidate)
        if match is None:
            raise ModelOutputError(f"No JSON object in model output: {raw!r}")
        try:
            payload = json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            raise ModelOutputError(f"Invalid JSON in model output: {raw!r}") from exc

    if not isinstance(payload, dict):
        raise ModelOutputError("Model JSON was not an object.")

    missing = [key for key in REQUIRED_KEYS if key not in payload]
    if missing:
        raise ModelOutputError(f"Model JSON missing keys: {', '.join(missing)}")

    damage_type = str(payload["damage_type"]).strip().upper()
    severity = str(payload["severity"]).strip().upper()
    part = str(payload["part"]).strip()
    summary = str(payload["summary"]).strip()

    if damage_type not in DAMAGE_TYPES:
        raise ModelOutputError(f"Unknown damage_type: {damage_type!r}")
    if severity not in SEVERITIES:
        raise ModelOutputError(f"Unknown severity: {severity!r}")
    if not part or not summary:
        raise ModelOutputError("part and summary must be non-empty.")

    return {
        "damage_type": damage_type,
        "severity": severity,
        "part": part,
        "summary": summary,
    }
