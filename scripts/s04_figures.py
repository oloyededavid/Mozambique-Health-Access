"""Figures for the paper (paper/figures/*.png) and the page (docs/assets/figures/*.webp, desktop and phone).
Every value drawn comes from data/derived/ and outputs/, which the earlier scripts write.

    python scripts/s04_figures.py
"""
import json
import sys
from pathlib import Path

import geopandas as gpd
import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import BoundaryNorm, ListedColormap  # noqa: E402
from PIL import Image  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import access as A  # noqa: E402
from s02_grid import MAIN_LAYER  # noqa: E402

PAPER = A.ROOT / "paper" / "figures"
WEB = A.ROOT / "docs" / "assets" / "figures"
INK, MUTED, RULE = "#141412", "#62625d", "#d9d9d5"
COL_A, COL_B, COL_H = "#1f56b0", "#d9500b", "#2f7d4f"
TT_BOUNDS = [0, 30, 60, 120, 240, 1e9]
TT_COLS = ["#fbe9d3", "#f6b77a", "#e5772e", "#b6430e", "#5e1f06"]
TT_LABELS = ["under 30 min", "30 min to 1 h", "1 to 2 h", "2 to 4 h", "over 4 h"]

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11, "axes.edgecolor": RULE, "axes.labelcolor": INK,
                     "xtick.color": MUTED, "ytick.color": MUTED, "axes.titlesize": 12, "axes.titleweight": "bold",
                     "axes.titlelocation": "left", "figure.facecolor": "white", "savefig.facecolor": "white"})


def save(fig, name, phone=False):
    PAPER.mkdir(parents=True, exist_ok=True); WEB.mkdir(parents=True, exist_ok=True)
    tmp = WEB / f"_{name}.png"
    fig.savefig(tmp, dpi=150, bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)
    im = Image.open(tmp).convert("RGB")
    if phone:
        im.save(WEB / f"{name}_phone.webp", "WEBP", quality=82, method=6)
    else:
        im.save(WEB / f"{name}.webp", "WEBP", quality=82, method=6)
        im.save(PAPER / f"{name}.png", optimize=True)
    tmp.unlink()


def outlines():
    a0 = gpd.read_file(A.RAW / "boundaries" / "moz_ADM0.geojson")
    a1 = gpd.read_file(A.RAW / "boundaries" / "moz_ADM1_simplified.geojson")
    return a0, a1


def map_axes(ax, a0, a1):
    a1.boundary.plot(ax=ax, color="#9a9a94", linewidth=0.5)
    a0.boundary.plot(ax=ax, color=INK, linewidth=0.8)
    ax.set_xlim(30.1, 41.0); ax.set_ylim(-27.0, -10.3)
    ax.set_aspect(1 / np.cos(np.radians(18.5)))
    ax.set_xticks([]); ax.set_yticks([]); ax.set_xlabel(""); ax.set_ylabel("")
    for s in ax.spines.values():
        s.set_visible(False)


def fig1_facilities(phone):
    fac = pd.read_parquet(A.DERIVED / "facilities.parquet")
    F = json.loads((A.OUT / "facilities.json").read_text())
    a0, a1 = outlines()
    u = fac[fac.use]
    a, b = u[u.list == "A"], u[(u.list == "B") & (u["class"] != "pharmacy")]
    fig, axs = plt.subplots(2 if phone else 1, 2 if not phone else 1, figsize=(6.2, 11.5) if phone else (11, 7.4))
    axs = np.ravel(axs)
    for ax, d, col, title in ((axs[0], a, COL_A, f"List A: Maina et al. ({len(a):,})"), (axs[1], b, COL_B, f"List B: OpenStreetMap ({len(b):,})")):
        map_axes(ax, a0, a1)
        h = d[d.hospital]; o = d[~d.hospital]
        ax.scatter(o.lon, o.lat, s=4, color=col, alpha=0.55, linewidths=0, label="other facility")
        ax.scatter(h.lon, h.lat, s=22, facecolor="white", edgecolor=col, linewidths=1.1, label="hospital")
        ax.set_title(title, color=INK)
        ax.legend(loc="lower right", frameon=False, fontsize=9, markerscale=1.5)
    fig.text(0.01, 0.0, f"Hospitals: {F['lists']['A']['n_hospital_used']} in list A, {F['lists']['B']['n_hospital_used']} in list B. "
             "Province outlines: geoBoundaries.", fontsize=8.5, color=MUTED)
    save(fig, "fig1_facilities", phone)


def tt_grid(name):
    g = np.load(A.DERIVED / "grid.npz")
    tt = np.load(A.DERIVED / f"tt_{name}.npy").astype("float64")
    tt[~g["moz"]] = np.nan
    ext = [float(g["left"]), float(g["left"]) + tt.shape[1] * float(g["res"]), float(g["top"]) - tt.shape[0] * float(g["res"]), float(g["top"])]
    return tt, ext


def fig2_traveltime(phone):
    a0, a1 = outlines()
    cmap = ListedColormap(TT_COLS); norm = BoundaryNorm(TT_BOUNDS, cmap.N)
    fig, axs = plt.subplots(2 if phone else 1, 2 if not phone else 1, figsize=(6.2, 11.8) if phone else (11, 7.6))
    axs = np.ravel(axs)
    for ax, mode, title in ((axs[0], "motorized", "Motorized"), (axs[1], "walking", "Walking only")):
        tt, ext = tt_grid(f"AB_{mode}")
        tt = np.where(np.isinf(tt), 1e8, tt)
        ax.imshow(np.ma.masked_invalid(tt), extent=ext, cmap=cmap, norm=norm, interpolation="nearest")
        map_axes(ax, a0, a1)
        ax.set_title(f"{title}, lists A and B together", color=INK)
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in TT_COLS]
    fig.legend(handles, TT_LABELS, loc="lower center", ncol=3 if phone else 5, frameon=False, fontsize=9.5,
               bbox_to_anchor=(0.5, -0.04 if phone else -0.02))
    save(fig, "fig2_traveltime", phone)


def fig3_scatter(phone):
    S = json.loads((A.OUT / "scenarios.json").read_text())
    idx = S["compared_districts"]
    fig, axs = plt.subplots(2 if phone else 1, 2 if not phone else 1, figsize=(6.2, 11) if phone else (11, 5.4))
    axs = np.ravel(axs)
    for ax, mode, title in ((axs[0], "motorized", "Motorized"), (axs[1], "walking", "Walking only")):
        a = np.array([S["scenarios"]["A"][mode][MAIN_LAYER]["districts"][i]["share_over_60"] for i in idx]) * 100
        b = np.array([S["scenarios"]["B"][mode][MAIN_LAYER]["districts"][i]["share_over_60"] for i in idx]) * 100
        ax.plot([0, 100], [0, 100], color=RULE, linewidth=1)
        ax.scatter(a, b, s=18, color=COL_B, alpha=0.75, edgecolor="white", linewidths=0.4)
        ax.set_xlim(-2, 102); ax.set_ylim(-2, 102)
        ax.set_xlabel("List A: % of residents over 1 h"); ax.set_ylabel("List B: % of residents over 1 h")
        ax.set_title(title, color=INK)
        ax.grid(color="#efefec", linewidth=0.6); ax.set_axisbelow(True)
        ax.text(60, 6, "List B nearer than A", color=MUTED, fontsize=9); ax.text(4, 92, "List A nearer than B", color=MUTED, fontsize=9)
    fig.tight_layout()
    save(fig, "fig4_scatter", phone)


def fig4_scenarios(phone):
    S = json.loads((A.OUT / "scenarios.json").read_text())
    P = json.loads((A.OUT / "population.json").read_text())
    alt = [k for k in P["layers"] if k != MAIN_LAYER][0]
    rows = ["A", "B", "AB", "B_pharm", "A_cross", "A_sea", "A_hosp", "B_hosp", "AB_hosp"]
    lab = {"A": "List A", "B": "List B", "AB": "Lists A and B", "B_pharm": "List B with pharmacies", "A_cross": "List A + across the border",
           "A_sea": "List A, sea passable", "A_hosp": "List A, hospitals", "B_hosp": "List B, hospitals", "AB_hosp": "Lists A and B, hospitals"}
    fig, axs = plt.subplots(2 if phone else 1, 2 if not phone else 1, figsize=(6.4, 10.5) if phone else (11.5, 5.2), sharey=not phone)
    axs = np.ravel(axs)
    y = np.arange(len(rows))[::-1]
    for ax, mode, title in ((axs[0], "motorized", "Motorized"), (axs[1], "walking", "Walking only")):
        m = [S["scenarios"][r][mode][MAIN_LAYER]["national"]["share_over_60"] * 100 for r in rows]
        u = [S["scenarios"][r][mode][alt]["national"]["share_over_60"] * 100 for r in rows]
        for yi, a, b in zip(y, m, u):
            ax.plot([a, b], [yi, yi], color=RULE, linewidth=2, zorder=1)
        ax.scatter(m, y, s=46, color=COL_A, zorder=2, label="constrained population (main)")
        ax.scatter(u, y, s=46, facecolor="white", edgecolor=COL_A, linewidths=1.4, zorder=2, label="unconstrained population")
        ax.set_yticks(y); ax.set_yticklabels([lab[r] for r in rows])
        ax.set_xlim(0, 100); ax.set_xlabel("% of residents over 1 h from the nearest facility")
        ax.set_title(title, color=INK); ax.grid(axis="x", color="#efefec"); ax.set_axisbelow(True)
        if phone or mode == "motorized":
            ax.legend(loc="lower right", frameon=False, fontsize=8.5)
    fig.tight_layout()
    save(fig, "fig3_scenarios", phone)


def fig5_herams(phone):
    S = json.loads((A.OUT / "scenarios.json").read_text())
    idx = [i for i in S["compared_districts"] if S["district_provinces"][i] in S["herams_provinces"]]
    mode = "walking"
    get = lambda k: np.array([S["scenarios"][k][mode][MAIN_LAYER]["districts"][i]["share_over_60"] for i in idx]) * 100  # noqa: E731
    al, fu, fl = get("H_all"), get("H_func"), get("H_fully")
    ch = np.maximum(np.abs(fu - al), np.abs(fl - al))
    keep = np.argsort(-ch, kind="stable")[:12]
    keep = keep[np.argsort(fl[keep] - al[keep], kind="stable")]   # largest change at the top
    names = [f"{S['district_names'][idx[k]]} ({S['district_provinces'][idx[k]]})" for k in keep]
    fig, ax = plt.subplots(figsize=(6.4, 7.2) if phone else (10, 5.6))
    y = np.arange(len(keep))
    for yi, k in zip(y, keep):
        ax.plot([al[k], fl[k]], [yi, yi], color=RULE, linewidth=2, zorder=1)
    ax.scatter(fl[keep], y, s=44, marker="s", color=COL_B, zorder=2, label="fully functioning only")
    ax.scatter(fu[keep], y, s=70, marker="D", facecolor="white", edgecolor=COL_H, linewidths=1.3, zorder=3, label="without non-functioning")
    ax.scatter(al[keep], y, s=20, color=COL_H, zorder=4, label="every used facility")
    ax.set_yticks(y); ax.set_yticklabels(names, fontsize=9)
    ax.set_xlim(-2, 102); ax.set_xlabel("% of residents over 1 h on foot")
    ax.grid(axis="x", color="#efefec"); ax.set_axisbelow(True)
    h, l = ax.get_legend_handles_labels()
    ax.legend(h[::-1], l[::-1], loc="upper center", bbox_to_anchor=(0.35 if phone else 0.5, -0.11 if phone else -0.13),
              frameon=False, fontsize=9, ncol=1 if phone else 3)
    fig.tight_layout()
    save(fig, "fig5_herams", phone)


def main():
    for phone in (False, True):
        fig1_facilities(phone); fig2_traveltime(phone); fig3_scatter(phone); fig4_scenarios(phone); fig5_herams(phone)
    print("wrote", sorted(p.name for p in WEB.glob("*.webp")))


if __name__ == "__main__":
    main()
