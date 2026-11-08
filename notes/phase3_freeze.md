# Phase 3 freeze (step 6, 2026-11-08)

Estimates for all 169 clean lines x 40 combinations were built and checked on
known cells only (AY + lag - 1 <= 2007) before any grading code was written.
This commit, tagged `phase3-freeze`, fixes the code that made them. Grading
(notebooks/05_phase3_grade.ipynb) comes after it and is the first Phase 3 code
to read actual development after 2007.

The estimate files are gitignored (D5) and rebuilt by `python3 src/backtest.py`.
Their hashes at the freeze:

| File | Rows | SHA-256 |
|---|---|---|
| results/estimates.csv | 62,320 | 68968d57fd202ebd0c1ee8d764e08a0372dc8ab2c332833b84db738e167c2a2f |
| results/d1_counts.csv | 2,028 | 44e17c2085d928c85b24defafd2fd00df0d00247234537c8d9492c11def86070 |

Built with Python 3.13.18, pandas 3.0.5, numpy 2.5.3. A rebuild with other library
versions can change how floats are written to CSV, and so the hash, without
changing any estimate; compare values if the hash differs.

Checks passed before the freeze (step 5): 40 estimates per company-AY
(1,558 company-AYs); AY 1998 paid CL unpaid = 0; BF identity on all 37,296
checkable BF rows; NaN/inf only WC 26956 reported BF (96 rows, CDF = 0);
D4 common sample PPA 109, WC 59. Tests: 26 pass (tests/).
