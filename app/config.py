"""Runtime settings. One place decides model, temperature, and token budget.

The course named llama-3.1-8b-instant (development) and
llama-3.3-70b-versatile (demo). Groq shut those IDs down for the free
tier on 16 August 2026. The replacements below are the ones Groq lists
on its deprecations page, and they keep the same split:

  development -> smaller, faster, more daily tokens
  demo        -> larger, higher quality, used for the final run
"""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

# Official Groq replacements (deprecations page, shutdown 2026-08-16).
DEV_MODEL = "openai/gpt-oss-20b"
DEMO_MODEL = "openai/gpt-oss-120b"

# Factual labels must stay stable. 0.0 is robotic; 0.3 allows tiny wording
# changes without flipping the class. Creative work (captions) would use ~0.8.
CLASSIFICATION_TEMPERATURE = 0.3

# A classification is a short JSON object. 512 tokens is enough and stops
# a runaway reply from burning the free-tier daily budget.
CLASSIFICATION_MAX_TOKENS = 512

PLACEHOLDER_KEY = "your_groq_api_key_here"


@dataclass(frozen=True)
class Settings:
    groq_api_key: str
    stage: str
    model: str
    temperature: float
    max_tokens: int

    @property
    def has_api_key(self) -> bool:
        key = self.groq_api_key.strip()
        return bool(key) and key != PLACEHOLDER_KEY


def load_settings() -> Settings:
    """Read .env from the project root. Safe to call more than once."""
    load_dotenv()

    stage = os.getenv("APP_STAGE", "development").strip().lower()
    if stage not in {"development", "demo"}:
        raise ValueError(
            "APP_STAGE must be 'development' or 'demo', "
            f"got {stage!r}."
        )

    override = os.getenv("GROQ_MODEL", "").strip()
    if override:
        model = override
    elif stage == "demo":
        model = DEMO_MODEL
    else:
        model = DEV_MODEL

    return Settings(
        groq_api_key=os.getenv("GROQ_API_KEY", "").strip(),
        stage=stage,
        model=model,
        temperature=CLASSIFICATION_TEMPERATURE,
        max_tokens=CLASSIFICATION_MAX_TOKENS,
    )
