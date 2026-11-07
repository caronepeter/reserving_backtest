# Reserving Backtest: How Accurate Are Basic Reserving Methods on Real Insurers?

> Status: Phase 1 (data) and Phase 2 (one company by hand) complete. Phase 3 (all companies) next. The question, target and scoring rules below were set **before** any estimates were made, so the design can't be tuned to the results.

## Research question

How accurate are basic reserving methods on real insurers, and what drives the errors when they miss?

I run paid and reported chain ladder, the expected claims method and Bornhuetter-Ferguson on every company-line that passes the cleaning rules (109 PPA, 60 WC), using only the data available at 12/31/2007. Then I grade every estimate against how the losses actually developed over the next 10 years.

Specific questions:
1. Which method is most accurate on total reserves, by line?
2. How does error change with accident-year maturity?
3. Paid vs reported basis: which is more accurate, and does the answer differ between PPA and WC?
4. Which development-factor averaging method works best?
5. How sensitive is BF to the choice of expected loss ratio?

## Data

- **Source:** CAS Loss Reserving Database (NAIC Schedule P), newer release: accident years 1998–2007, valued 12/31/2007, with actual development through 2016. [CAS page](https://www.casact.org/publications-research/research/research-resources/loss-reserving-data-pulled-naic-schedule-p) Downloaded: 2026/10/29
- **Lines:** Private passenger auto (PPA) and workers' compensation (WC).
- **Column mapping:**
  - Paid = `CumPaidLoss`
  - Reported (paid + case) = `IncurredLosses − BulkLoss`
  - Premium = `EarnedPremNet`
## Data cleaning

Rules are judged on known cells only (valuation 12/31/2007) and were frozen before any estimates. Full reasons and evidence: [docs/cleaning_rules.md](docs/cleaning_rules.md). Code: `src/clean.py`. Dropped lines: [docs/dropped_lines.csv](docs/dropped_lines.csv).

| Step | PPA lines | PPA graded AYs | WC lines | WC graded AYs |
|---|---|---|---|---|
| Start | 143 | 1,182 | 132 | 1,078 |
| Rule 1: no paid losses in any known cell | 135 | 1,125 | 106 | 868 |
| Rule 2: net earned premium ≤ 0 in any AY | 113 | 951 | 63 | 501 |
| Rule 4: any negative case reserve > 10% of paid | 109 | 915 | 60 | 474 |

A graded AY is an accident year 1999–2007 that is present (AY 1998's reserve is zero at the valuation date). Rules 3 and 5–8 are notes and drop nothing: changes in ceded share of premium (reinsurance), negative bulk reserves, lines missing their latest AYs (graded on the AYs present), company size, and groups vs single companies (both kept).

**Sample size.** WC ends at 60 lines, below the original target of 100. Rather than drop BF and expected claims for WC, results report n and interval widths, methods are compared on the same company-lines, and comparisons are paired (per-company error differences).

**Limitations from cleaning:**
- *Survivorship:* lines that stopped filing before 2007 can't be graded. Companies that exit or fail likely reserved worse, so measured errors are probably a lower bound, and the bias can narrow gaps between methods.
- *Selection (rule 2):* dropped lines may lean toward runoff, heavily reinsured or pooled companies.
- *Reinsurance:* Schedule P doesn't record treaty type, so changes in excess-of-loss reinsurance are a possible driver of chain ladder errors that can't be separated out.
- *Groups:* group membership can change through mergers between 2007 and 2016.

## Phase 2: one company by hand (WC, GRCODE 23663)

Before scaling up, every method was built by hand in Excel on one randomly picked mid-size WC company ([excel/wc_23663.xlsx](excel/wc_23663.xlsx)), rebuilt in Python (`src/methods.py`, checked against Friedland ch. 7 Exhibit I in `tests/`) and reconciled to the workbook at every stage, both bases (largest gap $0.07; `notebooks/03_one_company.ipynb`). A written prediction ([notes/phase2_prediction.md](notes/phase2_prediction.md)) was committed with the estimates (tag `phase2-freeze`) before the answer key was opened (`notebooks/04_phase2_reveal.ipynb`).

| Basis | Closest method | Error, % of reserve | Actual unpaid, AYs 1999–2007 ($000) |
|---|---|---|---|
| Paid | Chain ladder | −4.4% | 13,659 |
| Reported | Chain ladder | +11.5% | 14,436 |

- **Prediction:** 3 of 7 calls hit. The diagnostics were read correctly (the AY 1998 loss ratio overstated recent AYs; case reserves strengthened), but I picked BF to hedge against AY 1998-style late emergence, which didn't happen.
- **Main driver:** AYs 2002–2007 finished at 38–58% paid loss ratios, well below the expected loss ratios (company AY 1998: 84.1%; industry: 64.2%). BF and expected claims lean on those ratios, so they overstated; chain ladder used each AY's own losses.
- **Judgment vs averages:** my factor selections beat all 6 averages on the reported basis (+11.5% vs +25% to +60%). On the paid basis every averaging method landed within ±10%.
- **Changes for Phase 3:** accident-year errors are shown as % of earned premium, because % of reserve explodes on mature AYs (AY 2000's actual unpaid was $12K). The loss ratio options stay as set; changing them after one result would be hindsight. Question 5 tests the loss ratio effect across every line.

## Target definition

- **Target:** cumulative losses at 120 months of development (lag 10). The data contains this value for every accident year, so no tail factor is needed. Development factors run to 120 months and stop.
- **Caveat:** for WC, 120 months is not ultimate. The paid-to-reported ratio at lag 10 shows how much remains open.
- **Target per method:** Matching basis: paid methods are graded against paid at 120 and reported methods against reported at 120. Expected claims and BF are each run twice: once using paid losses, paid development factors and a paid expected loss ratio, and once using the reported versions of all three. Each run is graded against the matching target. Why: stopping at 120 months (no tail factors) leaves case reserves open at lag 10, so paid and reported at 120 differ. A common target would count that gap as error for one chain ladder, and the gap varies by line and maturity. Open case at 120 is reported separately by line.

## Backtest design

- **Blind split:** a cell (accident year, lag) is *known* if AY + lag − 1 ≤ 2007; otherwise it is *hidden*. Estimates are frozen before the hidden data is opened.
- **Error is measured on the reserve, not the ultimate:**
  error = (estimated unpaid − actual unpaid) / actual unpaid.
  It is also reported as a percentage of earned premium. AY 1998 is excluded from the reserve error because its reserve is zero by construction.
- **Summary statistics:** medians and IQRs across companies. Bias (median signed error) is reported separately from accuracy (median absolute error).
- **Known limitation:** selecting the best averaging method and scoring it on the same data is an in-sample comparison. TODO: either say so in the results or fix it with the second-era (1988–1997) extension.

## Scope

**In scope:** paid/reported chain ladder, expected claims, BF; 6 averaging methods (simple and volume-weighted × all years, latest 5, latest 3; Friedland ch. 7); 2 expected loss ratio options (company AY 1998 at 120 months; premium-weighted industry); PPA and WC; 120-month target.

**Out of scope:** tail factors, Mack/bootstrap, Berquist-Sherman, frequency-severity methods, case outstanding development. The data has no claim counts, so a shift in the paid-to-reported ratio can't be attributed to faster settlement vs. weakening case reserves.

## Repository layout

```
data/raw/        CAS download, unmodified
data/clean/      output of src/clean.py (not committed; rebuild by running it)
docs/            cleaning rules, cleaning counts, dropped lines, data dictionary
data/hidden/     Phase 2 answer key (not committed)
excel/           Phase 2 hand-built exhibits, WC GRCODE 23663
notes/           Phase 2 prediction, written before the reveal
src/             clean.py (cleaning rules); methods.py (triangles, factors, averages, CL, expected claims, BF, grading)
notebooks/       01_data_checks (probes behind each rule), 02_clean (applies the rules),
                 03_one_company (pick, export, Python-to-Excel reconciliation), 04_phase2_reveal (grading)
tests/           test_methods.py: Friedland ch. 7 Exhibit I (factors, averages, CDFs, chain ladder)
```

## References

- Friedland, *Estimating Unpaid Claims Using Basic Techniques* (CAS)
- ASOP No. 23, Data Quality
