# Mozambique health access: how district travel-time estimates change with the inputs

Modelled travel time to the nearest health facility across the 159 districts of Mozambique, and how much district
estimates change with the facility list, the mode of travel, the type of facility counted, facility functionality
and the population layer.

**Live site:** https://oloyededavid.github.io/Mozambique-Health-Access/

The site is one study page built from `paper/paper.md`, with figures and an interactive district map. The results
are in the paper and in `outputs/`; this file does not repeat them, so that every number has one source.

## Question

District estimates of geographic access are often reported from one facility list, one mode of travel and one
population map. This study repeats the calculation with:

- two facility lists: the public-sector list of Maina et al. (2019) (list A) and the OpenStreetMap health facilities
  exported by the Humanitarian OpenStreetMap Team (list B), separately and together;
- motorized and walking-only travel (Malaria Atlas Project friction surfaces, 2020);
- all facilities and hospitals only;
- in Cabo Delgado, Nampula and Zambézia, every facility listed by WHO HeRAMS against those reported functioning;
- two WorldPop population layers for 2020 (R2025A constrained, and the 2000–2020 unconstrained series);
- sensitivity runs with facilities across the border, pharmacies, the sea made passable, and 10% of a list removed
  at random.

All travel times are modelled. None was compared with measured journeys. The comparison with the Malaria Atlas
Project's published travel-time layer uses the same friction surface and is not an independent check.

## Method in brief

- Travel time is the least-cost path over an 8-neighbour graph of the 30 arc-second friction grid. The cost of a
  link is the mean friction of its two cells times the great-circle distance between their centres, so geographic
  cell sizes are handled exactly. Paths are found with Dijkstra's algorithm from all facilities at once
  (`scipy.sparse.csgraph`). A test checks the result against scikit-image's `MCP_Geometric` near the equator.
- The sea is impassable (cells where MAP's published travel-time layer has no value); inland water keeps the
  friction values.
- Population stays at 100 m: each WorldPop cell is assigned to the district and the travel-time cell that contain
  its centre.
- Districts are compared through the share of residents more than one and two hours away, with Spearman rank
  correlations (bootstrap intervals over districts), changes in percentage points and overlap of the 20 districts
  with the highest share.

## Reproduce

```bash
pip install -r requirements-dev.txt
python scripts/s00_download.py      # about 620 MB into data/raw/ (not committed); records SHA-256 in outputs/sources.json
python scripts/s01_facilities.py    # facility rules and positional checks
python scripts/s02_grid.py          # friction grid and population tables
python scripts/s03_scenarios.py     # all scenarios and comparisons (a few minutes)
python scripts/s03b_paired.py       # paired bootstrap of differences between rank correlations
python scripts/s04_figures.py       # figures
python scripts/s05_web.py           # data for the district map
python scripts/build_paper.py && pandoc paper/paper.md -o paper/paper.docx --resource-path=. && python scripts/build_page.py
pytest
```

`scripts/build_paper.py` fills `paper/template.md` from `outputs/*.json` and stops if a statement in the template
is no longer true. `scripts/build_page.py` builds `docs/index.html` from `paper/paper.md`.

## Layout

| Path | What |
| :--- | :--- |
| `scripts/access.py` | Travel-time graph, population-weighted summaries, comparison measures, facility rules |
| `scripts/s00`–`s05` | Pipeline steps, in order |
| `outputs/` | Result files the paper is built from |
| `paper/` | Template, built paper (Markdown and Word) and figures |
| `docs/` | The study page, its data files and the vendored Leaflet 1.9.4 |
| `tests/` | Tests of the travel-time code on toy grids, the rules, the result files and the build |

## Licence

Code: MIT (`LICENSE`). Derived data and figures: CC BY 4.0, except data derived from OpenStreetMap, which stay
under the ODbL (`LICENSE-DATA.md`). Source data keep their own terms.

## Citation

See `CITATION.cff`.
