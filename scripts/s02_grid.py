"""Prepare the travel grid and the population tables.

The grid is the Malaria Atlas Project friction surface (30 arc-seconds, about 0.9 km in Mozambique). The sea is
impassable: it is taken as the cells where MAP's own published travel-time layer has no value. Population stays at
100 m: each WorldPop cell goes to the district that contains its centre and to the grid cell that contains its
centre, and the table keeps the population of every (district, grid cell) pair. Population on a sea cell at the
coast is moved to the nearest land cell.

Writes data/derived/grid.npz, data/derived/pop_<layer>.npz and outputs/population.json.

    python scripts/s02_grid.py
"""
import json
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.features import rasterize

sys.path.insert(0, str(Path(__file__).resolve().parent))
import access as A  # noqa: E402

LAYERS = {
    "r2025a_constrained": ("worldpop/moz_pop_2020_CN_100m_R2025A_v1.tif", "WorldPop R2025A, 2020, constrained"),
    "unconstrained_2020": ("worldpop/moz_ppp_2020.tif", "WorldPop 2000-2020 series, 2020, unconstrained"),
}
MAIN_LAYER = "r2025a_constrained"


def grid():
    with rasterio.open(A.RAW / "mapwcs" / "tt_health_motorized_2020.tif") as s:
        sea = s.read(1) == s.nodata
        T = s.transform
    fr = {}
    for mode in ("motorized", "walking"):
        with rasterio.open(A.RAW / "friction" / f"{mode}_2020.tif") as s:
            assert s.transform == T and s.crs.to_epsg() == 4326
            fr[mode] = s.read(1).astype("float32")
    passable = ~sea & np.isfinite(fr["motorized"]) & (fr["motorized"] > 0) & np.isfinite(fr["walking"]) & (fr["walking"] > 0)
    a0 = gpd.read_file(A.RAW / "boundaries" / "moz_ADM0.geojson")
    moz = rasterize(a0.geometry, out_shape=sea.shape, transform=T, fill=0, default_value=1).astype(bool)
    np.savez_compressed(A.DERIVED / "grid.npz", motorized=fr["motorized"], walking=fr["walking"], passable=passable, moz=moz,
                        left=T.c, top=T.f, res=T.a)
    return T, passable, moz


def pop_table(path, a2, T, passable):
    with rasterio.open(A.RAW / path) as s:
        PT, shape, nod = s.transform, s.shape, s.nodata
        dras = rasterize(((g, i + 1) for g, i in zip(a2.geometry, a2.district_id)), out_shape=shape, transform=PT, fill=0, dtype="uint8")
        nr, nc = passable.shape
        keys, vals = [], []
        total = 0.0
        step = 1024
        for r0 in range(0, shape[0], step):
            win = rasterio.windows.Window(0, r0, shape[1], min(step, shape[0] - r0))
            p = s.read(1, window=win).astype("float64")
            ok = np.isfinite(p) & (p > 0)
            if nod is not None:
                ok &= p != nod
            rr, cc = np.nonzero(ok)
            if rr.size == 0:
                continue
            lon = PT.c + (cc + 0.5) * PT.a
            lat = PT.f + (rr + r0 + 0.5) * PT.e
            fr_, fc_ = A.cells_for_points(lon, lat, T.c, T.f, T.a, (nr, nc))
            assert (fr_ >= 0).all()
            fidx = fr_ * nc + fc_
            dist = dras[rr + r0, cc].astype("int64") - 1
            k = (dist + 1) * (nr * nc) + fidx
            u, inv = np.unique(k, return_inverse=True)
            keys.append(u); vals.append(np.bincount(inv, weights=p[ok]))
            total += p[ok].sum()
    k = np.concatenate(keys); v = np.concatenate(vals)
    u, inv = np.unique(k, return_inverse=True)
    v = np.bincount(inv, weights=v)
    district = (u // (nr * nc) - 1).astype("int16")
    fidx = (u % (nr * nc)).astype("int64")
    # population on sea cells at the coast moves to the nearest land cell
    on_sea = ~passable.ravel()[fidx]
    moved_pop = float(v[on_sea].sum())
    r, c, mv = A.snap_to_passable(fidx[on_sea] // nc, fidx[on_sea] % nc, passable, max_cells=3)
    newf = fidx[on_sea].copy()
    placed = mv >= 0
    newf[placed] = r[placed] * nc + c[placed]
    fidx[on_sea] = newf
    lost = float(v[on_sea][~placed].sum())
    return {"district": district, "fidx": fidx, "pop": v}, {
        "total": float(total), "outside_districts": float(v[district < 0].sum()),
        "moved_from_sea_cells": moved_pop, "on_sea_not_placed": lost, "pairs": int(v.size),
    }


def main():
    A.DERIVED.mkdir(parents=True, exist_ok=True)
    T, passable, moz = grid()
    import pandas as pd
    a2 = gpd.read_file(A.RAW / "boundaries" / "moz_ADM2.geojson")
    d = pd.read_parquet(A.DERIVED / "districts.parquet")
    a2 = a2.merge(d[["shapeID", "district_id"]], on="shapeID")
    rec = {"grid": {"res_deg": float(T.a), "shape": list(passable.shape), "passable_cells": int(passable.sum()),
                    "moz_cells": int(moz.sum()), "moz_cells_impassable": int((moz & ~passable).sum())},
           "main_layer": MAIN_LAYER, "layers": {}}
    for key, (path, label) in LAYERS.items():
        tab, info = pop_table(path, a2, T, passable)
        np.savez_compressed(A.DERIVED / f"pop_{key}.npz", **tab)
        info["label"] = label
        info["by_district"] = np.bincount(tab["district"][tab["district"] >= 0], weights=tab["pop"][tab["district"] >= 0],
                                          minlength=len(a2)).tolist()
        rec["layers"][key] = info
        print(key, {k: v for k, v in info.items() if k != "by_district"})
    (A.OUT / "population.json").write_text(json.dumps(rec, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
