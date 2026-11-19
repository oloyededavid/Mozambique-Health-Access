"""The paper and the page are built from the result files: every placeholder is filled and the built files match."""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def built():
    from conftest import load
    bp = load("build_paper")
    return bp.build(bp.load())


def test_all_placeholders_filled(built):
    t = (ROOT / "paper" / "template.md").read_text(encoding="utf-8")
    assert re.findall(r"\{\{(\w+)\}\}", t), "template has placeholders"
    assert "{{" not in built and "}}" not in built
    assert "nan" not in re.sub(r"[A-Za-z]nan|nan[a-z]", "", built)
    assert "None" not in built


def test_committed_paper_matches_build(built):
    drop_date = lambda s: re.sub(r'^date: ".*"$', "", s, flags=re.M)  # noqa: E731
    assert drop_date((ROOT / "paper" / "paper.md").read_text(encoding="utf-8")) == drop_date(built)


def test_page_is_built_from_paper():
    html = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
    assert "{{" not in html and "$body$" not in html
    assert 'data-counter="mozambique-health-access"' in html
    for marker in ("study-bar:start", "study-nav:start", "study-others:start", "page-end:start", 'id="explore"',
                   'id="key-terms"', 'id="data-code"', 'id="h-note"', 'id="feedback"', '<ol class="refs"'):
        assert marker in html, marker
    paper = (ROOT / "paper" / "paper.md").read_text(encoding="utf-8")
    abstract = paper.split("# Abstract", 1)[1].split("**Keywords", 1)[0].strip()
    for num in set(re.findall(r"\d+\.\d+%", abstract)):
        assert num.replace("%", " %") in html or num in html, num
    for f in re.findall(r'(?:src|srcset|href)="((?:assets|data|vendor)/[^"#]+)"', html):
        assert (ROOT / "docs" / f).exists(), f


def test_no_emoji_in_published_text():
    emoji = re.compile("[\U0001F300-\U0001FAFF☀-➿]")
    for p in [ROOT / "paper" / "paper.md", ROOT / "docs" / "index.html", ROOT / "README.md"]:
        if p.exists():
            s = p.read_text(encoding="utf-8")
            assert not emoji.search(s), p
            for word in ("Cla" + "ude", "Anthr" + "opic"):
                assert word not in s, (p, word)


def test_no_visible_placeholder_on_page():
    html = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
    visible = re.sub(r"<!--.*?-->", "", html, flags=re.S)
    assert "PLACEHOLDER" not in visible.upper().replace("PLACEHOLDERS", "")
    assert "draft: author to revise" in html


def test_figure_numbers_match_file_names():
    paper = (ROOT / "paper" / "paper.md").read_text(encoding="utf-8")
    for num, f in re.findall(r"\*\*Figure (\d+)\.\*\*.*?\]\(paper/figures/fig(\d+)_", paper):
        assert num == f
