import pathlib
import sys

import numpy as np
import pandas as pd
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import analyse  # noqa: E402
import parse  # noqa: E402
import score  # noqa: E402

LEX = score.load_lexicon()


def test_negation_flips_direction():
    pos = score.score_text("There was evidence of knock-on effects on prices.", LEX)
    neg = score.score_text("There was limited evidence of knock-on effects on prices.", LEX)
    assert pos["hawk_hits"] == 1 and pos["dove_hits"] == 0
    assert neg["hawk_hits"] == 0 and neg["dove_hits"] == 1 and neg["negated_hits"] == 1


def test_longest_match_consumes_tokens():
    r = score.score_text("Activity was weaker than expected.", LEX)
    assert r["dove_hits"] == 1  # 'weaker than expected' only, not also 'weak*'


def test_length_normalisation():
    a = score.score_text("Inflation persistence. " + "filler " * 98, LEX)
    assert a["n_words"] == 100 and a["score_per_1k"] == pytest.approx(10.0)


def test_decision_parse_majority_and_size():
    s = ("At its meeting ending on 4 November 2026, the Monetary Policy Committee (MPC) voted by a "
         "majority of 8-1 to increase Bank Rate by 0.25 percentage points, to 4%.")
    d = parse.parse_decision(s)
    assert d["decision_bp"] == 25 and d["rate_after"] == 4 and d["majority"] == 8 and d["n_dissent"] == 1


def test_dissent_parse_split_votes():
    v = ("Three members voted against the proposition. Two members (Swati Dhingra and Silvana Tenreyro) "
         "preferred to maintain Bank Rate at 3%. Catherine L Mann preferred to increase Bank Rate by "
         "0.75 percentage points, to 3.75%.")
    assert sorted(parse.parse_dissents(v, 50)) == [(1, 75.0), (2, 0.0)]
    v2 = "Jon Cunliffe voted against the proposition, preferring to maintain Bank Rate at 0.5%."
    assert parse.parse_dissents(v2, 25) == [(1, 0.0)]


def test_ols_recovers_known_slope():
    x = np.arange(50, dtype=float)
    df = pd.DataFrame({"x": x, "y": 2.0 + 3.0 * x})
    r = analyse.ols("y", ["x"], df)
    assert r["coef"] == pytest.approx(3.0) and r["r2"] == pytest.approx(1.0) and r["n"] == 50


@pytest.mark.skipif(not (ROOT / "data/processed/meetings.csv").exists(), reason="run pipeline first")
def test_parsed_votes_consistent_with_headline_and_rate_path():
    m = pd.read_csv(ROOT / "data/processed/meetings.csv")
    assert len(m) >= 70
    assert m.vote_check_ok.all() and m.rate_check_ok.all()
    assert ((m.n_hike + m.n_hold + m.n_cut) == 9).all()
