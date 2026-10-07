"""Builds the "Save my card" image and the "Save my contact" vCard.

    python3 tools/card/make.py            # card image (if the two sides are here), contact photo (if missing) and vCard
    python3 tools/card/make.py --photo    # also re-render the contact photo from the logo SVG
    python3 tools/card/make.py --vcard-only --out DIR   # only the vCard, into DIR (the pressure test uses this)

Inputs, all in tools/card/:
  card-front.png   the contact side of the printed card
  card-back.png    the logo side
  contact-photo.png  256px square, Dark Coffee mark on Pale Oak, rendered from public/be-human-labs-mark.svg (never redrawn)
The vCard fields come from CONFIG in public/index.html.
Needs Pillow for the card image (pip install pillow) and Playwright for the photo.
"""
import argparse, base64, io, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PUBLIC = ROOT / "public"
CARD = "shikhar-anand-be-human-labs.png"
VCARD = "shikhar-anand-be-human-labs.vcf"
GROUND, PALE_OAK = "#E7DDD2", "#C5B7AA"
MAX_BYTES = 1_000_000


def fail(msg):
    sys.exit(f"tools/card/make.py: {msg}")


def config():
    """Reads the contact fields from CONFIG in public/index.html."""
    block = re.search(r"const CONFIG = \{(.*?)\n\};", (PUBLIC / "index.html").read_text(encoding="utf-8"), re.S)
    if not block: fail("CONFIG block not found in public/index.html")
    def cfg(key):
        m = re.search(rf'^\s*{key}:\s*"([^"]*)"', block.group(1), re.M)
        if not m: fail(f"CONFIG.{key} not found in public/index.html")
        return m.group(1)
    return {k: cfg(k) for k in ("name", "title", "org", "phone", "email", "website", "note")}


def card(out):
    """Contact side on top, logo side below, a small gap in the ground colour, at full resolution."""
    from PIL import Image
    front, back = HERE / "card-front.png", HERE / "card-back.png"
    if not (front.exists() and back.exists()):
        print("card image skipped: put card-front.png and card-back.png in tools/card/"); return
    a, b = Image.open(front).convert("RGB"), Image.open(back).convert("RGB")
    w = max(a.width, b.width); gap = max(16, round(w * 0.03))
    sheet = Image.new("RGB", (w, a.height + gap + b.height), GROUND)
    sheet.paste(a, ((w - a.width) // 2, 0)); sheet.paste(b, ((w - b.width) // 2, a.height + gap))
    data = encode(sheet)
    if len(data) > MAX_BYTES:   # a printed card has few colours: a 256-colour palette keeps it sharp and small
        data = encode(sheet.quantize(256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE))
    (out / CARD).write_bytes(data)
    print(f"wrote public/{CARD} ({sheet.width}x{sheet.height}, {len(data) // 1024} KB)")
    if len(data) > MAX_BYTES: print(f"warning: public/{CARD} is over 1 MB")


def encode(img):
    buf = io.BytesIO(); img.save(buf, "PNG", optimize=True); return buf.getvalue()


def photo():
    """Renders the logo SVG (exact paths, Dark Coffee) on Pale Oak at 256px. The mark sits inside the circle phones crop to."""
    from playwright.sync_api import sync_playwright
    svg = (PUBLIC / "be-human-labs-mark.svg").read_text(encoding="utf-8").replace("<svg ", '<svg width="168" height="168" ', 1)
    page = (f'<html><body style="margin:0;width:256px;height:256px;background:{PALE_OAK};display:grid;place-items:center">'
            f'<div style="width:168px;height:168px">{svg}</div></body></html>')
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={"width": 256, "height": 256})
        pg.set_content(page); png = pg.screenshot(); b.close()
    try:
        from PIL import Image
        png = encode(Image.open(io.BytesIO(png)).convert("RGB").quantize(64, dither=Image.Dither.NONE))
    except ImportError:
        pass
    (HERE / "contact-photo.png").write_bytes(png)
    print(f"wrote tools/card/contact-photo.png ({len(png) // 1024} KB)")


def esc(s):
    return s.replace("\\", "\\\\").replace(",", "\\,").replace(";", "\;").replace("\n", "\\n")


def fold(line):
    """vCard line folding: at most 75 octets a line, continuation lines start with one space."""
    raw = line.encode("utf-8"); out = []
    while len(raw) > 75:
        cut = 75 if not out else 74
        while cut and (raw[cut] & 0xC0) == 0x80: cut -= 1   # never split a UTF-8 character
        out.append(raw[:cut]); raw = raw[cut:]
    out.append(raw)
    return b"\r\n ".join(out)


def vcard(out):
    c = config(); photo_png = HERE / "contact-photo.png"
    if not photo_png.exists(): fail("tools/card/contact-photo.png is missing: run python3 tools/card/make.py --photo")
    first, _, last = c["name"].rpartition(" ")
    lines = ["BEGIN:VCARD", "VERSION:3.0",
             f"N:{esc(last)};{esc(first)};;;", f"FN:{esc(c['name'])}",
             f"ORG:{esc(c['org'])}", f"TITLE:{esc(c['title'])}",
             f"TEL;TYPE=CELL,VOICE:{c['phone']}", f"EMAIL;TYPE=INTERNET,WORK:{c['email']}",
             f"URL:{c['website']}", f"NOTE:{esc(c['note'])}",
             "PHOTO;ENCODING=b;TYPE=PNG:" + base64.b64encode(photo_png.read_bytes()).decode("ascii"),
             "END:VCARD"]
    (out / VCARD).write_bytes(b"\r\n".join(fold(l) for l in lines) + b"\r\n")
    print(f"wrote {VCARD}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--photo", action="store_true"); ap.add_argument("--vcard-only", action="store_true")
    ap.add_argument("--out", default=str(PUBLIC))
    a = ap.parse_args(); out = Path(a.out)
    if not a.vcard_only:
        if a.photo or not (HERE / "contact-photo.png").exists(): photo()
        card(out)
    vcard(out)
