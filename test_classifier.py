import os
import sys

from dotenv import load_dotenv

from modules.classifier import classify_damage_description


def run_classifier_smoke_test(image_path):
    load_dotenv()
    notes = "Reported as a superficial door scratch; verify the uploaded photo independently."
    result = classify_damage_description(notes, image_path, "door_scratch")

    print("Groq vision inference succeeded.")
    print(f"Damage type: {result['damage_type']}")
    print(f"Severity: {result['severity']}")
    print(f"Action: {result['estimated_action']}")
    print(f"Estimated confidence: {result['confidence_score']:.2f}")
    print(f"Preset conflict: {result['preset_conflict']}")
    print(f"Review recommended: {result['review_recommended']}")
    print(f"Review reasons: {', '.join(result['review_reasons']) or 'none'}")
    print(f"Visual findings: {'; '.join(result['visual_findings'])}")
    print(f"Summary: {result['summary']}")
    print(f"Groq request ID: {result['inference']['request_id']}")
    print(
        "Token usage: "
        f"{result['inference']['prompt_tokens']} input / "
        f"{result['inference']['completion_tokens']} output"
    )
    print("This smoke test sends one Groq inference request.")


if __name__ == "__main__":
    if len(sys.argv) != 2 or not os.path.isfile(sys.argv[1]):
        print("Usage: python test_classifier.py <path-to-damage-photo>")
        sys.exit(2)
    run_classifier_smoke_test(sys.argv[1])
