# ==============================
# SCORING
# ==============================

import re
from turtle import save

import polars as pl
from wordle_bot.parser import parser_wordle_score

class ScoreCalculator:
    
    def __init__(self, player, wordle_num, score):

        # self.date = date
        self.player = str(player)
        self.wordle_num = int(wordle_num)
        self.score = score # contains 'X' for fail, or '1/6', '2/6', etc. for success

    def __repr__(self):
        return f"(player={self.player}, wordle={self.wordle_num}, score={self.score})\n"

    def score_cleaner(self):
        """
        Accepts either a list of ScoreCalculator objects or a polars DataFrame and returns a cleaned polars DataFrame.
        The DataFrame will have columns: player, wordle_num, score.
        Create a polars DataFrame from a list of ScoreCalculator objects
        Convert 'X' to 7 and cast score to Int64 for ranking purposes
        If wordle_num is not complete for a player, populate score with 7
        """

        if isinstance(self, pl.DataFrame):
            return self

        if not self:
            return []  
        
        data = [(score.player, score.wordle_num, score.score) for score in self]
        df = pl.DataFrame(data, schema=["player", "wordle_num", "score"], orient = "row")
        df = df.with_columns(
            pl.when(pl.col("score") == "X")
            .then(7)
            .otherwise(pl.col("score"))
            .alias("score").cast(pl.Int64)
        )

        players = df.select(pl.col("player")).unique()
        wordles = df.select(pl.col("wordle_num")).unique()
        wordles_min = df.select(pl.col("wordle_num")).min().item()
        wordles_max = df.select(pl.col("wordle_num")).max().item()

        # fill all values between min and max wordle_num 
        wordles_fill = pl.DataFrame({"wordle_num": list(range(wordles_min, wordles_max + 1))})

        full_grid = players.join(wordles_fill, how="cross")

        df_fill_incompletes = full_grid.join(
            df, on=["player", "wordle_num"], how="left"
            )

        # Conditional fill with 6 only for wordle_num < max        
        df_fill_incompletes = df_fill_incompletes.with_columns(
            pl.when(pl.col("wordle_num") < wordles_max)
            .then(pl.col("score").fill_null(7))
            .otherwise(pl.col("score"))
            .alias("score")
        )

        df_fill_incompletes = df_fill_incompletes.sort(["wordle_num", "player"])

        return df_fill_incompletes
        

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


        
        


    def sender_tracker(msg):

        """
        Extract the sender's name from a WhatsApp message.
        """

        header_pattern = re.compile(
            f"^\d+/\d+/\d+,\s+\d+:\d+"
        )



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
    def store_week_ranges(df):
        """
        Store the week_ranges for all unique Wordle weeks in a DataFrame that is .
        """

        week_ranges = []

        week_start, week_end = ScoreCalculator.wordle_week(df['wordle_num'].unique()[0])

        week_ranges.append((week_start, week_end))

        wordle_numbers = df['wordle_num'].unique()

        for w_num in wordle_numbers[1:]:
            if w_num > week_end:
                week_start, week_end = ScoreCalculator.wordle_week(w_num)
                week_ranges.append((week_start, week_end))

        return week_ranges
        

    @staticmethod
    def compute_weekly_score(df):
        """
        Calculate the total score for a player within all Wordle weeks.
        """

        weekly_dfs = []
        for week_start, week_end in ScoreCalculator.store_week_ranges(df):
           wordle_week = str(week_start) + '-' + str(week_end)
           df_week = df.filter(
               (pl.col("wordle_num") >= week_start) 
               & (pl.col("wordle_num") <= week_end)
           )
           weekly_dfs.append((df_week, week_start, week_end))


        weekly_scores = []

        for df_week, week_start, week_end in weekly_dfs:
            wordle_week = f"{week_start}-{week_end}"
            weekly_score = df_week.group_by('player').agg(pl.sum('score')).sort('score')
            weekly_score = weekly_score.with_columns(
                            pl.lit(wordle_week).alias("wordle_week")
                        )
            weekly_scores.append(weekly_score)
            

        return weekly_scores




    def week_ranking(df):

  
        weekly_scores = ScoreCalculator.compute_weekly_score(df)

        ranked_weeks = []

        for weekly_score in weekly_scores:

            # competition ranking with mean ranks
            df_ranked  = weekly_score.with_columns(
                pl.arange(1, weekly_score.height +1).alias("raw_rank")
            )

            # compute mean ranks per score group
            df_ranked_grouped = df_ranked.group_by("score").agg(
                pl.col("raw_rank").mean().alias("rank")
            )

            df_final = df_ranked.join(df_ranked_grouped, on="score", how="left").sort("rank")
            df_final = df_final.drop("raw_rank")
            ranked_weeks.append(df_final)

            
        return ranked_weeks

    def running_ranking(weekly_scores, interest="overall_rank"):
        """
        
        weekly_scores: list of polars DataFrames, each representing a week's scores
        returns list of polars DataFrames with an additional column 'overall_rank' and 'overall_score' representing the cumulative rank and score across all weeks
        """

        cumulative_rank = {}
        cumulative_score = {}
        
        ranked_weeks = []

        for week in weekly_scores:
                # Compute this week's rank contribution
                week_rank = (
                    week.group_by("player")
                        .agg(pl.sum("rank").alias("week_rank"))
                )

                # Update cumulative totals
                for row in week_rank.iter_rows(named=True):
                    player = row["player"]
                    cumulative_rank[player] = cumulative_rank.get(player, 0) + row["week_rank"]

                # Compute this week's score contribution
                week_score = (
                    week.group_by("player")
                        .agg(pl.sum("score").alias("week_score"))
                )

                # Update cumulative totals
                for row in week_score.iter_rows(named=True):
                    player = row["player"]
                    cumulative_score[player] = cumulative_score.get(player, 0) + row["week_score"]

                # Convert cumulative dict → Polars DF
                cumulative_df = pl.DataFrame(
                    {"player": list(cumulative_rank.keys()),
                     "overall_rank": list(cumulative_rank.values())}
                )

                cumulative_score_df = pl.DataFrame(
                    {"player": list(cumulative_score.keys()),
                     "overall_score": list(cumulative_score.values())}
                )

                # Join cumulative rank into this week's DF
                week_with_running = (
                    week.join(cumulative_df, on="player", how="left")
                    .join(cumulative_score_df, on="player", how="left")
                    .with_columns([
                          pl.col("overall_rank").cast(pl.Float64), 
                          pl.col("overall_score").cast(pl.Float64)])
                        .sort(interest)
                )

                ranked_weeks.append(week_with_running)
                
        # ranked_weeks[-1] = ranked_weeks[-1].sort(interest)

        return ranked_weeks
    

    def ranking(df):
      
        '''
        Rank players based on overall 'score'
        '''
        return df.group_by("player").agg(
            pl.sum("score").alias("total_score")
        ).sort("total_score")


