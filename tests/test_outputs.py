"""The committed result files: counts match the sources, shares are valid, and the scenarios behave as their
definitions require (adding facilities can never lengthen travel times, removing them can never shorten them)."""
import json
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
MAIN = "r2025a_constrained"


def J(name):
    return json.loads((OUT / f"{name}.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def S():
    return J("scenarios")


def test_source_counts():
    F = J("facilities")
    assert F["lists"]["A"]["n_rows_mozambique"] == 1579
    assert F["lists"]["B"]["n_features"] == 1223
    am = F["lists"]["B"]["amenity_counts"]
    assert (am["clinic"], am["hospital"], am["pharmacy"], am["doctors"]) == (782, 197, 133, 81)
    assert F["lists"]["H"]["n_rows"] == 676
    assert F["lists"]["H"]["provinces"] == ["Cabo Delgado", "Nampula", "Zambezia"]
    assert F["districts"]["n"] == 159
    assert sum(F["lists"]["H"]["status_used"].values()) == F["lists"]["H"]["n_used"]


def test_sources_recorded():
    src = J("sources")
    assert len(src) >= 10
    for rec in src.values():
        assert len(rec["sha256"]) == 64 and rec["bytes"] > 0 and rec["url"].startswith("https://")


def test_population_totals():
    P = J("population")
    for lay in P["layers"].values():
        assert 25e6 < lay["total"] < 40e6
        assert sum(lay["by_district"]) + lay["outside_districts"] == pytest.approx(lay["total"], rel=1e-9)


def _shares(S, key, mode, lay=MAIN, t=60):
    return np.array([np.nan if d[f"share_over_{t}"] is None else d[f"share_over_{t}"] for d in S["scenarios"][key][mode][lay]["districts"]])


def test_shares_valid(S):
    for key, sc in S["scenarios"].items():
        for mode in ("motorized", "walking"):
            for lay, r in sc[mode].items():
                n = r["national"]
                assert 0 <= n["share_over_120"] <= n["share_over_60"] <= 1
                pops = sum(d["population"] for d in r["districts"])
                assert pops == pytest.approx(n["population"], rel=1e-6)


@pytest.mark.parametrize("more,fewer", [("AB", "A"), ("AB", "B"), ("A", "A_hosp"), ("B", "B_hosp"), ("AB", "AB_hosp"),
                                        ("A_cross", "A"), ("B_pharm", "B"), ("H_all", "H_func"), ("H_func", "H_fully"),
                                        ("A_sea", "A"), ("AB_sea", "AB")])
def test_more_facilities_never_worse(S, more, fewer):
    for mode in ("motorized", "walking"):
        for t in (60, 120):
            a, b = _shares(S, more, mode, t=t), _shares(S, fewer, mode, t=t)
            ok = np.isfinite(a) & np.isfinite(b)
            assert (a[ok] <= b[ok] + 1e-9).all(), (more, fewer, mode, t)


def test_walking_slower_than_motorized(S):
    for key in ("A", "B", "AB"):
        m, w = _shares(S, key, "motorized"), _shares(S, key, "walking")
        ok = np.isfinite(m) & np.isfinite(w)
        assert (w[ok] >= m[ok] - 1e-9).all()


def test_comparisons_cover_compared_districts(S):
    C = J("comparisons")
    assert C["n_compared"] == len(S["compared_districts"]) == 159 - len(S["excluded_districts"])
    for block in ("pairs", "herams", "modes", "population_layer"):
        for v in C[block].values():
            assert -1 <= v["spearman"] <= 1 and v["spearman_ci95"][0] <= v["spearman"] + 1e-9


def test_map_data_matches_results(S):
    V = json.loads((ROOT / "docs" / "data" / "district_values.json").read_text(encoding="utf-8"))
    assert len(V["districts"]) == 159
    for s in V["scenarios"]:
        for mode in ("motorized", "walking"):
            for i, row in enumerate(V["values"][f"{s['key']}|{mode}"]):
                if row is None:
                    continue
                d = S["scenarios"][s["key"]][mode][MAIN]["districts"][i]
                assert row[0] == pytest.approx(d["share_over_60"], abs=1e-4)
                assert row[1] == pytest.approx(d["share_over_120"], abs=1e-4)


@pytest.mark.skipif(not (ROOT / "data" / "raw" / "osm" / "health_facilities.parquet").exists(), reason="raw data not downloaded")
def test_osm_rule_on_raw_file(access):
    import geopandas as gpd
    g = gpd.read_parquet(ROOT / "data" / "raw" / "osm" / "health_facilities.parquet")
    cls = [access.osm_class(a, h) for a, h in zip(g["amenity"], g["healthcare"])]
    F = J("facilities")["lists"]["B"]
    assert cls.count("pharmacy") == F["n_pharmacy"] and cls.count("hospital") == F["n_hospital"]
