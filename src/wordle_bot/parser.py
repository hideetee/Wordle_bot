import re


def find_sender(lines, index):
    """
    If sender is not found in the current line, walk backwards to find the most recent sender in the previous lines.
    """
    HEADER = re.compile(r"^\d{1,2}/\d{1,2}/\d{2}, ")
    for i in range(index, -1, -1):

        if HEADER.match(lines[i]):
            sender = lines[i].split("-")[1].split(":")[0].strip()
            return sender
        
def parser_wordle_score(msg):
    results = []
    WORDLE = re.compile(
                r"Wordle\s+([\d,\s]+)\s+([1-6X])/6",
                re.I
            )
    for i, line in enumerate(msg):
        res = WORDLE.search(line)

        if not res:
            continue    # Skip lines that don't match the Wordle pattern
        # Find sender in the current line or previous lines
        sender = find_sender(msg, i)
        wordle = int(res.group(1).replace(",", "").strip())
        score = res.group(2).strip()
        results.append((sender, wordle, score))
    return results