# Reserving Backtest: How Accurate Are Basic Reserving Methods on Real Insurers?

> Status: Phase 0 (design). Results not yet produced. This section records the question, target and scoring rules **before** any estimates are made, so the design can't be tuned to the results.

## Research question

How accurate are basic reserving methods on real insurers, and what drives the errors when they miss?

I run paid and reported chain ladder, the expected claims method and Bornhuetter-Ferguson on 100+ companies per line, using only the data available at 12/31/2007. Then I grade every estimate against how the losses actually developed over the next 10 years.

Specific questions:
1. Which method is most accurate on total reserves, by line?
2. How does error change with accident-year maturity?
3. Paid vs reported basis: which is more accurate, and does the answer differ between PPA and WC?
4. Which development-factor averaging method works best?
5. How sensitive is BF to the choice of expected loss ratio?

## Data

- **Source:** CAS Loss Reserving Database (NAIC Schedule P), newer release: accident years 1998–2007, valued 12/31/2007, with actual development through 2016. [CAS page](https://www.casact.org/publications-research/research/research-resources/loss-reserving-data-pulled-naic-schedule-p)
- **Lines:** Private passenger auto (PPA) and workers' compensation (WC).
- **Column mapping:**
  - Paid = `CumPaidLoss`
  - Reported (paid + case) = `IncurLoss − BulkLoss`
  - Premium = `EarnedPremNet`
- **Cleaning rules:** TODO (Phase 1). This will be a table of each rule, the reason for it, and the company count remaining after it.

## Target definition

- **Target:** cumulative losses at 120 months of development (lag 10). The data contains this value for every accident year, so no tail factor is needed. Development factors run to 120 months and stop.
- **Caveat:** for WC, 120 months is not ultimate. The paid-to-reported ratio at lag 10 shows how much remains open.
- **Target per method:** TODO. Choose one and write down why:
  - (a) Matching basis: paid methods are graded against paid at 120 and reported methods against reported at 120, or
  - (b) Common target: every method is graded against the same quantity.

## Backtest design

- **Blind split:** a cell (accident year, lag) is *known* if AY + lag − 1 ≤ 2007; otherwise it is *hidden*. Estimates are frozen before the hidden data is opened.
- **Error is measured on the reserve, not the ultimate:**
  error = (estimated unpaid − actual unpaid) / actual unpaid.
  It is also reported as a percentage of earned premium. AY 1998 is excluded from the reserve error because its reserve is zero by construction.
- **Summary statistics:** medians and IQRs across companies. Bias (median signed error) is reported separately from accuracy (median absolute error).
- **Known limitation:** selecting the best averaging method and scoring it on the same data is an in-sample comparison. TODO: either say so in the results or fix it with the second-era (1988–1997) extension.

## Scope

**In scope:** paid/reported chain ladder, expected claims, BF; 5–7 averaging methods (Friedland ch. 7); 2–3 expected loss ratio options; PPA and WC; 120-month target.

**Out of scope:** tail factors, Mack/bootstrap, Berquist-Sherman, frequency-severity methods, case outstanding development. The data has no claim counts, so a shift in the paid-to-reported ratio can't be attributed to faster settlement vs. weakening case reserves.

## Repository layout

```
data/raw/        CAS download, unmodified
src/             reserving methods (self-written module)
notebooks/       exploration and charts
tests/           reproductions of Friedland exhibits
```

## References

- Friedland, *Estimating Unpaid Claims Using Basic Techniques* (CAS)
- ASOP No. 23, Data Quality
