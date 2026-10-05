"""Scroll-motion pressure test and content checks for BE Human Labs.

Run from the repo root:
    pip install -r tests/requirements.txt && python3 -m playwright install chromium
    python3 -m http.server 8000 -d public      # in another terminal
    python3 tests/pressure_test.py              # or: python3 tests/pressure_test.py https://yourdomain.com

Exits with code 1 if any check fails.
"""
import json, random, re, sys
from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000/"
STATE = """() => ({k:document.querySelectorAll('#knotMark .st.on').length, f:!!document.querySelector('#knotMark .frame.on'),
 lock:document.querySelector('#knotMark .mark').classList.contains('locked'), cap:document.getElementById('knotCap').textContent,
 off:document.querySelectorAll('#fieldMark .cell.off').length, fcap:document.getElementById('fieldCap').textContent,
 eng:document.querySelectorAll('#engine .erow.on').length})"""
FIELDS = {"email", "path", "option", "chip", "message", "keep_me_posted", "source", "site", "time", "company_website"}
# Every request to Apps Script is intercepted; the form checks never reach the real endpoint.
APPS_SCRIPT = re.compile(r"^https://script\.google(usercontent)?\.com/")
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

    # ---------- form checks, phone and desktop (endpoint mocked) ----------
    for name, w, h in [("phone", 390, 844), ("desktop", 1280, 800)]:
        ctx = b.new_context(viewport={"width": w, "height": h}); errs = []; sent = []; mock = {"reply": None}
        def handle(route, request):
            sent.append(request)
            if mock["reply"] is None: route.abort("failed"); return
            route.fulfill(status=200, headers={"Access-Control-Allow-Origin": "*"}, content_type="application/json", body=json.dumps(mock["reply"]))
        ctx.route(APPS_SCRIPT, handle)
        pg = ctx.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(URL); pg.wait_for_timeout(300)
        endpoint = pg.evaluate("CONFIG.formEndpoint")
        check(bool(re.fullmatch(r"https://script\.google\.com/macros/s/[\w-]+/exec", endpoint or "")), f"{name}: formEndpoint is an Apps Script /exec URL")

        missing = []
        for tab in ("talk", "join"):
            pg.click(f'[data-tab="{tab}"]')
            for opt in pg.evaluate("[...document.querySelectorAll('[data-opt]')].map(b => b.dataset.opt)"):
                pg.click(f'[data-opt="{opt}"]')
                ok = pg.evaluate("""(() => { const f = document.querySelector('#f input[name=company_website]'); if (!f) return false;
                  const r = f.getBoundingClientRect(), cs = getComputedStyle(f);
                  return f.classList.contains('hp') && f.getAttribute('aria-hidden') === 'true' && f.getAttribute('tabindex') === '-1'
                    && f.getAttribute('autocomplete') === 'off' && cs.display !== 'none' && r.right <= 0; })()""")
                if not ok: missing.append(opt)
        check(not missing, f"{name}: every form has the hidden company_website field {missing or ''}")

        def open_ask(email="test@example.com", msg="Testing the form, please ignore."):
            pg.goto(URL); pg.wait_for_timeout(200)
            pg.click('[data-tab="talk"]'); pg.click('[data-opt="ask"]')
            pg.fill("#em", email); pg.fill("#msg", msg)
            return msg

        mock["reply"] = {"ok": True}; open_ask(); pg.click('#f button[type="submit"]')
        pg.wait_for_selector(".done", timeout=5000)
        req = sent[-1] if sent else None
        body = {}
        try: body = json.loads(req.post_data) if req else {}
        except ValueError: pass
        check(req is not None and req.method == "POST", f"{name}: form sends a POST")
        check(req is not None and req.headers.get("content-type", "").startswith("text/plain"), f"{name}: request Content-Type is text/plain")
        check(FIELDS <= set(body), f"{name}: body is JSON with all payload fields {sorted(FIELDS - set(body)) or ''}")
        check(pg.is_visible(".done h3"), f"{name}: confirmation appears on ok:true")

        mock["reply"] = {"ok": False, "error": "email"}; open_ask(); pg.click('#f button[type="submit"]')
        pg.wait_for_selector("#err:not([hidden])", timeout=5000)
        check("valid email" in pg.inner_text("#err") and not pg.is_visible(".done"), f"{name}: ok:false email asks for a valid email")

        for label, reply in [("ok:false server", {"ok": False, "error": "server"}), ("network abort", None)]:
            mock["reply"] = reply; typed = open_ask(); pg.click('#f button[type="submit"]')
            pg.wait_for_selector("#err:not([hidden])", timeout=17000)
            pg.wait_for_function("!document.querySelector('#f button[type=submit]').disabled", timeout=17000)
            href = pg.get_attribute("#err a", "href") or ""
            check(not pg.is_visible(".done"), f"{name}: no confirmation on {label}")
            check("didn't go through" in pg.inner_text("#err") and href.startswith("mailto:" + pg.evaluate("CONFIG.email")) and "subject=" in href,
                  f"{name}: error message with mailto link on {label}")
            check(pg.input_value("#msg") == typed and pg.input_value("#em") == "test@example.com", f"{name}: typed message kept on {label}")
        check(not errs, f"{name}: no script errors in forms {errs or ''}")
        ctx.close()
    b.close()

print(f"\n{len(failures)} failure(s)")
sys.exit(1 if failures else 0)
