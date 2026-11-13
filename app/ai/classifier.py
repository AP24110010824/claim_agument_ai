"""Inference: POST a prompt to Groq, parse the JSON it returns.

Training already happened at the lab that built the model. This file only
runs inference. The Groq SDK is not imported here: it depends on
pydantic-core, and the MSYS2 Python in this project cannot install that
wheel. urllib is the Python standard library, so the HTTP call is visible
in the same shape as the Stripe request from the e-commerce project.
"""

import json
import urllib.error
import urllib.request

from app.ai.json_parse import parse_model_json
from app.ai.prompts import build_messages
from app.config import Settings, load_settings

API_URL = "https://api.groq.com/openai/v1/chat/completions"


class MissingApiKeyError(RuntimeError):
    """GROQ_API_KEY is still the placeholder from .env."""


class GroqAPIError(RuntimeError):
    """Groq answered with an HTTP error. The body is included."""


def build_request_body(description: str, settings: Settings) -> dict:
    return {
        "model": settings.model,
        "messages": build_messages(description),
        "temperature": settings.temperature,
        "max_tokens": settings.max_tokens,
        "response_format": {"type": "json_object"},
    }


def classify_damage(description: str) -> dict:
    settings = load_settings()
    if not settings.has_api_key:
        raise MissingApiKeyError(
            "Set GROQ_API_KEY in .env. Create it at https://console.groq.com "
            "(profile icon -> API Keys -> Create API Key). "
            "Name it claimaugment-key and paste it once; Groq will not show it again."
        )

    body = build_request_body(description, settings)
    request = urllib.request.Request(
        API_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {settings.groq_api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise GroqAPIError(f"Groq API HTTP {exc.code}: {detail}") from exc

    message = payload["choices"][0]["message"].get("content") or ""
    usage = payload.get("usage") or {}
    return {
        "classification": parse_model_json(message),
        "model": settings.model,
        "stage": settings.stage,
        "temperature": settings.temperature,
        "raw": message,
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
    }
