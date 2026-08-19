from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ScoreRecord:
    """Represents a single player's score for a specific Wordle puzzle."""
    player: str
    wordle_num: int
    score: Optional[int]  # 1-6 for success, 7 for X/penalty, None for unplayed current day


@dataclass(frozen=True)
class WeekRange:
    """Represents the inclusive start and end Wordle numbers for a 7-day competition week."""
    start: int
    end: int

    @property
    def is_complete(self) -> bool:
        return (self.end - self.start + 1) == 7

    def __iter__(self):
        yield self.start
        yield self.end


@dataclass(frozen=True)
class WeeklyScore:
    """Represents a player's aggregated score and rank for a single week."""
    player: str
    week_start: int
    week_end: int
    score: int
    rank: float


@dataclass(frozen=True)
class LeaderboardEntry:
    """Represents a player's full weekly result and running cumulative standing."""
    player: str
    week_start: int
    week_end: int
    score: int
    rank: float
    overall_score: float
    overall_rank: float
