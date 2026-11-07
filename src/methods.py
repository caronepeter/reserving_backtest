"""Phase 2 step 7: reserving methods on one company-line, built to match the
Phase 2 Excel workbook (excel/wc_23663.xlsx) cell for cell.

Everything is measured to 120 months (lag 10), not ultimate: CDFs carry no
tail unless one is passed (only the Friedland test does). Amounts are $000.

Basis: "paid" = CumPaidLoss; "reported" = IncurredLosses - BulkLoss (paid + case).
Unpaid on both bases = estimated losses at 120 - paid to date, so the reported
basis includes case still open at 120 (Phase 2 decision, 2026-11-04).

Layout: a triangle is a DataFrame, index = AccidentYear, columns = lag 1..10,
NaN where the cell is hidden (AY + lag - 1 > 2007) or the AY is missing.
Factor k is lag k -> k+1 (Excel's "12--24" is k = 1).

Usage (one company-line):
    line = wc_clean[wc_clean.GRCODE == 23663]
    elrs = {"company": elr_company(line, "paid"),
            "industry": elr_industry(wc_clean, "paid")}
    sel = {1: 2.211, 2: 1.256, ...}            # or average(tri, "volume", 3)
    out = project(line, "paid", sel, elrs)
"""
import numpy as np
import pandas as pd

VALUATION_YEAR = 2007
FIRST_AY = 1998
TARGET_LAG = 10  # 120 months

# The 6 averages, in the Excel row order (Part 3, rows 32-37).
AVERAGES = [
    ("simple", None), ("simple", 5), ("simple", 3),
    ("volume", None), ("volume", 5), ("volume", 3),
]


# --- Data -> triangles -------------------------------------------------------

def known(df):
    """Known cells only: AY + lag - 1 <= 2007. Every function below that reads
    loss data goes through this, so hidden cells never enter an estimate."""
    return df[df.AccidentYear + df.DevelopmentLag - 1 <= VALUATION_YEAR]


def _values(df, basis):
    if basis == "paid":
        return df.CumPaidLoss
    if basis == "reported":
        return df.IncurredLosses - df.BulkLoss
    raise ValueError(f"basis must be 'paid' or 'reported', got {basis!r}")


def triangle(line, basis):
    """Cumulative triangle for one company-line (Excel Part 1)."""
    k = known(line)
    tri = (k.assign(v=_values(k, basis))
             .pivot(index="AccidentYear", columns="DevelopmentLag", values="v"))
    return tri.reindex(columns=range(1, TARGET_LAG + 1)).astype(float)


def premium(line):
    """Net earned premium, one value per AY (the lag 1 row, as in Excel)."""
    k = known(line)
    return k[k.DevelopmentLag == 1].set_index("AccidentYear").EarnedPremNet.astype(float)


def latest(tri):
    """Latest diagonal: for each AY, its last known lag and value."""
    lag = tri.notna().iloc[:, ::-1].idxmax(axis=1)
    value = pd.Series([tri.at[ay, l] for ay, l in lag.items()], index=tri.index)
    return pd.DataFrame({"lag": lag, "value": value})


# --- Factors, averages, CDFs ---------------------------------------------------

def ata_factors(tri):
    """Age-to-age factors (Excel Part 2): lag k+1 / lag k, k = 1..9.
    A zero denominator gives NaN (undefined), not inf."""
    num = tri.loc[:, 2:].to_numpy()
    den = tri.loc[:, :TARGET_LAG - 1].to_numpy()
    with np.errstate(divide="ignore", invalid="ignore"):
        f = np.where(den != 0, num / den, np.nan)
    return pd.DataFrame(f, index=tri.index, columns=range(1, TARGET_LAG))


def average(tri, kind, n=None):
    """Average age-to-age factor per k (Excel Part 3).

    kind: "simple" (mean of the factors) or "volume" (sum of lag k+1 over
    sum of lag k, same AYs). n: latest n AYs with a factor; None = all.
    Fewer than n factors -> uses all there are (Excel's MAX(1, c - n + 1)).
    """
    f = ata_factors(tri)
    out = {}
    for k in f.columns:
        ays = f[k].dropna().index.sort_values()
        if n is not None:
            ays = ays[-n:]
        if len(ays) == 0:
            out[k] = np.nan
        elif kind == "simple":
            out[k] = f.loc[ays, k].mean()
        elif kind == "volume":
            out[k] = tri.loc[ays, k + 1].sum() / tri.loc[ays, k].sum()
        else:
            raise ValueError(f"kind must be 'simple' or 'volume', got {kind!r}")
    return pd.Series(out, name=f"{kind} {'all' if n is None else f'latest {n}'}")


def cdfs(selected, tail=1.0):
    """CDF to 120 at each lag (Excel Part 4: PRODUCT(k:J)), times an optional
    tail. Lag 10 gets the tail alone (1.0 in this project)."""
    sel = pd.Series(selected, dtype=float).reindex(range(1, TARGET_LAG))
    if sel.isna().any():
        raise ValueError(f"missing selected factors at k = {sel[sel.isna()].index.tolist()}")
    out = sel[::-1].cumprod()[::-1] * tail
    out[TARGET_LAG] = tail
    return out.sort_index()


# --- Expected loss ratios ----------------------------------------------------

def elr_company(line, basis):
    """First AY's loss ratio at 120 months (AY 1998 lag 10 = 2007, known)."""
    tri = triangle(line, basis)
    return tri.at[FIRST_AY, TARGET_LAG] / premium(line)[FIRST_AY]


def elr_industry(all_lines, basis):
    """AY 1998 at 120, premium-weighted across every line passed in:
    sum of losses / sum of net EP."""
    a = known(all_lines)
    a = a[(a.AccidentYear == FIRST_AY) & (a.DevelopmentLag == TARGET_LAG)]
    return _values(a, basis).sum() / a.EarnedPremNet.sum()


# --- Projections -------------------------------------------------------------

def project(line, basis, selected, elrs):
    """All methods for one company-line on one basis (Excel Projections sheet).

    selected: factor per k = 1..9 (judgment picks or an average()).
    elrs: dict of name -> ELR, e.g. {"company": 0.84, "industry": 0.64}.

    Returns one row per AY with each method's estimate at 120 (est_*) and
    unpaid (unpaid_* = est_* - paid to date). Expected claims unpaid can be
    negative (paid already above ELR x EP); it is left as is.
    """
    tri = triangle(line, basis)
    paid = latest(triangle(line, "paid"))["value"]
    lat = latest(tri)
    ep = premium(line)
    cdf = cdfs(selected)

    out = pd.DataFrame({
        "age": lat["lag"] * 12,
        "paid": paid,
        "latest": lat["value"],
        "ep": ep,
        "cdf": lat["lag"].map(cdf),
    })
    out["est_cl"] = out.latest * out.cdf
    for name, elr in elrs.items():
        expected = elr * out.ep
        out[f"est_ec_{name}"] = expected
        out[f"est_bf_{name}"] = out.latest + expected * (1 - 1 / out.cdf)
    for col in [c for c in out.columns if c.startswith("est_")]:
        out["unpaid_" + col[4:]] = out[col] - out.paid
    return out


def totals(proj):
    """Total unpaid per method (Excel row 18)."""
    return proj.filter(like="unpaid_").sum()


# --- Grading (step 10 only) --------------------------------------------------

def actual_at_120(line, basis):
    """Actual losses at 120 per AY. READS HIDDEN CELLS: call only at the
    reveal, after the freeze commit."""
    a = line[line.DevelopmentLag == TARGET_LAG].set_index("AccidentYear")
    return _values(a, basis).astype(float)


def grade(est_unpaid, actual_unpaid, ep):
    """Error on the reserve, both scales, per AY (Series aligned on AY).

    pct_reserve = (est - actual) / actual unpaid; NaN where actual is 0
    (AY 1998 on the paid basis). pct_ep = (est - actual) / EP.
    """
    err = est_unpaid - actual_unpaid
    pct_reserve = err / actual_unpaid.where(actual_unpaid != 0)
    return pd.DataFrame({"est": est_unpaid, "actual": actual_unpaid, "error": err,
                         "pct_reserve": pct_reserve, "pct_ep": err / ep})
