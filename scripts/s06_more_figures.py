"""Two more figures, drawn from committed files only, so they rebuild without the raw downloads:

    fig5_change_map   how much each district's share beyond one hour changes when list B replaces list A
                      (outputs/scenarios.json, district shapes from docs/data/districts.geojson)
    fig6_rank         rank correlation of district shares between pairs of runs, with 95% bootstrap intervals
                      (outputs/comparisons.json)

Written to paper/figures/*.png and docs/assets/figures/*.webp (desktop and phone) by the same helper as
scripts/s04_figures.py.

    python scripts/s06_more_figures.py
"""
import json
import sys
import textwrap
import warnings
from pathlib import Path

import geopandas as gpd
import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import BoundaryNorm, ListedColormap  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import access as A  # noqa: E402
from s02_grid import MAIN_LAYER  # noqa: E402
from s04_figures import COL_A, COL_B, INK, MUTED, RULE, map_axes, save  # noqa: E402

# change in percentage points, list B minus list A: blue where fewer residents are beyond one hour, orange where more are
CH_BOUNDS = [-100, -20, -10, -2, 2, 10, 20, 100]
CH_COLS = ["#1f4e8c", "#6b9bd1", "#c7d9ef", "#f1f0ec", "#f6c89a", "#e5772e", "#9c3a08"]
CH_LABELS = ["over 20 points lower", "10 to 20 lower", "2 to 10 lower", "within 2 points",
             "2 to 10 higher", "10 to 20 higher", "over 20 points higher"]


def shapes():
    d = gpd.read_file(A.ROOT / "docs" / "data" / "districts.geojson").sort_values("id")
    warnings.filterwarnings("ignore", message="Geometry is in a geographic CRS")  # a 0.002° cosmetic buffer
    # close the hairline gaps between districts before merging, so no slivers are drawn inside the country
    m = d.copy(); m["geometry"] = m.buffer(0.002)
    a1 = m.dissolve(by="province").reset_index(); a1["geometry"] = a1.buffer(-0.002)
    a0 = m.dissolve(); a0["geometry"] = a0.buffer(-0.002)
    return d, a0, a1


def fig5_change_map(phone):
    S = json.loads((A.OUT / "scenarios.json").read_text())
    C = json.loads((A.OUT / "comparisons.json").read_text())["pairs"]
    d, a0, a1 = shapes()
    compared = set(S["compared_districts"])
    cmap = ListedColormap(CH_COLS); norm = BoundaryNorm(CH_BOUNDS, cmap.N)
    fig, axs = plt.subplots(2 if phone else 1, 2 if not phone else 1, figsize=(4.0, 8.4) if phone else (11, 7.6))
    axs = np.ravel(axs)
    for ax, mode, title in ((axs[0], "motorized", "Motorized"), (axs[1], "walking", "Walking only")):
        a = S["scenarios"]["A"][mode][MAIN_LAYER]["districts"]
        b = S["scenarios"]["B"][mode][MAIN_LAYER]["districts"]
        g = d.copy()
        g["compared"] = [i in compared for i in g["id"]]
        g["change"] = [(b[i]["share_over_60"] - a[i]["share_over_60"]) * 100 if i in compared else np.nan
                       for i in g["id"]]
        g[g.compared].plot(ax=ax, column="change", cmap=cmap, norm=norm, edgecolor="white", linewidth=0.25)
        g[~g.compared].plot(ax=ax, facecolor="#e5e5e1", edgecolor="white", hatch="////", linewidth=0.25)
        map_axes(ax, a0, a1)
        n10 = C[f"A|B|{mode}|60"]["n_change_over_10pp"]
        ax.set_title(f"{title}\n{n10} districts change by over 10 points", color=INK)
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in CH_COLS]
    handles.append(plt.Rectangle((0, 0), 1, 1, facecolor="#e5e5e1", hatch="////", edgecolor="white"))
    handles[-1].set_edgecolor("#999")
    title = "List B against list A: share of residents over 1 h, percentage points"
    fig.legend(handles, CH_LABELS + ["not compared (lake, islands)"], loc="lower center", ncol=2 if phone else 4,
               frameon=False, fontsize=8 if phone else 9, bbox_to_anchor=(0.5, -0.06 if phone else -0.02),
               title=textwrap.fill(title, 44) if phone else title, title_fontsize=8.5 if phone else 9.5)
    note = ("District and province outlines: geoBoundaries gbOpen MOZ ADM2. "
            "Constrained WorldPop R2025A population.")
    fig.text(0.01, -0.105 if phone else -0.05, textwrap.fill(note, 52) if phone else note, fontsize=7.5 if phone else 8.5,
             color=MUTED, va="top")
    save(fig, "fig5_change_map", phone)


def fig6_rank(phone):
    C = json.loads((A.OUT / "comparisons.json").read_text())
    P, M, L = C["pairs"], C["modes"], C["population_layer"]
    rows = [  # label, motorized entry, walking entry
        ("List A against list B", P["A|B|motorized|60"], P["A|B|walking|60"]),
        ("Population layer, constrained against unconstrained (both lists)", L["AB|motorized|60"], L["AB|walking|60"]),
        ("All facilities against hospitals only (both lists)", P["AB|AB_hosp|motorized|60"], P["AB|AB_hosp|walking|60"]),
        ("List B with and without pharmacies", P["B|B_pharm|motorized|60"], P["B|B_pharm|walking|60"]),
        ("Sea closed against sea passable (list A)", P["A|A_sea|motorized|60"], P["A|A_sea|walking|60"]),
        ("List A with and without facilities across the border", P["A|A_cross|motorized|60"], P["A|A_cross|walking|60"]),
    ]
    mode = M["AB|60"]
    fig, ax = plt.subplots(figsize=(4.0, 7.2) if phone else (11, 5.6))
    y = np.arange(len(rows) + 1)
    for k, (label, colour, off) in enumerate((("Motorized", COL_A, -0.13), ("Walking only", COL_B, 0.13))):
        for j, (_, mo, wa) in enumerate(rows):
            e = (mo, wa)[k]
            lo, hi = e["spearman_ci95"]
            ax.plot([lo, hi], [j + off] * 2, color=colour, linewidth=2, alpha=0.55, solid_capstyle="round")
            ax.scatter(e["spearman"], j + off, s=34, color=colour, zorder=3, label=label if j == 0 else None)
    lo, hi = mode["spearman_ci95"]
    j = len(rows)
    ax.plot([lo, hi], [j, j], color=INK, linewidth=2, alpha=0.55, solid_capstyle="round")
    ax.scatter(mode["spearman"], j, s=34, color=INK, zorder=3)
    labels = [r[0] for r in rows] + ["Mode of travel, motorized against walking (both lists)"]
    if phone:
        labels = [textwrap.fill(l, 24) for l in labels]
    ax.set_yticks(y, labels, fontsize=8 if phone else 10)
    ax.invert_yaxis()
    ax.set_xlim(0.4, 1.01)
    ax.axvline(1, color=RULE, linewidth=1)
    ax.set_xlabel("Spearman rank correlation, 95% interval" if phone else
                  "Rank correlation of district shares over 1 h (Spearman), with 95% bootstrap interval",
                  fontsize=8.5 if phone else None)
    ax.grid(axis="x", color="#efefec", linewidth=0.6); ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.legend(loc="upper center", bbox_to_anchor=(0.35 if not phone else 0.2, -0.13 if not phone else -0.08),
              ncol=2 if not phone else 1, frameon=False, fontsize=9)
    note = (f"{C['n_compared']} districts. Lower values: the choice reorders districts more. Intervals "
            "treat districts as independent, so they are likely too narrow.")
    fig.text(0.01, -0.1 if not phone else -0.005, textwrap.fill(note, 50) if phone else note, fontsize=7.5 if phone else 8.5,
             color=MUTED, va="top" if phone else "baseline")
    fig.tight_layout()
    save(fig, "fig6_rank", phone)


def main():
    for phone in (False, True):
        fig5_change_map(phone)
        fig6_rank(phone)
    print("wrote fig5_change_map, fig6_rank")


if __name__ == "__main__":
    main()
