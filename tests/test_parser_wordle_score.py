import re
import pytest

import game_bot.parser as parser





def test_wordle_simple():
    # Arrange
    msg = "1/25/26, 1:32 AM - H: Wordle 1,681 5/6*"
    # Act
    result = parser.parser_wordle_score([msg])

    # Assert
    assert result is not None
    assert result[0][0] == "H"
    assert result[0][1] == 1681
    assert result[0][2] == "5"


def test_wordle_with_commas():
    # Arrange
    msg = "6/29/26, 1:32 AM - A: Wordle 1,230 4/6"

    # Act
    result = parser.parser_wordle_score([msg])

    # Assert
    assert result is not None
    assert result[0][1] == 1230
    assert result[0][2] == "4"




def test_wordle_lowercase():
    # Arrange
    msg = "01/01/26, 1:32 AM - C: wordle 500 2/6"

    # Act
    result = parser.parser_wordle_score([msg])

    # Assert
    assert result is not None
    assert result[0][1] == 500
    assert result[0][2] == "2"


def test_wordle_x_score():
    # Arrange
    msg = "01/01/26, 1:32 AM - D: Wordle 321 X/6"

    # Act
    result = parser.parser_wordle_score([msg])

    # Assert
    assert result is not None
    assert result[0][1] == 321
    assert result[0][2] == "X"


def test_non_wordle_message():
    # Arrange
    msg = "01/01/26, 1:32 AM - E: Welcome!"

    # Act
    result = parser.parser_wordle_score([msg])

    # Assert
    assert result == []



def test_pips_simple():
    # Arrange
    msg = "1/25/26, 1:32 AM - H: Pips #391 Hard 🔴 \n 8:20"
    # Act
    result = parser.parser_pips_score([msg])
    print(result)

    # Assert
    assert result is not None
    assert result[0]['sender'] == "H"
    assert result[0]['pips_num'] == 391
    assert result[0]['time'] == "8:20"


def test_pips_with_commas():
    # Arrange
    msg = "6/29/26, 1:32 AM - H: Pips #1,391 Hard 🔴 \n 8:20"

    # Act
    result = parser.parser_pips_score([msg])

    # Assert
    assert result is not None
    assert result[0]['pips_num'] == 1391
    assert result[0]['time'] == "8:20"




def test_pips_lowercase():
    # Arrange
    msg = "01/01/26, 1:32 AM - C: pips #852 Hard 🔴 \n 2:10"

    # Act
    result = parser.parser_pips_score([msg])

    # Assert
    assert result is not None
    assert result[0]['sender'] == "C"
    assert result[0]['pips_num'] == 852
    assert result[0]['time'] == "2:10"



def test_non_pips_message():
    # Arrange
    msg = "01/01/26, 1:32 AM - E: Welcome!"

    # Act
    result = parser.parser_pips_score([msg])

    # Assert
    assert result == []
