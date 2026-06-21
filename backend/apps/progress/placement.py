"""Placement test question bank (master prompt §5).

The data model has no PlacementQuestion table (PlacementResult only), so the
question bank lives here in code — no DB change. Score → level mapping below.
Replace/extend the bank without touching the API contract.
"""
QUESTIONS = [
    {"id": "q1", "question": "Choose: I ___ a student.",
     "options": ["am", "is", "are"], "correct_index": 0},
    {"id": "q2", "question": "Plural of 'child'?",
     "options": ["childs", "children", "childes"], "correct_index": 1},
    {"id": "q3", "question": "She ___ to school every day.",
     "options": ["go", "goes", "going"], "correct_index": 1},
    {"id": "q4", "question": "Past tense of 'buy'?",
     "options": ["buyed", "bought", "buy"], "correct_index": 1},
    {"id": "q5", "question": "If I ___ rich, I would travel.",
     "options": ["am", "was", "were"], "correct_index": 2},
    {"id": "q6", "question": "Choose the correct: 'I have lived here ___ 2010.'",
     "options": ["since", "for", "from"], "correct_index": 0},
    {"id": "q7", "question": "'Ubiquitous' most nearly means:",
     "options": ["rare", "everywhere", "ancient"], "correct_index": 1},
    {"id": "q8", "question": "Pick the correctly punctuated sentence:",
     "options": ["Its raining.", "It's raining.", "Its' raining."],
     "correct_index": 1},
    {"id": "q9", "question": "'Notwithstanding' is closest to:",
     "options": ["because of", "despite", "in addition"], "correct_index": 1},
    {"id": "q10", "question": "Choose: 'Had I known, I ___ have come.'",
     "options": ["would", "will", "did"], "correct_index": 0},
]

# Number-correct thresholds (inclusive lower bound) → level code.
# Ordered from highest to lowest.
SCORE_TO_LEVEL = [
    (9, "C2"),
    (8, "C1"),
    (6, "B2"),
    (4, "B1"),
    (2, "A2"),
    (0, "A1"),
]


def public_questions():
    """Questions without the correct answers (for the client)."""
    return [
        {"id": q["id"], "question": q["question"], "options": q["options"]}
        for q in QUESTIONS
    ]


def grade(answers: dict) -> int:
    """Return number of correct answers. ``answers`` maps id -> selected_index."""
    correct = 0
    for q in QUESTIONS:
        if answers.get(q["id"]) == q["correct_index"]:
            correct += 1
    return correct


def level_code_for_score(correct: int) -> str:
    for threshold, code in SCORE_TO_LEVEL:
        if correct >= threshold:
            return code
    return "A1"
