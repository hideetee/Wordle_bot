
# ==============================
# SCORING
# ==============================

class Score:
    
    def __init__(self, player, wordle, score):

        # self.date = date
        self.player = player
        self.wordle = wordle
        self.score = score
        

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
        
    # def wordle_week(self, wordle_number, date):
    #     """
    #     Given a Wordle number and its actual date,
    #     return the Sunday–Saturday Wordle range.
    #     """
    #     weekday_index = datetime.strptime(date, "%m/%d/%y").weekday() # Monday=0, Sunday=6
        
    #     sunday_index = (weekday_index + 1) % 7  # Sunday=0, Saturday=6

    #     week_start = wordle_number - sunday_index
    #     week_end = week_start + 6
    #     return week_start, week_end

    @staticmethod
    def wordle_week(wordle_number):
        """
        Computer weekday for a Wordle, given a known Wordle anchor.
        Sunday = 0, Saturday = 6
        """
        wordle_anchor = 1860
        anchor_weekday = 4 # Thursday

        weekday = (anchor_weekday + (wordle_number - wordle_anchor)) % 7

        week_start = wordle_number - weekday
        week_end = week_start + 6

        return week_start, week_end



    @staticmethod
    def weekly_score(scores, week_start, week_end):
        """
        Calculate the total score for a player within a specific Wordle week.
        """
        week_total_score = 0
        for score in scores:
            if week_start <= score.wordle <= week_end:
                week_total_score += score.numeric_score()
        return week_total_score




    def ranking(self):

        '''
        Rank players based on 'wordle' and 'score'
        '''
        
        



    #, with 'X' treated as 7 for ranking purposes
    #    Print raw weekly score, rank, and add raw score to overall score for each player
        



