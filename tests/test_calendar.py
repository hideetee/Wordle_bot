import pytest
from game_bot.calendar_utils import CalendarUtils

def test_get_week_range_wordle():
    # Wordle 1875 is Friday -> week starts on Sunday (1875 - 5 = 1870), ends on Saturday (1876)
    calendar = CalendarUtils("wordle")

    assert calendar.get_week_range(1875) == (1870, 1876)
    assert calendar.get_week_range(1865) == (1863, 1869)

    

def test_get_week_range_pips():
    # Pips 395 is Thursday -> week starts on Sunday (392 - 1 = 391), ends on Saturday (397)
    calendar = CalendarUtils("pips")

    assert calendar.get_week_range(395) == (391, 397)
    assert calendar.get_week_range(396) == (391, 397)
    assert calendar.get_week_range(397) == (391, 397)

    assert calendar.get_week_range(398) == (398, 404)



def test_get_week_range_invalid_type_raises_wordle():
    with pytest.raises(TypeError):
        get_week_range = CalendarUtils('wordle').get_week_range
        get_week_range("invalid")  # type: ignore

def test_get_week_range_invalid_type_raises_pips():
    with pytest.raises(TypeError):
        get_week_range = CalendarUtils('pips').get_week_range
        get_week_range("invalid")  # type: ignore

def test_get_unique_week_ranges_empty_wordle():
    get_unique_week_ranges = CalendarUtils('wordle').get_unique_week_ranges
    assert get_unique_week_ranges([]) == []


def test_get_unique_week_ranges_empty_pips():
    get_unique_week_ranges = CalendarUtils('pips').get_unique_week_ranges
    assert get_unique_week_ranges([]) == []


def test_get_unique_week_ranges_multiple_weeks_wordle():
    # Two full consecutive weeks: 1870..1876 and 1877..1883
    numbers = [1870, 1872, 1876, 1878, 1883]
    get_unique_week_ranges = CalendarUtils('wordle').get_unique_week_ranges
    ranges = get_unique_week_ranges(numbers)
    assert ranges == [(1870, 1876), (1877, 1883)]

def test_get_unique_week_ranges_multiple_weeks_pips():
    # Two full consecutive weeks: 392..398 and 399..405
    numbers = [391, 394, 398, 400, 405]
    calendar = CalendarUtils('pips')
    ranges = calendar.get_unique_week_ranges(numbers)
    assert ranges == [(391, 397), (398, 404), (405, 411)]