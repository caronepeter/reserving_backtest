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

import numpy as np
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


# --- Step 3: estimates ---------------------------------------------------------
#
# 40 estimates per company-AY: CL 6 averages x 2 bases; EC 2 ELRs x 2 bases
# (no factors, so no average); BF 6 averages x 2 ELRs x 2 bases. Every
# projection goes through methods.project, the code reconciled to Excel.

AVG_LABEL = {(kind, n): f"{kind}_{'all' if n is None else n}" for kind, n in m.AVERAGES}
HEADLINE_AVERAGE = "volume_all"  # D3
RESULTS = ROOT / "results"
BASE_COLS = ["age", "paid", "latest", "ep", "cdf"]


def selected_factors(tri, kind, n):
    """One of the 6 averages with the D1 rule.

    ata_factors gives NaN where the lag k cumulative is 0, and average() drops
    NaN factors, so AYs with a zero denominator are already left out of that
    k's average. If no AY is left at some k, average() returns NaN there; D1
    sets that factor to 1.0. Returns the factors and how many were set to 1.0.
    """
    avg = m.average(tri, kind, n)
    return avg.fillna(1.0), int(avg.isna().sum())


def zero_denominators(tri):
    """Known factor cells left out by D1: lag k+1 known and lag k cumulative 0."""
    den = tri.loc[:, :m.TARGET_LAG - 1].to_numpy()
    num = tri.loc[:, 2:].to_numpy()
    return int(((den == 0) & ~np.isnan(num)).sum())


def _rows(proj, lob, g, basis, method, average, elr, est):
    out = proj[BASE_COLS].copy()
    if method == "ec":
        out["cdf"] = np.nan  # expected claims uses no development factors
    out = out.assign(lob=lob, GRCODE=g, basis=basis, method=method,
                     average=average, elr=elr, est=est.to_numpy())
    out["unpaid"] = out.est - out.paid
    return out.rename_axis("AccidentYear").reset_index()


def line_attributes(clean, elrs):
    """One row per (lob, GRCODE, basis): size, AYs present, incomplete,
    single or group, ceded swing (probe 7 definition), zero company ELR (D8)."""
    parts = []
    for lob, df in clean.items():
        ay = m.known(df).drop_duplicates(["GRCODE", "AccidentYear"])
        ay = ay.assign(ratio=(ay.EarnedPremCeded / ay.EarnedPremDIR)
                       .where(ay.EarnedPremDIR != 0))
        g = ay.groupby("GRCODE")
        a = pd.DataFrame({"size_ep": g.EarnedPremNet.mean(), "n_ays": g.size(),
                          "single": g.Single.first(),
                          "ceded_swing": g.ratio.max() - g.ratio.min()})
        a["incomplete"] = a.n_ays < 10
        parts.append(a.reset_index().assign(lob=lob))
    attrs = pd.concat(parts, ignore_index=True)
    flag = elrs.assign(zero_company_elr=elrs.elr_company == 0)
    return flag[["lob", "GRCODE", "basis", "zero_company_elr"]].merge(attrs, on=["lob", "GRCODE"])


def estimates(clean, elrs):
    """Long estimates table (one row per company-AY x combination) and the
    D1 counts (one row per lob x GRCODE x basis x average)."""
    elr = elrs.set_index(["lob", "GRCODE", "basis"])
    parts, d1 = [], []
    for lob, df in clean.items():
        k = m.known(df)
        assert_known(k)
        for g, line in k.groupby("GRCODE"):
            for basis in BASES:
                e = elr.loc[(lob, g, basis)]
                line_elrs = {"company": e.elr_company, "industry": e.elr_industry}
                tri = m.triangle(line, basis)
                n_zero = zero_denominators(tri)
                for i, (kind, n) in enumerate(m.AVERAGES):
                    label = AVG_LABEL[(kind, n)]
                    sel, n_fallback = selected_factors(tri, kind, n)
                    proj = m.project(line, basis, sel, line_elrs)
                    parts.append(_rows(proj, lob, g, basis, "cl", label, None, proj.est_cl))
                    for name in line_elrs:
                        parts.append(_rows(proj, lob, g, basis, "bf", label, name,
                                           proj[f"est_bf_{name}"]))
                        if i == 0:  # EC is the same for every average
                            parts.append(_rows(proj, lob, g, basis, "ec", None, name,
                                               proj[f"est_ec_{name}"]))
                    d1.append({"lob": lob, "GRCODE": g, "basis": basis, "average": label,
                               "zero_den_ays": n_zero, "fallback_factors": n_fallback})
    cols = ["lob", "GRCODE", "basis", "method", "average", "elr", "AccidentYear",
            "age", "ep", "paid", "latest", "cdf", "est", "unpaid"]
    est = pd.concat(parts, ignore_index=True)[cols]
    return est, pd.DataFrame(d1)


def check_estimates(est, clean):
    """Step 3 checks: 40 rows per company-AY, known cells only."""
    n_company_ays = sum(m.known(df).drop_duplicates(["GRCODE", "AccidentYear"]).shape[0]
                        for df in clean.values())
    assert len(est) == 40 * n_company_ays, f"{len(est)} rows, expected 40 x {n_company_ays}"
    per = est.groupby(["lob", "GRCODE", "AccidentYear"]).size()
    assert (per == 40).all(), "a company-AY doesn't have 40 estimates"
    combos = est.drop_duplicates(["basis", "method", "average", "elr"]).groupby("method").size()
    assert combos.to_dict() == {"bf": 24, "cl": 12, "ec": 4}, combos.to_dict()
    assert (est.age <= 120).all() and (est.AccidentYear + est.age / 12 - 1 <= m.VALUATION_YEAR).all()
    return n_company_ays


def build():
    """Steps 2-3: ELRs, estimates, line attributes and D1 counts."""
    clean = load_clean()
    check_premium_constant(clean)
    elrs = elr_table(clean)
    check_elrs(elrs)
    est, d1 = estimates(clean, elrs)
    check_estimates(est, clean)
    est = est.merge(line_attributes(clean, elrs), on=["lob", "GRCODE", "basis"], how="left")
    return clean, elrs, est, d1


if __name__ == "__main__":
    pd.set_option("display.width", 140)
    clean, elrs, est, d1 = build()
    industry, spread, zeros = check_elrs(elrs)
    print("Industry ELRs\n", industry.round(4), "\n")
    print("Company ELRs\n", spread.round(3), "\n")
    print("Company ELR = 0 (D8):", zeros.drop_duplicates(["lob", "GRCODE"]).GRCODE.tolist(), "\n")

    RESULTS.mkdir(exist_ok=True)
    est.to_csv(RESULTS / "estimates.csv", index=False)
    d1.to_csv(RESULTS / "d1_counts.csv", index=False)
    print(f"Estimates: {len(est):,} rows ({len(est) // 40:,} company-AYs x 40) -> results/estimates.csv")
    print("Rows by method:", est.groupby("method").size().to_dict())
    bad = est.est.isna() | np.isinf(est.est)
    print("NaN or infinite estimates:", int(bad.sum()))

    # D1 counts: zero-denominator AY factors left out (per line and basis) and
    # factors set to 1.0 because no AY was left (per line, basis and average)
    z = d1.drop_duplicates(["lob", "GRCODE", "basis"])
    print("\nD1 zero-denominator AY factors left out, by lob x basis:")
    print(z.groupby(["lob", "basis"]).agg(cells=("zero_den_ays", "sum"),
                                          lines=("zero_den_ays", lambda s: (s > 0).sum())))
    print("\nD1 factors set to 1.0 (no AY left), by lob x basis x average:")
    fb = d1[d1.fallback_factors > 0]
    print(fb.groupby(["lob", "basis", "average"]).agg(factors=("fallback_factors", "sum"),
                                                      lines=("GRCODE", "nunique"))
          if len(fb) else "none")
