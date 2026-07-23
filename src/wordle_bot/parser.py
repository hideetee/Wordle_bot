import re


msg = """

Wordle 1853 5/6*

🟨⬛⬛⬛⬛
⬛⬛⬛🟩⬛
⬛⬛🟨🟩🟩
⬛🟩⬛🟩🟩
🟩🟩🟩🟩🟩
"""


pattern = re.compile(
    r"Wordle\s+(\d+)\s+([1-6X])/6",
    re.I
)


result = pattern.search(msg)


print(result.groups())


def parser_wordle_score(msg):
    pattern = re.compile(
        r"Wordle\s+([\d,\s]+)\s+([1-6X])/6",
        re.I
    )

    result = pattern.search(msg)

    return result