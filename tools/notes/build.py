#!/usr/bin/env python3
"""Builds the "From the lab" pages from content/notes/*.md.

    pip install -r tools/notes/requirements.txt
    python3 tools/notes/build.py              # writes public/lab/ and public/notes/
    python3 tools/notes/build.py --out DIR    # writes the same files under DIR (the pressure test uses this)

public/lab/ and public/notes/ are generated: never edit them by hand, and commit them after building.
Form endpoint, contact email, site URL and the logo symbol are read from public/index.html,
so the homepage stays the single source for all of them.
"""
import argparse, datetime, json, re, shutil, sys
from pathlib import Path

import markdown, yaml
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader, StrictUndefined

ROOT = Path(__file__).resolve().parents[2]
CONTENT = ROOT / "content" / "notes"
HOME = ROOT / "public" / "index.html"
TEMPLATES = Path(__file__).resolve().parent / "templates"

TYPES = {"research": "Research note", "deep-dive": "Deep dive", "pov": "Point of view"}
STATUSES = ("draft", "unlisted", "public", "gated")
REQUIRED = ("title", "summary", "type", "status", "date", "read_time", "author", "featured")
MORE, FADE = "<!-- more -->", "<!-- fade -->"
DASHES = ("–", "—")


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


def md(text):
    return markdown.markdown(text, output_format="html").strip()


def load(path, site):
    text = path.read_text(encoding="utf-8")
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    if not m: fail(f"{path.name}: missing front matter")
    meta = yaml.safe_load(m.group(1)) or {}
    body = text[m.end():]
    slug = path.stem
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", slug): fail(f"{path.name}: file name must be a lowercase slug")
    missing = [k for k in REQUIRED if k not in meta]
    if missing: fail(f"{path.name}: front matter is missing {', '.join(missing)}")
    if meta["type"] not in TYPES: fail(f"{path.name}: type must be one of {', '.join(TYPES)}")
    if meta["status"] not in STATUSES: fail(f"{path.name}: status must be one of {', '.join(STATUSES)}")
    if not isinstance(meta["date"], datetime.date): fail(f"{path.name}: date must be YYYY-MM-DD")
    if MORE not in body: fail(f"{path.name}: add a '{MORE}' line where the open opening ends")

    opening_md, rest_md = body.split(MORE, 1)
    rest = md(rest_md)
    teaser = None
    if FADE in rest:
        # The faded preview under the gate: the rest of the note up to the fade marker,
        # with tags closed and ids removed so they don't clash with the full text.
        soup = BeautifulSoup(rest.split(FADE, 1)[0], "html.parser")
        for tag in soup.find_all(id=True): del tag["id"]
        teaser = str(soup).strip()
        rest = rest.replace(FADE, "")
    elif meta["status"] == "gated":
        fail(f"{path.name}: gated notes need a '{FADE}' marker where the faded preview ends")

    return dict(meta, slug=slug, type_label=TYPES[meta["type"]], month=meta["date"].strftime("%B %Y"),
                path=f"/notes/{slug}/", url=f"{site['site']}/notes/{slug}/",
                opening=md(opening_md), teaser=teaser, rest=rest, covers=meta.get("covers") or [],
                jump_label=meta.get("jump_label"), jump_to=meta.get("jump_to"), jump_hint=meta.get("jump_hint"))


def page_data(**kw):
    # JSON for lab.js, safe inside a <script> element.
    return json.dumps(kw, ensure_ascii=False, sort_keys=True).replace("</", "<\\/")


def build(out):
    site = site_settings()
    notes = [load(p, site) for p in sorted(CONTENT.glob("*.md"))]
    built = [n for n in notes if n["status"] != "draft"]
    listed = sorted((n for n in built if n["status"] in ("public", "gated")), key=lambda n: (n["date"], n["slug"]), reverse=True)

    env = Environment(loader=FileSystemLoader(TEMPLATES), autoescape=True, undefined=StrictUndefined,
                      trim_blocks=True, lstrip_blocks=True, keep_trailing_newline=True)
    pages = {"lab/index.html": env.get_template("lab.html").render(
        site=site, notes=listed, current="lab", url=f"{site['site']}/lab/",
        data=page_data(kind="lab", endpoint=site["endpoint"], email=site["email"], source="lab"))}
    for n in built:
        pages[f"notes/{n['slug']}/index.html"] = env.get_template("note.html").render(
            site=site, n=n, current="note", url=n["url"],
            data=page_data(kind="note", endpoint=site["endpoint"], email=site["email"], slug=n["slug"],
                           title=n["title"], url=n["url"], gated=n["status"] == "gated", source=f"note:{n['slug']}"))

    for rel, html in pages.items():
        bad = [d for d in DASHES if d in html]
        if bad: fail(f"{rel}: contains an em or en dash; use plain punctuation")

    # public/lab and public/notes are fully generated: clear them so removed or drafted notes disappear.
    for d in ("lab", "notes"):
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
    pages = build(args.out.resolve())
    for rel in pages: print("built", rel)
