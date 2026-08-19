import pytest
from wordle_bot.calendar import get_unique_week_ranges, get_wordle_week


def test_get_wordle_week_anchor_date():
    # Wordle 1875 is Friday -> week starts on Sunday (1875 - 5 = 1870), ends on Saturday (1876)
    start, end = get_wordle_week(1875)
    assert start == 1870
    assert end == 1876


def test_get_wordle_week_random_number():
    # Wordle 1865
    start, end = get_wordle_week(1865)
    assert start == 1863
    assert end == 1869


def test_get_wordle_week_invalid_type_raises():
    with pytest.raises(TypeError):
        get_wordle_week("invalid")  # type: ignore


def test_get_unique_week_ranges_empty():
    assert get_unique_week_ranges([]) == []


def test_get_unique_week_ranges_multiple_weeks():
    # Two full consecutive weeks: 1870..1876 and 1877..1883
    numbers = [1870, 1872, 1876, 1878, 1883]
    ranges = get_unique_week_ranges(numbers)
    assert ranges == [(1870, 1876), (1877, 1883)]
