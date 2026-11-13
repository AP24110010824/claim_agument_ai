"""System prompt = rules on every call. User prompt = this one claim."""

SYSTEM_PROMPT = """You are an insurance damage-assessment model.
Reply with one JSON object and no other text.
Use exactly these keys:
  damage_type: SCRATCH, DENT, CRACK, PAINT, BROKEN, or OTHER
  severity: MINOR, MODERATE, or SEVERE
  part: the vehicle part named in the description
  summary: one short sentence
Do not invent damage that the description does not mention."""


def build_messages(description: str) -> list[dict[str, str]]:
    text = description.strip()
    if not text:
        raise ValueError("Damage description is empty.")

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"Classify this damage:\n{text}",
        },
    ]
