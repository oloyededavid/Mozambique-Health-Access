# Contributing and working on this repository

Static research site (GitHub Pages, `docs/`) on modelled travel time to health facilities in Mozambique, with the
Python scripts that produce every number and figure on it.

## Rules

- Every number in `paper/paper.md` and `docs/index.html` is read from a file in `outputs/` that a script in
  `scripts/` writes. Never type a result into the template, the HTML or the JavaScript.
  `scripts/build_paper.py` fills `paper/template.md` and checks each statement with `need()`;
  `scripts/build_page.py` builds the page from the paper; `docs/assets/explore.js` reads
  `docs/data/district_values.json`.
- Every figure is written by `scripts/s04_figures.py` or `scripts/s06_more_figures.py`. Do not edit images by hand.
- Travel times are modelled, not measured. WorldPop is a model, not a census. OpenStreetMap coverage is uneven.
  HeRAMS covers three provinces and assessments from different quarters. Say so wherever they are used.
- The comparison with the Malaria Atlas Project's published travel-time layer is not independent (same friction
  surface). Do not present it as validation.
- Cite only sources that have been checked to exist, with their DOI where there is one.
- Design: light only, as on the other study sites. No emojis or decorative icons.

## Pipeline

| Step | Command | Writes |
| :--- | :--- | :--- |
| Download sources | `python scripts/s00_download.py` | `data/raw/`, `outputs/sources.json` |
| Facility rules and checks | `python scripts/s01_facilities.py` | `data/derived/facilities.parquet`, `data/derived/districts.parquet`, `outputs/facilities.json`, `docs/data/facilities.csv` |
| Grid and population tables | `python scripts/s02_grid.py` | `data/derived/grid.npz`, `data/derived/pop_*.npz`, `outputs/population.json` |
| Scenarios and comparisons | `python scripts/s03_scenarios.py` | `outputs/scenarios.json`, `outputs/comparisons.json`, `data/derived/tt_*.npy` |
| Paired bootstrap | `python scripts/s03b_paired.py` | `outputs/paired.json` |
| Figures | `python scripts/s04_figures.py` | `paper/figures/*.png`, `docs/assets/figures/*.webp` |
| Figures from committed outputs (no raw downloads needed) | `python scripts/s06_more_figures.py` | `fig5_change_map`, `fig6_rank` in the same folders |
| Map data | `python scripts/s05_web.py` | `docs/data/districts.geojson`, `docs/data/district_values.json`, `docs/data/district_access.csv`, copies of `outputs/*.json` |
| Paper and page | `python scripts/build_paper.py && pandoc paper/paper.md -o paper/paper.docx --resource-path=. && python scripts/build_page.py` | `paper/paper.md`, `paper/paper.docx`, `docs/index.html` |
| Tests | `pytest` | |

`data/` is not committed (about 620 MB of downloads plus derived grids); rebuild it with the commands above.

## Shared page parts

`docs/assets/study-bar.html`, `study-nav.html` and `study-others.html` are kept in step with the other study sites
by the portfolio's sync tool; `scripts/build_page.py` inserts them. `docs/assets/style.css` and `study.js` come from
the Lagos study site, with a section for the Leaflet district map added at the end of the stylesheet.
