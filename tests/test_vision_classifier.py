import json
from types import SimpleNamespace

import pytest

import modules.classifier as classifier


def _valid_assessment(**overrides):
    assessment = {
        "damage_type": "DENT",
        "severity": "SEVERE",
        "estimated_action": "REPLACE",
        "confidence_score": 0.94,
        "components": ["door"],
        "visual_findings": ["Deep creases deform both visible door panels."],
        "preset_conflict": False,
        "notes_conflict": False,
        "review_recommended": False,
        "review_reasons": [],
        "summary": "Severe visible door deformation.",
    }
    assessment.update(overrides)
    return assessment


def _fake_client(assessment, captured_request):
    completion = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=json.dumps(assessment))
            )
        ],
        usage=SimpleNamespace(prompt_tokens=1200, completion_tokens=120),
        model="qwen/qwen3.8-27b",
        id="chatcmpl-test-123",
        _request_id="req-test-123",
    )

    def create(**kwargs):
        captured_request.update(kwargs)
        return completion

    return SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(create=create)
        )
    )


def test_vision_classification_flags_severe_damage_against_door_scratch(tmp_path, monkeypatch):
    image_path = tmp_path / "damage.jpg"
    image_path.write_bytes(b"mock-jpeg")
    captured_request = {}
    monkeypatch.setattr(
        classifier,
        "_get_client",
        lambda: _fake_client(_valid_assessment(), captured_request),
    )

    result = classifier.classify_damage_description(
        "Heavy impact on the passenger side.",
        str(image_path),
        "door_scratch",
    )

    assert result["damage_type"] == "DENT"
    assert result["severity"] == "SEVERE"
    assert result["preset_conflict"] is True
    assert result["review_recommended"] is True
    assert any("Door Scratch" in reason for reason in result["review_reasons"])
    assert result["inference"]["request_id"] == "req-test-123"
    assert result["inference"]["prompt_tokens"] == 1200

    user_content = captured_request["messages"][1]["content"]
    assert "Door Scratch" in user_content[0]["text"]
    assert "Heavy impact" in user_content[0]["text"]
    assert user_content[1]["image_url"]["url"].startswith("data:image/jpeg;base64,")


def test_vision_classification_does_not_invent_door_scratch_conflict_for_minor_scratch(
    tmp_path, monkeypatch
):
    image_path = tmp_path / "scratch.jpg"
    image_path.write_bytes(b"mock-jpeg")
    monkeypatch.setattr(
        classifier,
        "_get_client",
        lambda: _fake_client(
            _valid_assessment(
                damage_type="SCRATCH",
                severity="MINOR",
                estimated_action="REPAIR",
                confidence_score=0.9,
            ),
            {},
        ),
    )

    result = classifier.classify_damage_description("", str(image_path), "door_scratch")

    assert result["preset_conflict"] is False
    assert result["review_recommended"] is False


def test_invalid_vision_response_fails_instead_of_returning_a_fake_assessment(tmp_path, monkeypatch):
    image_path = tmp_path / "damage.jpg"
    image_path.write_bytes(b"mock-jpeg")
    monkeypatch.setattr(
        classifier,
        "_get_client",
        lambda: _fake_client(_valid_assessment(damage_type="NOT_A_DAMAGE"), {}),
    )

    with pytest.raises(classifier.DamageClassificationError, match="invalid assessment"):
        classifier.classify_damage_description("Door damage", str(image_path), "door_scratch")


def test_vision_classification_requires_the_uploaded_photo():
    with pytest.raises(ValueError, match="photo is required"):
        classifier.classify_damage_description("Door scratch notes", "missing-photo.jpg")
