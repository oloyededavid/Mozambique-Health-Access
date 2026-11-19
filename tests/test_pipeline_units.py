"""Pipeline pieces on small synthetic inputs: HeRAMS de-duplication, province matching, population tables and the
paired bootstrap."""
import numpy as np
import pandas as pd
import pytest

from conftest import load


@pytest.fixture(scope="module")
def s01():
    return load("s01_facilities")


@pytest.fixture(scope="module")
def s02():
    return load("s02_grid")


def herams_rows():
    return pd.DataFrame({
        "MoSD2": ["CS Nahadje", "CS nahadje ", "CS Nahadje", "PS SaÃºde", "CS Other"],
        "GEO1": ["Nampula / Nacaroa"] * 4 + ["Nampula / Memba"],
        "Quarter": ["2022 - Q2", "2024 - Q2", "2023 - Q1", "2023 - Q4", "2024 - Q1"],
        "date": pd.to_datetime(["2022-05-01", "2024-05-01", "2023-02-01", "2023-11-01", "2024-02-01"]),
        "MoSDGPS_SQ001": [-14.42, None, -14.40, "ESTRADA N13", -13.9],
        "MoSDGPS_SQ002": [39.9, None, 39.8, -14.9, 40.5],
        "MoSDGPS1": ["Yes", None, "No", "37.6", "No"],
        "MoSD3": ["HF Type 2", "HF Type 2", "HF Type 2", "Health Post", "District Hospital"],
        "HFFUNCT": ["Fully Functioning", "Non-Functioning", "Partially Functioning", None, "Fully Functioning"],
    })


def test_herams_one_row_per_facility_latest_status(s01):
    out = s01.herams_latest(herams_rows())
    assert len(out) == 3                                   # name spacing and case do not split a facility
    nah = out[out.name.str.lower().str.startswith("cs nahadje")].iloc[0]
    assert nah.quarter == "2024 - Q2" and nah.status == "Non-Functioning"   # latest assessment gives the status
    assert (nah.lat, nah.lon) == (-14.40, 39.8)            # coordinates from the latest assessment that has them
    ps = out[out.name == "PS Saúde"].iloc[0]                # mojibake repaired, shifted coordinates moved back
    assert ps.coord_fix == "shifted column" and (ps.lat, ps.lon) == (-14.9, 37.6)
    assert bool(out[out.name == "CS Other"].iloc[0].hospital)


def test_province_match(s01):
    assert s01.province_match("Zambezia", "Zambézia", "H") is True
    assert s01.province_match("Nampula", "Zambézia", "H") is False
    assert s01.province_match("Maputo Cidade", "Maputo", "A") is True
    assert s01.province_match("Maputo Provincia", "Maputo", "A") is True
    assert s01.province_match("Nampula", None, "H") is None    # point outside every province: not checked
    assert s01.province_match("Nampula", "Nampula", "B") is None


def test_pop_table_on_a_synthetic_raster(s02, tmp_path):
    import geopandas as gpd
    import rasterio
    from rasterio.transform import from_origin
    from shapely.geometry import box
    path = tmp_path / "pop.tif"
    with rasterio.open(path, "w", driver="GTiff", width=20, height=20, count=1, dtype="float32", crs="EPSG:4326",
                       transform=from_origin(0.0, 0.0, 0.001, 0.001), nodata=-99999.0) as dst:
        a = np.ones((20, 20), "float32"); a[0, 0] = -99999.0
        dst.write(a, 1)
    T = from_origin(0.0, 0.0, 0.01, 0.01)                   # travel grid: 2 x 2 cells of 10 x 10 population cells
    passable = np.array([[True, False], [True, True]])     # the top-right cell is sea
    a2 = gpd.GeoDataFrame({"district_id": [0, 1]}, geometry=[box(0, -0.02, 0.01, 0), box(0.01, -0.02, 0.02, 0)], crs="EPSG:4326")
    tab, info = s02.pop_table(path, a2, T, passable)
    assert info["total"] == pytest.approx(399)             # one no-data cell
    assert info["moved_from_sea_cells"] == pytest.approx(100) and info["on_sea_not_placed"] == 0
    assert not (tab["fidx"] == 1).any()                     # nothing left on the sea cell
    by_d = np.bincount(tab["district"], weights=tab["pop"])
    assert by_d.tolist() == pytest.approx([199, 200])        # district from the 100 m cell, not from the travel cell
    by_cell = np.bincount(tab["fidx"], weights=tab["pop"], minlength=4)
    assert by_cell.tolist() == pytest.approx([99 + 100, 0, 100, 100])   # sea population goes to the nearest land cell (top left)


def test_paired_bootstrap_detects_a_clear_difference():
    s03b = load("s03b_paired")
    rng = np.random.default_rng(0)
    x = rng.uniform(size=150)
    same = s03b.paired_diff(x, x + rng.normal(0, 0.01, 150), x, rng.uniform(size=150), n_boot=300)
    assert same["diff"] > 0.5 and same["ci95"][0] > 0
    null = s03b.paired_diff(x, x, x, x, n_boot=50)
    assert null["diff"] == 0 and null["ci95"] == [0.0, 0.0]
