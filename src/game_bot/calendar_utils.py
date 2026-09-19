from typing import List, Sequence, Tuple
from game_bot.config import (
    DAYS_PER_WEEK,
    WORDLE_ANCHOR_NUMBER,
    WORDLE_ANCHOR_WEEKDAY,
    PIPS_ANCHOR_NUMBER,
    PIPS_ANCHOR_WEEKDAY
)
from game_bot.models import WeekRange

class CalendarUtils:
    def __init__(self, game: str):
        if game not in {"wordle", "pips"}:
            raise ValueError("game must be 'wordle' or 'pips'")
        self.game = game

    def __repr__(self) -> str:
        return f"CalendarUtils(game={self.game!r})"


    def get_week_range(self, game_num: int) -> Tuple[int, int]:
        """
        Calculate the week start and week end numbers for a given Wordle or Pips number.
        Weeks run from Sunday to Saturday (7 days).

        """
        if not isinstance(game_num, int):
            raise TypeError(f"game_num must be an integer, got {type(game_num).__name__}")

        if self.game == "wordle":
            anchor_num = WORDLE_ANCHOR_NUMBER
            anchor_weekday = WORDLE_ANCHOR_WEEKDAY
        elif self.game == "pips":
            anchor_num = PIPS_ANCHOR_NUMBER
            anchor_weekday = PIPS_ANCHOR_WEEKDAY
        else:
            raise ValueError("game must be 'wordle' or 'pips'")

        weekday = (anchor_weekday + (game_num - anchor_num)) % DAYS_PER_WEEK
        week_start = game_num - weekday
        week_end = week_start + (DAYS_PER_WEEK - 1)

        return int(week_start), int(week_end)



    def get_unique_week_ranges(self, game_numbers: Sequence[int]) -> List[Tuple[int, int]]:
        """
        Identify and return all distinct (week_start, week_end) ranges spanned by the given Wordle numbers.
        """
        if not game_numbers:
            return []

        if self.game not in ["wordle", "pips"]:
            raise ValueError("game must be 'wordle' or 'pips'")

        # sorted_nums = sorted(set(game_numbers))
        # week_ranges: List[Tuple[int, int]] = []

        # week_start, week_end = get_week_range(self, sorted_nums[0])
        # week_ranges.append((week_start, week_end))

        # for w_num in sorted_nums[1:]:
        #     if w_num > week_end:
        #         week_start, week_end = get_week_range(self, w_num)
        #         week_ranges.append((week_start, week_end))

        # return week_ranges

        

        return list(
            dict.fromkeys(
                self.get_week_range(game_num)
                for game_num in sorted(set(game_numbers))
            )
        )


    # Backward-compatible alias
    game_week = get_week_range
