"""Friedland ch. 7, Exhibit I, Sheet 2 (U.S. Industry Auto, paid): rebuild the
book's factors, averages, CDFs and chain ladder projection with src/methods.py.

Book values are printed to 3 decimals (factors, CDFs) or whole $000 (Sheet 3),
so each check allows half a unit of the last printed digit.

Run from the repo root:  python tests/test_methods.py   (or: pytest tests)
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.methods import ata_factors, average, cdfs, latest, triangle  # noqa: E402

# Part 1 - paid triangle, AY 1998-2007 x 12..120 months ($000)
PAID = {
    1998: [18539254, 33231039, 40062008, 43892039, 45896535, 46765422, 47221322, 47446877, 47555456, 47644187],
    1999: [20410193, 36090684, 43259402, 47159241, 49208532, 50162043, 50625757, 50878808, 51000534],
    2000: [22120843, 38976014, 46389282, 50562385, 52735280, 53740101, 54284334, 54533225],
    2001: [22992259, 40096198, 47767835, 52093916, 54363436, 55378801, 55878421],
    2002: [24092782, 41795313, 49903803, 54352884, 56754376, 57807215],
    2003: [24084451, 41399612, 49070332, 53584201, 55930654],
    2004: [24369770, 41489863, 49236678, 53774672],
    2005: [25100697, 42702229, 50644994],
    2006: [25608776, 43606497],
    2007: [27229969],
}

# Part 2 - age-to-age factors, k = 1..9
FACTORS = {
    1998: [1.792, 1.206, 1.096, 1.046, 1.019, 1.010, 1.005, 1.002, 1.002],
    1999: [1.768, 1.199, 1.090, 1.043, 1.019, 1.009, 1.005, 1.002],
    2000: [1.762, 1.190, 1.090, 1.043, 1.019, 1.010, 1.005],
    2001: [1.744, 1.191, 1.091, 1.044, 1.019, 1.009],
    2002: [1.735, 1.194, 1.089, 1.044, 1.019],
    2003: [1.719, 1.185, 1.092, 1.044],
    2004: [1.703, 1.187, 1.092],
    2005: [1.701, 1.186],
    2006: [1.703],
}

# Part 3 - the four book averages that are also among the project's six
BOOK_AVERAGES = {
    ("simple", 5): [1.712, 1.189, 1.091, 1.044, 1.019, 1.010, 1.005, 1.002, 1.002],
    ("simple", 3): [1.702, 1.186, 1.091, 1.044, 1.019, 1.009, 1.005, 1.002, 1.002],
    ("volume", 5): [1.712, 1.189, 1.091, 1.044, 1.019, 1.010, 1.005, 1.002, 1.002],
    ("volume", 3): [1.702, 1.186, 1.091, 1.044, 1.019, 1.009, 1.005, 1.002, 1.002],
}

# Part 4 - selections, tail and CDFs to ultimate (lags 1..10)
SELECTED = [1.702, 1.186, 1.091, 1.044, 1.019, 1.009, 1.005, 1.002, 1.002]
TAIL = 1.002
BOOK_CDF = [2.390, 1.404, 1.184, 1.085, 1.040, 1.020, 1.011, 1.006, 1.004, 1.002]

# Sheet 3, column (8): projected ultimate, paid development method
BOOK_ULT = [47739475, 51204536, 54860424, 56493084, 58963359,
            58167880, 58345519, 59963673, 61223522, 65079626]


def long_rows():
    """Book triangle in the clean-data long format (known cells only)."""
    return pd.DataFrame(
        [{"AccidentYear": ay, "DevelopmentLag": lag, "CumPaidLoss": v}
         for ay, row in PAID.items() for lag, v in enumerate(row, start=1)])


def close(got, want, tol):
    return abs(got - want) <= tol + 1e-9


def test_triangle_and_factors():
    tri = triangle(long_rows(), "paid")
    assert tri.shape == (10, 10)
    assert tri.notna().sum().sum() == 55
    f = ata_factors(tri)
    for ay, row in FACTORS.items():
        for k, want in enumerate(row, start=1):
            assert close(f.at[ay, k], want, 0.0005), (ay, k, f.at[ay, k], want)
    assert f.loc[2007].isna().all()


def test_averages():
    tri = triangle(long_rows(), "paid")
    for (kind, n), row in BOOK_AVERAGES.items():
        got = average(tri, kind, n)
        for k, want in enumerate(row, start=1):
            assert close(got[k], want, 0.0005), (kind, n, k, got[k], want)


def test_cdfs():
    got = cdfs(dict(enumerate(SELECTED, start=1)), tail=TAIL)
    for lag, want in enumerate(BOOK_CDF, start=1):
        assert close(got[lag], want, 0.0005), (lag, got[lag], want)


def test_chain_ladder():
    # The book multiplies by CDFs rounded to 3 decimals, so this does too.
    lat = latest(triangle(long_rows(), "paid"))
    cdf = cdfs(dict(enumerate(SELECTED, start=1)), tail=TAIL).round(3)
    ult = lat["value"] * lat["lag"].map(cdf)
    for ay, want in zip(range(1998, 2008), BOOK_ULT):
        assert close(ult[ay], want, 0.5), (ay, ult[ay], want)
    assert close(ult.sum(), 572041099, 5)  # Sheet 3 total


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("pass", name)
