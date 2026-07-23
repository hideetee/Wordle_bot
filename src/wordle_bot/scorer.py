
# ==============================
# SCORING
# ==============================

class ScoreCalculator:
    
    def __init__(self, player, wordle_num, score):

        # self.date = date
        self.player = str(player)
        self.wordle_num = int(wordle_num)
        self.score = score # contains 'X' for fail, or '1/6', '2/6', etc. for success

    def __repr__(self):
        return f"(player={self.player}, wordle={self.wordle_num}, score={self.score})\n"
        

    def numeric_score(self):
        """
        Convert raw Wordle score into a numeric value.
        X = 7 
        Otherwise take the number before '/6'
        """

        if self.score == "X":

            return 7

        else:
            return int(self.score)
        

    @staticmethod
    def wordle_week(wordle_num):
        """
        Computer weekday for a Wordle, given a known Wordle anchor.
        Sunday = 0, Saturday = 6
        """
        wordle_anchor = 1860
        anchor_weekday = 4 # Thursday

        weekday = (anchor_weekday + (wordle_num - wordle_anchor)) % 7

        week_start = int(wordle_num - weekday)
        week_end = int(week_start + 6)

        return week_start, week_end


    @staticmethod
    def store_week_scores(scores, wordle_num):
        """
        Store the scores for a specific Wordle week.
        """

        scores = ScoreCalculator.numeric_score(scores)  
        week_start, week_end = ScoreCalculator.wordle_week(wordle_num)
        
        return [s for s in scores if week_start <= s.wordle_num <= week_end]
        

    @staticmethod
    def weekly_score(scores, wordle_num):
        """
        Calculate the total score for a player within a specific Wordle week.
        """
        week_total_score = 0

        week_start, week_end = ScoreCalculator.wordle_week(wordle_num)

        for score in scores:
            if week_start <= score.wordle_num <= week_end:
                week_total_score += score
        return week_total_score




    def ranking(self):

        '''
        Rank players based on 'wordle' and 'score'
        '''
        
        



    #, with 'X' treated as 7 for ranking purposes
    #    Print raw weekly score, rank, and add raw score to overall score for each player
        



