import os
import sys
from dotenv import load_dotenv
from modules.classifier import classify_damage_description

# Step 0: Ensure our environment is healthy before running tests
load_dotenv()

def verify_schema(result: dict, case_name: str):
    """
    Helper function to enforce our strict REST/JSON schema contract.
    If the LLM omits even one key, the test suite catches it immediately.
    """
    required_keys = ["damage_type", "severity", "estimated_action", "confidence_score", "summary"]
    for key in required_keys:
        assert key in result, f"[{case_name}] CONTRACT VIOLATION: Missing key '{key}' in response!"
    
    # Assert data types
    assert isinstance(result["damage_type"], str), f"[{case_name}] damage_type must be a string"
    assert isinstance(result["severity"], str), f"[{case_name}] severity must be a string"
    assert isinstance(result["estimated_action"], str), f"[{case_name}] estimated_action must be a string"
    assert isinstance(result["confidence_score"], (int, float)), f"[{case_name}] confidence_score must be numeric"
    assert 0.0 <= float(result["confidence_score"]) <= 1.0, f"[{case_name}] confidence_score must be between 0.0 and 1.0"
    assert isinstance(result["summary"], str), f"[{case_name}] summary must be a string"

def test_classifier_suite():
    print("=" * 60)
    print("🤖 CLAIM-AUGMENT AI: PRODUCTION LLM CLASSIFIER TEST SUITE")
    print("=" * 60)

    # Pre-flight check: Verify API key exists
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or api_key == "your_groq_api_key_here":
        print("❌ CRITICAL ERROR: GROQ_API_KEY is missing or unconfigured in .env!")
        print("   Please open .env and paste your real key from https://console.groq.com")
        sys.exit(1)

    # -------------------------------------------------------------
    # CASE 1: Severe Crash Analysis
    # -------------------------------------------------------------
    print("\n[Case 1/3] Testing Severe Impact Case...")
    severe_notes = "Front bumper completely crumpled, radiator pierced and leaking, frame rails bent."
    res_severe = classify_damage_description(severe_notes)
    
    print(f"   -> Damage Type: {res_severe.get('damage_type')}")
    print(f"   -> Severity:    {res_severe.get('severity')}")
    print(f"   -> Action:      {res_severe.get('estimated_action')}")
    print(f"   -> Confidence:  {res_severe.get('confidence_score')}")
    print(f"   -> Summary:     {res_severe.get('summary')}")
    
    verify_schema(res_severe, "Case 1: Severe")
    assert res_severe["severity"] in ["SEVERE", "MODERATE"], f"Expected SEVERE/MODERATE but got {res_severe['severity']}"

    # -------------------------------------------------------------
    # CASE 2: Minor Cosmetic Damage Analysis
    # -------------------------------------------------------------
    print("\n[Case 2/3] Testing Minor Cosmetic Case...")
    minor_notes = "Superficial 3-inch hairline paint scratch on passenger door, clear coat only."
    res_minor = classify_damage_description(minor_notes)
    
    print(f"   -> Damage Type: {res_minor.get('damage_type')}")
    print(f"   -> Severity:    {res_minor.get('severity')}")
    print(f"   -> Action:      {res_minor.get('estimated_action')}")
    print(f"   -> Summary:     {res_minor.get('summary')}")
    
    verify_schema(res_minor, "Case 2: Minor")
    assert res_minor["damage_type"] in ["SCRATCH", "OTHER"], f"Expected SCRATCH but got {res_minor['damage_type']}"

    # -------------------------------------------------------------
    # CASE 3: Defensive Edge Case (Empty Input / Zero Token Waste)
    # -------------------------------------------------------------
    print("\n[Case 3/3] Testing Defensive Handling (Empty Input)...")
    res_empty = classify_damage_description("   ")
    
    print(f"   -> Handled safely without API crash:")
    print(f"   -> Result: {res_empty}")
    
    verify_schema(res_empty, "Case 3: Empty Input")
    assert res_empty["confidence_score"] == 0.0, "Empty input should yield 0.0 confidence"

    print("\n" + "=" * 60)
    print("✨ ALL 3 PRODUCTION TEST CASES PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    test_classifier_suite()