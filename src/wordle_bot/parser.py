import re


# ==============================
# WORDLE PARSER
# ==============================


class WordleParser:

    # initialize a class variable to keep track of the number of Wordle scores parsed
    def __init__(self):
        self.wordle_tally = 0

        self.pattern = re.compile(
            r"Wordle\s+([\d,\s]+)\s+([1-6X])/6",
            re.I
        )

    def parse(self, message):

        result = self.pattern.search(message)

        
        if result:
            self.wordle_tally += 1

            return {

                "wordle":
                    int(result.group(1).replace(",", "").strip()),


                "score":
                    result.group(2)

                

            }


        return None


    @staticmethod
    def find_sender(lines, index):
        """
        If sender is not found in the current line, walk backwards to find the most recent sender in the previous lines.
        """
        HEADER = re.compile(r"^\d{1,2}/\d{1,2}/\d{2}, ")
        for i in range(index, -1, -1):

            if HEADER.match(lines[i]):
                sender = lines[i].split("-")[1].split(":")[0].strip()
                return sender

    @staticmethod
    def parser_wordle_score(msg):
        results = []
        WORDLE = re.compile(r"Wordle\s+([\d,\s]+)\s+([1-6X])/6", re.I)
        for i, line in enumerate(msg):
            res = WORDLE.search(line)
    
            if not res:
                continue    # Skip lines that don't match the Wordle pattern
            # Find sender in the current line or previous lines
            sender = WordleParser.find_sender(msg, i)
            wordle = int(res.group(1).replace(",", "").strip())
            score = res.group(2).strip()
            results.append((sender, wordle, score))
        return results


# Module-level convenience aliases
parser_wordle_score = WordleParser.parser_wordle_score
parse_wordle_score = WordleParser.parser_wordle_score