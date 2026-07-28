import sqlite3

from wordle_bot.scorer import ScoreCalculator
from wordle_bot.scorer import ScoreCalculator as SC
import polars as pl

class Database_wordle:
    def __init__(self, database_path):
        self.conn = sqlite3.connect(
            database_path,
            check_same_thread=False
        )
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS scores (
                player TEXT,
                wordle INTEGER,
                score INTEGER,
                PRIMARY KEY(player, wordle)
            )
            """
        )
        self.conn.commit()

    def save_score(self, player, wordle, score):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO scores (player, wordle, score)
            VALUES (?, ?, ?)
            """,
            (player, wordle, score)
        )
        self.conn.commit()

    

    def save_score_if_missing_or_7(self, df):

        # # make sure scores are int or None
        df = df.with_columns(
            pl.col("score").cast(pl.Int64)
        )

        cursor = self.conn.cursor()

        inserted_lines = 0
        updated_lines = 0.
        existing_lines = 0

        for row in df.to_dicts():

            player = row["player"]
            wordle = row["wordle_num"]
            score = row["score"]

            # check existing score for each player and wordle
            cursor.execute(
                """
                SELECT score 
                FROM scores 
                WHERE player = ? AND wordle = ?
                """,

                (player, wordle)
            )
            existing = cursor.fetchone()

            if existing is None:
                # Insert the new score if it doesn't exist
                self.save_score(player, wordle, score)
                inserted_lines += 1
                continue

            existing_score = existing[0]

            if existing_score == None:
                # Update the score if the existing score is None
                self.save_score(player, wordle, score)
                updated_lines += 1
            else:
                existing_lines += 1

        print(f"Inserted lines: {inserted_lines}, Updated lines: {updated_lines}, Existing lines: {existing_lines}")
        




    def load_scores(self, wordle_num=None, wordle_min=None, wordle_max=None):

        cursor = self.conn.cursor()

        if wordle_min is not None and wordle_max is not None:
            cursor.execute(
                "SELECT player, wordle, score FROM scores WHERE wordle BETWEEN ? AND ?",
                (wordle_min, wordle_max)
            )
        elif wordle_min is not None:
            cursor.execute(
                "SELECT player, wordle, score FROM scores WHERE wordle >= ?",
                (wordle_min,)
            )
        elif wordle_max is not None:
            cursor.execute(
                "SELECT player, wordle, score FROM scores WHERE wordle <= ?",
                (wordle_max,)
            )
        elif wordle_num is not None:
            cursor.execute(
                "SELECT player, wordle, score FROM scores WHERE wordle = ?", 
                (wordle_num,)
            )
        else:
            cursor.execute("SELECT player, wordle, score FROM scores")

        rows = cursor.fetchall()
        

        scores = [
            SC(
                player=row[0], 
                wordle_num=row[1],
                score=row[2] 
                )
            for row in rows
        ]

        data = [(score.player, score.wordle_num, score.score) for score in scores]
        df = pl.DataFrame(data, schema=["player", "wordle_num", "score"], orient = "row").sort(by=["wordle_num", "player"])

        return df

    def save_weekly_scores(conn, weekly_scores):

        """
        Save a list of weekly scores to the database.
        """

        cursor = conn.cursor()
        for i, week_df in enumerate(weekly_scores):
            table_name = f"week_{i}"
    
            week_df.write_database(
                table_name=table_name,
                connection=conn,
                if_table_exists="replace"
            )
    
            print(f"Saved {table_name} to database.")
        conn.commit()

    def save_leaderboard(self,leaderboard_df):

            """
            Save a leaderboard DataFrame to the database.
            """
    
            cursor = self.conn.cursor()
    
    
            cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS leaderboard (
                player TEXT,
                score INTEGER,
                week_start INTEGER,
                week_end INTEGER,
                rank INTEGER,
                overall_rank INTEGER,
                overall_score REAL,
                PRIMARY KEY(player, week_start, week_end)
            )
            """)

            for row in leaderboard_df.to_dicts():
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO leaderboard (player, week_start, week_end, score, rank, overall_rank, overall_score)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (row['player'], row['week_start'], row['week_end'], row['score'], row['rank'], row['overall_rank'], row['overall_score'])
                )
            self.conn.commit()

    def load_leaderboard(self, wordle_num=None, week_start=None, week_end=None):
    
            cursor = self.conn.cursor()
    
            if week_start is not None and week_end is not None:
                cursor.execute(
                    """
                    SELECT player, week_start, week_end, score, rank, overall_rank, overall_score 
                    FROM leaderboard 
                    WHERE week_start >= ? AND week_end <= ?""",
                    (week_start, week_end)
                )
            elif week_start is not None:
                cursor.execute(
                    """
                    SELECT player, week_start, week_end, score, rank, overall_rank, overall_score 
                    FROM leaderboard 
                    WHERE week_start >= ?""",
                    (week_start,)
                )
            elif week_end is not None:
                cursor.execute(
                    """
                    SELECT player, week_start, week_end, score, rank, overall_rank, overall_score 
                    FROM leaderboard 
                    WHERE week_end <= ?""",
                    (week_end,)
                )
            elif wordle_num is not None:
                cursor.execute(
                    """
                    SELECT player, week_start, week_end, score, rank, overall_rank, overall_score 
                    FROM leaderboard 
                    WHERE week_start >= ? AND week_end <= ?""",
                    (wordle_num, wordle_num)
                )
            else:
                cursor.execute("SELECT player, week_start, week_end, score, rank, overall_rank, overall_score FROM leaderboard")

            rows = cursor.fetchall()
            
    
            data = [(row[0], row[1], row[2], row[3], row[4], row[5], row[6]) for row in rows]
            df = pl.DataFrame(data, schema=["player", "week_start", "week_end", "score", "rank", "overall_rank", "overall_score"], orient = "row")
    
            return df