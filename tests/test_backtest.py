"""Phase 3 step 4: tests for src/backtest.py.

1. 23663 regression: the batch pipeline reproduces Phase 2 for GRCODE 23663
   (chain ladder under each of the 6 averages, notebooks/04_phase2_reveal.ipynb
   10.4; expected claims totals, Excel Projections sheets row 18).
2. D1 rule: zero-denominator AYs left out of the average; factor 1.0 when none left.
3. Latest n with a gap: "latest 3" means the latest 3 AYs that have a factor.
4. Incomplete line: dropping a line's latest AYs leaves every present AY's
   estimates unchanged (cleaning rule 6's argument).
5. ELRs: step 2 checks (counts, Phase 2 values, EP constant across lags).

Needs data/clean (rebuilt by src/clean.py). Run from the repo root:
    pytest tests
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import backtest as bt  # noqa: E402
from src import methods as m  # noqa: E402

GRADED = range(1999, 2008)


@pytest.fixture(scope="module")
def clean():
    return bt.load_clean()


@pytest.fixture(scope="module")
def elrs(clean):
    return bt.elr_table(clean)


@pytest.fixture(scope="module")
def est_23663(clean, elrs):
    wc = clean["WC"]
    est, _ = bt.estimates({"WC": wc[wc.GRCODE == 23663]}, elrs)
    return est


# --- 1. 23663 regression --------------------------------------------------------

# Chain ladder total unpaid, AYs 1999-2007 ($000, printed whole), Phase 2 10.4
PHASE2_CL = {
    "paid": {"simple_all": 14971, "simple_5": 13721, "simple_3": 13606,
             "volume_all": 14006, "volume_5": 12782, "volume_3": 13356},
    "reported": {"simple_all": 23068, "simple_5": 20983, "simple_3": 18358,
                 "volume_all": 22119, "volume_5": 20635, "volume_3": 18119},
}

# Expected claims total unpaid, all AYs incl. 1998 ($000), Excel row 18
PHASE2_EC = {("paid", "company"): 44539, ("paid", "industry"): 10408,
             ("reported", "company"): 49188, ("reported", "industry"): 17237}


@pytest.mark.parametrize("basis", ["paid", "reported"])
@pytest.mark.parametrize("average", list(PHASE2_CL["paid"]))
def test_23663_chain_ladder(est_23663, basis, average):
    cl = est_23663[(est_23663.method == "cl") & (est_23663.basis == basis)
                   & (est_23663.average == average)].set_index("AccidentYear")
    assert abs(cl.loc[GRADED, "unpaid"].sum() - PHASE2_CL[basis][average]) <= 0.5


@pytest.mark.parametrize("basis,elr", list(PHASE2_EC))
def test_23663_expected_claims(est_23663, basis, elr):
    ec = est_23663[(est_23663.method == "ec") & (est_23663.basis == basis)
                   & (est_23663.elr == elr)]
    assert abs(ec.unpaid.sum() - PHASE2_EC[(basis, elr)]) <= 0.5


def test_23663_shape(est_23663):
    assert len(est_23663) == 10 * 40
    assert est_23663.est.notna().all() and np.isfinite(est_23663.est).all()


# --- 2. D1 rule ----------------------------------------------------------------

def _tri(rows):
    """Triangle from {AY: [lag 1, lag 2, ...]}, padded to 10 lags."""
    return pd.DataFrame({ay: v + [np.nan] * (10 - len(v)) for ay, v in rows.items()},
                        index=range(1, 11)).T.astype(float)


def test_d1_zero_denominator_left_out():
    # k = 1: AY 2000 goes 0 -> 50 (infinite ratio), left out of the average
    tri = _tri({1998: [100, 150] + [150] * 8, 1999: [100, 130] + [130] * 7, 2000: [0, 50]})
    sel, n_fallback = bt.selected_factors(tri, "volume", None)
    assert sel[1] == pytest.approx((150 + 130) / (100 + 100))
    sel, _ = bt.selected_factors(tri, "simple", None)
    assert sel[1] == pytest.approx((1.5 + 1.3) / 2)
    assert n_fallback == 0
    assert bt.zero_denominators(tri) == 1


def test_d1_no_ay_left_gives_one():
    # k = 9 comes only from AY 1998, whose lag 9 is 0: no factor left -> 1.0
    tri = _tri({1998: [10, 20, 20, 20, 20, 20, 20, 20, 0, 5], 1999: [10, 20] + [20] * 7})
    sel, n_fallback = bt.selected_factors(tri, "volume", None)
    assert sel[9] == 1.0 and n_fallback == 1
    assert not sel.isna().any()


# --- 3. Latest n with a gap ----------------------------------------------------

def test_latest_n_skips_gap():
    # k = 1 factors: 1998 2.0, 1999 1.5, 2000 left out (0 denominator), 2001 1.2,
    # 2002 1.1. Latest 3 = 2002, 2001, 1999 (2000 has no factor).
    tri = _tri({1998: [10, 20] + [20] * 8, 1999: [10, 15] + [15] * 7, 2000: [0, 5] + [5] * 6,
                2001: [10, 12] + [12] * 5, 2002: [10, 11] + [11] * 4})
    sel, _ = bt.selected_factors(tri, "simple", 3)
    assert sel[1] == pytest.approx((1.1 + 1.2 + 1.5) / 3)


# --- 4. Incomplete line ----------------------------------------------------------

def test_incomplete_line_present_ays_unchanged(clean, elrs):
    wc = clean["WC"]
    full = wc[wc.GRCODE == 23663]
    cut = full[full.AccidentYear <= 2005]  # as if it stopped filing after AY 2005
    keys = ["basis", "method", "average", "elr", "AccidentYear"]
    a, _ = bt.estimates({"WC": full}, elrs)
    b, _ = bt.estimates({"WC": cut}, elrs)
    merged = a.merge(b, on=keys, suffixes=("_full", "_cut"))
    assert len(merged) == 8 * 40  # AYs 1998-2005 present in both
    assert np.allclose(merged.est_full, merged.est_cut, rtol=0, atol=1e-9)


# --- 5. ELRs ---------------------------------------------------------------------

def test_elrs(clean, elrs):
    bt.check_premium_constant(clean)
    bt.check_elrs(elrs)
