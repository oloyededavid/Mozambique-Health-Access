"""Download every source file into data/raw/ (not committed) and record size, SHA-256 and the access date in
outputs/sources.json. Files already present are not downloaded again; their hashes are recorded.

    python scripts/s00_download.py
"""
import hashlib
import json
import sys
import urllib.request
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from access import OUT, RAW  # noqa: E402

BBOX = (29.2, -27.9, 41.9, -9.4)  # lon min, lat min, lon max, lat max: Mozambique plus about 1 degree
WCS = ("https://data.malariaatlas.org/geoserver/Accessibility/wcs?service=WCS&version=2.0.1&request=GetCoverage"
       f"&subset=Long({BBOX[0]},{BBOX[2]})&subset=Lat({BBOX[1]},{BBOX[3]})&format=image/tiff&coverageId=")
GB = "https://media.githubusercontent.com/media/wmgeolab/geoBoundaries/9469f09/releaseData/gbOpen/MOZ"

SOURCES = {
    "maina/ssa_mfl.xlsx": ("https://ndownloader.figshare.com/files/14379593",
                           "Maina et al. (2019) public-sector health facilities, sub-Saharan Africa (figshare 7725374, file '00 SSA MFL (130219).xlsx'), CC0"),
    "osm/health_facilities.parquet": ("https://production-raw-data-api.s3.amazonaws.com/ISO3/MOZ/_layers/osm/health_facilities.parquet",
                                      "HOT OpenStreetMap export, health facilities of Mozambique (HDX hotosm_moz_health_facilities), ODbL"),
    "herams/moz_herams_2022-2024_by-qtr.xlsx": (
        "https://data.humdata.org/dataset/0dd449f0-558d-4e30-9f7b-cedbeef8949e/resource/2aeb63f8-f5d1-4860-a9dd-f2df437d7e8c/download/moz_herams_2022-2024_by-qtr.xlsx",
        "WHO HeRAMS Mozambique 2022-2024 by quarter (HDX 'Mozambique: Health Facilities'), CC BY"),
    "friction/motorized_2020.tif": (WCS + "Accessibility__202001_Global_Motorized_Friction_Surface",
                                    "Malaria Atlas Project motorized friction surface 2020 (Weiss et al., 2020), minutes per metre"),
    "friction/walking_2020.tif": (WCS + "Accessibility__202001_Global_Walking_Only_Friction_Surface",
                                  "Malaria Atlas Project walking-only friction surface 2020 (Weiss et al., 2020), minutes per metre"),
    "mapwcs/tt_health_motorized_2020.tif": (WCS + "Accessibility__202001_Global_Motorized_Travel_Time_to_Healthcare",
                                            "Malaria Atlas Project published motorized travel time to healthcare 2020 (Weiss et al., 2020)"),
    "mapwcs/tt_health_walking_2020.tif": (WCS + "Accessibility__202001_Global_Walking_Only_Travel_Time_To_Healthcare",
                                          "Malaria Atlas Project published walking-only travel time to healthcare 2020 (Weiss et al., 2020)"),
    "worldpop/moz_pop_2020_CN_100m_R2025A_v1.tif": (
        "https://data.worldpop.org/GIS/Population/Global_2015_2030/R2025A/2020/MOZ/v1/100m/constrained/moz_pop_2020_CN_100m_R2025A_v1.tif",
        "WorldPop Global2 R2025A v1, Mozambique 2020, constrained, 100 m (doi:10.5258/SOTON/WP00839)"),
    "worldpop/moz_ppp_2020.tif": ("https://data.worldpop.org/GIS/Population/Global_2000_2020/2020/MOZ/moz_ppp_2020.tif",
                                  "WorldPop Global 2000-2020, Mozambique 2020, unconstrained, 100 m"),
    "boundaries/moz_ADM0.geojson": (f"{GB}/ADM0/geoBoundaries-MOZ-ADM0.geojson", "geoBoundaries gbOpen MOZ ADM0 (commit 9469f09)"),
    "boundaries/moz_ADM1.geojson": (f"{GB}/ADM1/geoBoundaries-MOZ-ADM1.geojson", "geoBoundaries gbOpen MOZ ADM1 (commit 9469f09)"),
    "boundaries/moz_ADM2.geojson": (f"{GB}/ADM2/geoBoundaries-MOZ-ADM2.geojson", "geoBoundaries gbOpen MOZ ADM2 (commit 9469f09)"),
    "boundaries/moz_ADM1_simplified.geojson": (f"{GB}/ADM1/geoBoundaries-MOZ-ADM1_simplified.geojson", "geoBoundaries ADM1, simplified"),
    "boundaries/moz_ADM2_simplified.geojson": (f"{GB}/ADM2/geoBoundaries-MOZ-ADM2_simplified.geojson", "geoBoundaries ADM2, simplified"),
    "boundaries/adm2_meta.json": ("https://www.geoboundaries.org/api/current/gbOpen/MOZ/ADM2/", "geoBoundaries API record for MOZ ADM2"),
}


HDX = {  # dataset name on the Humanitarian Data Exchange for sources published there: its update date is recorded
    "osm/health_facilities.parquet": "hotosm_moz_health_facilities",
    "herams/moz_herams_2022-2024_by-qtr.xlsx": "health-cluster-mozambique",
}


def hdx_dates(name, url):
    """Last-modified dates of an HDX dataset and of the resource with this download address."""
    with urllib.request.urlopen(f"https://data.humdata.org/api/3/action/package_show?id={name}", timeout=60) as r:
        m = json.load(r)["result"]
    res = [x for x in m["resources"] if x.get("url") == url or x.get("download_url") == url]
    return {"hdx_dataset": name, "hdx_dataset_last_modified": m.get("last_modified"),
            "hdx_resource_last_modified": res[0].get("last_modified") if res else None}


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    OUT.mkdir(exist_ok=True)
    old = json.loads((OUT / "sources.json").read_text()) if (OUT / "sources.json").exists() else {}
    rec = {}
    for rel, (url, note) in SOURCES.items():
        p = RAW / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        fresh = not p.exists()
        if fresh:
            print("downloading", rel)
            urllib.request.urlretrieve(url, p)
        accessed = date.today().isoformat() if fresh or rel not in old else old[rel]["accessed"]
        rec[rel] = {"url": url, "note": note, "bytes": p.stat().st_size, "sha256": sha256(p), "accessed": accessed}
        if rel in HDX:
            try:
                rec[rel].update(hdx_dates(HDX[rel], url))
            except OSError as e:   # keep what was recorded before if HDX cannot be reached
                rec[rel].update({k: v for k, v in old.get(rel, {}).items() if k.startswith("hdx_")})
                print("HDX not reached:", e)
    (OUT / "sources.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print("wrote outputs/sources.json")


if __name__ == "__main__":
    main()
