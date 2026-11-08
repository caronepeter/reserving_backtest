"""Phase 3: every method on every clean line (src/backtest.py).

Step 2: ELRs from known cells, using methods.elr_company / elr_industry
(the Phase 2 definitions, reconciled to Excel):
  company  = AY 1998 losses at lag 10 / AY 1998 net EP, per line and basis
  industry = sum of those losses / sum of those EPs over all clean lines in
             a line of business, per basis (4 total; decision D2)
Step 3 (estimates) is added below this section.
"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src import methods as m  # noqa: E402

LINES = {"PPA": "ppa_clean.csv", "WC": "wc_clean.csv"}
BASES = ["paid", "reported"]
N_LINES = {"PPA": 109, "WC": 60}


def load_clean():
    """Clean rows per line of business (data/clean, rebuilt by src/clean.py)."""
    return {lob: pd.read_csv(ROOT / "data" / "clean" / f) for lob, f in LINES.items()}


def assert_known(df):
    """Leakage guard: fail if any cell after 2007 is present."""
    assert (df.AccidentYear + df.DevelopmentLag - 1 <= m.VALUATION_YEAR).all(), \
        "input contains cells after 2007"


def elr_table(clean):
    """Long table: lob, GRCODE, basis, elr_company, elr_industry.

    Keyed on (lob, GRCODE): a company can appear in both lines.
    Only known cells are passed in, so the ELRs can't see hidden data.
    """
    rows = []
    for lob, df in clean.items():
        k = m.known(df)
        assert_known(k)
        industry = {b: m.elr_industry(k, b) for b in BASES}
        for g, line in k.groupby("GRCODE"):
            for b in BASES:
                rows.append({"lob": lob, "GRCODE": g, "basis": b,
                             "elr_company": m.elr_company(line, b),
                             "elr_industry": industry[b]})
    return pd.DataFrame(rows)


def check_premium_constant(clean):
    """elr_company takes EP from the lag 1 row; elr_industry from the lag 10
    row. They agree only if EP is the same at every lag of an AY."""
    for lob, df in clean.items():
        n = m.known(df).groupby(["GRCODE", "AccidentYear"]).EarnedPremNet.nunique()
        assert (n == 1).all(), f"{lob}: EP varies across lags in {(n > 1).sum()} AYs"


def check_elrs(elrs):
    """Step 2 checks; returns the tables to read."""
    for lob, n in N_LINES.items():
        got = (elrs.lob == lob).sum()
        assert got == 2 * n, f"{lob}: {got} rows, expected {2 * n}"
    assert elrs.elr_company.notna().all(), "NaN company ELR"

    # Phase 2 values (rounded to 0.01%): GRCODE 23663 and WC industry
    wc = elrs[elrs.lob == "WC"].set_index(["GRCODE", "basis"])
    phase2 = {("company", "paid"): (wc.loc[(23663, "paid"), "elr_company"], 0.8406),
              ("company", "reported"): (wc.loc[(23663, "reported"), "elr_company"], 0.8677),
              ("industry", "paid"): (wc.loc[(23663, "paid"), "elr_industry"], 0.6419),
              ("industry", "reported"): (wc.loc[(23663, "reported"), "elr_industry"], 0.6816)}
    for key, (got, want) in phase2.items():
        assert abs(got - want) < 5e-5, f"WC {key}: {got:.6f} vs Phase 2 {want}"

    industry = elrs.drop_duplicates(["lob", "basis"]).set_index(["lob", "basis"]).elr_industry
    spread = elrs.groupby(["lob", "basis"]).elr_company.describe(percentiles=[.1, .25, .5, .75, .9])
    zeros = elrs[elrs.elr_company <= 0]
    return industry, spread, zeros


if __name__ == "__main__":
    clean = load_clean()
    check_premium_constant(clean)
    elrs = elr_table(clean)
    industry, spread, zeros = check_elrs(elrs)
    pd.set_option("display.width", 140)
    print("Industry ELRs\n", industry.round(4), "\n")
    print("Company ELRs\n", spread.round(3), "\n")
    print("Company ELR <= 0:", len(zeros))
    print(zeros.to_string() if len(zeros) else "")
