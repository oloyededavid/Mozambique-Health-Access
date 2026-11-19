"""Build paper/paper.md from paper/template.md. Every number comes from outputs/*.json, which scripts s00 to s03
write. The build stops if a statement in the template would no longer be true or if a placeholder is left unfilled.

    python scripts/build_paper.py && pandoc paper/paper.md -o paper/paper.docx --resource-path=. && python scripts/build_page.py
"""
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
MAIN, ALT = "r2025a_constrained", "unconstrained_2020"
MODES = ("motorized", "walking")


def need(cond, msg):
    if not cond:
        raise SystemExit("template statement no longer true: " + msg)


def p1(x):
    """Share as a percentage with one decimal."""
    return f"{x * 100:.1f}"


def p0(x):
    return f"{x * 100:.0f}"


def pp(x):
    """Change in a share, in percentage points, no decimals, with a sign word left to the text."""
    return f"{abs(x) * 100:.0f}"


def r2(x):
    return f"{x:.2f}"


def ci(c):
    return f"{c[0]:.2f} to {c[1]:.2f}"


def mins(x):
    return "not reached" if x is None else f"{x:.0f}"


def load():
    return {k: json.loads((OUT / f"{k}.json").read_text(encoding="utf-8")) for k in ("facilities", "population", "scenarios", "comparisons", "sources", "paired")}


def build(J):
    F, P, S, C = J["facilities"], J["population"], J["scenarios"], J["comparisons"]
    sc = S["scenarios"]
    nat = lambda k, m, lay=MAIN: (S["published"][m] if k == "published" else sc[k][m])[lay]["national"]  # noqa: E731
    h3 = lambda k, m: sc[k][m][MAIN]["herams_provinces"]  # noqa: E731
    cp = lambda a, b, m, t=60: C["pairs"][f"{a}|{b}|{m}|{t}"]  # noqa: E731
    ch = lambda a, b, m, t=60: C["herams"][f"{a}|{b}|{m}|{t}"]  # noqa: E731
    LA, LB, LH = F["lists"]["A"], F["lists"]["B"], F["lists"]["H"]
    M = F["matching"]
    v = {"date": date.today().strftime("%B %Y")}
    Q, SRC = J["paired"], J["sources"]
    osm_mod = SRC["osm/health_facilities.parquet"].get("hdx_resource_last_modified")
    need(osm_mod is not None, "sources.json records the HDX date of the OpenStreetMap file")
    od = date.fromisoformat(osm_mod[:10])
    v["osm_date"] = f"{od.day} {od.strftime('%B %Y')}"
    ex = LB["excluded_types"]
    need(LB["n_excluded"] == sum(ex.values()) == LB["n_features"] - LB["n_facility"] - LB["n_hospital"] - LB["n_pharmacy"],
         "the excluded OpenStreetMap features account for the rest of the file")
    v["b_excl"] = str(LB["n_excluded"])
    v["b_excl_list"] = ", ".join(f"`{t if '=' in t else 'amenity=' + t}` ({n})" for t, n in sorted(ex.items(), key=lambda x: -x[1]))
    v["b_pharm_used"] = str(LB["n_pharmacy_used"])
    need(sc["B_pharm"]["n_facilities"] - sc["B"]["n_facilities"] == LB["n_pharmacy_used"], "the pharmacy run adds exactly the used pharmacies")
    v["h_non_file"] = str(LH["status_latest"].get("Non-Functioning", 0))
    need(LH["status_latest"].get("Non-Functioning", 0) >= LH["status_used"].get("Non-Functioning", 0), "used non-functioning count is within the file count")

    # ---------------------------------------------------------------- data
    need(LA["n_rows_mozambique"] == LA["n_points"], "every list A row for Mozambique has coordinates")
    need(LB["n_pharmacy"] > 0 and "pharmacy" not in F["osm_rule"]["facility_amenity"], "pharmacies are left out of list B in the main run")
    st = LH["status_latest"]
    need(set(st) <= {"Fully Functioning", "Partially Functioning", "Non-Functioning", "missing"}, "HeRAMS status values are the three expected ones")
    need(LH["n_facilities"] < LH["n_rows"], "some HeRAMS rows repeat a facility")
    v.update({
        "a_rows": f"{LA['n_rows_mozambique']:,}", "a_used": f"{LA['n_used']:,}", "a_hosp": str(LA["n_hospital_used"]),
        "a_hosp_all": str(sum(n for t, n in LA["by_type"].items() if t.startswith("Hospital"))),
        "a_cs": f"{sum(n for t, n in LA['by_type'].items() if t.startswith('Centro')):,}",
        "a_ps": f"{LA['by_type'].get('Posto de Saúde', 0):,}",
        "b_feat": f"{LB['n_features']:,}", "b_used": f"{sc['B']['n_facilities']:,}",
        "b_hosp": str(LB["n_hospital_used"]), "b_pharm": str(LB["n_pharmacy"]), "b_poly": str(LB["n_polygons"]),
        "b_clinic": str(LB["amenity_counts"].get("clinic", 0)), "b_doctors": str(LB["amenity_counts"].get("doctors", 0)),
        "b_dentist": str(LB["amenity_counts"].get("dentist", 0)),
        "cross_n": f"{F['lists']['A_cross']['n_points']:,}",
        "h_rows": str(LH["n_rows"]), "h_fac": str(LH["n_facilities"]), "h_nocoord": str(LH["n_without_coords"]),
        "h_points": str(LH["n_points"]), "h_used": str(LH["n_used"]), "h_hosp": str(LH["n_hospital_used"]),
        "h_approx": str(LH["n_approx_coords"]), "h_shift": str(LH["n_coord_column_shift_fixed"]),
        "h_full": str(LH["status_used"].get("Fully Functioning", 0)), "h_part": str(LH["status_used"].get("Partially Functioning", 0)),
        "h_non": str(LH["status_used"].get("Non-Functioning", 0)), "h_miss": str(LH["status_used"].get("missing", 0)),
        "h_q_first": min(q for q in LH["latest_quarter"] if q != "nan").replace(" - ", " "),
        "h_q_last": max(q for q in LH["latest_quarter"] if q != "nan").replace(" - ", " "),
        "h_q_2024": str(sum(n for q, n in LH["latest_quarter"].items() if q.startswith("2024"))),
        "n_districts": str(F["districts"]["n"]), "n_prov": str(F["districts"]["n_provinces"]),
        "n_compared": str(C["n_compared"]), "n_excluded": str(F["districts"]["n"] - C["n_compared"]),
        "excluded": ", ".join(S["excluded_districts"]), "min_pop": f"{C['min_district_population']:,}",
        "n_compared_h": str(C["n_compared_herams"]),
        "pop_main": f"{P['layers'][MAIN]['total'] / 1e6:.1f}", "pop_alt": f"{P['layers'][ALT]['total'] / 1e6:.1f}",
        "grid_cells": f"{P['grid']['moz_cells']:,}",
    })
    need(sc["H_all"]["n_facilities"] - sc["H_func"]["n_facilities"] == LH["status_used"].get("Non-Functioning", 0),
         "the functioning rule removes exactly the non-functioning facilities")

    # ---------------------------------------------------------------- positional checks
    need(M["B_to_A"]["share_within_100m"] > 0.5, "more than half of list B lies within 100 m of a list A facility")
    need(M["B_to_A"]["median_km"] < 0.1, "the median distance from B to A is under 100 m")
    need(M["A_to_B"]["share_over_10km"] > 0.2, "over a fifth of list A has no list B facility within 10 km")
    v.update({
        "a_out": str(LA["n_outside_moz_over_1km"]), "a_out_max": f"{LA['max_outside_km']:.1f}",
        "b_out": str(LB["n_outside_moz_over_1km"]), "b_out_max": f"{LB['max_outside_km']:.1f}",
        "h_out": str(LH["n_outside_moz_over_1km"]), "h_out_max": f"{LH['max_outside_km']:.0f}", "h_mismatch": str(LH["n_province_mismatch"]),
        "a_mismatch": str(LA["n_province_mismatch"]),
        "a_sea": str(LA["n_in_sea_cell"]), "b_sea": str(LB["n_in_sea_cell"]), "h_sea": str(LH["n_in_sea_cell"]),
        "a_water": str(LA["n_in_inland_water_cell"]), "b_water": str(LB["n_in_inland_water_cell"]), "h_water": str(LH["n_in_inland_water_cell"]),
        "a_dup": str(LA["n_duplicate_coords"]), "b_dup": str(LB["n_duplicate_coords"]), "h_dup": str(LH["n_duplicate_coords"]),
        "ba_100": p0(M["B_to_A"]["share_within_100m"]), "ba_1k": p0(M["B_to_A"]["share_within_1km"]), "ba_med": f"{M['B_to_A']['median_km'] * 1000:.0f}",
        "ab_1k": p0(M["A_to_B"]["share_within_1km"]), "ab_10k": p0(M["A_to_B"]["share_over_10km"]),
        "mutual": str(M["mutual_A_B_within_1km"]),
        "ha_1k": p0(M["H_to_A"]["share_within_1km"]), "ha_10k": p0(M["H_to_A"]["share_over_10km"]), "ha_med": f"{M['H_to_A']['median_km'] * 1000:.0f}",
        "snap_a": str(sc["A"]["n_snapped_to_land"]), "snap_b": str(sc["B"]["n_snapped_to_land"]),
    })
    need(sc["A"]["n_not_placed"] == 0 and sc["B"]["n_not_placed"] == 0, "every used facility of lists A and B is placed on the grid")

    # ---------------------------------------------------------------- national results
    for k in ("A", "B", "AB", "A_hosp", "B_hosp", "AB_hosp", "published", "A_cross", "B_pharm", "A_sea"):
        for m in MODES:
            n = nat(k, m)
            v[f"{k}_{m[0]}60"] = p1(n["share_over_60"]); v[f"{k}_{m[0]}120"] = p1(n["share_over_120"]); v[f"{k}_{m[0]}med"] = mins(n["median_min"])
            n2 = nat(k, m, ALT)
            v[f"{k}_{m[0]}60u"] = p1(n2["share_over_60"])
    for m in MODES:
        need(nat("B", m)["share_over_60"] > nat("A", m)["share_over_60"] > nat("AB", m)["share_over_60"], f"B > A > A and B ({m})")
        need(nat("AB_hosp", m)["share_over_60"] > 3 * nat("AB", m)["share_over_60"] if m == "motorized" else nat("AB_hosp", m)["share_over_60"] > nat("AB", m)["share_over_60"] + 0.15,
             "hospital-only shares are much higher")
        # the population layer moves the national share more than switching facility lists
        d_pop = nat("A", m, ALT)["share_over_60"] - nat("A", m)["share_over_60"]
        d_list = nat("B", m)["share_over_60"] - nat("A", m)["share_over_60"]
        need(d_pop > d_list > 0, f"population layer changes the national share more than the list ({m})")
        v[f"dpop_{m[0]}"] = pp(d_pop); v[f"dlist_{m[0]}"] = pp(d_list)
        need(nat("AB", m, ALT)["share_over_60"] > nat("AB", m)["share_over_60"], "unconstrained population gives higher shares")
    unreach = nat("AB", "motorized")["unreachable_share"] * nat("AB", "motorized")["population"]
    v["unreach_k"] = f"{unreach / 1e3:.0f}"
    need(nat("A_sea", "motorized")["unreachable_share"] < nat("A", "motorized")["unreachable_share"], "opening the sea removes unreachable residents")

    # province table
    rows = []
    for prov in S["provinces"]:
        g = lambda k, m: sc[k][m][MAIN]["provinces"][prov]  # noqa: E731
        rows.append(f"| {prov} | {g('A', 'motorized')['population'] / 1e6:.1f} | {p1(g('A', 'motorized')['share_over_60'])} | "
                    f"{p1(g('B', 'motorized')['share_over_60'])} | {p1(g('AB', 'motorized')['share_over_60'])} | "
                    f"{p0(g('A', 'walking')['share_over_60'])} | {p0(g('B', 'walking')['share_over_60'])} | {p0(g('AB', 'walking')['share_over_60'])} |")
    n_ = lambda k, m: nat(k, m)  # noqa: E731
    rows.append(f"| **Mozambique** | **{n_('A', 'motorized')['population'] / 1e6:.1f}** | **{p1(n_('A', 'motorized')['share_over_60'])}** | "
                f"**{p1(n_('B', 'motorized')['share_over_60'])}** | **{p1(n_('AB', 'motorized')['share_over_60'])}** | "
                f"**{p0(n_('A', 'walking')['share_over_60'])}** | **{p0(n_('B', 'walking')['share_over_60'])}** | **{p0(n_('AB', 'walking')['share_over_60'])}** |")
    v["prov_table"] = "\n".join(rows)
    pa = {p: sc["A"]["motorized"][MAIN]["provinces"][p]["share_over_60"] for p in S["provinces"]}
    pb = {p: sc["B"]["motorized"][MAIN]["provinces"][p]["share_over_60"] for p in S["provinces"]}
    gap = {p: pb[p] - pa[p] for p in pa}
    pmax = max(gap, key=gap.get)
    v.update({"prov_gap_name": pmax, "prov_gap": pp(gap[pmax]), "prov_gap_a": p1(pa[pmax]), "prov_gap_b": p1(pb[pmax])})
    need(gap[pmax] > 0.15, "one province differs by more than 15 points between lists (motorized)")
    need(min(gap.values()) > -0.05, "no province is much better covered by list B than list A (motorized)")

    # ---------------------------------------------------------------- district comparisons
    def row(label, key_fn):
        a, b = key_fn("motorized"), key_fn("walking")
        return (f"| {label} | {r2(a['spearman'])} / {r2(b['spearman'])} | {pp(a['median_abs_change'])} / {pp(b['median_abs_change'])} | "
                f"{a['n_change_over_10pp']} / {b['n_change_over_10pp']} | {pp(a['max_abs_change'])} / {pp(b['max_abs_change'])} |")
    trows = [
        row("List A against list B", lambda m: cp("A", "B", m)),
        row("List A against lists A and B", lambda m: cp("A", "AB", m)),
        row("All facilities against hospitals (A and B)", lambda m: cp("AB", "AB_hosp", m)),
        row("List A against list A plus facilities across the border", lambda m: cp("A", "A_cross", m)),
        row("List B against list B with pharmacies", lambda m: cp("B", "B_pharm", m)),
        row("Sea closed against sea passable (list A)", lambda m: cp("A", "A_sea", m)),
        row("Constrained against unconstrained population (A and B)", lambda m: C["population_layer"][f"AB|{m}|60"]),
        row(f"HeRAMS: all used facilities against non-functioning removed ({C['n_compared_herams']} districts)", lambda m: ch("H_all", "H_func", m)),
        row(f"HeRAMS: all used facilities against fully functioning only ({C['n_compared_herams']} districts)", lambda m: ch("H_all", "H_fully", m)),
        row("List A against MAP's published layer (not independent)", lambda m: cp("A", "published", m)),
    ]
    v["cmp_table"] = "\n".join(trows)
    ab_m, ab_w = cp("A", "B", "motorized"), cp("A", "B", "walking")
    mo = C["modes"]["AB|60"]
    v.update({
        "ab_rho_m": r2(ab_m["spearman"]), "ab_ci_m": ci(ab_m["spearman_ci95"]), "ab_rho_w": r2(ab_w["spearman"]), "ab_ci_w": ci(ab_w["spearman_ci95"]),
        "ab_max_m": pp(ab_m["max_abs_change"]), "ab_max_m_d": ab_m["max_change_district"], "ab_max_w": pp(ab_w["max_abs_change"]), "ab_max_w_d": ab_w["max_change_district"],
        "ab_10_m": str(ab_m["n_change_over_10pp"]), "ab_10_w": str(ab_w["n_change_over_10pp"]),
        "ab_20_m": str(ab_m["n_change_over_20pp"]), "ab_20_w": str(ab_w["n_change_over_20pp"]),
        "ab_top_m": str(ab_m["top_k_overlap"]), "ab_top_w": str(ab_w["top_k_overlap"]), "top_k": str(ab_m["top_k"]),
        "ab_mrs_m": f"{ab_m['median_rank_shift']:.0f}", "ab_mrs_w": f"{ab_w['median_rank_shift']:.0f}",
        "aab_rho_m": r2(cp("A", "AB", "motorized")["spearman"]), "aab_rho_w": r2(cp("A", "AB", "walking")["spearman"]),
        "aab_10_m": str(cp("A", "AB", "motorized")["n_change_over_10pp"]), "aab_10_w": str(cp("A", "AB", "walking")["n_change_over_10pp"]),
        "mode_rho": r2(mo["spearman"]), "mode_ci": ci(mo["spearman_ci95"]), "mode_top": str(mo["top_k_overlap"]),
        "hosp_rho_m": r2(cp("AB", "AB_hosp", "motorized")["spearman"]), "hosp_rho_w": r2(cp("AB", "AB_hosp", "walking")["spearman"]),
        "hosp_top_m": str(cp("AB", "AB_hosp", "motorized")["top_k_overlap"]),
        "hab_rho_m": r2(cp("A_hosp", "B_hosp", "motorized")["spearman"]), "hab_10_m": str(cp("A_hosp", "B_hosp", "motorized")["n_change_over_10pp"]),
        "pop_rho_m": r2(C["population_layer"]["AB|motorized|60"]["spearman"]), "pop_rho_w": r2(C["population_layer"]["AB|walking|60"]["spearman"]),
        "pop_10_m": str(C["population_layer"]["AB|motorized|60"]["n_change_over_10pp"]),
        "pop_max_m": pp(C["population_layer"]["AB|motorized|60"]["max_abs_change"]), "pop_max_d": C["population_layer"]["AB|motorized|60"]["max_change_district"],
        "cross_max_m": pp(cp("A", "A_cross", "motorized")["max_abs_change"]), "cross_max_w": pp(cp("A", "A_cross", "walking")["max_abs_change"]),
        "cross_d_w": cp("A", "A_cross", "walking")["max_change_district"],
        "pharm_10_w": str(cp("B", "B_pharm", "walking")["n_change_over_10pp"]),
        "pharm_max_w": pp(cp("B", "B_pharm", "walking")["max_abs_change"]), "pharm_d_w": cp("B", "B_pharm", "walking")["max_change_district"],
        "sea_max_m": pp(cp("A", "A_sea", "motorized")["max_abs_change"]), "sea_d_m": cp("A", "A_sea", "motorized")["max_change_district"],
        "sea_max_w": pp(cp("A", "A_sea", "walking")["max_abs_change"]),
    })
    UB = F["used_by_district"]
    for key in ("ab_max_m_d", "ab_max_w_d"):
        need(UB["B"][v[key]] == 0, f"list B has no facility in {v[key]}")
    v["ab_max_m_na"] = str(UB["A"][v["ab_max_m_d"]]); v["ab_max_w_na"] = str(UB["A"][v["ab_max_w_d"]])
    hm, hw = cp("AB", "AB_hosp", "motorized"), cp("AB", "AB_hosp", "walking")
    v["hosp_ci_m"] = ci(hm["spearman_ci95"]); v["hosp_ci_w"] = ci(hw["spearman_ci95"])
    overlap = lambda a, b: a[0] <= b[1] and b[0] <= a[1]  # noqa: E731
    for m, other in (("motorized", hm), ("walking", hw), ("motorized", mo), ("walking", mo)):
        need(overlap(cp("A", "B", m)["spearman_ci95"], other["spearman_ci95"]), f"separate intervals overlap ({m})")
    for k, key in (("hosp", "list_vs_hospitals"), ("mode", "list_vs_mode"), ("pop", "list_vs_population")):
        for m in MODES:
            q = Q[f"{key}|{m}"]
            v[f"pd_{k}_{m[0]}"] = f"{q['diff']:.2f}".replace("-", "−"); v[f"pd_{k}_{m[0]}_ci"] = ci(q["ci95"]).replace("-", "−")
    need(Q["list_vs_hospitals|motorized"]["ci95"][0] > 0 and Q["list_vs_mode|motorized"]["ci95"][0] > 0, "paired intervals exclude zero by motor")
    need(Q["list_vs_hospitals|walking"]["ci95"][0] < 0 < Q["list_vs_hospitals|walking"]["ci95"][1]
         and Q["list_vs_mode|walking"]["ci95"][0] < 0 < Q["list_vs_mode|walking"]["ci95"][1], "paired intervals include zero on foot")
    for m in MODES:
        need(Q[f"list_vs_population|{m}"]["ci95"][0] < 0 < Q[f"list_vs_population|{m}"]["ci95"][1], f"population and list not separable ({m})")
    need(ab_m["spearman"] < cp("A", "AB", "motorized")["spearman"], "adding list B to A changes rankings less than replacing A with B")
    need(cp("A", "A_cross", "motorized")["n_change_over_10pp"] == 0, "cross-border facilities move no district by more than 10 points (motorized)")
    need(mo["spearman"] < ab_m["spearman"], "mode changes district rankings more than the facility list (motorized)")
    for m in MODES:
        need(cp("AB", "AB_hosp", m)["spearman"] < cp("A", "B", m)["spearman"], f"hospitals only reorders districts more than the list ({m})")
        popr = C["population_layer"][f"AB|{m}|60"]["spearman"]
        need(abs(popr - cp("A", "B", m)["spearman"]) < 0.1, f"population layer reorders about as much as the list ({m})")
        small = max(1 - cp("A", "A_cross", m)["spearman"], 1 - cp("B", "B_pharm", m)["spearman"], 1 - cp("A", "A_sea", m)["spearman"])
        need(small < 1 - max(cp("A", "B", m)["spearman"], popr), f"border, pharmacies and sea reorder least ({m})")

    # agreement with the published layer
    pc = C["published_cells"]
    need(pc["A|motorized"]["spearman_every_7th_cell"] > 0.99, "list A reproduces the published motorized layer closely")
    need(pc["A|motorized"]["spearman_every_7th_cell"] > pc["B|motorized"]["spearman_every_7th_cell"], "list A is closer to the published layer than list B")
    v.update({"pub_cell_a_m": f"{pc['A|motorized']['spearman_every_7th_cell']:.3f}", "pub_cell_a_w": f"{pc['A|walking']['spearman_every_7th_cell']:.3f}",
              "pub_cell_b_m": f"{pc['B|motorized']['spearman_every_7th_cell']:.2f}",
              "pub_med_a_m": f"{pc['A|motorized']['median_diff_min']:.1f}", "pub_p95_a_m": f"{pc['A|motorized']['p95_diff_min']:.1f}",
              "pub_rho_a_m": r2(cp("A", "published", "motorized")["spearman"]), "pub_rho_a_w": r2(cp("A", "published", "walking")["spearman"]),
              "pub_rho_b_m": r2(cp("B", "published", "motorized")["spearman"])})

    # random removal
    dr = C["drop10"]
    v.update({"drop_share": p0(dr["A|motorized"]["share_dropped"]), "drop_runs": str(dr["A|motorized"]["runs"]),
              "drop_a_m_lo": p1(dr["A|motorized"]["national_share_over_60_min"]), "drop_a_m_hi": p1(dr["A|motorized"]["national_share_over_60_max"]),
              "drop_a_w_lo": p1(dr["A|walking"]["national_share_over_60_min"]), "drop_a_w_hi": p1(dr["A|walking"]["national_share_over_60_max"]),
              "drop_a_m_dmed": pp(dr["A|motorized"]["district_max_abs_change_median"]), "drop_a_m_dmax": pp(dr["A|motorized"]["district_max_abs_change_max"]),
              "drop_a_w_dmed": pp(dr["A|walking"]["district_max_abs_change_median"]), "drop_a_w_dmax": pp(dr["A|walking"]["district_max_abs_change_max"])})
    need(dr["A|motorized"]["national_share_over_60_max"] - dr["A|motorized"]["national_share_over_60_min"] < 0.02, "national share is stable when 10% of list A is dropped")
    need(dr["A|motorized"]["district_max_abs_change_median"] > 0.10, "single districts move by more than 10 points when 10% of list A is dropped")

    # ---------------------------------------------------------------- HeRAMS
    for k in ("H_all", "H_func", "H_fully", "A", "AB"):
        for m in MODES:
            v[f"{k}_h3_{m[0]}60"] = p1(h3(k, m)["share_over_60"])
    hf_m, hf_w = ch("H_all", "H_func", "motorized"), ch("H_all", "H_func", "walking")
    hs_m, hs_w = ch("H_all", "H_fully", "motorized"), ch("H_all", "H_fully", "walking")
    v.update({"hf_max_m": pp(hf_m["max_abs_change"]), "hf_d_m": hf_m["max_change_district"], "hf_max_w": pp(hf_w["max_abs_change"]), "hf_d_w": hf_w["max_change_district"],
              "hf_10_w": str(hf_w["n_change_over_10pp"]), "hs_10_w": str(hs_w["n_change_over_10pp"]), "hs_10_m": str(hs_m["n_change_over_10pp"]),
              "hs_max_w": pp(hs_w["max_abs_change"]), "hs_d_w": hs_w["max_change_district"], "hs_max_m": pp(hs_m["max_abs_change"]), "hs_d_m": hs_m["max_change_district"],
              "hs_rho_w": r2(hs_w["spearman"]), "hs_ci_w": ci(hs_w["spearman_ci95"]),
              "ah_rho_m": r2(ch("A", "H_all", "motorized")["spearman"]), "ah_rho_w": r2(ch("A", "H_all", "walking")["spearman"])})
    need(abs(h3("H_func", "walking")["share_over_60"] - h3("H_all", "walking")["share_over_60"]) < 0.01, "removing non-functioning facilities barely moves the three-province share")
    need(h3("H_fully", "walking")["share_over_60"] > h3("H_func", "walking")["share_over_60"], "the strict rule raises the share")
    D = S["district_names"]; DP = dict(zip(D, S["district_provinces"]))
    need(DP[hs_m["max_change_district"]] == DP[hs_w["max_change_district"]] == DP[hf_m["max_change_district"]], "largest HeRAMS changes are in one province")
    need(hs_m["max_change_district"] == hs_w["max_change_district"], "the strict rule's largest change is in the same district in both modes")
    v["hs_d"] = hs_m["max_change_district"]
    v["hs_prov"] = DP[hs_m["max_change_district"]]
    need(DP["Cidade De Maputo"] == "Maputo", "Maputo city is part of Maputo province in the ADM1 layer")
    need(hf_w["n_change_over_10pp"] <= 3, "only a few districts move by more than 10 points when non-functioning facilities are removed")

    t = (ROOT / "paper" / "template.md").read_text(encoding="utf-8")
    missing = sorted(set(re.findall(r"\{\{(\w+)\}\}", t)) - set(v))
    if missing:
        raise SystemExit("no value for placeholder(s): " + ", ".join(missing))
    out = re.sub(r"\{\{(\w+)\}\}", lambda m: v[m.group(1)], t)
    if "{{" in out or "}}" in out:
        raise SystemExit("unfilled placeholder")
    return out


def main():
    (ROOT / "paper" / "paper.md").write_text(build(load()), encoding="utf-8")
    print("wrote paper/paper.md")


if __name__ == "__main__":
    sys.exit(main())
