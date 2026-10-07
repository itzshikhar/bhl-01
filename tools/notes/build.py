#!/usr/bin/env python3
"""Builds "From the lab" from content/notes/*.html.

    pip install -r tools/notes/requirements.txt
    python3 tools/notes/build.py              # writes public/notes/
    python3 tools/notes/build.py --out DIR    # writes the same files under DIR (the pressure test uses this)

public/notes/ is generated: never edit it by hand, and commit it after building.
Form endpoint, contact email, site URL and the logo symbol are read from public/index.html,
so the homepage stays the single source for all of them.

The one rule that must never break: for a request piece, nothing after <!-- more --> is written to
public/. Only its section headings (listed in the request panel) leave the source file.
"""
import argparse, json, re, shutil, sys
from pathlib import Path

import yaml
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader, StrictUndefined

ROOT = Path(__file__).resolve().parents[2]
CONTENT = ROOT / "content" / "notes"
HOME = ROOT / "public" / "index.html"
TEMPLATES = Path(__file__).resolve().parent / "templates"

TYPES = {"research": "Research note", "deep-dive": "Deep dive", "pov": "Point of view"}
ACCESS = ("free", "request")
STATUSES = ("draft", "unlisted", "published")
REQUIRED = ("title", "dek", "type", "access", "status", "date", "author", "related")
MORE = "<!-- more -->"
DASHES = ("–", "—")
WORDS_PER_MINUTE = 220
EDNOTE = re.compile(r'<(p|div|aside)\b[^>]*class="[^"]*\bednote\b[^"]*"[^>]*>.*?</\1>\s*', re.S)
LOCK = '<svg class="lock" viewBox="0 0 16 16" aria-hidden="true"><rect x="3" y="7" width="10" height="7" rx="1"/><path d="M5.5 7V5a2.5 2.5 0 0 1 5 0v2"/></svg>'


def fail(msg):
    sys.exit(f"build: {msg}")


def site_settings():
    """Reads CONFIG values, the canonical site URL and the logo symbol from the homepage."""
    html = HOME.read_text(encoding="utf-8")
    block = re.search(r"const CONFIG = \{(.*?)\n\};", html, re.S)
    if not block: fail("CONFIG block not found in public/index.html")

    def cfg(key):
        m = re.search(rf'^\s*{key}:\s*"([^"]*)"', block.group(1), re.M)
        if not m: fail(f"CONFIG.{key} not found in public/index.html")
        return m.group(1)

    symbol = re.search(r'<symbol id="bhl-mark".*?</symbol>', html, re.S)
    site = re.search(r'<link rel="canonical" href="(https://[^"]+?)/?">', html)
    if not symbol or not site: fail("logo symbol or canonical link not found in public/index.html")
    return {"endpoint": cfg("formEndpoint"), "email": cfg("email"), "symbol": symbol.group(0), "site": site.group(1)}


def text_of(html):
    return BeautifulSoup(html, "html.parser").get_text(" ")


def headings(rest):
    """Section headings listed on the gate and request panel: every h2 after <!-- more -->, except calls to action."""
    soup = BeautifulSoup(rest, "html.parser")
    return [h.get_text(" ", strip=True).rstrip(".") for h in soup.find_all("h2") if not h.find_parent(class_="cta")]


def first_kicker_and_heading(rest):
    soup = BeautifulSoup(rest, "html.parser")
    h2 = soup.find("h2")
    k = soup.find(class_="kicker")
    return (k.get_text(strip=True) if k else ""), (h2.get_text(" ", strip=True) if h2 else "")


def teaser_of(rest, blocks=3):
    """The faded preview on a free piece: the first few blocks after <!-- more -->, without ids."""
    soup = BeautifulSoup(rest, "html.parser")
    tops = [t for t in soup.contents if getattr(t, "name", None)][:blocks]
    for t in tops:
        for tag in [t] + t.find_all(True):
            if tag.has_attr("id"): del tag["id"]
            if tag.has_attr("tabindex"): del tag["tabindex"]
    return "\n".join(str(t) for t in tops)


def load(path, site):
    text = path.read_text(encoding="utf-8")
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    if not m: fail(f"{path.name}: missing front matter")
    meta = yaml.safe_load(m.group(1)) or {}
    body = EDNOTE.sub("", text[m.end():])   # editor's notes are never published
    slug = path.stem
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", slug): fail(f"{path.name}: file name must be a lowercase slug")
    missing = [k for k in REQUIRED if k not in meta]
    if missing: fail(f"{path.name}: front matter is missing {', '.join(missing)}")
    if meta["type"] not in TYPES: fail(f"{path.name}: type must be one of {', '.join(TYPES)}")
    if meta["access"] not in ACCESS: fail(f"{path.name}: access must be free or request")
    if meta["status"] not in STATUSES: fail(f"{path.name}: status must be one of {', '.join(STATUSES)}")
    if body.count(MORE) != 1: fail(f"{path.name}: add exactly one '{MORE}' line where the open opening ends")
    if "ednote" in body: fail(f"{path.name}: an editor's note survived stripping; use <p class=\"ednote\">")

    opening, rest = (s.strip() for s in body.split(MORE))
    words = len(text_of(opening + " " + rest).split())
    kicker, first_h2 = first_kicker_and_heading(rest)
    return dict(meta, slug=slug, type_label=TYPES[meta["type"]], eyebrow=meta.get("eyebrow") or TYPES[meta["type"]],
                lead=meta.get("lead") or meta["dek"], order=meta.get("order", 999), minutes=max(3, round(words / WORDS_PER_MINUTE)),
                path=f"/notes/{slug}/", url=f"{site['site']}/notes/{slug}/", opening=opening, rest=rest,
                headings=headings(rest), kicker=kicker, first_h2=first_h2,
                jump_label=meta.get("jump_label"), jump_to=meta.get("jump_to"))


def next_cards(n, by_slug):
    out = []
    for s in n["related"] or []:
        r = by_slug.get(s)
        if not r: fail(f"{n['slug']}: related '{s}' is not a built note")
        out.append(r)
    return out


def page_data(**kw):
    # JSON for lab.js, safe inside a <script> element.
    return json.dumps(kw, ensure_ascii=False, sort_keys=True).replace("</", "<\\/")


def build(out):
    site = site_settings()
    notes = [load(p, site) for p in sorted(CONTENT.glob("*.html"))]
    built = [n for n in notes if n["status"] != "draft"]
    by_slug = {n["slug"]: n for n in built}
    listed = sorted((n for n in built if n["status"] == "published"), key=lambda n: (n["order"], n["slug"]))
    free = [n for n in listed if n["access"] == "free"]
    requested = [n for n in listed if n["access"] == "request"]

    env = Environment(loader=FileSystemLoader(TEMPLATES), autoescape=True, undefined=StrictUndefined,
                      trim_blocks=True, lstrip_blocks=True, keep_trailing_newline=True)
    common = dict(site=site, lock=LOCK)
    pages = {"notes/index.html": env.get_template("index.html").render(
        **common, free=free, requested=requested, current="index", url=f"{site['site']}/notes/",
        data=page_data(kind="index", endpoint=site["endpoint"], email=site["email"]))}
    for n in built:
        view = dict(n)
        if n["access"] == "request":
            view.pop("rest")   # locked text never reaches the template
        else:
            view["teaser"] = teaser_of(n["rest"])
            # "Next from the lab" sits just above the sources, or at the end.
            cut = n["rest"].find('<div class="sources">')
            view["rest_before"], view["rest_after"] = (n["rest"][:cut], n["rest"][cut:]) if cut >= 0 else (n["rest"], "")
        pages[f"notes/{n['slug']}/index.html"] = env.get_template("note.html").render(
            **common, n=view, free_list=free, next=next_cards(n, by_slug), current="note", url=n["url"],
            data=page_data(kind="note", endpoint=site["endpoint"], email=site["email"], slug=n["slug"],
                           title=n["title"], url=n["url"], access=n["access"]))

    for rel, html in pages.items():
        if any(d in html for d in DASHES): fail(f"{rel}: contains an em or en dash; use plain punctuation")
        if "ednote" in html: fail(f"{rel}: contains an editor's note")
        locked = next((n for n in built if n["access"] == "request" and rel == f"notes/{n['slug']}/index.html"), None)
        if locked:
            # Belt and braces: no paragraph of locked text may appear in the page.
            for para in BeautifulSoup(locked["rest"], "html.parser").find_all(["p", "li", "dd", "td"]):
                t = para.get_text(" ", strip=True)
                if len(t.split()) >= 6 and t in text_of(html): fail(f"{rel}: locked text leaked: {t[:60]}")

    # public/notes is fully generated, and public/lab is the old location (now a redirect): clear both.
    for d in ("notes", "lab"):
        shutil.rmtree(out / d, ignore_errors=True)
    for rel, html in pages.items():
        f = out / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(html, encoding="utf-8")
    return pages


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", type=Path, default=ROOT / "public", help="output folder (default: public/)")
    args = ap.parse_args()
    for rel in build(args.out.resolve()): print("built", rel)
