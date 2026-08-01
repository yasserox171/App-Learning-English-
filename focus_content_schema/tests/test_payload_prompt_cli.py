"""Layers 4 and 5, plus the CLI."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

from focus_content_schema import (
    VALID_LEVELS,
    build_import_payload,
    example_ir,
    example_media_manifest,
    export_ir_json_schema,
    render_prompt_fragment,
    validate_payload,
)
from focus_content_schema.__main__ import EXIT_INVALID, EXIT_OK, EXIT_USAGE, main

SRC = str(Path(__file__).resolve().parents[1] / "src")


def _payload(**kwargs):
    params = dict(
        level="A1",
        unit={"title": "Travel"},
        lesson={"title": "At the airport"},
    )
    params.update(kwargs)
    return build_import_payload(
        example_ir(), example_media_manifest(), **params
    )


# --------------------------------------------------------------------------- #
# Layer 4 — backend rules
# --------------------------------------------------------------------------- #
def test_valid_payload_has_no_errors():
    assert validate_payload(_payload()) == []


@pytest.mark.parametrize("level", VALID_LEVELS)
def test_all_cefr_levels_accepted(level):
    assert validate_payload(_payload(level=level)) == []


def test_invalid_level_rejected():
    errors = validate_payload(_payload(level="Z9"))
    assert any("'level' must be one of" in e for e in errors)


def test_missing_titles_rejected():
    payload = _payload()
    payload["unit"]["title"] = ""
    payload["lesson"] = {}
    errors = validate_payload(payload)
    assert any("unit" in e for e in errors)
    assert any("lesson" in e for e in errors)


def test_unknown_component_type_rejected():
    payload = _payload()
    payload["components"][0]["type"] = "hologram"
    assert any("unknown type 'hologram'" in e for e in validate_payload(payload))


def test_unknown_template_rejected_in_payload():
    payload = _payload()
    exercises = next(c for c in payload["components"] if c["type"] == "exercise")
    exercises["exercises"][0]["template"] = "final_test"
    errors = validate_payload(payload)
    assert any("final_test" in e for e in errors)


def test_template_content_rules_enforced_at_payload_level():
    """The backend never checks this; Layer 4 is the last chance."""
    payload = _payload()
    exercises = next(c for c in payload["components"] if c["type"] == "exercise")
    del exercises["exercises"][0]["content"]["correct_index"]
    errors = validate_payload(payload)
    assert any("'correct_index' is required" in e for e in errors)


def test_duplicate_component_orders_rejected():
    payload = _payload()
    payload["components"][1]["order"] = payload["components"][0]["order"]
    assert any("must be unique" in e for e in validate_payload(payload))


def test_relative_vocabulary_url_rejected():
    payload = _payload()
    vocab = next(c for c in payload["components"] if c["type"] == "vocabulary")
    vocab["items"][0]["image_url"] = "images/x.png"
    errors = validate_payload(payload)
    assert any("URLField" in e for e in errors)


def test_absolute_video_storage_key_rejected():
    payload = _payload()
    video = next(c for c in payload["components"] if c["type"] == "video")
    video["storage_key"] = "http://cdn.example.com/x.mp4"
    errors = validate_payload(payload)
    assert any("should be the relative key" in e for e in errors)


def test_script_segment_rules_enforced():
    payload = _payload()
    video = next(c for c in payload["components"] if c["type"] == "video")
    video["script"]["segments"][1]["start"] = 1.0  # overlaps the first
    assert any("overlaps" in e for e in validate_payload(payload))


def test_segment_beyond_duration_rejected():
    payload = _payload()
    video = next(c for c in payload["components"] if c["type"] == "video")
    video["duration"] = 5
    assert any("only 5s long" in e for e in validate_payload(payload))


def test_blank_idempotency_key_rejected():
    payload = _payload()
    payload["idempotency_key"] = "   "
    assert any("idempotency_key" in e for e in validate_payload(payload))


def test_validate_payload_never_raises():
    for garbage in (None, [], "x", 42, {"components": "no"}):
        assert isinstance(validate_payload(garbage), list)


def test_validate_payload_collects_multiple_errors():
    payload = _payload(level="ZZ")
    payload["unit"]["title"] = ""
    payload["components"][0]["content"] = ""
    assert len(validate_payload(payload)) >= 3


# --------------------------------------------------------------------------- #
# Layer 5 — one source of truth
# --------------------------------------------------------------------------- #
def test_schema_is_serialisable_and_describes_the_ir():
    schema = export_ir_json_schema()
    assert json.dumps(schema)
    assert "components" in schema["properties"]


def test_schema_forbids_extra_properties():
    """This is what stops the LLM inventing `order` or `storage_key`."""
    schema = export_ir_json_schema()
    defs = schema.get("$defs", {})
    assert defs, "expected component models in $defs"
    assert any(d.get("additionalProperties") is False for d in defs.values())


def test_prompt_fragment_embeds_the_live_schema():
    fragment = render_prompt_fragment()
    for token in ("components", "asset", "final_test", "___"):
        assert token in fragment
    # The schema is rendered from the models, not pasted in.
    assert json.dumps(export_ir_json_schema(), indent=2, ensure_ascii=False)[:40] in fragment


def test_prompt_fragment_sections_can_be_disabled():
    minimal = render_prompt_fragment(
        include_schema=False, include_examples=False,
        include_content_examples=False,
    )
    assert "JSON Schema" not in minimal
    assert len(minimal) < len(render_prompt_fragment())


def test_prompt_example_is_itself_valid():
    """A few-shot example that fails our own validator would teach the model
    to produce invalid output."""
    from focus_content_schema import validate_ir_dict

    assert validate_ir_dict(example_ir()) == []


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def test_cli_validate_accepts_good_payload(tmp_path, capsys):
    file = tmp_path / "payload.json"
    file.write_text(json.dumps(_payload()), encoding="utf-8")
    assert main(["validate", str(file)]) == EXIT_OK
    assert "valid import payload" in capsys.readouterr().out


def test_cli_validate_rejects_bad_payload_with_errors(tmp_path, capsys):
    payload = _payload()
    payload["level"] = "Z9"
    file = tmp_path / "bad.json"
    file.write_text(json.dumps(payload), encoding="utf-8")

    assert main(["validate", str(file)]) == EXIT_INVALID
    err = capsys.readouterr().err
    assert "error(s)" in err
    assert "Z9" in err


def test_cli_validate_ir(tmp_path):
    file = tmp_path / "ir.json"
    file.write_text(json.dumps(example_ir()), encoding="utf-8")
    assert main(["validate-ir", str(file)]) == EXIT_OK


def test_cli_missing_file_and_bad_json(tmp_path):
    assert main(["validate", str(tmp_path / "nope.json")]) == EXIT_USAGE
    broken = tmp_path / "broken.json"
    broken.write_text("{not json", encoding="utf-8")
    assert main(["validate", str(broken)]) == EXIT_USAGE


def test_cli_schema_and_prompt_to_file(tmp_path):
    out = tmp_path / "schema.json"
    assert main(["schema", "-o", str(out)]) == EXIT_OK
    assert json.loads(out.read_text())["properties"]["components"]

    prompt = tmp_path / "prompt.md"
    assert main(["prompt", "-o", str(prompt)]) == EXIT_OK
    assert "components" in prompt.read_text()


def test_cli_runs_as_a_module_with_nonzero_exit(tmp_path):
    """End-to-end: `python -m focus_content_schema validate <bad file>`."""
    payload = _payload()
    payload["components"][0]["type"] = "hologram"
    file = tmp_path / "bad.json"
    file.write_text(json.dumps(payload), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "-m", "focus_content_schema", "validate", str(file)],
        capture_output=True, text=True,
        env={"PYTHONPATH": SRC, "PATH": "/usr/bin:/bin"},
    )
    assert result.returncode == EXIT_INVALID
    assert "hologram" in result.stderr
