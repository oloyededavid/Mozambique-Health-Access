"""Paired bootstrap of differences between rank correlations: does one choice reorder districts more than another?
Both correlations are computed on the same resample of districts, so the interval is for their difference.
Districts are resampled as if independent; neighbouring districts share facilities and roads, so the intervals are
likely too narrow. Reads outputs/scenarios.json, writes outputs/paired.json.

    python scripts/s03b_paired.py
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import access as A  # noqa: E402
from s02_grid import LAYERS, MAIN_LAYER  # noqa: E402

N_BOOT = 2000
ALT = [k for k in LAYERS if k != MAIN_LAYER][0]


def paired_diff(x1, y1, x2, y2, n_boot=N_BOOT, seed=7):
    """rho(x1, y1) - rho(x2, y2) over the same districts, with a percentile interval from paired resamples."""
    x1, y1, x2, y2 = (np.asarray(v, dtype="float64") for v in (x1, y1, x2, y2))
    rng = np.random.default_rng(seed)
    diffs = []
    for _ in range(n_boot):
        i = rng.integers(0, x1.size, x1.size)
        a, b = A.spearman(x1[i], y1[i]), A.spearman(x2[i], y2[i])
        if a is not None and b is not None:
            diffs.append(a - b)
    diffs = np.array(diffs)
    return {"diff": A.spearman(x1, y1) - A.spearman(x2, y2), "ci95": [float(np.percentile(diffs, 2.5)), float(np.percentile(diffs, 97.5))],
            "share_positive": float((diffs > 0).mean()), "n_boot": int(diffs.size)}


def main():
    S = json.loads((A.OUT / "scenarios.json").read_text())
    idx = S["compared_districts"]

    def sh(key, mode, lay=MAIN_LAYER):
        return [S["scenarios"][key][mode][lay]["districts"][i]["share_over_60"] for i in idx]
    out = {"note": "positive diff: the facility list (A against B) keeps districts in a more similar order than the other choice",
           "districts_resampled_as_independent": True}
    for mode in ("motorized", "walking"):
        lst = (sh("A", mode), sh("B", mode))
        out[f"list_vs_hospitals|{mode}"] = paired_diff(*lst, sh("AB", mode), sh("AB_hosp", mode))
        out[f"list_vs_population|{mode}"] = paired_diff(*lst, sh("AB", mode), sh("AB", mode, ALT))
        out[f"list_vs_mode|{mode}"] = paired_diff(*lst, sh("AB", "motorized"), sh("AB", "walking"))
    (A.OUT / "paired.json").write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    for k, v in out.items():
        if isinstance(v, dict):
            print(k, round(v["diff"], 3), [round(c, 3) for c in v["ci95"]], v["share_positive"])


if __name__ == "__main__":
    main()
