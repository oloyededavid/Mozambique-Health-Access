"""Core functions shared by the pipeline scripts and the tests: travel time over a friction grid in geographic
coordinates, population-weighted summaries, and the facility rules. No file paths here except the constants."""
import math
import re
import unicodedata
from pathlib import Path

import numpy as np
from scipy import sparse
from scipy.sparse.csgraph import dijkstra

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
DERIVED = ROOT / "data" / "derived"
OUT = ROOT / "outputs"
DOCS_DATA = ROOT / "docs" / "data"
EARTH_RADIUS_M = 6371008.8  # mean Earth radius (IUGG)
THRESHOLDS_MIN = (60, 120)
HERAMS_PROVINCES = ("Cabo Delgado", "Nampula", "Zambezia")


# ---------------------------------------------------------------- geometry
def haversine_m(lon1, lat1, lon2, lat2):
    """Great-circle distance in metres on a sphere of mean Earth radius. Accepts arrays."""
    lon1, lat1, lon2, lat2 = map(np.radians, (lon1, lat1, lon2, lat2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 2 * EARTH_RADIUS_M * np.arcsin(np.sqrt(np.minimum(a, 1.0)))


def build_graph(friction, passable, top_lat, res_deg, left_lon=0.0):
    """Undirected 8-neighbour graph over a north-up geographic grid.

    friction: minutes per metre for each cell (rows run north to south).
    passable: boolean mask; edges touching an impassable cell are left out.
    Edge cost = mean friction of the two cells x great-circle distance between their centres, so cells that get
    narrower towards the pole cost less to cross east-west, as they should.
    """
    friction = np.asarray(friction, dtype="float64")
    nr, nc = friction.shape
    lat = top_lat - (np.arange(nr) + 0.5) * res_deg          # centre latitude of each row
    idx = np.arange(nr * nc).reshape(nr, nc)
    ok = passable & np.isfinite(friction) & (friction > 0)
    rows, cols, wts = [], [], []

    def add(sl_a, sl_b, dist):
        a_ok = ok[sl_a] & ok[sl_b]
        cost = 0.5 * (friction[sl_a] + friction[sl_b]) * dist
        rows.append(idx[sl_a][a_ok]); cols.append(idx[sl_b][a_ok]); wts.append(cost[a_ok])

    # east: same row
    d_e = haversine_m(0.0, lat, res_deg, lat)[:, None]
    add((slice(None), slice(0, nc - 1)), (slice(None), slice(1, nc)), d_e)
    # south: next row
    d_s = haversine_m(0.0, lat[:-1], 0.0, lat[1:])[:, None]
    add((slice(0, nr - 1), slice(None)), (slice(1, nr), slice(None)), d_s)
    # south-east and south-west diagonals
    d_d = haversine_m(0.0, lat[:-1], res_deg, lat[1:])[:, None]
    add((slice(0, nr - 1), slice(0, nc - 1)), (slice(1, nr), slice(1, nc)), d_d)
    add((slice(0, nr - 1), slice(1, nc)), (slice(1, nr), slice(0, nc - 1)), d_d)
    r = np.concatenate(rows); c = np.concatenate(cols); w = np.concatenate(wts)
    # scipy treats stored zeros as missing edges: keep a tiny positive floor (friction is always > 0 here anyway)
    w = np.maximum(w, 1e-9)
    return sparse.csr_matrix((w, (r, c)), shape=(nr * nc, nr * nc))


def travel_time(graph, shape, source_cells):
    """Minutes from every cell to the nearest source cell (flat indices). Unreachable cells get +inf."""
    src = np.unique(np.asarray(source_cells, dtype="int64"))
    if src.size == 0:
        return np.full(shape, np.inf)
    d = dijkstra(graph, directed=False, indices=src, min_only=True)
    return d.reshape(shape)


def cells_for_points(lon, lat, left, top, res_deg, shape):
    """Row, column of the grid cell that contains each point; -1 where a point falls outside the grid."""
    lon = np.asarray(lon, dtype="float64"); lat = np.asarray(lat, dtype="float64")
    c = np.floor((lon - left) / res_deg).astype("int64")
    r = np.floor((top - lat) / res_deg).astype("int64")
    out = (r < 0) | (c < 0) | (r >= shape[0]) | (c >= shape[1]) | ~np.isfinite(lon) | ~np.isfinite(lat)
    r[out] = -1; c[out] = -1
    return r, c


def snap_to_passable(r, c, passable, max_cells=3):
    """Move points that sit on an impassable cell (for example the sea at the coast) to the nearest passable cell
    within max_cells. Returns new rows, columns and how far each moved in cells (-1 = could not be placed)."""
    r = np.array(r); c = np.array(c); moved = np.zeros(r.size, dtype="int64")
    nr, nc = passable.shape
    for i in range(r.size):
        if r[i] < 0:
            moved[i] = -1; continue
        if passable[r[i], c[i]]:
            continue
        best = None
        for k in range(1, max_cells + 1):
            rr, cc = np.mgrid[max(0, r[i] - k):min(nr, r[i] + k + 1), max(0, c[i] - k):min(nc, c[i] + k + 1)]
            m = passable[rr, cc]
            if m.any():
                dd = (rr[m] - r[i]) ** 2 + (cc[m] - c[i]) ** 2
                j = int(np.argmin(dd)); best = (rr[m][j], cc[m][j], k); break
        if best is None:
            moved[i] = -1; r[i] = -1; c[i] = -1
        else:
            r[i], c[i], moved[i] = best
    return r, c, moved


# ---------------------------------------------------------------- population-weighted summaries
def weighted_summary(minutes, pop, thresholds=THRESHOLDS_MIN):
    """Share of population beyond each threshold (unreachable counts as beyond) and the population-weighted
    median travel time. minutes and pop are 1-D arrays of the same length."""
    minutes = np.asarray(minutes, dtype="float64"); pop = np.asarray(pop, dtype="float64")
    keep = pop > 0
    minutes, pop = minutes[keep], pop[keep]
    total = pop.sum()
    out = {"population": float(total)}
    if total <= 0:
        out.update({f"share_over_{t}": None for t in thresholds}); out["median_min"] = None; out["unreachable_share"] = None
        return out
    for t in thresholds:
        out[f"share_over_{t}"] = float(pop[~(minutes <= t)].sum() / total)
    out["median_min"] = weighted_median(minutes, pop)
    out["unreachable_share"] = float(pop[~np.isfinite(minutes)].sum() / total)
    return out


def weighted_median(values, weights):
    """Smallest value at which the cumulative weight reaches half the total (lower weighted median).
    Returns None if that value is infinite."""
    v = np.asarray(values, dtype="float64"); w = np.asarray(weights, dtype="float64")
    o = np.argsort(v, kind="stable"); v, w = v[o], w[o]
    cw = np.cumsum(w)
    k = int(np.searchsorted(cw, 0.5 * cw[-1]))
    m = v[min(k, v.size - 1)]
    return float(m) if np.isfinite(m) else None


def summarise_groups(minutes, pop, group, n_groups, thresholds=THRESHOLDS_MIN):
    """weighted_summary for each group id 0..n_groups-1 (group -1 is ignored)."""
    res = []
    order = np.argsort(group, kind="stable")
    g_sorted = group[order]
    starts = np.searchsorted(g_sorted, np.arange(n_groups), side="left")
    ends = np.searchsorted(g_sorted, np.arange(n_groups), side="right")
    for g in range(n_groups):
        sel = order[starts[g]:ends[g]]
        res.append(weighted_summary(minutes[sel], pop[sel], thresholds))
    return res


# ---------------------------------------------------------------- comparing scenarios
def rankdata(x):
    from scipy.stats import rankdata as rd
    return rd(x)


def spearman(x, y):
    x = np.asarray(x, dtype="float64"); y = np.asarray(y, dtype="float64")
    ok = np.isfinite(x) & np.isfinite(y)
    rx, ry = rankdata(x[ok]), rankdata(y[ok])
    if rx.std() == 0 or ry.std() == 0:
        return None
    return float(np.corrcoef(rx, ry)[0, 1])


def spearman_ci(x, y, n_boot=2000, seed=1):
    """Percentile bootstrap interval over units (districts)."""
    rng = np.random.default_rng(seed)
    x = np.asarray(x, dtype="float64"); y = np.asarray(y, dtype="float64")
    vals = []
    for _ in range(n_boot):
        i = rng.integers(0, x.size, x.size)
        s = spearman(x[i], y[i])
        if s is not None:
            vals.append(s)
    return [float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))]


def compare_shares(a, b, names, top_k=20):
    """How district shares change from scenario a to scenario b (same district order)."""
    a = np.asarray(a, dtype="float64"); b = np.asarray(b, dtype="float64")
    d = b - a
    i = int(np.nanargmax(np.abs(d)))
    ra = rankdata(-a); rb = rankdata(-b)
    top_a = set(np.argsort(-a, kind="stable")[:top_k]); top_b = set(np.argsort(-b, kind="stable")[:top_k])
    return {
        "spearman": spearman(a, b),
        "spearman_ci95": spearman_ci(a, b),
        "mean_change": float(np.nanmean(d)),
        "median_abs_change": float(np.nanmedian(np.abs(d))),
        "max_abs_change": float(abs(d[i])),
        "max_change_signed": float(d[i]),
        "max_change_district": names[i],
        "n_change_over_10pp": int((np.abs(d) > 0.10).sum()),
        "n_change_over_20pp": int((np.abs(d) > 0.20).sum()),
        "max_rank_shift": int(np.max(np.abs(ra - rb))),
        "median_rank_shift": float(np.median(np.abs(ra - rb))),
        "top_k": top_k,
        "top_k_overlap": len(top_a & top_b),
        "n": int(a.size),
    }


# ---------------------------------------------------------------- facility rules
OSM_HEALTH_AMENITY = {"clinic", "hospital", "doctors", "health_post"}
OSM_HEALTH_HEALTHCARE = {"clinic", "hospital", "centre", "doctor", "health_post"}
OSM_PHARMACY = {"pharmacy"}


def osm_class(amenity, healthcare):
    """Classify an OSM feature: 'hospital', 'facility' (other health facility), 'pharmacy' or None (left out).
    amenity is read first; healthcare=* only when amenity is missing. Dentists are left out."""
    a = (amenity or "").strip().lower() if isinstance(amenity, str) else ""
    h = (healthcare or "").strip().lower() if isinstance(healthcare, str) else ""
    if a:
        if a == "hospital":
            return "hospital"
        if a in OSM_HEALTH_AMENITY:
            return "facility"
        if a in OSM_PHARMACY:
            return "pharmacy"
        return None
    if h == "hospital":
        return "hospital"
    if h in OSM_HEALTH_HEALTHCARE:
        return "facility"
    if h in OSM_PHARMACY:
        return "pharmacy"
    return None


def maina_is_hospital(facility_type):
    return isinstance(facility_type, str) and facility_type.strip().lower().startswith("hospital")


def fix_mojibake(s):
    """Undo UTF-8 read as Latin-1 (for example 'SaÃºde' -> 'Saúde'), as found in some HeRAMS names."""
    if not isinstance(s, str):
        return s
    if "Ã" in s or "Â" in s:
        try:
            return s.encode("latin-1").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            return s
    return s


def norm_text(s):
    """Lower case, no accents, single spaces: for matching names and province labels."""
    if not isinstance(s, str):
        return ""
    s = unicodedata.normalize("NFKD", fix_mojibake(s))
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", s.lower())).strip()


FUNCTIONING_MAIN = {"Fully Functioning", "Partially Functioning"}   # main rule: drop only facilities reported non-functioning
FUNCTIONING_STRICT = {"Fully Functioning"}                          # strict rule: keep only those reported fully functioning


def herams_keep(status, rule):
    """Whether a HeRAMS facility counts under a rule. 'all' keeps every listed facility; 'functioning' drops those
    reported Non-Functioning (missing status is kept); 'fully' keeps only Fully Functioning."""
    s = status.strip() if isinstance(status, str) else None
    if rule == "all":
        return True
    if rule == "functioning":
        return s != "Non-Functioning"
    if rule == "fully":
        return s in FUNCTIONING_STRICT
    raise ValueError(rule)


def quarter_key(q):
    """'2024 - Q2' -> 20242, for ordering assessments."""
    m = re.match(r"\s*(\d{4})\s*-\s*Q([1-4])", str(q))
    return int(m.group(1)) * 10 + int(m.group(2)) if m else -1
