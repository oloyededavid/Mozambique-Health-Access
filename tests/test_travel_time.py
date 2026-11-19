"""Travel time on toy grids with known answers."""
import math

import numpy as np
import pytest


def test_haversine_one_degree_of_latitude(access):
    d = access.haversine_m(0.0, 0.0, 0.0, 1.0)
    assert d == pytest.approx(access.EARTH_RADIUS_M * math.pi / 180, rel=1e-12)


def test_straight_line_east_at_equator(access):
    res = 0.01
    f = np.full((3, 11), 0.002)                       # 0.002 min per metre = 30 km/h
    g = access.build_graph(f, np.ones_like(f, bool), top_lat=0.015, res_deg=res)
    tt = access.travel_time(g, f.shape, [1 * 11 + 0])  # source: middle row, first column
    lat = 0.015 - 1.5 * res
    step = access.haversine_m(0, lat, res, lat)
    for k in range(11):
        assert tt[1, k] == pytest.approx(k * step * 0.002, rel=1e-9)


def test_diagonal_uses_great_circle_length(access):
    res = 0.01
    f = np.full((5, 5), 0.01)
    g = access.build_graph(f, np.ones_like(f, bool), top_lat=0.025, res_deg=res)
    tt = access.travel_time(g, f.shape, [0])
    lat = 0.025 - (np.arange(5) + 0.5) * res
    expect = sum(access.haversine_m(0, lat[i], res, lat[i + 1]) for i in range(4)) * 0.01
    assert tt[4, 4] == pytest.approx(expect, rel=1e-9)


def test_east_west_cost_falls_with_latitude(access):
    """A cell at 60 degrees south is about half as wide as one at the equator, so crossing it costs about half."""
    res = 0.01
    f = np.full((1, 2), 0.01)
    t0 = access.travel_time(access.build_graph(f, np.ones_like(f, bool), 0.005, res), f.shape, [0])[0, 1]
    t60 = access.travel_time(access.build_graph(f, np.ones_like(f, bool), -59.995, res), f.shape, [0])[0, 1]
    assert t60 / t0 == pytest.approx(math.cos(math.radians(60)), rel=1e-3)


def test_mean_friction_of_the_two_cells(access):
    res = 0.01
    f = np.array([[0.002, 0.010]])
    tt = access.travel_time(access.build_graph(f, np.ones_like(f, bool), 0.005, res), f.shape, [0])
    assert tt[0, 1] == pytest.approx(0.006 * access.haversine_m(0, 0, res, 0), rel=1e-9)


def test_barrier_forces_detour_and_closed_area_is_unreachable(access):
    res = 0.01
    f = np.full((5, 5), 0.01)
    ok = np.ones_like(f, bool)
    ok[0:4, 2] = False                                 # wall with a gap in the bottom row
    g = access.build_graph(f, ok, 0.025, res)
    tt = access.travel_time(g, f.shape, [0])
    straight = 4 * access.haversine_m(0, 0.02, res, 0.02) * 0.01
    assert np.isfinite(tt[0, 4]) and tt[0, 4] > straight * 1.5
    assert np.isinf(tt[0, 2])                          # impassable cell itself
    ok2 = ok.copy(); ok2[4, 2] = False                  # close the gap
    tt2 = access.travel_time(access.build_graph(f, ok2, 0.025, res), f.shape, [0])
    assert np.isinf(tt2[:, 3:]).all()


def test_nearest_of_several_sources(access):
    res = 0.01
    f = np.full((1, 9), 0.01)
    g = access.build_graph(f, np.ones_like(f, bool), 0.005, res)
    tt = access.travel_time(g, f.shape, [0, 8])
    step = access.haversine_m(0, 0, res, 0) * 0.01
    assert tt[0, 4] == pytest.approx(4 * step, rel=1e-9)
    assert tt[0, 2] == pytest.approx(2 * step, rel=1e-9)
    assert np.isinf(access.travel_time(g, f.shape, [])).all()


def test_matches_scikit_image_mcp_near_the_equator(access):
    """Near the equator with tiny cells the geographic grid is almost square, so scikit-image's MCP_Geometric
    (cost = mean of the two cells x step length) must give nearly the same times."""
    from skimage.graph import MCP_Geometric
    rng = np.random.default_rng(3)
    res = 0.0005
    f = rng.uniform(0.001, 0.02, (40, 40))
    g = access.build_graph(f, np.ones_like(f, bool), top_lat=0.01, res_deg=res)
    ours = access.travel_time(g, f.shape, [20 * 40 + 20])
    side = access.haversine_m(0, 0, 0, res)
    mcp = MCP_Geometric(f * side, fully_connected=True)
    theirs, _ = mcp.find_costs([(20, 20)])
    assert np.allclose(ours, theirs, rtol=2e-3)


def test_points_to_cells_and_snapping(access):
    r, c = access.cells_for_points([0.005, 0.025, 5.0], [-0.005, -0.015, 0.0], left=0.0, top=0.0, res_deg=0.01, shape=(3, 3))
    assert list(r) == [0, 1, -1] and list(c) == [0, 2, -1]
    ok = np.ones((5, 5), bool); ok[0, 0] = False; ok[4, :] = False; ok[3, 4] = False
    r2, c2, mv = access.snap_to_passable([0, 4, -1], [0, 4, -1], ok, max_cells=1)
    assert mv.tolist() == [1, 1, -1]
    assert ok[r2[0], c2[0]] and ok[r2[1], c2[1]]
    far = np.zeros((7, 7), bool); far[0, 0] = True
    assert access.snap_to_passable([6], [6], far, max_cells=3)[2].tolist() == [-1]
