"""Read the three facility sources, apply the inclusion rules, locate every facility in a province and district,
and run the positional checks. Writes data/derived/facilities.parquet, data/derived/districts.parquet,
docs/data/facilities.csv and outputs/facilities.json.

    python scripts/s01_facilities.py
"""
import json
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
import access as A  # noqa: E402

AEQD = "+proj=aeqd +lat_0=-18.5 +lon_0=35.5 +datum=WGS84 +units=m"   # distances in metres around Mozambique
NEIGHBOURS = ["Malawi", "Tanzania", "Zambia", "Zimbabwe", "South Africa", "eSwatini"]
BORDER_TOL_M = 1000   # facilities up to 1 km outside the national outline are kept (coastline and border detail)


def districts():
    a1 = gpd.read_file(A.RAW / "boundaries" / "moz_ADM1.geojson")[["shapeName", "geometry"]].rename(columns={"shapeName": "province"})
    a2 = gpd.read_file(A.RAW / "boundaries" / "moz_ADM2.geojson")[["shapeName", "shapeID", "geometry"]].rename(columns={"shapeName": "district"})
    # province of a district = the province with the largest overlap (outlines do not match exactly at the edges)
    a1p, a2p = a1.to_crs(AEQD), a2.to_crs(AEQD)
    ov = gpd.overlay(a2p[["shapeID", "geometry"]], a1p, how="intersection", keep_geom_type=True)
    ov["area"] = ov.area
    prov = ov.sort_values("area").groupby("shapeID").tail(1).set_index("shapeID")["province"]
    a2["province"] = a2.shapeID.map(prov)
    a2["area_km2"] = a2p.area.values / 1e6
    a2 = a2.sort_values(["province", "district"]).reset_index(drop=True)
    a2["district_id"] = np.arange(len(a2))
    return a1, a2


def locate(df, a1, a2, a0p):
    g = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.lon, df.lat), crs="EPSG:4326")
    j = gpd.sjoin(g, a2[["district_id", "province", "geometry"]], how="left", predicate="within")
    j = j[~j.index.duplicated()]
    df = df.copy()
    df["district_id"] = j["district_id"].fillna(-1).astype(int).values
    df["province_loc"] = j["province"].values
    gp = g.to_crs(AEQD)
    df["dist_outside_m"] = gp.distance(a0p).values   # 0 inside the national outline
    # points just outside (coast) take the nearest district
    miss = (df.district_id < 0) & (df.dist_outside_m <= BORDER_TOL_M)
    if miss.any():
        a2p = a2.to_crs(AEQD)
        for i in np.where(miss)[0]:
            k = int(a2p.distance(gp.geometry.iloc[i]).values.argmin())
            df.iloc[i, df.columns.get_loc("district_id")] = int(a2.district_id.iloc[k])
            df.iloc[i, df.columns.get_loc("province_loc")] = a2.province.iloc[k]
    return df


def grid_flags(df):
    with rasterio.open(A.RAW / "mapwcs" / "tt_health_motorized_2020.tif") as s:
        sea = s.read(1) == s.nodata
        T = s.transform
    with rasterio.open(A.RAW / "friction" / "walking_2020.tif") as s:
        walk = s.read(1)
    r, c = A.cells_for_points(df.lon.values, df.lat.values, T.c, T.f, T.a, sea.shape)
    ins = r >= 0
    in_sea = np.zeros(len(df), bool); in_water = np.zeros(len(df), bool)
    in_sea[ins] = sea[r[ins], c[ins]]
    in_water[ins] = (walk[r[ins], c[ins]] >= 0.0599) & ~in_sea[ins]   # inland water: walking friction of 1 km/h
    return in_sea, in_water


def nearest_m(src, dst):
    """Distance in metres from each src point to the nearest dst point (both DataFrames with lon, lat)."""
    t = cKDTree(np.c_[dst.lon.values * np.cos(np.radians(-18.5)), dst.lat.values])
    _, k = t.query(np.c_[src.lon.values * np.cos(np.radians(-18.5)), src.lat.values], k=1)
    return A.haversine_m(src.lon.values, src.lat.values, dst.lon.values[k], dst.lat.values[k]), k


def load_maina():
    d = pd.read_excel(A.RAW / "maina" / "ssa_mfl.xlsx", sheet_name="SSA MFL")
    keep = d.Country.isin(["Mozambique"] + NEIGHBOURS)
    d = d[keep].copy()
    out = pd.DataFrame({
        "list": np.where(d.Country == "Mozambique", "A", "A_cross"),
        "src_id": d.index.astype(str), "name": d["Facility name"].astype(str), "type": d["Facility type"].astype(str),
        "country": d.Country, "admin1_reported": d.Admin1.astype(str),
        "lon": pd.to_numeric(d.Long, errors="coerce"), "lat": pd.to_numeric(d.Lat, errors="coerce"),
    })
    out["hospital"] = out["type"].map(A.maina_is_hospital)
    out["class"] = np.where(out.hospital, "hospital", "facility")
    lo, la0, hi, la1 = 29.2, -27.9, 41.9, -9.4
    cross = (out.list == "A_cross") & out.lon.between(lo, hi) & out.lat.between(la0, la1)
    return out[(out.list == "A") | cross].reset_index(drop=True), int((d.Country == "Mozambique").sum())


def load_osm():
    g = gpd.read_parquet(A.RAW / "osm" / "health_facilities.parquet")
    n_all = len(g)
    amen = g["amenity"].value_counts(dropna=False)
    cls = [A.osm_class(a, h) for a, h in zip(g["amenity"], g["healthcare"])]
    g["class"] = cls
    pts = g.geometry.to_crs(AEQD).representative_point().to_crs("EPSG:4326")   # polygons (buildings, grounds) become one point
    out = pd.DataFrame({
        "list": "B", "src_id": g["id"].astype(str), "name": g["name"].fillna("").astype(str),
        "type": g["amenity"].fillna("healthcare=" + g["healthcare"].fillna("none")).astype(str), "country": "Mozambique",
        "admin1_reported": g["adm1_name"].fillna("").astype(str), "lon": pts.x.values, "lat": pts.y.values, "class": g["class"],
        "geom_type": g.geometry.geom_type.values,
    })
    out["hospital"] = out["class"] == "hospital"
    excluded = out[out["class"].isna()]["type"].value_counts().to_dict()
    out = out[out["class"].notna()].reset_index(drop=True)
    return out, n_all, {str(k): int(v) for k, v in amen.items()}, {str(k): int(v) for k, v in excluded.items()}


def province_match(reported, located, list_code):
    """Whether a facility's point falls in the province its source reports. None when it cannot be checked
    (list B, or a point outside every province). List A's 'Maputo Cidade' and 'Maputo Provincia' both count as
    Maputo, because Maputo city is part of Maputo in the geoBoundaries ADM1 layer used here."""
    if list_code not in ("A", "H") or not isinstance(located, str) or not isinstance(reported, str):
        return None
    rep = reported.replace(" Provincia", "").replace(" Cidade", "")
    return A.norm_text(rep) == A.norm_text(located)


def herams_latest(raw):
    """One row per HeRAMS facility from the assessment rows. Facility codes are reused across different facilities,
    so a facility is its cleaned name plus its 'Province / District' label. The latest assessment gives the status;
    coordinates come from the latest assessment that has them. One known row has its coordinates one column to the
    right (a road name in the latitude field) and is shifted back."""
    d = raw.copy()
    d["name_clean"] = d.MoSD2.map(A.fix_mojibake).astype(str).str.strip()
    d["prov_rep"] = d.GEO1.astype(str).str.split("/").str[0].str.strip()
    d["dist_rep"] = d.GEO1.astype(str).str.split("/").str[1].str.strip()
    d["key"] = d.name_clean.map(A.norm_text) + "|" + d.GEO1.map(A.norm_text)
    d["qkey"] = d.Quarter.map(A.quarter_key)
    lat = pd.to_numeric(d.MoSDGPS_SQ001, errors="coerce"); lon = pd.to_numeric(d.MoSDGPS_SQ002, errors="coerce")
    fix = pd.Series("as given", index=d.index)
    shifted = lat.isna() & d.MoSDGPS_SQ001.notna() & pd.to_numeric(d.MoSDGPS1, errors="coerce").notna()
    lat = lat.where(~shifted, pd.to_numeric(d.MoSDGPS_SQ002, errors="coerce"))
    lon = lon.where(~shifted, pd.to_numeric(d.MoSDGPS1, errors="coerce"))
    fix[shifted] = "shifted column"
    d["lat"], d["lon"], d["coord_fix"] = lat, lon, fix
    d = d.sort_values(["key", "qkey", "date"])
    latest = d.groupby("key").tail(1).set_index("key")
    coords = d[d.lat.notna() & d.lon.notna()].groupby("key").tail(1).set_index("key")[["lat", "lon", "coord_fix"]]
    latest = latest.drop(columns=["lat", "lon", "coord_fix"]).join(coords, how="left")
    out = pd.DataFrame({
        "list": "H", "src_id": latest.index, "name": latest.name_clean, "type": latest.MoSD3.astype(str), "country": "Mozambique",
        "admin1_reported": latest.prov_rep, "district_reported": latest.dist_rep, "lon": latest.lon.values, "lat": latest.lat.values,
        "quarter": latest.Quarter.astype(str), "status": latest.HFFUNCT.where(latest.HFFUNCT.notna(), None),
        "approx_coords": latest.MoSDGPS1.astype(str).eq("Yes").values, "coord_fix": latest.coord_fix.fillna("none").values,
    }).reset_index(drop=True)
    out["hospital"] = out["type"].str.contains("hospital", case=False, na=False)
    out["class"] = np.where(out.hospital, "hospital", "facility")
    return out


def load_herams():
    raw = pd.read_excel(A.RAW / "herams" / "moz_herams_2022-2024_by-qtr.xlsx", sheet_name="HeRAMS_Cabo_Nampula_Zambezia", header=1)
    return herams_latest(raw), len(raw), int(raw.subject_id.nunique())


def main():
    A.DERIVED.mkdir(parents=True, exist_ok=True); A.OUT.mkdir(exist_ok=True); A.DOCS_DATA.mkdir(parents=True, exist_ok=True)
    a1, a2 = districts()
    a0 = gpd.read_file(A.RAW / "boundaries" / "moz_ADM0.geojson")
    a0p = a0.to_crs(AEQD).geometry.iloc[0]
    a2.drop(columns="geometry").to_parquet(A.DERIVED / "districts.parquet")

    fa, n_maina_moz = load_maina()
    fb, n_osm_all, osm_amenity, osm_excluded = load_osm()
    fh, n_h_rows, n_h_subjects = load_herams()
    fh_coords = fh[fh.lat.notna() & fh.lon.notna()].copy()
    fac = pd.concat([fa, fb, fh_coords], ignore_index=True)
    fac = locate(fac, a1, a2, a0p)
    fac["in_sea"], fac["in_inland_water"] = grid_flags(fac)
    fac["inside_moz"] = fac.dist_outside_m <= BORDER_TOL_M
    # HeRAMS: does the point fall in the province it reports?
    fac["province_match"] = [province_match(p, q, l) for p, q, l in zip(fac.admin1_reported, fac.province_loc, fac.list)]
    # HeRAMS facilities whose point is outside the province they report are not used (coordinates not trusted)
    fac["use"] = True
    fac.loc[fac.list.isin(["A", "B", "H"]) & ~fac.inside_moz, "use"] = False
    fac.loc[(fac.list == "H") & (fac.province_match != True), "use"] = False  # noqa: E712
    fac.loc[fac.list == "A_cross", "use"] = True
    fac.to_parquet(A.DERIVED / "facilities.parquet")

    # ------------------------------------------------------------ summary
    def lst(code):
        return fac[fac.list == code]
    S = {"lists": {}}
    for code, label in (("A", "Maina et al. (2019)"), ("B", "OpenStreetMap (HOT export)"), ("H", "HeRAMS 2022-2024")):
        x = lst(code)
        S["lists"][code] = {
            "label": label, "n_points": int(len(x)), "n_used": int(x.use.sum()),
            "n_hospital_used": int((x.use & x.hospital).sum()),
            "n_outside_moz_over_1km": int((~x.inside_moz).sum()),
            "max_outside_km": float(x.dist_outside_m.max() / 1000),
            "n_in_sea_cell": int(x.in_sea.sum()), "n_in_inland_water_cell": int(x.in_inland_water.sum()),
            "n_duplicate_coords": int(x.duplicated(["lon", "lat"]).sum()),
            "n_province_mismatch": int((x.province_match == False).sum()) if code in ("A", "H") else None,  # noqa: E712
            "by_province_used": {k: int(v) for k, v in x[x.use].province_loc.value_counts().sort_index().items()},
        }
    S["lists"]["A"]["n_rows_mozambique"] = n_maina_moz
    S["lists"]["A"]["by_type"] = {k: int(v) for k, v in lst("A").type.value_counts().items()}
    S["lists"]["A_cross"] = {"n_points": int(len(lst("A_cross"))), "by_country": {k: int(v) for k, v in lst("A_cross").country.value_counts().items()}}
    S["lists"]["B"].update({"n_features": n_osm_all, "amenity_counts": osm_amenity, "excluded_types": osm_excluded,
                            "n_facility": int((lst("B")["class"] == "facility").sum()), "n_hospital": int((lst("B")["class"] == "hospital").sum()),
                            "n_pharmacy": int((lst("B")["class"] == "pharmacy").sum()),
                            "n_polygons": int((lst("B").geom_type != "Point").sum())})
    hb = fh
    S["lists"]["H"].update({
        "n_rows": n_h_rows, "n_subject_ids": n_h_subjects, "n_facilities": int(len(hb)),
        "n_without_coords": int((hb.lat.isna() | hb.lon.isna()).sum()),
        "n_coord_column_shift_fixed": int((hb.coord_fix == "shifted column").sum()),
        "n_approx_coords": int(hb.approx_coords.sum()),
        "latest_quarter": {k: int(v) for k, v in hb.quarter.value_counts().sort_index().items()},
        "status_latest": {str(k): int(v) for k, v in hb.status.fillna("missing").value_counts().items()},
        "status_used": {str(k): int(v) for k, v in lst("H")[lst("H").use].status.fillna("missing").value_counts().items()},
        "provinces": list(A.HERAMS_PROVINCES),
    })
    # cross-list positions: how far is each facility from the nearest one in the other list
    a, b = lst("A")[lst("A").use], lst("B")[lst("B").use & (lst("B")["class"] != "pharmacy")]
    h = lst("H")[lst("H").use]
    match = {}
    for name, src, dst in (("A_to_B", a, b), ("B_to_A", b, a),
                           ("A_to_H", a[a.province_loc.isin(["Cabo Delgado", "Nampula", "Zambézia"])], h),
                           ("H_to_A", h, a)):
        dm, _ = nearest_m(src, dst)
        match[name] = {"n": int(len(dm)), "median_km": float(np.median(dm) / 1000),
                       "share_within_100m": float((dm <= 100).mean()), "share_within_1km": float((dm <= 1000).mean()), "share_within_5km": float((dm <= 5000).mean()),
                       "share_over_10km": float((dm > 10000).mean())}
    dab, kab = nearest_m(a, b); dba, kba = nearest_m(b, a)
    mutual = (kba[kab] == np.arange(len(a))) & (dab <= 1000)
    match["mutual_A_B_within_1km"] = int(mutual.sum())
    S["matching"] = match
    # facilities used per district, for statements such as "list B has no facility in this district"
    used = fac[fac.use & (fac.district_id >= 0)]
    S["used_by_district"] = {code: {a2.district.iloc[i]: int(((used.list == code) & (used.district_id == a2.district_id.iloc[i]) &
                                                               (used["class"] != "pharmacy")).sum()) for i in range(len(a2))}
                             for code in ("A", "B", "H")}
    S["lists"]["B"]["n_pharmacy_used"] = int((lst("B").use & (lst("B")["class"] == "pharmacy")).sum())
    S["lists"]["B"]["n_excluded"] = int(sum(osm_excluded.values()))
    S["districts"] = {"n": int(len(a2)), "n_provinces": int(a1.shape[0]), "provinces": sorted(a1.province.tolist())}
    S["border_tolerance_m"] = BORDER_TOL_M
    S["osm_rule"] = {"facility_amenity": sorted(A.OSM_HEALTH_AMENITY - {"hospital"}), "hospital": "amenity=hospital, or healthcare=hospital when amenity is missing",
                     "excluded_main": ["pharmacy", "dentist"], "pharmacy_sensitivity": True}
    (A.OUT / "facilities.json").write_text(json.dumps(S, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    pub = fac[fac.list.isin(["A", "B", "H"])][["list", "name", "type", "class", "lon", "lat", "province_loc", "district_id", "inside_moz",
                                               "in_sea", "in_inland_water", "use", "status", "quarter"]].copy()
    pub["district"] = pub.district_id.map(a2.set_index("district_id").district)
    pub["lon"] = pub.lon.round(5); pub["lat"] = pub.lat.round(5)
    pub.drop(columns="district_id").to_csv(A.DOCS_DATA / "facilities.csv", index=False)
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if not isinstance(vv, dict)} for k, v in S["lists"].items()}, indent=1, ensure_ascii=False))
    print(json.dumps(S["matching"], indent=1))


if __name__ == "__main__":
    main()
