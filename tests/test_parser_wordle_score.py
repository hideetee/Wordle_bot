import re
import pytest

from wordle_bot.scorer import ScoreCalculator as SC





def test_wordle_simple():
    # Arrange
    msg = "1/25/26, 1:32 AM - H: Wordle 1,681 5/6*"
    # Haidee Tang: Wordle 1,681 5/6*
    # Act
    result = SC.parser_wordle_score(msg)

    # Assert
    assert result is not None
    assert result[0] == "H"
    assert result[1] == 1681
    assert result[2] == "5"


def test_wordle_with_commas():
    # Arrange
    msg = "6/29/26, 1:32 AM - A: Wordle 1,230 4/6"

    # Act
    result = SC.parser_wordle_score(msg)

    # Assert
    assert result is not None
    assert result[1] == 1230
    assert result[2] == "4"




def test_wordle_lowercase():
    # Arrange
    msg = "01/01/26, 1:32 AM - C: wordle 500 2/6"

    # Act
    result = SC.parser_wordle_score(msg)

    # Assert
    assert result is not None
    assert result[1] == 500
    assert result[2] == "2"


def test_wordle_x_score():
    # Arrange
    msg = "01/01/26, 1:32 AM - D: Wordle 321 X/6"

    # Act
    result = SC.parser_wordle_score(msg)

    # Assert
    assert result is not None
    assert result[1] == 321
    assert result[2] == "X"


def test_non_wordle_message():
    # Arrange
    msg = "01/01/26, 1:32 AM - E: Welcome!"

    # Act
    result = SC.parser_wordle_score(msg)

    # Assert
    assert result is None
