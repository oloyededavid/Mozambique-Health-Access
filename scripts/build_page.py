"""Build docs/index.html from paper/paper.md, so the page and the paper cannot disagree. Figures are shown from
docs/assets/figures/ (desktop and phone versions written by scripts/s04_figures.py).

    python scripts/build_paper.py && python scripts/build_page.py
"""
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIG = re.compile(r"!\[(\*\*Figure (\d+)\.\*\* )?(.*?)\]\((paper/figures/([^)/]+)\.png)\)")

EXPLORE = """<h3 id="explore">3.5 Map of the districts</h3>
<p>Pick a facility list, a mode of travel and a measure, then select a district on the map or from the list. The HeRAMS options cover Cabo Delgado, Nampula and Zambézia only. Districts with too few residents to compare are left grey. Values use the WorldPop R2025A constrained population layer and are modelled, not measured.</p>
<div class="xp-controls">
<p class="xp-pick"><label for="xp-scen">Facilities</label> <select id="xp-scen"></select></p>
<div id="xp-modes" class="xp-buttons" role="group" aria-label="Mode of travel"></div>
<div id="xp-buttons" class="xp-buttons" role="group" aria-label="Measure"></div>
<p class="xp-pick"><label for="xp-select">District</label> <select id="xp-select"></select></p>
</div>
<div id="explore-map" class="xp-map" role="region" aria-label="Map of the districts of Mozambique"></div>
<div class="xp-legend"><span id="xp-min"></span><span id="xp-legend-bar" class="xp-legend-bar" aria-hidden="true"></span><span id="xp-max"></span></div>
<p id="xp-unit" class="xp-unit"></p>
<p id="xp-readout" class="xp-readout" role="status">Select a district on the map, on the list above it, or use Tab and Enter.</p>
<details class="xp-table"><summary>Show all districts as a table</summary><div id="xp-table"></div></details>
"""


def image_size(rel):
    from PIL import Image
    with Image.open(ROOT / "docs" / rel) as im:
        return im.size


def figure_html(m):
    num, desc, name = m.group(2), m.group(3), m.group(5)
    desk, phone = f"assets/figures/{name}.webp", f"assets/figures/{name}_phone.webp"
    for f in (desk, phone):
        if not (ROOT / "docs" / f).exists():
            raise SystemExit(f"missing figure {f}: run scripts/s04_figures.py")
    alt = re.sub(r"\*\*", "", desc).replace('"', "&quot;")
    w, h = image_size(desk)
    return (f'<figure class="wide mapimg" id="fig-{num}">'
            f'<picture><source media="(max-width: 760px)" srcset="{phone}"><img src="{desk}" width="{w}" height="{h}" loading="lazy" alt="{alt}"></picture>'
            f'<figcaption><b>Figure {num}.</b> {desc}</figcaption></figure>')


def tidy(html):
    """Keep a number and its unit together, put the title and description on one line each, and let wide tables
    scroll inside their own box instead of widening the page."""
    parts = re.split(r"(<[^>]+>)", html)
    unit = re.compile(r"(\d) (km\b|m\b|%|minutes\b|points\b|million\b|thousand\b)")
    html = "".join(p if p.startswith("<") else unit.sub("\\1\u00a0\\2", p) for p in parts)
    html = re.sub(r"<title>(.*?)</title>", lambda m: "<title>" + " ".join(m.group(1).split()) + "</title>", html, flags=re.S)
    html = re.sub(r'(<meta (?:name|property)="(?:og:)?description" content=")(.*?)(">)', lambda m: m.group(1) + " ".join(m.group(2).split()) + m.group(3), html, flags=re.S)
    n = [0]

    def wrap(m):
        n[0] += 1
        return f'<div class="table-wrap" tabindex="0" role="region" aria-label="Table {n[0]}, scrolls sideways">{m.group(0)}</div>'
    return re.sub(r"<table>.*?</table>", wrap, html, flags=re.S)


def main():
    md = (ROOT / "paper" / "paper.md").read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", md, flags=re.S)
    meta = dict(re.findall(r'^(\w+): "?([^"\n]*)"?$', m.group(1), flags=re.M)) if m else {}
    body = FIG.sub(figure_html, md[m.end():] if m else md)
    if "](paper/figures/" in body:
        raise SystemExit("a figure in paper.md was not converted")
    tmp = ROOT / "paper" / "_page_body.md"
    tmp.write_text(body, encoding="utf-8")
    out = ROOT / "docs" / "index.html"
    try:
        subprocess.run(["pandoc", str(tmp), "-f", "markdown-raw_html+raw_html", "-t", "html5", "--shift-heading-level-by=1",
                        "--template", str(ROOT / "scripts" / "page_template.html"), "-o", str(out),
                        "--metadata", f"pagetitle={meta.get('title', '')}", "--metadata", f"title={meta.get('title', '')}",
                        "--metadata", f"author={meta.get('author', '')}", "--metadata", f"date={meta.get('date', '')}",
                        "--metadata", "description=Modelled travel time to health facilities across the districts of Mozambique, and how much it changes with the facility list, mode of travel, facility functionality and population layer."],
                       check=True)
    finally:
        tmp.unlink(missing_ok=True)
    html = out.read_text(encoding="utf-8")
    marker = '<h2 id="discussion">'
    if html.count(marker) != 1:
        raise SystemExit("discussion heading not found")
    html = tidy(html.replace(marker, EXPLORE + marker))
    out.write_text(_study_links(_page_end(html), out.parent), encoding="utf-8")
    print("wrote", out)


def _study_links(html, docs):
    """Re-insert the cross-site links that the portfolio's tools/sync_nav.py keeps in docs/assets/study-*.html."""
    for key, where in (("study-bar", "top"), ("study-nav", "end")):
        f = docs / "assets" / f"{key}.html"
        if not f.exists():
            continue
        block = f.read_text(encoding="utf-8").strip()
        html = re.sub(rf"<!-- {key}:start -->.*?<!-- {key}:end -->\n?", "", html, flags=re.S)
        if where == "top":
            html = re.sub(r"(<body[^>]*>)", lambda m: m.group(1) + "\n" + block, html, count=1)
        else:
            html = html.replace("</body>", block + "\n</body>", 1)
    f = docs / "assets" / "study-others.html"  # the "Other studies" line in the footer, kept in place
    if f.exists():
        block = f.read_text(encoding="utf-8").strip()
        html = re.sub(r"<!-- study-others:start -->.*?<!-- study-others:end -->", lambda m: block, html, flags=re.S)
    return html


def _web_ending(html, end):
    """Shape the end of the page like the other study sites: the paper's own data-and-code section becomes the
    opening paragraph of "Data, code and citation" (so the page says it once), the page end goes before the
    references, and the references become the same compact list, with DOIs shown as doi:..."""
    m = re.search(r'<h2 id="[^"]*data-and-code[^"]*">.*?</h2>\s*(.*?)(?=<h2 )', html, flags=re.S)
    if not m:
        raise SystemExit("page end: the paper's data-and-code section was not found (its heading id changed?)")
    html = html[:m.start()] + html[m.end():]
    end, n = re.subn(r'(<h2 id="h-dc">.*?</h2>)', lambda k: k.group(1) + "\n    " + m.group(1).strip(), end, count=1, flags=re.S)
    if not n:
        raise SystemExit('page end: page_end.html has no <h2 id="h-dc"> heading')
    anchor = '<h2 id="references">'
    if anchor not in html:
        raise SystemExit("page end: no References heading to place the end of the page before")
    html = html.replace(anchor, end + "\n" + anchor, 1)
    r = re.search(r'(<h2 id="references">References</h2>\s*)((?:<p>.*?</p>\s*)+)', html, flags=re.S)
    if not r:
        raise SystemExit("page end: no reference paragraphs after the References heading")

    def item(p):
        p = " ".join(p.split())  # pandoc wraps lines, even inside tags
        p = re.sub(r'<a href="https://doi\.org/([^"]+)"[^>]*>[^<]*</a>', lambda k: f'<a href="https://doi.org/{k.group(1)}">doi:{k.group(1)}</a>', p)

        def trim(u):
            return (u[:-1] if u.endswith(")") and u.count("(") < u.count(")") else u).rstrip(".,;:")

        def bare(k, doi):
            u = trim(k.group(1)); rest = k.group(1)[len(u):]
            return (f'<a href="https://doi.org/{u}">doi:{u}</a>' if doi else f'<a href="{u}">{u}</a>') + rest
        p = re.sub(r'(?<![">/])https://doi\.org/([^\s<]+)', lambda k: bare(k, True), p)
        p = re.sub(r'(?<![">/])(https?://[^\s<]+)', lambda k: bare(k, False), p)
        return "<li>" + p + "</li>"
    items = [item(p) for p in re.findall(r"<p>(.*?)</p>", r.group(2), flags=re.S)]
    return html[:r.start(2)] + '<ol class="refs" role="list">\n' + "\n".join(items) + "\n</ol>\n" + html[r.end(2):]


def _page_end(html):
    """The end of the page (key terms, data and citation, a note, feedback) lives in page_end.html next to this script."""
    return _web_ending(html, Path(__file__).with_name("page_end.html").read_text(encoding="utf-8").strip())


if __name__ == "__main__":
    main()
