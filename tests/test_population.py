"""Population weighting and scenario comparison."""
import numpy as np
import pytest


def test_shares_beyond_thresholds(access):
    minutes = np.array([10, 59.9, 60, 61, 130, np.inf])
    pop = np.array([100, 100, 100, 100, 100, 100.0])
    s = access.weighted_summary(minutes, pop)
    assert s["population"] == 600
    assert s["share_over_60"] == pytest.approx(3 / 6)      # 61, 130 and the unreachable cell; 60 itself is not beyond
    assert s["share_over_120"] == pytest.approx(2 / 6)
    assert s["unreachable_share"] == pytest.approx(1 / 6)


def test_population_weights_not_cell_counts(access):
    s = access.weighted_summary([5, 200], [900, 100])
    assert s["share_over_60"] == pytest.approx(0.1)
    assert s["median_min"] == 5


def test_weighted_median(access):
    assert access.weighted_median([1, 2, 3], [1, 1, 1]) == 2
    assert access.weighted_median([1, 2, 3], [10, 1, 1]) == 1
    assert access.weighted_median([1, np.inf], [1, 5]) is None
    assert access.weighted_summary([1, 2], [0, 0])["share_over_60"] is None


def test_groups(access):
    minutes = np.array([10, 100, 10, 10]); pop = np.array([1, 1, 5, 5.0]); grp = np.array([0, 0, 1, -1])
    out = access.summarise_groups(minutes, pop, grp, 3)
    assert out[0]["share_over_60"] == pytest.approx(0.5)
    assert out[1]["share_over_60"] == 0
    assert out[2]["population"] == 0


def test_compare_identical_and_shifted(access):
    a = np.linspace(0, 1, 30)
    same = access.compare_shares(a, a, [str(i) for i in range(30)])
    assert same["spearman"] == pytest.approx(1) and same["max_abs_change"] == 0 and same["top_k_overlap"] == 20
    b = a.copy(); b[3] += 0.5
    d = access.compare_shares(a, b, [str(i) for i in range(30)])
    assert d["max_change_district"] == "3" and d["max_abs_change"] == pytest.approx(0.5)
    assert d["n_change_over_10pp"] == 1 and d["spearman"] < 1
