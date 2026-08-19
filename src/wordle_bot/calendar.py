from typing import List, Sequence, Tuple
from wordle_bot.config import (
    DAYS_PER_WEEK,
    WORDLE_ANCHOR_NUMBER,
    WORDLE_ANCHOR_WEEKDAY,
)
from wordle_bot.models import WeekRange


def get_wordle_week(wordle_num: int) -> Tuple[int, int]:
    """
    Calculate the week start and week end Wordle numbers for a given Wordle number.
    Weeks run from Sunday to Saturday (7 days).
    Anchor: Wordle 1875 is Friday (weekday index 5, where Sunday = 0, Saturday = 6).
    """
    if not isinstance(wordle_num, int):
        raise TypeError(f"wordle_num must be an integer, got {type(wordle_num).__name__}")

    weekday = (WORDLE_ANCHOR_WEEKDAY + (wordle_num - WORDLE_ANCHOR_NUMBER)) % DAYS_PER_WEEK
    week_start = int(wordle_num - weekday)
    week_end = int(week_start + (DAYS_PER_WEEK - 1))

    return week_start, week_end


def get_unique_week_ranges(wordle_numbers: Sequence[int]) -> List[Tuple[int, int]]:
    """
    Identify and return all distinct (week_start, week_end) ranges spanned by the given Wordle numbers.
    """
    if not wordle_numbers:
        return []

    sorted_wordles = sorted(set(wordle_numbers))
    week_ranges: List[Tuple[int, int]] = []

    week_start, week_end = get_wordle_week(sorted_wordles[0])
    week_ranges.append((week_start, week_end))

    for w_num in sorted_wordles[1:]:
        if w_num > week_end:
            week_start, week_end = get_wordle_week(w_num)
            week_ranges.append((week_start, week_end))

    return week_ranges


# Backward-compatible alias
wordle_week = get_wordle_week
