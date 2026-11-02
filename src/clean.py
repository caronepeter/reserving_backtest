"""Phase 1 step 7: apply the cleaning rules in docs/cleaning_rules.md.

Each drop rule looks at known cells only (DevelopmentYear <= 2007) and returns
the GRCODEs to drop. Rules run in order 1, 2, 4; each one sees only the lines
the earlier rules kept, which is how the step 5 counts were made.
Rules 3 and 5-8 are notes: they drop nothing, so they have no code here.

Usage (one line of business at a time):
    clean, counts, dropped = apply_rules(ppa, "PPA")
    check_counts(counts, "PPA")
"""
import pandas as pd

VALUATION_YEAR = 2007
FIRST_AY = 1998  # its reserve is zero at 12/31/2007, so it isn't graded


def split_known(df):
    """Known cells: AY + lag - 1 <= 2007, i.e. DevelopmentYear <= 2007."""
    return df[df.DevelopmentYear <= VALUATION_YEAR]


# --- Drop rules: each takes known cells, returns a set of GRCODEs to drop ---

def rule1_zero_paid(known):
    """No paid losses in any known cell."""
    nonzero = (known.CumPaidLoss != 0).groupby(known.GRCODE).sum()
    return set(nonzero[nonzero == 0].index)


def rule2_premium(known):
    """Net earned premium <= 0 in any accident year."""
    min_prem = (known.drop_duplicates(["GRCODE", "AccidentYear"])
                .groupby("GRCODE").EarnedPremNet.min())
    return set(min_prem[min_prem <= 0].index)


def rule4_negative_case(known):
    """Any known cell with a real negative case reserve (<= -2, below that is
    $000 rounding) larger than 10% of paid."""
    k = known.assign(case=known.IncurredLosses - known.BulkLoss - known.CumPaidLoss)
    bad = ((k.case <= -2) & (-k.case > 0.1 * k.CumPaidLoss)).groupby(k.GRCODE).any()
    return set(bad[bad].index)


RULES = [
    ("Rule 1: zero paid", rule1_zero_paid),
    ("Rule 2: net premium <= 0", rule2_premium),
    ("Rule 4: negative case > 10% of paid", rule4_negative_case),
]


def graded_ays(df):
    """Company-AYs that get a grade: every AY present except 1998."""
    ays = df.loc[df.AccidentYear > FIRST_AY, ["GRCODE", "AccidentYear"]]
    return len(ays.drop_duplicates())


def apply_rules(full, line):
    """Apply the drop rules in order to one line's full data (known + hidden).

    Returns:
        clean   - rows for the lines that survive every rule
        counts  - one row per step: lines dropped, lines left, graded AYs left
        dropped - one row per dropped line: GRCODE, GRNAME, rule
    """
    kept = full
    counts = [{"line": line, "step": "Start", "dropped": 0,
               "lines_left": kept.GRCODE.nunique(), "graded_ays": graded_ays(kept)}]
    dropped = []

    for name, rule in RULES:
        drop = rule(split_known(kept))
        names = (kept[kept.GRCODE.isin(drop)]
                 .drop_duplicates("GRCODE")
                 .set_index("GRCODE")
                 .get("GRNAME", pd.Series(dtype=object)))
        for g in sorted(drop):
            dropped.append({"line": line, "GRCODE": g,
                            "GRNAME": names.get(g, ""), "rule": name})
        kept = kept[~kept.GRCODE.isin(drop)]
        counts.append({"line": line, "step": name, "dropped": len(drop),
                       "lines_left": kept.GRCODE.nunique(),
                       "graded_ays": graded_ays(kept)})

    return kept, pd.DataFrame(counts), pd.DataFrame(dropped)


# Counts from step 5 (notebook probes). If apply_rules disagrees, either the
# probes or this code has a bug; find out which before going on.
EXPECTED = {
    "PPA": {"lines_left": [143, 135, 113, 109], "final_graded_ays": 915},
    "WC":  {"lines_left": [132, 106, 63, 60],   "final_graded_ays": 474},
}


def check_counts(counts, line):
    exp = EXPECTED[line]
    got = counts.lines_left.tolist()
    assert got == exp["lines_left"], f"{line} lines left {got}, expected {exp['lines_left']}"
    final = counts.graded_ays.iloc[-1]
    assert final == exp["final_graded_ays"], f"{line} graded AYs {final}, expected {exp['final_graded_ays']}"
    print(f"{line}: counts match step 5 ({got[-1]} lines, {final} graded company-AYs)")
