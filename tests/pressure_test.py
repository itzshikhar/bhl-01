"""Scroll-motion pressure test and content checks for BE Human Labs.

Run from the repo root:
    pip install -r tests/requirements.txt && python3 -m playwright install chromium
    python3 -m http.server 8000 -d public      # in another terminal
    python3 tests/pressure_test.py              # or: python3 tests/pressure_test.py https://yourdomain.com

Exits with code 1 if any check fails.
"""
import random, re, sys
from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000/"
STATE = """() => ({k:document.querySelectorAll('#knotMark .st.on').length, f:!!document.querySelector('#knotMark .frame.on'),
 lock:document.querySelector('#knotMark .mark').classList.contains('locked'), cap:document.getElementById('knotCap').textContent,
 off:document.querySelectorAll('#fieldMark .cell.off').length, fcap:document.getElementById('fieldCap').textContent,
 eng:document.querySelectorAll('#engine .erow.on').length})"""
failures = []

def check(ok, label):
    print(("PASS " if ok else "FAIL ") + label)
    if not ok: failures.append(label)

def go(pg, y):
    pg.evaluate(f"window.scrollTo({{top:{y},behavior:'instant'}})"); pg.wait_for_timeout(60)

with sync_playwright() as p:
    b = p.chromium.launch()

    # ---------- content checks ----------
    pg = b.new_page(); pg.goto(URL); pg.wait_for_timeout(500)
    text = pg.inner_text("body")
    check(not re.search(r"\b(US|U\.S\.|American|Americans)\b", text), "content: no US-specific wording")
    check("\u2014" not in text and "\u2013" not in text, "content: no em or en dashes")
    nums = pg.evaluate("[...document.querySelectorAll('.figure')].map(f => !!f.querySelector('.num') && !!f.querySelector('cite'))")
    check(all(nums) and len(nums) > 0, "content: every big number has a source line")
    check(pg.evaluate("document.querySelector('#welcome').hidden"), "content: welcome tag hidden without ?src=")
    pg.goto(URL + ("&" if "?" in URL else "?") + "src=conf"); pg.wait_for_timeout(300)
    check(not pg.evaluate("document.querySelector('#welcome').hidden"), "content: welcome tag shows with ?src=conf")
    pg.close()

    # ---------- motion checks, phone and desktop ----------
    for name, w, h in [("phone", 390, 844), ("desktop", 1280, 800)]:
        pg = b.new_page(viewport={"width": w, "height": h}); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(URL); pg.wait_for_timeout(600)
        top = pg.evaluate("document.getElementById('lab').offsetTop - 200")
        sec = "document.querySelector('[data-story=field]').closest('section')"
        end = pg.evaluate(f"{sec}.offsetTop + {sec}.offsetHeight")
        ys = list(range(top, end, 40))
        down = {}
        for y in ys: go(pg, y); down[y] = pg.evaluate(STATE)
        up = {}
        for y in reversed(ys): go(pg, y); up[y] = pg.evaluate(STATE)
        check(all(down[y] == up[y] for y in ys), f"{name}: same state scrolling down and up ({len(ys)} positions)")
        jumps = [y for y in (random.choice(ys) for _ in range(60)) if (go(pg, y) or pg.evaluate(STATE)) != down[y]]
        check(not jumps, f"{name}: random jumps land on the right state")
        ks = [down[y]["k"] for y in ys]
        check(all(a <= b2 for a, b2 in zip(ks, ks[1:])), f"{name}: knot only builds while scrolling down")
        check(sorted({k for k in ks}) == [0, 2, 4, 6, 8], f"{name}: knot passes through 0, 2, 4, 6, 8 strands")

        faded = []
        n = pg.evaluate("document.querySelectorAll('.story .step').length")
        for i in range(n):
            for frac in (0.25, 0.45, 0.65):
                pg.evaluate(f"""(()=>{{const d=document.querySelectorAll('.story .step')[{i}].querySelector('p.d');
                  const st=d.closest('.story').querySelector('.stage').getBoundingClientRect();
                  const top=innerWidth<900? st.bottom: 0; const target=top+(innerHeight-top)*{frac};
                  window.scrollBy({{top:d.getBoundingClientRect().top-target,behavior:'instant'}});}})()""")
                pg.wait_for_timeout(450)
                r = pg.evaluate(f"""(()=>{{const s=document.querySelectorAll('.story .step')[{i}], q=s.querySelector('p.d').getBoundingClientRect();
                  const st=s.closest('.story').querySelector('.stage').getBoundingClientRect(); const top=innerWidth<900? st.bottom:0;
                  return {{visible:q.top>=top && q.bottom<=innerHeight, op:+getComputedStyle(s).opacity}}}})()""")
                if r["visible"] and r["op"] < 0.99: faded.append((i, frac, r["op"]))
        check(not faded, f"{name}: no step text is dimmed while it is readable {faded or ''}")

        kt = pg.evaluate("document.getElementById('dimensions').offsetTop")
        for y in [end, kt + 3000, kt + 200, kt + 2600, kt + 900]: go(pg, y)
        pg.wait_for_timeout(1800)
        settled = pg.evaluate("""[...document.querySelectorAll('#knotMark .st')].every(g => {
            const d = +getComputedStyle(g.querySelector('.ln')).strokeDashoffset.replace('px','');
            return g.classList.contains('on') ? d < 0.01 : d > 0.99; })""")
        check(settled, f"{name}: knot drawing settles after a rapid flick")
        check(not errs, f"{name}: no script errors {errs or ''}")
        pg.close()
    b.close()

print(f"\n{len(failures)} failure(s)")
sys.exit(1 if failures else 0)
