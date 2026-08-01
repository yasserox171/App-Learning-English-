"""Layer 2 — golden fixtures from the real seed data, plus a deliberately
malformed case per template asserting the specific error."""
import pytest

from focus_content_schema import (
    FINAL_TEST_REJECTION,
    GOLDEN_CONTENT,
    VALID_TEMPLATES,
    validate_exercise_content,
)
from focus_content_schema.examples import SEEDED_RELATIVE_MEDIA


# --------------------------------------------------------------------------- #
# golden: every template's known-good content validates clean
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("template", VALID_TEMPLATES)
def test_golden_content_is_valid(template):
    assert template in GOLDEN_CONTENT, f"no golden fixture for {template}"
    assert validate_exercise_content(template, GOLDEN_CONTENT[template]) == []


def test_golden_covers_every_template():
    assert set(GOLDEN_CONTENT) == set(VALID_TEMPLATES)


# --------------------------------------------------------------------------- #
# final_test is out of scope for automation
# --------------------------------------------------------------------------- #
def test_final_test_rejected_with_explanation():
    errors = validate_exercise_content(
        "final_test", {"exercise_ids": ["4f0e...", "9a1b..."]}
    )
    assert errors == [FINAL_TEST_REJECTION]
    assert "cannot be generated automatically" in errors[0]


def test_unknown_template_rejected():
    errors = validate_exercise_content("quiz", {})
    assert len(errors) == 1
    assert "unknown template 'quiz'" in errors[0]


# --------------------------------------------------------------------------- #
# multiple_choice
# --------------------------------------------------------------------------- #
def test_mc_needs_two_options():
    errors = validate_exercise_content(
        "multiple_choice",
        {"question": "Q?", "options": ["only"], "correct_index": 0},
    )
    assert any("at least 2 options" in e for e in errors)


def test_mc_rejects_duplicate_options():
    errors = validate_exercise_content(
        "multiple_choice",
        {"question": "Q?", "options": ["yes", "Yes ", "no"], "correct_index": 0},
    )
    assert any("duplicate options" in e for e in errors)


def test_mc_correct_index_out_of_range():
    errors = validate_exercise_content(
        "multiple_choice",
        {"question": "Q?", "options": ["a", "b"], "correct_index": 5},
    )
    assert any("out of range" in e for e in errors)


def test_mc_correct_index_must_be_int_not_bool_or_string():
    for bad in ("1", True, 1.5, None):
        errors = validate_exercise_content(
            "multiple_choice",
            {"question": "Q?", "options": ["a", "b"], "correct_index": bad},
        )
        assert any("must be an integer" in e for e in errors), bad


def test_mc_collects_all_errors_not_just_the_first():
    errors = validate_exercise_content(
        "multiple_choice", {"question": "", "options": ["a"], "correct_index": 9}
    )
    assert len(errors) >= 3


# --------------------------------------------------------------------------- #
# true_false
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("bad", ["true", "false", 1, 0, None])
def test_tf_rejects_non_boolean_answer(bad):
    errors = validate_exercise_content(
        "true_false", {"statement": "S.", "answer": bad}
    )
    assert any("real boolean" in e or "required" in e for e in errors)


def test_tf_accepts_both_real_booleans():
    for value in (True, False):
        assert validate_exercise_content(
            "true_false", {"statement": "S.", "answer": value}
        ) == []


# --------------------------------------------------------------------------- #
# fill_blank
# --------------------------------------------------------------------------- #
def test_fill_blank_requires_marker():
    errors = validate_exercise_content(
        "fill_blank", {"sentence": "I am a passenger.", "answer": "am"}
    )
    assert any("___" in e for e in errors)


def test_fill_blank_options_absent_is_valid_not_missing():
    """The backend generates a word bank when options are omitted."""
    assert validate_exercise_content(
        "fill_blank", {"sentence": "I ___ here.", "answer": "am"}
    ) == []


def test_fill_blank_supplied_options_must_contain_answer():
    errors = validate_exercise_content(
        "fill_blank",
        {"sentence": "I ___ here.", "answer": "am", "options": ["is", "are"]},
    )
    assert any("must contain the answer" in e for e in errors)

    assert validate_exercise_content(
        "fill_blank",
        {"sentence": "I ___ here.", "answer": "am",
         "options": ["am", "is", "are"]},
    ) == []


# --------------------------------------------------------------------------- #
# matching — the critical one (grader uses bracket access)
# --------------------------------------------------------------------------- #
def test_matching_missing_key_is_caught():
    """A pair missing 'right' would raise KeyError in the backend grader and
    500 a learner mid-lesson. It must never reach the API."""
    errors = validate_exercise_content(
        "matching",
        {"pairs": [{"left": "Airport", "right": "مطار"}, {"left": "Passport"}]},
    )
    assert any("missing 'right'" in e for e in errors)
    assert any("KeyError" in e for e in errors)


def test_matching_missing_left_is_caught():
    errors = validate_exercise_content(
        "matching",
        {"pairs": [{"left": "A", "right": "1"}, {"right": "2"}]},
    )
    assert any("missing 'left'" in e for e in errors)


def test_matching_empty_side_is_caught():
    errors = validate_exercise_content(
        "matching",
        {"pairs": [{"left": "A", "right": "1"}, {"left": "B", "right": "   "}]},
    )
    assert any("non-empty" in e for e in errors)


def test_matching_needs_two_pairs():
    errors = validate_exercise_content(
        "matching", {"pairs": [{"left": "A", "right": "1"}]}
    )
    assert any("at least 2 pairs" in e for e in errors)


def test_matching_rejects_duplicate_lefts():
    errors = validate_exercise_content(
        "matching",
        {"pairs": [
            {"left": "Airport", "right": "مطار"},
            {"left": "airport", "right": "something else"},
        ]},
    )
    assert any("duplicate left" in e for e in errors)


def test_matching_never_raises_on_garbage():
    for garbage in ({"pairs": "nope"}, {"pairs": [None, 5]}, {}):
        assert isinstance(
            validate_exercise_content("matching", garbage), list
        )


# --------------------------------------------------------------------------- #
# reorder — multiset permutation, not just length
# --------------------------------------------------------------------------- #
def test_reorder_same_length_different_words_rejected():
    errors = validate_exercise_content(
        "reorder",
        {"words": ["I", "am", "here"], "correct_order": ["I", "am", "there"]},
    )
    assert any("permutation" in e for e in errors)


def test_reorder_respects_duplicate_word_counts():
    # 'very' twice in words, once in correct_order -> not a permutation
    errors = validate_exercise_content(
        "reorder",
        {"words": ["very", "very", "good"],
         "correct_order": ["very", "good", "good"]},
    )
    assert any("permutation" in e for e in errors)

    assert validate_exercise_content(
        "reorder",
        {"words": ["very", "very", "good"],
         "correct_order": ["good", "very", "very"]},
    ) == []


# --------------------------------------------------------------------------- #
# listening / pronunciation — absolute URL rule
# --------------------------------------------------------------------------- #
def test_listening_relative_audio_url_rejected():
    """The seeded example predates the upload API and uses a relative path."""
    content = dict(GOLDEN_CONTENT["listening"])
    content["audio_url"] = SEEDED_RELATIVE_MEDIA["listening"]
    errors = validate_exercise_content("listening", content)
    assert any("absolute http(s) URL" in e for e in errors)


def test_pronunciation_relative_reference_audio_rejected():
    content = dict(GOLDEN_CONTENT["pronunciation"])
    content["reference_audio_url"] = SEEDED_RELATIVE_MEDIA["pronunciation"]
    errors = validate_exercise_content("pronunciation", content)
    assert any("absolute http(s) URL" in e for e in errors)


def test_pronunciation_reference_audio_is_optional():
    assert validate_exercise_content(
        "pronunciation", {"target_text": "Boarding pass"}
    ) == []


def test_listening_audio_url_required():
    content = {k: v for k, v in GOLDEN_CONTENT["listening"].items()
               if k != "audio_url"}
    errors = validate_exercise_content("listening", content)
    assert any("'audio_url' is required" in e for e in errors)


def test_asset_refs_allowed_only_in_ir_mode():
    content = dict(GOLDEN_CONTENT["listening"])
    content["audio_url"] = {"asset": "gate_audio"}

    assert validate_exercise_content(
        "listening", content, allow_asset_refs=True
    ) == []
    # After the builder has run, an unresolved ref is a bug.
    assert validate_exercise_content(
        "listening", content, allow_asset_refs=False
    ) != []


# --------------------------------------------------------------------------- #
# dictation
# --------------------------------------------------------------------------- #
def test_dictation_requires_answer():
    errors = validate_exercise_content("dictation", {"hint": "four words"})
    assert any("'answer'" in e for e in errors)


def test_dictation_minimal_form_is_valid():
    assert validate_exercise_content("dictation", {"answer": "I am here."}) == []


def test_dictation_rejects_negative_hint_threshold():
    errors = validate_exercise_content(
        "dictation", {"answer": "x", "show_hint_after_attempts": -1}
    )
    assert any("non-negative integer" in e for e in errors)


# --------------------------------------------------------------------------- #
# total robustness
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("template", VALID_TEMPLATES)
@pytest.mark.parametrize(
    "garbage", [None, [], "string", 42, {"unexpected": object()}]
)
def test_validators_never_raise(template, garbage):
    result = validate_exercise_content(template, garbage)
    assert isinstance(result, list)
    assert all(isinstance(e, str) for e in result)
    assert result, "invalid content must produce at least one error"
