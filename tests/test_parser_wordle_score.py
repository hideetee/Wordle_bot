import re
import pytest

from wordle_bot.parser import parser_wordle_score



def test_wordle_simple():
    # Arrange
    msg = "Wordle 247 3/6"

    # Act
    result = parser_wordle_score(msg)

    # Assert
    assert result is not None
    assert result.group(1) == "247"
    assert result.group(2) == "3"


def test_wordle_with_commas():
    # Arrange
    msg = "Wordle 1,230 4/6"

    # Act
    result = parser_wordle_score(msg)

    # Assert
    assert result is not None
    assert result.group(1) == "1,230"
    assert result.group(2) == "4"


def test_wordle_with_spaces_in_number():
    # Arrange
    msg = "Wordle 1, 230 4/6"

    # Act
    result = parser_wordle_score(msg)

    # Assert
    assert result is not None
    assert result.group(1).replace(" ", "") == "1,230"
    assert result.group(2) == "4"


def test_wordle_lowercase():
    # Arrange
    msg = "wordle 500 2/6"

    # Act
    result = parser_wordle_score(msg)

    # Assert
    assert result is not None
    assert result.group(1) == "500"
    assert result.group(2) == "2"


def test_wordle_x_score():
    # Arrange
    msg = "Wordle 321 X/6"

    # Act
    result = parser_wordle_score(msg)

    # Assert
    assert result is not None
    assert result.group(1) == "321"
    assert result.group(2) == "X"


def test_non_wordle_message():
    # Arrange
    msg = "Amy: Welcome!"

    # Act
    result = parser_wordle_score(msg)

    # Assert
    assert result is None
