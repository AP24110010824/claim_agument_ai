import os
import json
from dotenv import load_dotenv
from groq import Groq

# Load environment variables from .env file (GROQ_API_KEY)
load_dotenv()

# Initialize the Groq Client
# By default, Groq() automatically looks for os.environ.get("GROQ_API_KEY")
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# The model to use:
# - During development: "llama-3.1-8b-instant" (ultra-fast, saves quota)
# - For production demo: "llama-3.3-70b-versatile"
MODEL_NAME = "openai/gpt-oss-20b"

SYSTEM_INSTRUCTION = """You are an automated automotive insurance damage assessment AI.
Analyze the user's description of vehicular damage.

You MUST respond with ONLY a valid, raw JSON object (no markdown, no ```json ``` fences) with the exact following schema:
{
  "damage_type": "SCRATCH" | "DENT" | "CRACK" | "SHATTER" | "STRUCTURAL" | "OTHER",
  "severity": "MINOR" | "MODERATE" | "SEVERE",
  "estimated_action": "REPAIR" | "REPLACE" | "FURTHER_INSPECTION",
  "confidence_score": 0.0 to 1.0,
  "summary": "Brief 1-sentence assessment summary"
}
"""

def classify_damage_description(description_text: str) -> dict:
    """
    Calls Groq LLM to classify vehicle damage based on claims notes.
    Returns a standardized dictionary.
    """
    # 1. Defensive programming: Validate input
    if not description_text or not description_text.strip():
        return {
            "damage_type": "OTHER",
            "severity": "MINOR",
            "estimated_action": "FURTHER_INSPECTION",
            "confidence_score": 0.0,
            "summary": "No description provided."
        }

    try:
        # 2. Call the Groq Chat Completions API
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": SYSTEM_INSTRUCTION},
                {"role": "user", "content": f"Damage Notes: {description_text.strip()}"}
            ],
            model=MODEL_NAME,
            temperature=0.2,     # Low temperature for deterministic, consistent classification
            max_tokens=300       # Prevent run-away token usage
        )

        # 3. Extract the raw string response from the LLM
        raw_response = chat_completion.choices[0].message.content.strip()

        # 4. Strip any accidental markdown formatting (e.g., ```json ... ```)
        if raw_response.startswith("```"):
            raw_response = raw_response.strip("`")
            if raw_response.startswith("json"):
                raw_response = raw_response[4:].strip()

        # 5. Parse the JSON string into a Python dictionary
        parsed_data = json.loads(raw_response)
        return parsed_data

    except Exception as e:
        # 6. Fallback in case of API timeout, rate-limit, or malformed JSON
        print(f"⚠️ Groq API Error / Fallback triggered: {str(e)}")
        return {
            "damage_type": "OTHER",
            "severity": "MODERATE",
            "estimated_action": "FURTHER_INSPECTION",
            "confidence_score": 0.5,
            "summary": f"Automated classification unavailable: {str(e)}"
        }