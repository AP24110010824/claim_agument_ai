"""Milestone 1: one real classification call.

Run from the project root:

    venv/bin/python.exe scripts/first_ai_call.py
    venv/bin/python.exe scripts/first_ai_call.py "Rear door has a deep dent"
"""

import json
import sys
from pathlib import Path

# Running a file puts its own folder on sys.path, not the project root.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.ai.classifier import MissingApiKeyError, classify_damage
from app.config import load_settings

SAMPLE = "Front bumper has a 6-inch scratch with paint transfer."


def main() -> int:
    description = " ".join(sys.argv[1:]).strip() or SAMPLE
    settings = load_settings()

    print("ClaimAugment AI — first classification call")
    print(f"  stage:       {settings.stage}")
    print(f"  model:       {settings.model}")
    print(f"  temperature: {settings.temperature}")
    print(f"  max_tokens:  {settings.max_tokens}")
    print(f"  description: {description}")
    print()

    if not settings.has_api_key:
        print("No Groq API key yet.")
        print("1. Open https://console.groq.com and sign in (no card).")
        print("2. Profile icon -> API Keys -> Create API Key.")
        print("3. Name it claimaugment-key, copy it, paste it into .env as GROQ_API_KEY.")
        print("4. Run this script again.")
        return 2

    try:
        result = classify_damage(description)
    except MissingApiKeyError as exc:
        print(exc)
        return 2

    print("Classification")
    print(json.dumps(result["classification"], indent=2))
    print()
    print(
        "Tokens this call: "
        f"prompt={result['prompt_tokens']}  "
        f"completion={result['completion_tokens']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
