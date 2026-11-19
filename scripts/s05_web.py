"""Files for the interactive district map: docs/data/districts.geojson (simplified outlines) and
docs/data/district_values.json (district values for each scenario and mode, from outputs/scenarios.json).
Also copies the result files offered for download into docs/data/.

    python scripts/s05_web.py
"""
import json
import shutil
import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import access as A  # noqa: E402
from s02_grid import MAIN_LAYER  # noqa: E402

MAP_SCENARIOS = ["AB", "A", "B", "AB_hosp", "A_hosp", "B_hosp", "H_all", "H_func", "H_fully"]
SIMPLIFY_DEG = 0.004


def main():
    S = json.loads((A.OUT / "scenarios.json").read_text())
    D = pd.read_parquet(A.DERIVED / "districts.parquet")
    g = gpd.read_file(A.RAW / "boundaries" / "moz_ADM2.geojson")[["shapeID", "geometry"]].merge(D[["shapeID", "district_id", "district", "province"]], on="shapeID")
    g["geometry"] = g.geometry.simplify(SIMPLIFY_DEG, preserve_topology=True)
    g = g.sort_values("district_id")[["district_id", "district", "province", "geometry"]].rename(columns={"district_id": "id", "district": "name"})
    A.DOCS_DATA.mkdir(parents=True, exist_ok=True)
    g.to_file(A.DOCS_DATA / "districts.geojson", driver="GeoJSON", COORDINATE_PRECISION=4)

    compared = set(S["compared_districts"])
    h3 = set(S["herams_provinces"])
    names = S["district_names"]; provs = S["district_provinces"]
    pops = [x["population"] for x in S["scenarios"]["A"]["motorized"][MAIN_LAYER]["districts"]]
    out = {
        "population_layer": MAIN_LAYER, "herams_provinces": sorted(h3),
        "measures": [{"index": i, "kind": "share", "minutes": t, "label": f"Residents over {t // 60} h"} for i, t in enumerate(A.THRESHOLDS_MIN)]
                    + [{"index": len(A.THRESHOLDS_MIN), "kind": "minutes", "label": "Median travel time"}],
        "modes": [{"key": "motorized", "label": "Motorized"}, {"key": "walking", "label": "Walking"}],
        "scenarios": [{"key": k, "label": S["labels"][k], "herams": k.startswith("H_")} for k in MAP_SCENARIOS],
        "districts": [{"id": i, "name": names[i], "province": provs[i], "population": round(pops[i]), "compared": i in compared}
                      for i in range(len(names))],
        "values": {},
    }
    for k in MAP_SCENARIOS:
        for mode in ("motorized", "walking"):
            rows = []
            for i, d in enumerate(S["scenarios"][k][mode][MAIN_LAYER]["districts"]):
                ok = i in compared and (not k.startswith("H_") or provs[i] in h3)
                rows.append([round(d["share_over_60"], 4), round(d["share_over_120"], 4),
                             None if d["median_min"] is None else round(d["median_min"], 1)] if ok else None)
            out["values"][f"{k}|{mode}"] = rows
    (A.DOCS_DATA / "district_values.json").write_text(json.dumps(out, separators=(",", ":"), ensure_ascii=False) + "\n", encoding="utf-8")
    for f in ("comparisons.json", "paired.json", "facilities.json", "population.json", "sources.json"):
        shutil.copy(A.OUT / f, A.DOCS_DATA / f)
    # district table for download: main population layer, both modes, the three main lists
    rows = []
    for i in range(len(names)):
        r = {"district": names[i], "province": provs[i], "population": round(pops[i]), "compared": i in compared}
        for k in ("A", "B", "AB", "AB_hosp"):
            for mode in ("motorized", "walking"):
                d = S["scenarios"][k][mode][MAIN_LAYER]["districts"][i]
                r[f"{k}_{mode}_share_over_60"] = d["share_over_60"]; r[f"{k}_{mode}_share_over_120"] = d["share_over_120"]
                r[f"{k}_{mode}_median_min"] = d["median_min"]
        rows.append(r)
    pd.DataFrame(rows).to_csv(A.DOCS_DATA / "district_access.csv", index=False, float_format="%.4f")
    print("wrote docs/data/districts.geojson, district_values.json, district_access.csv",
          round((A.DOCS_DATA / "districts.geojson").stat().st_size / 1e3), "kB")


if __name__ == "__main__":
    main()
