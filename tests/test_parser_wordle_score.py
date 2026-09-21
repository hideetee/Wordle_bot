import re
import pytest

import game_bot.parser as parser


def test_parser_wordle_score_unique_prefix():
    # Arrange
    lines = [
        "1/25/26, 1:32 AM - Alice: Wordle 1,681 5/6*",
        "1/25/26, 1:33 AM - Abe: Wordle 1,681 4/6",
        "1/25/26, 1:34 AM - Charlie: Wordle 1,681 3/6",
    ]

    # Act
    result_alice = parser.WordleParser.find_sender(lines, 0)
    result_abe = parser.WordleParser.find_sender(lines, 1)
    result_charlie = parser.WordleParser.find_sender(lines, 2)

    # Assert
    assert result_alice == "Al"
    assert result_abe == "Ab"
    assert result_charlie == "C"
    




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


def test_parse_messages_with_game_parameter():
    wordle_msg = "1/25/26, 1:32 AM - H: Wordle 1,681 5/6*"
    pips_msg = "1/25/26, 1:32 AM - H: Pips #391 Hard 🔴 \n 8:20"

    # Wordle parsing via game parameter
    wordle_res = parser.parse_messages([wordle_msg], game="wordle")
    assert len(wordle_res) == 1
    assert wordle_res[0] == ("H", 1681, "5")

    # Pips parsing via game parameter
    pips_res = parser.parse_messages([pips_msg], game="pips")
    assert len(pips_res) == 1
    assert pips_res[0]["sender"] == "H"
    assert pips_res[0]["pips_num"] == 391

    # Invalid game type
    with pytest.raises(ValueError):
        parser.parse_messages([wordle_msg], game="invalid_game")

