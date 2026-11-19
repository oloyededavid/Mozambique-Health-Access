"""Travel time to the nearest facility for every scenario and mode, summarised by district, province and nation,
and the comparisons between scenarios. Writes outputs/scenarios.json, outputs/comparisons.json and, for the figures,
data/derived/tt_<scenario>_<mode>.npy.

    python scripts/s03_scenarios.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio

sys.path.insert(0, str(Path(__file__).resolve().parent))
import access as A  # noqa: E402
from s02_grid import LAYERS, MAIN_LAYER  # noqa: E402

MODES = ("motorized", "walking")
H3 = ("Cabo Delgado", "Nampula", "Zambézia")
N_DROP, DROP_SHARE = 20, 0.10
MIN_DISTRICT_POP = 5000   # units below this (the Lake Niassa unit and two lake islands in geoBoundaries) are not compared
SAVE_TT = {("AB", "motorized"), ("AB", "walking"), ("A", "motorized"), ("B", "motorized"), ("A", "walking"), ("B", "walking"),
           ("H_all", "walking"), ("H_func", "walking"), ("H_all", "motorized"), ("H_func", "motorized")}


def facility_sets(fac):
    u = fac[fac.use]
    A_ = u[u.list == "A"]; B_all = u[u.list == "B"]; B_ = B_all[B_all["class"] != "pharmacy"]
    H = u[u.list == "H"]
    bg = A_[~A_.province_loc.isin(H3)]   # list A outside the HeRAMS provinces, so travel across province lines is not cut off
    return {
        "A": A_, "B": B_, "AB": pd.concat([A_, B_]),
        "A_hosp": A_[A_.hospital], "B_hosp": B_[B_.hospital], "AB_hosp": pd.concat([A_[A_.hospital], B_[B_.hospital]]),
        "B_pharm": B_all, "A_cross": pd.concat([A_, u[u.list == "A_cross"]]),
        "H_all": pd.concat([H, bg]),
        "H_func": pd.concat([H[[A.herams_keep(s, "functioning") for s in H.status]], bg]),
        "H_fully": pd.concat([H[[A.herams_keep(s, "fully") for s in H.status]], bg]),
        "A_sea": A_, "AB_sea": pd.concat([A_, B_]),
    }


LABELS = {
    "A": "List A: Maina et al. (2019), public sector",
    "B": "List B: OpenStreetMap, without pharmacies",
    "AB": "Lists A and B together",
    "A_hosp": "List A, hospitals only",
    "B_hosp": "List B, hospitals only",
    "AB_hosp": "Lists A and B, hospitals only",
    "B_pharm": "List B with pharmacies",
    "A_cross": "List A plus facilities across the border",
    "H_all": "HeRAMS, every listed facility",
    "H_func": "HeRAMS, without facilities reported non-functioning",
    "H_fully": "HeRAMS, only facilities reported fully functioning",
    "A_sea": "List A, sea passable",
    "AB_sea": "Lists A and B, sea passable",
}


def sources(df, G):
    r, c = A.cells_for_points(df.lon.values, df.lat.values, G["left"], G["top"], G["res"], G["passable"].shape)
    r, c, mv = A.snap_to_passable(r, c, G["passable"], max_cells=3)
    ok = r >= 0
    return r[ok] * G["passable"].shape[1] + c[ok], int((mv > 0).sum()), int((~ok).sum())


def summarise(tt_flat, P, n_d, prov_of_d, provs):
    minutes = tt_flat[P["fidx"]]
    inside = P["district"] >= 0
    m, p, d = minutes[inside], P["pop"][inside], P["district"][inside].astype("int64")
    out = {"national": A.weighted_summary(m, p)}
    dist = A.summarise_groups(m, p, d, n_d)
    out["districts"] = [{k: (round(v, 5) if isinstance(v, float) else v) for k, v in x.items()} for x in dist]
    pid = np.array([provs.index(prov_of_d[i]) for i in d])
    out["provinces"] = {provs[i]: x for i, x in enumerate(A.summarise_groups(m, p, pid, len(provs)))}
    sel3 = np.isin(pid, [provs.index(x) for x in H3])
    out["herams_provinces"] = A.weighted_summary(m[sel3], p[sel3])
    return out


def main():
    fac = pd.read_parquet(A.DERIVED / "facilities.parquet")
    D = pd.read_parquet(A.DERIVED / "districts.parquet")
    names = D.district.tolist(); prov_of_d = D.province.tolist(); provs = sorted(set(prov_of_d))
    g = np.load(A.DERIVED / "grid.npz")
    G = {k: g[k] for k in g.files}
    G["left"], G["top"], G["res"] = float(G["left"]), float(G["top"]), float(G["res"])
    shape = G["passable"].shape
    graphs = {m: A.build_graph(G[m], G["passable"], G["top"], G["res"], G["left"]) for m in MODES}
    # sensitivity: the sea passable at the friction surface's own sea values (a stand-in for boats and bridges)
    open_sea = np.isfinite(G["motorized"]) & (G["motorized"] > 0) & np.isfinite(G["walking"]) & (G["walking"] > 0)
    graphs_sea = {m: A.build_graph(G[m], open_sea, G["top"], G["res"], G["left"]) for m in MODES}
    pops = {k: dict(np.load(A.DERIVED / f"pop_{k}.npz")) for k in LAYERS}
    sets = facility_sets(fac)

    res = {"labels": LABELS, "district_names": names, "district_provinces": prov_of_d, "provinces": provs,
           "herams_provinces": list(H3), "scenarios": {}}
    tts = {}
    for key, df in sets.items():
        sea = key.endswith("_sea")
        src, n_snap, n_out = sources(df, G)
        res["scenarios"][key] = {"n_facilities": int(len(df)), "n_source_cells": int(np.unique(src).size),
                                 "n_snapped_to_land": n_snap, "n_not_placed": n_out}
        for mode in MODES:
            tt = A.travel_time((graphs_sea if sea else graphs)[mode], shape, src)
            tts[(key, mode)] = tt.ravel()
            if (key, mode) in SAVE_TT:
                np.save(A.DERIVED / f"tt_{key}_{mode}.npy", tt.astype("float32"))
            res["scenarios"][key][mode] = {lay: summarise(tt.ravel(), pops[lay], len(names), prov_of_d, provs) for lay in LAYERS}
        print(key, res["scenarios"][key]["n_facilities"], {m: round(res["scenarios"][key][m][MAIN_LAYER]["national"]["share_over_60"], 4) for m in MODES})

    # MAP's published travel time to healthcare, summarised the same way (not an independent check: same friction surface)
    pub = {}
    for mode, f in (("motorized", "tt_health_motorized_2020.tif"), ("walking", "tt_health_walking_2020.tif")):
        with rasterio.open(A.RAW / "mapwcs" / f) as s:
            a = s.read(1).astype("float64"); a[a == s.nodata] = np.inf
        pub[mode] = a.ravel()
        res.setdefault("published", {})[mode] = {lay: summarise(pub[mode], pops[lay], len(names), prov_of_d, provs) for lay in LAYERS}
    (A.OUT / "scenarios.json").write_text(json.dumps(res, indent=None, separators=(",", ":")) + "\n", encoding="utf-8")

    # ------------------------------------------------------------ comparisons between scenarios
    S = res["scenarios"]

    popd = [x["population"] for x in S["A"]["motorized"][MAIN_LAYER]["districts"]]
    valid = [i for i in range(len(names)) if popd[i] >= MIN_DISTRICT_POP]
    res["compared_districts"] = valid
    res["excluded_districts"] = [names[i] for i in range(len(names)) if i not in valid]
    (A.OUT / "scenarios.json").write_text(json.dumps(res, indent=None, separators=(",", ":")) + "\n", encoding="utf-8")

    def shares(key, mode, thr, lay=MAIN_LAYER, block=None):
        src = (res["published"][mode] if key == "published" else S[key][mode])[lay]["districts"]
        idx = valid if block is None else block
        return np.array([src[i][f"share_over_{thr}"] for i in idx], dtype="float64")

    h3_idx = [i for i in valid if prov_of_d[i] in H3]
    vnames = [names[i] for i in valid]
    pairs = [("A", "B"), ("A", "AB"), ("B", "AB"), ("A", "A_hosp"), ("B", "B_hosp"), ("AB", "AB_hosp"), ("A_hosp", "B_hosp"),
             ("B", "B_pharm"), ("A", "A_cross"), ("A", "A_sea"), ("AB", "AB_sea"), ("A_sea", "published"), ("A", "published"), ("B", "published"), ("AB", "published")]
    C = {"min_district_population": MIN_DISTRICT_POP, "n_compared": len(valid), "n_compared_herams": len(h3_idx), "pairs": {}, "herams": {}, "modes": {}, "population_layer": {}}
    for thr in A.THRESHOLDS_MIN:
        for mode in MODES:
            for a, b in pairs:
                C["pairs"][f"{a}|{b}|{mode}|{thr}"] = A.compare_shares(shares(a, mode, thr), shares(b, mode, thr), vnames)
            for a, b in (("H_all", "H_func"), ("H_all", "H_fully"), ("A", "H_all")):
                C["herams"][f"{a}|{b}|{mode}|{thr}"] = A.compare_shares(shares(a, mode, thr, block=h3_idx), shares(b, mode, thr, block=h3_idx),
                                                                         [names[i] for i in h3_idx], top_k=10)
            alt = [k for k in LAYERS if k != MAIN_LAYER][0]
            for key in ("A", "B", "AB"):
                C["population_layer"][f"{key}|{mode}|{thr}"] = A.compare_shares(shares(key, mode, thr), shares(key, mode, thr, lay=alt), vnames)
        for key in ("A", "B", "AB"):
            C["modes"][f"{key}|{thr}"] = A.compare_shares(shares(key, "motorized", thr), shares(key, "walking", thr), vnames)

    # cell-level agreement with the published layer, inside Mozambique
    moz = (G["moz"] & G["passable"]).ravel()
    from scipy.stats import spearmanr
    C["published_cells"] = {}
    for key in ("A", "B", "AB", "A_sea"):
        for mode in MODES:
            ours, theirs = tts[(key, mode)][moz], pub[mode][moz]
            ok = np.isfinite(ours) & np.isfinite(theirs)
            rho = spearmanr(ours[ok][::7], theirs[ok][::7]).statistic
            diff = ours[ok] - theirs[ok]
            C["published_cells"][f"{key}|{mode}"] = {"spearman_every_7th_cell": float(rho), "median_diff_min": float(np.median(diff)),
                                                    "p05_diff_min": float(np.percentile(diff, 5)), "p95_diff_min": float(np.percentile(diff, 95)),
                                                    "n_cells": int(ok.sum())}

    # how much results depend on a few facilities: drop 10% of a list at random, 20 times
    rng = np.random.default_rng(20261119)
    C["drop10"] = {}
    for key in ("A", "B"):
        df = sets[key]
        for mode in MODES:
            nat, dmax = [], []
            base = shares(key, mode, 60)
            for _ in range(N_DROP):
                keep = df.iloc[rng.permutation(len(df))[: int(round(len(df) * (1 - DROP_SHARE)))]]
                src, _, _ = sources(keep, G)
                tt = A.travel_time(graphs[mode], shape, src).ravel()
                s = summarise(tt, pops[MAIN_LAYER], len(names), prov_of_d, provs)
                nat.append(s["national"]["share_over_60"])
                dmax.append(float(np.max(np.abs(np.array([s["districts"][i]["share_over_60"] for i in valid]) - base))))
            C["drop10"][f"{key}|{mode}"] = {"national_share_over_60_min": float(min(nat)), "national_share_over_60_max": float(max(nat)),
                                           "district_max_abs_change_median": float(np.median(dmax)), "district_max_abs_change_max": float(max(dmax)),
                                           "runs": N_DROP, "share_dropped": DROP_SHARE}
    (A.OUT / "comparisons.json").write_text(json.dumps(C, indent=1) + "\n", encoding="utf-8")
    print("wrote outputs/scenarios.json and outputs/comparisons.json")


if __name__ == "__main__":
    main()
