import math
import pytest
from openalgernon_mcp.fsrs import compute_next_state, CardState, GRADE_AGAIN, GRADE_GOOD


def make_state(stability=0.4, difficulty=0.3, reps=0, lapses=0,
               state="new", last_review=None):
    return CardState(
        stability=stability,
        difficulty=difficulty,
        reps=reps,
        lapses=lapses,
        state=state,
        last_review=last_review,
    )


def test_new_good_transitions_to_review():
    result = compute_next_state(make_state(), GRADE_GOOD, elapsed_days=0)
    assert result.state == "review"
    assert result.stability == 0.4
    assert result.next_interval == 1


def test_new_again_transitions_to_learning():
    result = compute_next_state(make_state(), GRADE_AGAIN, elapsed_days=0)
    assert result.state == "learning"
    assert result.stability == 0.1
    assert result.next_interval == 1


def test_learning_good_transitions_to_review():
    s = make_state(stability=0.4, difficulty=0.3, state="learning")
    result = compute_next_state(s, GRADE_GOOD, elapsed_days=1)
    assert result.state == "review"
    assert result.stability == pytest.approx(0.6, rel=0.01)


def test_review_good_increases_stability():
    s = make_state(stability=10.0, difficulty=0.3, state="review")
    result = compute_next_state(s, GRADE_GOOD, elapsed_days=10)
    assert result.state == "review"
    assert result.stability > 10.0
    assert result.next_interval >= 1


def test_review_again_relearning_and_lapses():
    s = make_state(stability=10.0, difficulty=0.3, lapses=0, state="review")
    result = compute_next_state(s, GRADE_AGAIN, elapsed_days=10)
    assert result.state == "relearning"
    assert result.lapses == 1
    assert result.next_interval == 1


def test_interval_equals_round_stability_for_review():
    s = make_state(stability=7.6, difficulty=0.3, state="review")
    result = compute_next_state(s, GRADE_GOOD, elapsed_days=8)
    assert result.next_interval == round(result.stability)
