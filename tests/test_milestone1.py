"""Milestone 1 checks that do not spend Groq tokens."""

import unittest

from app.ai.classifier import build_request_body
from app.ai.json_parse import ModelOutputError, parse_model_json
from app.ai.prompts import build_messages
from app.config import DEMO_MODEL, DEV_MODEL, load_settings


class PromptTests(unittest.TestCase):
    def test_system_rules_come_before_the_question(self):
        messages = build_messages("scratched bumper")
        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[1]["role"], "user")
        self.assertIn("JSON", messages[0]["content"])
        self.assertIn("scratched bumper", messages[1]["content"])

    def test_empty_description_is_rejected(self):
        with self.assertRaises(ValueError):
            build_messages("   ")


class JsonParseTests(unittest.TestCase):
    def test_plain_json(self):
        raw = (
            '{"damage_type": "scratch", "severity": "minor", '
            '"part": "front bumper", "summary": "Paint is scraped."}'
        )
        parsed = parse_model_json(raw)
        self.assertEqual(parsed["damage_type"], "SCRATCH")
        self.assertEqual(parsed["severity"], "MINOR")

    def test_markdown_fence_is_stripped(self):
        raw = """Sure, here you go:
```json
{"damage_type": "DENT", "severity": "MODERATE", "part": "door", "summary": "Panel is pushed in."}
```
Hope that helps!"""
        parsed = parse_model_json(raw)
        self.assertEqual(parsed["damage_type"], "DENT")
        self.assertEqual(parsed["part"], "door")

    def test_unknown_label_is_rejected(self):
        raw = (
            '{"damage_type": "FIRE", "severity": "SEVERE", '
            '"part": "hood", "summary": "Burned."}'
        )
        with self.assertRaises(ModelOutputError):
            parse_model_json(raw)


class SettingsTests(unittest.TestCase):
    def test_development_uses_the_smaller_model(self):
        settings = load_settings()
        self.assertEqual(settings.stage, "development")
        self.assertEqual(settings.model, DEV_MODEL)
        self.assertEqual(settings.temperature, 0.3)
        self.assertEqual(settings.max_tokens, 512)
        self.assertNotEqual(DEV_MODEL, DEMO_MODEL)

    def test_request_body_matches_the_milestone_decisions(self):
        settings = load_settings()
        body = build_request_body("scratched bumper", settings)
        self.assertEqual(body["model"], DEV_MODEL)
        self.assertEqual(body["temperature"], 0.3)
        self.assertEqual(body["max_tokens"], 512)
        self.assertEqual(body["response_format"], {"type": "json_object"})
        self.assertEqual(body["messages"][1]["role"], "user")


if __name__ == "__main__":
    unittest.main()
