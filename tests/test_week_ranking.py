from wordle_bot.scorer import ScoreCalculator as SC
import polars as pl
import polars.testing as pt


def test_week_ranking_complete_week():
    """
    Test the week_ranking function of ScoreCalculator.
    """
    ## Arrange ##
    scores_df = pl.DataFrame({
        "player": ["Alice", "Bob", "Alice", "Bob", "Alice", "Bob", "Alice", "Bob", "Alice", "Bob", "Alice", "Bob", "Alice", "Bob"],
        "wordle_num": [1870, 1870, 1871, 1871, 1872, 1872, 1873, 1873, 1874, 1874, 1875, 1875, 1876, 1876],
        "score": [3, 4, 5, 2, 3, 4, 1, 2, 3, 2, 1, 2, 3, 4]
    })



    ## Act ##
    week_ranks = SC.week_ranking(scores_df)

    ## Assert ##

    week_ranks_expected = pl.DataFrame({
        "player": ["Alice", "Bob"],
        "score": [19, 20],
        "week_start": [1870, 1870],
        "week_end": [1876, 1876],
        "rank": [1.0, 2.0]
    })

    pt.assert_frame_equal(week_ranks[-1], week_ranks_expected)

def test_week_ranking_incomplete_week():
    """
    Test the week_ranking function of ScoreCalculator with an incomplete week.
    """
    ## Arrange ##
    scores_df = pl.DataFrame({
        "player": ["Alice", "Bob", "Alice", "Bob", "Alice", "Bob", "Alice", "Bob"],
        "wordle_num": [1870, 1870, 1871, 1871, 1872, 1872, 1873, 1873],
        "score": [3, 4, 5, 2, 3, 4, 1, 2]
    })
    ## Act ##
    week_ranks = SC.week_ranking(scores_df)
    ## Assert ##
    # Since the last week is incomplete (missing days), it should not be included in the ranking.
    assert week_ranks == []