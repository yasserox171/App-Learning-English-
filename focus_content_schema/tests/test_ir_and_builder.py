"""Layers 1 and 3 — the IR's exclusions, and the builder's media substitution.

The storage_key/url swap is the single most likely bug in the pipeline, so it
is tested in both directions.
"""
import pytest

from focus_content_schema import (
    BuildError,
    LessonIR,
    build_import_payload,
    example_ir,
    example_media_manifest,
    validate_ir_dict,
    validate_payload,
)


def _build(ir=None, manifest=None, **kwargs):
    params = dict(
        level="A1",
        unit={"title": "Travel", "order": 1},
        lesson={"title": "At the airport", "order": 1},
    )
    params.update(kwargs)
    return build_import_payload(
        ir if ir is not None else example_ir(),
        manifest if manifest is not None else example_media_manifest(),
        **params,
    )


# --------------------------------------------------------------------------- #
# Layer 1 — the IR forbids what the builder owns
# --------------------------------------------------------------------------- #
def test_example_ir_is_valid():
    assert validate_ir_dict(example_ir()) == []


@pytest.mark.parametrize("forbidden,where", [
    ("order", "component"),
    ("storage_key", "component"),
    ("publish_mode", "root"),
    ("idempotency_key", "root"),
])
def test_ir_rejects_fields_the_builder_owns(forbidden, where):
    ir = example_ir()
    if where == "root":
        ir[forbidden] = "x"
    else:
        ir["components"][0][forbidden] = 1
    errors = validate_ir_dict(ir)
    assert errors, f"{forbidden} should be rejected"
    assert any("extra" in e.lower() or forbidden in e for e in errors)


def test_ir_rejects_absolute_url_in_place_of_asset_ref():
    ir = example_ir()
    ir["components"][2]["items"][0]["image"] = "http://cdn.example.com/x.png"
    assert validate_ir_dict(ir) != []


def test_ir_requires_at_least_one_component():
    assert validate_ir_dict({"components": []}) != []


def test_ir_reports_template_errors_with_position():
    ir = example_ir()
    ir["components"][3]["exercises"][0]["content"]["correct_index"] = 99
    errors = validate_ir_dict(ir)
    assert any("components[3].exercises[0]" in e for e in errors)


def test_ir_rejects_final_test():
    ir = example_ir()
    ir["components"][3]["exercises"][0] = {
        "template": "final_test", "content": {"exercise_ids": []},
    }
    errors = validate_ir_dict(ir)
    assert errors
    assert any("final_test" in e for e in errors)


# --------------------------------------------------------------------------- #
# Layer 3 — ordering
# --------------------------------------------------------------------------- #
def test_builder_assigns_order_from_position_starting_at_one():
    payload = _build()
    assert [c["order"] for c in payload["components"]] == [1, 2, 3, 4]

    vocab = next(c for c in payload["components"] if c["type"] == "vocabulary")
    assert [i["order"] for i in vocab["items"]] == [1, 2]

    exercises = next(
        c for c in payload["components"] if c["type"] == "exercise"
    )
    assert [e["order"] for e in exercises["exercises"]] == [1, 2, 3]


def test_builder_output_passes_final_validation():
    assert validate_payload(_build()) == []


def test_builder_sets_envelope_and_optional_keys():
    payload = _build(
        idempotency_key="batch-1", publish_mode="direct", on_duplicate="replace"
    )
    assert payload["level"] == "A1"
    assert payload["unit"]["title"] == "Travel"
    assert payload["lesson"]["title"] == "At the airport"
    assert payload["idempotency_key"] == "batch-1"
    assert payload["publish_mode"] == "direct"
    assert payload["on_duplicate"] == "replace"


def test_builder_omits_idempotency_key_when_not_given():
    assert "idempotency_key" not in _build()


# --------------------------------------------------------------------------- #
# Layer 3 — media substitution. storage_key and url are NOT interchangeable.
# --------------------------------------------------------------------------- #
def test_video_gets_relative_storage_key_vocabulary_gets_absolute_url():
    payload = _build()
    manifest = example_media_manifest()

    video = next(c for c in payload["components"] if c["type"] == "video")
    assert video["storage_key"] == manifest["lesson_intro_video"]["storage_key"]
    assert not video["storage_key"].startswith("http")

    vocab = next(c for c in payload["components"] if c["type"] == "vocabulary")
    item = vocab["items"][0]
    assert item["image_url"] == manifest["vocab_passport_image"]["url"]
    assert item["image_url"].startswith("http://")
    assert item["audio_url"] == manifest["vocab_passport_audio"]["url"]

    exercises = next(c for c in payload["components"] if c["type"] == "exercise")
    listening = next(
        e for e in exercises["exercises"] if e["template"] == "listening"
    )
    assert listening["content"]["audio_url"] == (
        manifest["gate_announcement_audio"]["url"]
    )
    assert listening["content"]["audio_url"].startswith("http://")


def test_swap_direction_one_url_where_storage_key_belongs():
    """Manifest entry whose storage_key holds an absolute URL — the classic
    swap. The video component must refuse it."""
    manifest = example_media_manifest()
    manifest["lesson_intro_video"]["storage_key"] = (
        "http://84.8.223.62/media/videos/9f2a1c04e7b3.mp4"
    )
    with pytest.raises(BuildError) as exc:
        _build(manifest=manifest)
    message = str(exc.value)
    assert "must be relative" in message
    assert "manifest 'url'" in message


def test_swap_direction_two_storage_key_where_url_belongs():
    """Manifest entry whose url holds a relative key — vocabulary image_url is
    a Django URLField and would be rejected server-side."""
    manifest = example_media_manifest()
    manifest["vocab_passport_image"]["url"] = "images/ebf4f635a17d.png"
    with pytest.raises(BuildError) as exc:
        _build(manifest=manifest)
    message = str(exc.value)
    assert "not absolute" in message
    assert "URLField" in message


def test_missing_storage_key_field_is_a_hard_error():
    manifest = example_media_manifest()
    del manifest["lesson_intro_video"]["storage_key"]
    with pytest.raises(BuildError, match="no 'storage_key'"):
        _build(manifest=manifest)


def test_missing_url_field_is_a_hard_error():
    manifest = example_media_manifest()
    del manifest["vocab_passport_image"]["url"]
    with pytest.raises(BuildError, match="no 'url'"):
        _build(manifest=manifest)


# --------------------------------------------------------------------------- #
# Layer 3 — dangling references
# --------------------------------------------------------------------------- #
def test_unresolved_asset_fails_loudly():
    manifest = example_media_manifest()
    del manifest["vocab_passport_image"]
    with pytest.raises(BuildError) as exc:
        _build(manifest=manifest)
    assert "unresolved asset id 'vocab_passport_image'" in str(exc.value)
    # The error names what IS available, to make the typo obvious.
    assert "Known assets:" in str(exc.value)


def test_empty_manifest_with_assets_fails():
    with pytest.raises(BuildError, match="manifest is empty"):
        _build(manifest={})


def test_manifest_entry_must_be_the_upload_response_object():
    manifest = example_media_manifest()
    manifest["vocab_passport_image"] = "images/x.png"
    with pytest.raises(BuildError, match="must be the upload API response"):
        _build(manifest=manifest)


def test_no_partial_payload_is_returned_on_failure():
    manifest = example_media_manifest()
    del manifest["gate_announcement_audio"]
    with pytest.raises(BuildError):
        _build(manifest=manifest)


# --------------------------------------------------------------------------- #
# Layer 3 — video script segments
# --------------------------------------------------------------------------- #
def _ir_with_segments(segments, duration=120):
    return {
        "components": [{
            "type": "video",
            "asset": {"asset": "lesson_intro_video"},
            "title": "V",
            "duration": duration,
            "segments": segments,
        }]
    }


def test_segments_emitted_under_script_key():
    payload = _build(_ir_with_segments([
        {"start": 0, "end": 2, "narration_en": "Hi", "subtitle_ar": "مرحبا"},
    ]))
    assert payload["components"][0]["script"]["segments"][0]["end"] == 2.0


def test_segment_start_must_precede_end():
    with pytest.raises(BuildError, match="must be less than"):
        _build(_ir_with_segments([
            {"start": 5, "end": 3, "narration_en": "a", "subtitle_ar": "ب"},
        ]))


def test_segments_must_not_overlap():
    with pytest.raises(BuildError, match="overlaps"):
        _build(_ir_with_segments([
            {"start": 0, "end": 5, "narration_en": "a", "subtitle_ar": "ب"},
            {"start": 3, "end": 8, "narration_en": "c", "subtitle_ar": "د"},
        ]))


def test_segments_must_be_sorted():
    with pytest.raises(BuildError, match="overlaps|sorted"):
        _build(_ir_with_segments([
            {"start": 10, "end": 15, "narration_en": "a", "subtitle_ar": "ب"},
            {"start": 0, "end": 5, "narration_en": "c", "subtitle_ar": "د"},
        ]))


def test_last_segment_cannot_exceed_duration():
    with pytest.raises(BuildError, match="only 10s long"):
        _build(_ir_with_segments(
            [{"start": 0, "end": 30, "narration_en": "a", "subtitle_ar": "ب"}],
            duration=10,
        ))


def test_segment_requires_both_languages():
    for missing in ("narration_en", "subtitle_ar"):
        seg = {"start": 0, "end": 2, "narration_en": "a", "subtitle_ar": "ب"}
        seg[missing] = ""
        assert validate_ir_dict(_ir_with_segments([seg])) != []


def test_video_without_segments_emits_no_script():
    payload = _build(_ir_with_segments([]))
    assert "script" not in payload["components"][0]


# --------------------------------------------------------------------------- #
# Layer 3 — argument guards
# --------------------------------------------------------------------------- #
def test_bad_publish_mode_rejected():
    with pytest.raises(BuildError, match="publish_mode"):
        _build(publish_mode="live")


def test_bad_on_duplicate_rejected():
    with pytest.raises(BuildError, match="on_duplicate"):
        _build(on_duplicate="merge")


def test_blank_titles_rejected():
    with pytest.raises(BuildError, match="unit"):
        _build(unit={"title": "  "})
    with pytest.raises(BuildError, match="lesson"):
        _build(lesson={"title": ""})


def test_accepts_a_lesson_ir_instance_as_well_as_a_dict():
    model = LessonIR.model_validate(example_ir())
    assert _build(model)["components"][0]["type"] == "text"
