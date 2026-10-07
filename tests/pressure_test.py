"""Scroll-motion pressure test and content checks for BE Human Labs.

Run from the repo root:
    pip install -r tests/requirements.txt && python3 -m playwright install chromium
    python3 -m http.server 8000 -d public      # in another terminal
    python3 tests/pressure_test.py              # or: python3 tests/pressure_test.py https://behumanlabs.com

Exits with code 1 if any check fails.
"""
import filecmp, json, random, re, subprocess, sys, tempfile, urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000/"
STATE = """() => ({k:document.querySelectorAll('#knotMark .st.on').length, f:!!document.querySelector('#knotMark .frame.on'),
 lock:document.querySelector('#knotMark .mark').classList.contains('locked'), cap:document.getElementById('knotCap').textContent,
 off:document.querySelectorAll('#fieldMark .cell.off').length, fcap:document.getElementById('fieldCap').textContent,
 eng:document.querySelectorAll('#engine .erow.on').length})"""
FIELDS = {"email", "path", "option", "chip", "message", "keep_me_posted", "source", "site", "time", "company_website"}
# Every request to Apps Script is intercepted; the form checks never reach the real endpoint.
APPS_SCRIPT = re.compile(r"^https://script\.google(usercontent)?\.com/")
ROOT = Path(__file__).resolve().parents[1]
NOTE = "learning-when-answers-are-free"
NOTE_TITLE = "Learning when answers are free."
NOTE_URL = f"https://behumanlabs.com/notes/{NOTE}/"
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

    # ---------- From the lab: content build ----------
    with tempfile.TemporaryDirectory() as tmp:
        run = subprocess.run([sys.executable, str(ROOT / "tools/notes/build.py"), "--out", tmp], capture_output=True, text=True)
        stale = [] if run.returncode == 0 else [run.stderr.strip()]
        for d in ("lab", "notes"):
            fresh = {p.relative_to(tmp) for p in (Path(tmp) / d).rglob("*") if p.is_file()}
            committed = {p.relative_to(ROOT / "public") for p in (ROOT / "public" / d).rglob("*") if p.is_file()}
            stale += [f"missing or extra: public/{f}" for f in sorted(fresh ^ committed)]
            stale += [f"out of date: public/{f}" for f in sorted(fresh & committed) if not filecmp.cmp(Path(tmp) / f, ROOT / "public" / f, shallow=False)]
    check(not stale, f"lab: public/ matches content/ (run python3 tools/notes/build.py) {stale or ''}")

    home_css, lab_css = (ROOT / "public/index.html").read_text(), (ROOT / "public/css/lab.css").read_text()
    shared = lambda css: [re.search(r":root\{.*?\n\}", css, re.S).group(0)] + re.findall(r"^\.skin[\w-]*\s*\{.*\}$", css, re.M)
    check(shared(home_css) == shared(lab_css), "lab: lab.css tokens and skins match the homepage")

    generated = [ROOT / "public/lab/index.html"] + sorted((ROOT / "public/notes").glob("*/index.html"))
    dashed = [str(f.relative_to(ROOT)) for f in generated if re.search("\u2013|\u2014|&[mn]dash;|&#821[12];", f.read_text())]
    check(not dashed, f"lab: no em or en dashes in generated pages {dashed or ''}")

    # ---------- From the lab: pages and forms (endpoint mocked) ----------
    def ctx_for(w, h, reply):
        ctx = b.new_context(viewport={"width": w, "height": h}); sent = []
        mock = {"reply": reply}
        def handle(route, request):
            sent.append(request)
            if mock["reply"] is None: route.abort("failed"); return
            route.fulfill(status=200, headers={"Access-Control-Allow-Origin": "*"}, content_type="application/json", body=json.dumps(mock["reply"]))
        ctx.route(APPS_SCRIPT, handle)
        return ctx, sent, mock

    note_url = URL.rstrip("/") + f"/notes/{NOTE}/"
    lab_url = URL.rstrip("/") + "/lab/"
    for name, w, h in [("phone", 390, 844), ("desktop", 1280, 800)]:
        ctx, sent, mock = ctx_for(w, h, {"ok": True}); errs = []
        pg = ctx.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))

        pg.goto(lab_url); pg.wait_for_timeout(200)
        cards = pg.evaluate("[...document.querySelectorAll('.list .card')].map(c => ({type: c.dataset.type, soon: c.classList.contains('soon'), href: (c.querySelector('a.card-title') || {}).pathname || ''}))")
        check(any(c["href"] == f"/notes/{NOTE}/" for c in cards) and any(c["soon"] for c in cards), f"{name}: lab lists the note and the placeholder")
        shown = lambda: pg.evaluate("[...document.querySelectorAll('.list .card')].filter(c => !c.hidden).map(c => c.dataset.type)")
        results = {}
        for f in ("research", "deep-dive", "pov", "all"):
            pg.click(f'[data-f="{f}"]'); results[f] = (shown(), pg.is_visible("#empty"))
        check(results["research"] == (["research"], False) and results["deep-dive"] == (["deep-dive"], False)
              and results["pov"] == ([], True) and results["all"][0] == ["research", "deep-dive"], f"{name}: lab filters work {results}")
        check("Free to read with your email" in pg.inner_text(".card.feature"), f"{name}: gated card asks for an email before sign-up")

        pg.goto(note_url); pg.wait_for_timeout(200)
        meta = pg.evaluate("Object.fromEntries([...document.querySelectorAll('meta[property^=og]')].map(m => [m.getAttribute('property'), m.content]))")
        check(meta.get("og:title") == NOTE_TITLE and meta.get("og:url") == NOTE_URL and meta.get("og:description", "").startswith("The barriers to learning"),
              f"{name}: note og tags describe the note")
        main = pg.inner_text("main")
        check(pg.is_hidden("#full") and pg.is_visible("#gate") and "Five barriers that now decide" not in main and "For most of history" in main,
              f"{name}: gated note shows the opening and hides the full text")

        pg.click('#gate [data-cta]')
        check(pg.is_visible("#dlg") and pg.inner_text("#dlg-topic b") == "A 20 minute conversation", f"{name}: gate's talk link opens the dialog")
        pg.click('#dlg-form ~ * [data-close], .dlg-top [data-close]')
        pg.click("[data-jump]"); pg.wait_for_timeout(500)
        check(pg.is_visible("#toast") and "roadmap is in the full note" in pg.inner_text("#toast"), f"{name}: skip to the roadmap points to the gate before sign-up")

        bad = []
        for fill, expect in [({}, "Enter a valid email so we can send you the link."), ({"#rq-email": "test@example.com"}, "Add your organisation."),
                             ({"#rq-org": "Test School"}, "Choose the role closest to yours.")]:
            for sel, v in fill.items(): pg.fill(sel, v)
            pg.click("#reqForm button[type=submit]")
            if pg.inner_text("#rq-err") != expect or not pg.is_hidden("#full"): bad.append(expect)
        check(not bad and not sent, f"{name}: missing fields show the right error and send nothing {bad or ''}")

        pg.select_option("#rq-role", "Faculty or teacher"); pg.click("#reqForm button[type=submit]")
        pg.wait_for_timeout(500)
        body = json.loads(sent[-1].post_data) if sent else {}
        check(sent and sent[-1].method == "POST" and sent[-1].headers.get("content-type", "").startswith("text/plain"), f"{name}: sign-up sends a text/plain POST")
        check(body.get("path") == "read" and body.get("note_title") == NOTE_TITLE and body.get("note_url") == NOTE_URL and body.get("option") == NOTE_TITLE
              and body.get("chip") == "Faculty or teacher" and body.get("message") == "Organisation: Test School" and body.get("keep_me_posted") is False
              and FIELDS <= set(body), f"{name}: sign-up payload has path read, note_title and note_url")
        check(pg.is_visible("#full") and pg.is_hidden("#gate") and "a link is on its way to test@example.com" in pg.inner_text("#welcomeLine")
              and pg.inner_text("#stateChip") == "Full note", f"{name}: sign-up opens the full note with the thanks line")

        ctas = pg.locator("#full [data-cta]"); wrong = []
        for i in range(ctas.count()):
            el = ctas.nth(i); topic = el.get_attribute("data-cta")
            el.click()
            if not (pg.is_visible("#dlg") and pg.inner_text("#dlg-topic b") == topic and pg.input_value("#dl-em") == "test@example.com"): wrong.append(topic)
            pg.keyboard.press("Escape")
        check(ctas.count() >= 10 and not wrong, f"{name}: each of {ctas.count()} CTAs opens the dialog with its topic {wrong or ''}")

        n = len(sent); pg.locator('#full [data-cta="Barrier review"]').click(); pg.fill("#dl-msg", "Testing, please ignore.")
        pg.click("#dl-send"); pg.wait_for_selector("#dl-done:not([hidden])", timeout=5000)
        body = json.loads(sent[-1].post_data) if len(sent) > n else {}
        check(body.get("path") == "talk" and body.get("option") == "Barrier review" and body.get("source") == f"note:{NOTE}" and FIELDS <= set(body)
              and "48 hours" in pg.inner_text("#dl-done"), f"{name}: CTA dialog sends path talk with the topic, then confirms")
        pg.keyboard.press("Escape")

        mock["reply"] = None; pg.locator('#full [data-cta="Faculty pilot group"]').click(); pg.fill("#dl-msg", "Kept after failure.")
        pg.click("#dl-send"); pg.wait_for_selector("#dl-err:not([hidden])", timeout=17000)
        check(pg.is_hidden("#dl-done") and "didn't go through" in pg.inner_text("#dl-err") and (pg.get_attribute("#dl-err a", "href") or "").startswith("mailto:")
              and pg.input_value("#dl-msg") == "Kept after failure.", f"{name}: CTA dialog failure keeps the message and offers email")
        pg.keyboard.press("Escape"); mock["reply"] = {"ok": True}

        n = len(sent); pg.locator("#full [data-notify]").click(); pg.click("#dl-send"); pg.wait_for_selector("#dl-done:not([hidden])", timeout=5000)
        body = json.loads(sent[-1].post_data) if len(sent) > n else {}
        check(body.get("path") == "join" and body.get("option") == "Next note" and body.get("keep_me_posted") is True, f"{name}: next note sign-up sends path join")
        pg.keyboard.press("Escape")

        pg.click("[data-jump]"); pg.wait_for_timeout(900)
        top = pg.evaluate("document.getElementById('roadmap').getBoundingClientRect().top")
        check(0 <= top < 200, f"{name}: skip to the roadmap scrolls to it once signed up (top {round(top)})")

        ctx.grant_permissions(["clipboard-read", "clipboard-write"])
        pg.click("[data-share]"); pg.wait_for_timeout(200)
        check(pg.evaluate("navigator.clipboard.readText()") == NOTE_URL, f"{name}: share copies the note URL")

        pg.reload(); pg.wait_for_timeout(300)
        check(pg.is_visible("#full") and pg.is_hidden("#gate") and pg.is_hidden("#welcomeLine"), f"{name}: reload keeps the note open")
        pg.goto(lab_url); pg.wait_for_timeout(200)
        check("Open to you" in pg.inner_text(".card.feature"), f"{name}: lab card shows Open to you after sign-up")
        check(not errs, f"{name}: no script errors on lab pages {errs or ''}")
        ctx.close()

        ctx, sent, mock = ctx_for(w, h, None)
        pg = ctx.new_page(); pg.goto(note_url); pg.wait_for_timeout(200)
        pg.fill("#rq-email", "test@example.com"); pg.fill("#rq-org", "Test School"); pg.select_option("#rq-role", "Student")
        pg.click("#reqForm button[type=submit]"); pg.wait_for_timeout(500)
        check(sent and pg.is_visible("#full"), f"{name}: a failed sign-up POST still opens the note")
        ctx.close()

    pg = b.new_page(viewport={"width": 360, "height": 740})
    for url in (URL, lab_url, note_url):
        pg.goto(url); pg.wait_for_timeout(300)
        check(pg.evaluate("document.documentElement.scrollWidth") <= 360, f"360px: no horizontal scroll on {url}")
    pg.goto(URL); pg.wait_for_timeout(200)
    links = pg.evaluate("[...document.querySelectorAll('#nav a[href=\"/lab/\"], .engine-link a')].map(a => a.href)")
    ok = [urllib.request.urlopen(u).status == 200 for u in links] if URL.startswith("http://localhost") else [True]
    check(len(links) == 2 and links[1].endswith(f"/notes/{NOTE}/") and all(ok), "homepage: nav and engine link to the lab and the note")
    pg.close()
    b.close()

print(f"\n{len(failures)} failure(s)")
sys.exit(1 if failures else 0)
