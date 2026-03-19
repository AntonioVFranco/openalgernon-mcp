"""FSRS-4.5 state machine — pure Python, no subprocess.

Reference: open-algernon/prompts/fsrs.md and schema/study.sql
Key insight: in FSRS-4.5, stability S is defined as days to 90% retention,
so next_interval = round(S) for review-state cards.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

GRADE_AGAIN = 1
GRADE_GOOD = 3

StateType = Literal["new", "learning", "review", "relearning"]


@dataclass
class CardState:
    stability: float
    difficulty: float
    reps: int
    lapses: int
    state: StateType
    last_review: str | None  # ISO date string or None


@dataclass
class NextState:
    stability: float
    difficulty: float
    reps: int
    lapses: int
    state: StateType
    next_interval: int  # days


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def compute_next_state(
    current: CardState,
    grade: int,
    elapsed_days: float,
) -> NextState:
    """Compute the next FSRS-4.5 state after a review.

    Args:
        current: Current card state.
        grade: 1 (Again) or 3 (Good).
        elapsed_days: Days since last review (0 if first review).

    Returns:
        NextState with updated fields and next_interval.
    """
    s = current.stability
    d = current.difficulty
    reps = current.reps
    lapses = current.lapses
    state = current.state

    if state == "new":
        if grade == GRADE_GOOD:
            new_s = 0.4
            new_d = 0.3
            new_state: StateType = "review"
            interval = 1
        else:  # GRADE_AGAIN
            new_s = 0.1
            new_d = 0.4
            new_state = "learning"
            interval = 1

    elif state == "learning":
        if grade == GRADE_GOOD:
            new_s = s * 1.5
            new_d = _clamp(d - 0.05, 0.1, 1.0)
            new_state = "review"
            interval = max(1, round(new_s))
        else:  # GRADE_AGAIN
            new_s = s
            new_d = _clamp(d + 0.1, 0.1, 1.0)
            new_state = "learning"
            interval = 1

    elif state == "relearning":
        if grade == GRADE_GOOD:
            new_s = s * 1.5
            new_d = _clamp(d - 0.05, 0.1, 1.0)
            new_state = "review"
            interval = max(1, round(new_s))
        else:  # GRADE_AGAIN
            new_s = max(0.1, s * 0.5)  # decay on repeated failure
            new_d = _clamp(d + 0.1, 0.1, 1.0)
            new_state = "relearning"
            interval = 1

    else:  # state == "review"
        if grade == GRADE_GOOD:
            retrievability = math.exp(math.log(0.9) * elapsed_days / s) if s > 0 else 0.9
            new_s = s * math.exp(0.9 * (1 - retrievability))
            new_d = _clamp(d - 0.05, 0.1, 1.0)
            new_state = "review"
            interval = max(1, round(new_s))
        else:  # GRADE_AGAIN
            new_s = max(0.1, s * 0.2)
            new_d = _clamp(d + 0.1, 0.1, 1.0)
            new_state = "relearning"
            lapses += 1
            interval = 1

    return NextState(
        stability=new_s,
        difficulty=new_d,
        reps=reps + 1,
        lapses=lapses,
        state=new_state,
        next_interval=interval,
    )
