"""Scroll-motion pressure test and content checks for BE Human Labs.

Run from the repo root:
    pip install -r tests/requirements.txt && python3 -m playwright install chromium
    python3 -m http.server 8000 -d public      # in another terminal
    python3 tests/pressure_test.py              # or: python3 tests/pressure_test.py https://behumanlabs.com

Exits with code 1 if any check fails.
"""
import filecmp, html, json, random, re, subprocess, sys, tempfile, urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000/"
STATE = """() => ({k:document.querySelectorAll('#knotMark .st.on').length, f:!!document.querySelector('#knotMark .frame.on'),
 lock:document.querySelector('#knotMark .mark').classList.contains('locked'), cap:document.getElementById('knotCap').textContent,
 off:document.querySelectorAll('#fieldMark .cell.off').length, fcap:document.getElementById('fieldCap').textContent,
 eng:document.querySelectorAll('#engine .erow.on').length})"""
FIELDS = {"name", "email", "org", "role", "whatsapp", "action", "item", "detail", "keep_me_posted", "source", "site", "time", "company_website"}
# Every request to Apps Script is intercepted; the form checks never reach the real endpoint.
APPS_SCRIPT = re.compile(r"^https://script\.google(usercontent)?\.com/")
ROOT = Path(__file__).resolve().parents[1]
FREE = ["the-question-has-changed", "homework-after-ai", "the-entry-level-gap"]
UNLISTED = "learning-when-answers-are-free"
PROFILE = {"name": "Asha Rao", "email": "test@example.com", "org": "Test School", "role": "Chair of governors & parent"}
AGE = "You need to be 18 or over to sign up."
PRIVACY = "We use your details to understand who reads our work, to reply to you, and, if you tick the box, to send updates. You can ask us to delete them any time."
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

    # ---------- shared helpers for form checks (every Apps Script request is mocked) ----------
    def mocked(w, h, reply=None):
        ctx = b.new_context(viewport={"width": w, "height": h}); sent = []
        mock = {"reply": reply if reply is not None else {"ok": True}}
        def handle(route, request):
            sent.append(request)
            if mock["reply"] == "abort": route.abort("failed"); return
            route.fulfill(status=200, headers={"Access-Control-Allow-Origin": "*"}, content_type="application/json", body=json.dumps(mock["reply"]))
        ctx.route(APPS_SCRIPT, handle)
        return ctx, sent, mock

    def bodies(sent):
        out = []
        for r in sent:
            try: out.append(json.loads(r.post_data))
            except (TypeError, ValueError): out.append({})
        return out

    def fill_profile(pg, prefix, prof=PROFILE):
        for k, v in prof.items(): pg.fill(f"#{prefix}-{k}", v)

    def form_extras_ok(pg, form_sel, prefix):
        """Consent box unticked by default, and the 18+ and privacy lines present."""
        return pg.evaluate(f"""(() => {{ const f = document.querySelector({json.dumps(form_sel)}); if (!f) return false;
            const keep = f.querySelector('#{prefix}-keep'); const t = f.innerText;
            return !!keep && !keep.checked && t.includes({json.dumps(AGE)}) && t.includes({json.dumps(PRIVACY)}); }})()""")

    def honeypot_ok(pg, form_sel):
        return pg.evaluate(f"""(() => {{ const f = document.querySelector({json.dumps(form_sel)} + ' input[name=company_website]'); if (!f) return false;
            const r = f.getBoundingClientRect(), cs = getComputedStyle(f);
            return f.classList.contains('hp') && f.getAttribute('aria-hidden') === 'true' && f.getAttribute('tabindex') === '-1'
              && f.getAttribute('autocomplete') === 'off' && cs.display !== 'none' && r.right <= 0; }})()""")

    # ---------- homepage forms, phone and desktop ----------
    for name, w, h in [("phone", 390, 844), ("desktop", 1280, 800)]:
        ctx, sent, mock = mocked(w, h); errs = []
        pg = ctx.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(URL); pg.wait_for_timeout(300)
        endpoint = pg.evaluate("CONFIG.formEndpoint")
        check(bool(re.fullmatch(r"https://script\.google\.com/macros/s/[\w-]+/exec", endpoint or "")), f"{name}: formEndpoint is an Apps Script /exec URL")
        check(pg.evaluate("CONFIG.events.edl") == "Ed Leadership", f"{name}: CONFIG.events has edl: Ed Leadership")

        missing = []
        for tab in ("talk", "join"):
            pg.click(f'[data-tab="{tab}"]')
            for opt in pg.evaluate("[...document.querySelectorAll('[data-opt]')].map(b => b.dataset.opt)"):
                pg.click(f'[data-opt="{opt}"]')
                if opt == "updates": continue   # choosing it is the consent; checked below
                if not (honeypot_ok(pg, "#f") and form_extras_ok(pg, "#f", "f")): missing.append(opt)
        check(not missing, f"{name}: every other homepage form has the honeypot, an unticked consent box and the 18+ and privacy lines {missing or ''}")
        pg.click('[data-tab="join"]'); pg.click('[data-opt="updates"]')
        upd = pg.evaluate(f"""(() => {{ const f = document.querySelector('#f'), t = f.innerText;
            return {{box: !!f.querySelector('input[type=checkbox]'), line: t.includes("You'll get occasional updates. You can opt out any time."),
                     notes: t.includes({json.dumps(AGE)}) && t.includes({json.dumps(PRIVACY)})}}; }})()""")
        check(upd == {"box": False, "line": True, "notes": True} and honeypot_ok(pg, "#f"),
              f"{name}: Keep me updated shows the updates line instead of a checkbox, with the 18+ and privacy lines {upd}")

        def open_ask(src=""):
            pg.goto(URL + src); pg.wait_for_timeout(200)
            pg.click('[data-tab="talk"]'); pg.click('[data-opt="ask"]')

        pg.evaluate("localStorage.clear()"); open_ask()
        errors = []
        for fill, expect in [({}, "Add your name."), ({"name": PROFILE["name"]}, "Enter a valid email so we can reply."),
                             ({"email": PROFILE["email"]}, "Add your school or organisation."), ({"org": PROFILE["org"]}, "Add your role, for example Principal or Teacher.")]:
            for k, v in fill.items(): pg.fill(f"#f-{k}", v)
            pg.click('#f button[type="submit"]')
            if pg.inner_text("#err") != expect: errors.append((expect, pg.inner_text("#err")))
        check(not errors and not sent, f"{name}: profile fields are required, with the right error for each {errors or ''}")
        pg.fill("#f-role", PROFILE["role"]); pg.fill("#msg", "Testing the form, please ignore.")
        pg.click('#f button[type="submit"]'); pg.wait_for_selector(".done", timeout=5000)
        req = sent[-1] if sent else None; body = bodies(sent)[-1] if sent else {}
        check(req is not None and req.method == "POST" and req.headers.get("content-type", "").startswith("text/plain"), f"{name}: form sends a text/plain POST")
        check(FIELDS <= set(body) and body.get("action") == "talk" and body.get("item") == "Ask or suggest: Question"
              and body.get("detail") == "Testing the form, please ignore." and body.get("role") == PROFILE["role"] and body.get("keep_me_posted") is False
              and body.get("source") == "site", f"{name}: homepage payload has the profile, action talk, item and detail (role accepts any text)")
        check(pg.is_visible(".done h3"), f"{name}: confirmation appears on ok:true")

        open_ask("?src=edl")
        sending = pg.inner_text("#f-sending") if pg.locator("#f-sending").count() else ""
        check(f"Sending as {PROFILE['name']}, {PROFILE['role']} at {PROFILE['org']}" in " ".join(sending.split()), f"{name}: profile is remembered and shown as Sending as ...")
        pg.click('#f button[type="submit"]'); pg.wait_for_selector(".done", timeout=5000)
        check(bodies(sent)[-1].get("source") == "edl" and bodies(sent)[-1].get("name") == PROFILE["name"], f"{name}: remembered profile sends, tagged with ?src=edl")

        pg.goto(URL); pg.wait_for_timeout(200); pg.click('[data-tab="join"]'); pg.click('[data-opt="updates"]')
        n = len(sent); pg.click('#f button[type="submit"]'); pg.wait_for_selector(".done", timeout=5000)
        bu = bodies(sent)[-1] if len(sent) > n else {}
        check(bu.get("action") == "join" and bu.get("item") == "Keep me updated" and bu.get("keep_me_posted") is True,
              f"{name}: Keep me updated sends action join with keep_me_posted true")

        mock["reply"] = {"ok": False, "error": "email"}; open_ask(); pg.click('#f button[type="submit"]')
        pg.wait_for_selector("#err:not([hidden])", timeout=5000)
        check("valid email" in pg.inner_text("#err") and not pg.is_visible(".done"), f"{name}: ok:false email asks for a valid email")

        for label, reply in [("ok:false server", {"ok": False, "error": "server"}), ("network abort", "abort")]:
            mock["reply"] = reply; open_ask(); pg.fill("#msg", "Kept after failure.")
            pg.click('#f button[type="submit"]')
            pg.wait_for_selector("#err:not([hidden])", timeout=17000)
            pg.wait_for_function("!document.querySelector('#f button[type=submit]').disabled", timeout=17000)
            href = pg.get_attribute("#err a", "href") or ""
            check(not pg.is_visible(".done") and "didn't go through" in pg.inner_text("#err") and href.startswith("mailto:" + pg.evaluate("CONFIG.email")),
                  f"{name}: {label} shows the error with a mailto link, no confirmation")
            check(pg.input_value("#msg") == "Kept after failure.", f"{name}: typed message kept on {label}")

        mock["reply"] = {"ok": True}; open_ask(); pg.click("[data-bhl-change]")
        stored = pg.evaluate("localStorage.getItem('bhl-profile')")
        check(stored is None and pg.is_visible("#f-name") and pg.input_value("#f-name") == "", f"{name}: Change clears the remembered profile")
        check(not errs, f"{name}: no script errors in homepage forms {errs or ''}")
        ctx.close()

    # ---------- From the lab: build ----------
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

    # Everything that is served, as text.
    served = {}
    for f in (ROOT / "public").rglob("*"):
        if f.is_file() and f.suffix in (".html", ".js", ".css", ".txt", "") or f.name == "_redirects":
            raw = f.read_text(errors="ignore")
            served[str(f.relative_to(ROOT))] = raw
    def plain(raw):
        return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", raw)).split())
    served_text = {k: plain(v) for k, v in served.items()}

    generated = {k: v for k, v in served.items() if k.startswith("public/notes/")}
    dashed = [k for k, v in generated.items() if re.search("–|—|&[mn]dash;|&#821[12];", v)]
    check(not dashed, f"lab: no em or en dashes in generated pages {dashed or ''}")
    leaks = [k for k, v in served.items() if "ednote" in v or "Prototype" in v or "On the live site" in v]
    check(not leaks, f"lab: no ednote, Prototype or On the live site anywhere in public/ {leaks or ''}")

    # Request pieces: no sentence from after <!-- more --> may be written to public/.
    from bs4 import BeautifulSoup
    def source(slug):
        t = (ROOT / f"content/notes/{slug}.html").read_text()
        m = re.match(r"---\n(.*?)\n---\n", t, re.S)
        return m.group(1), re.sub(r'<p class="ednote">.*?</p>', "", t[m.end():], flags=re.S)
    def sentences(fragment):
        soup = BeautifulSoup(fragment, "html.parser")
        for h in soup.find_all("h2"): h.decompose()   # section headings are listed on purpose in the request panel
        text = " ".join(soup.get_text(" ").split())
        return [s for s in re.split(r"(?<=[.!?])\s+", text) if len(s.split()) >= 6]
    pieces = sorted(p.stem for p in (ROOT / "content/notes").glob("*.html"))
    meta = {s: source(s)[0] for s in pieces}
    request = [s for s in pieces if re.search(r'^access:\s*"?request', meta[s], re.M)]
    public_sources = " ".join(" ".join(source(s)[1].split()) if s not in request else " ".join(source(s)[1].split("<!-- more -->")[0].split()) for s in pieces)
    public_sources = plain(public_sources)
    leaked = []
    for s in request:
        for sent_ in sentences(source(s)[1].split("<!-- more -->")[1]):
            if sent_ in public_sources: continue   # also legitimately public elsewhere
            hit = next((k for k, v in served_text.items() if sent_ in v), None)
            if hit: leaked.append((s, sent_[:60], hit))
    check(len(request) == 12 and not leaked, f"lab: no locked sentence from the 12 request pieces is in public/ {leaked[:3] or ''}")

    redirects = (ROOT / "public/_redirects").read_text() if (ROOT / "public/_redirects").exists() else ""
    check(re.search(r"^/lab/?\s+/notes/\s+301", redirects, re.M) is not None and not (ROOT / "public/lab").exists(), "lab: /lab/ redirects permanently to /notes/")
    unlisted_page = ROOT / f"public/notes/{UNLISTED}/index.html"
    check(unlisted_page.exists() and 'name="robots" content="noindex"' in unlisted_page.read_text(), "lab: the unlisted note builds, with noindex")

    # Fact-check spot checks, in what is served.
    def page_text(slug): return served_text.get(f"public/notes/{slug}/index.html", "")
    spots = {
        "Gallup stat names the US": "6 in 10 US public school teachers used AI for their work in 2024-25" in page_text("the-teacher-in-the-ai-era"),
        "Common Sense stat names the US": "of US teenagers had used an AI companion at least once" in page_text("belonging-in-the-age-of-chatbots"),
        "Challenge Success stat names the US": "of US high school students reported cheating in the past month" in page_text("outsourced-thinking"),
        "ICRIER chart says employment": "Entry-level employment fell" in page_text("the-entry-level-gap") and "hiring fell" not in page_text("the-entry-level-gap"),
        "Good questions says Top 10": "Top 10" in page_text("good-questions-have-a-shape") and "Top 6" not in page_text("good-questions-have-a-shape"),
    }
    check(all(spots.values()), f"lab: fact-check spot checks {[k for k, v in spots.items() if not v] or ''}")

    # ---------- From the lab: pages and forms, phone and desktop ----------
    base = URL.rstrip("/")
    for name, w, h in [("phone", 390, 844), ("desktop", 1280, 800)]:
        ctx, sent, mock = mocked(w, h); errs = []
        pg = ctx.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))

        pg.goto(base + "/notes/"); pg.wait_for_timeout(200)
        cards = pg.evaluate("""[...document.querySelectorAll('.card')].map(c => ({shelf: c.closest('.shelf').id, type: c.dataset.type,
            href: c.querySelector('a.card-title').pathname, lock: !!c.querySelector('.lock')}))""")
        free_cards = [c for c in cards if c["shelf"] == "freeShelf"]; req_cards = [c for c in cards if c["shelf"] == "reqShelf"]
        check(len(free_cards) == 3 and len(req_cards) == 12 and all(c["lock"] for c in req_cards) and not any(c["lock"] for c in free_cards)
              and [c["href"] for c in free_cards] == [f"/notes/{s}/" for s in FREE], f"{name}: index lists 3 free and 12 request cards")
        check(all(UNLISTED not in c["href"] for c in cards), f"{name}: the unlisted note is not on the index")
        shown = lambda: [c for c in pg.evaluate("[...document.querySelectorAll('#reqShelf .card')].filter(c => !c.hidden).map(c => c.dataset.type)")]
        res = {}
        for f in ("research", "deep-dive", "pov", "all"):
            pg.click(f'[data-f="{f}"]'); res[f] = (sorted(set(shown())), len(shown()), pg.is_visible("#empty"))
        check(res["research"][0] == ["research"] and res["deep-dive"][0] == ["deep-dive"] and res["pov"][0] == ["pov"] and res["all"][1] == 12
              and not any(v[2] for v in res.values()), f"{name}: request shelf type filter works")
        pg.evaluate("document.querySelectorAll('#reqShelf .card').forEach(c => c.hidden = true); document.getElementById('empty').hidden = false")
        check(pg.inner_text("#empty") == "Nothing of this kind yet.", f"{name}: empty filter message reads Nothing of this kind yet.")
        nav = pg.evaluate("[...document.querySelectorAll('#nav a')].map(a => a.textContent.trim())")
        check("How we work" in nav and "From the lab" in nav and "The lab" not in nav, f"{name}: lab nav shows How we work and From the lab")

        # Free piece: sign-up wall.
        pg.goto(base + f"/notes/{FREE[0]}/"); pg.wait_for_timeout(200)
        main = pg.inner_text("main")
        check(pg.is_hidden("#full") and pg.is_visible("#gate") and "What changes in a school." not in main, f"{name}: free piece hides the full text until sign-up")
        check(form_extras_ok(pg, "#signupForm", "su") and honeypot_ok(pg, "#signupForm"), f"{name}: sign-up wall has the honeypot, an unticked consent box and the 18+ and privacy lines")
        pg.click("#signupForm button[type=submit]")
        check(pg.inner_text("#su-err") == "Add your name." and not sent and pg.is_hidden("#full"), f"{name}: sign-up wall requires the profile")
        fill_profile(pg, "su"); pg.click("#signupForm button[type=submit]"); pg.wait_for_timeout(500)
        b0 = bodies(sent)[-1] if sent else {}
        check(b0.get("action") == "signup" and b0.get("item") == FREE[0] and b0.get("email") == PROFILE["email"] and FIELDS <= set(b0),
              f"{name}: sign-up sends action signup with the slug")
        check(pg.is_visible("#full") and pg.is_hidden("#gate") and f"Thanks, {PROFILE['name']}." in pg.inner_text("#welcomeLine")
              and "on its way" not in pg.inner_text("main"), f"{name}: sign-up reveals the full text at once")
        n = len(sent); pg.reload(); pg.wait_for_timeout(400)
        check(pg.is_visible("#full") and len(sent) == n, f"{name}: reload keeps the piece open and sends nothing")
        pg.goto(base + f"/notes/{FREE[1]}/"); pg.wait_for_timeout(500)
        opens = [x for x in bodies(sent)[n:] if x.get("action") == "open"]
        pg.reload(); pg.wait_for_timeout(400)
        opens2 = [x for x in bodies(sent)[n:] if x.get("action") == "open"]
        check(pg.is_visible("#full") and len(opens) == 1 and opens[0].get("item") == FREE[1] and len(opens2) == 1,
              f"{name}: a second free piece opens directly and sends one open event")
        nxt = pg.evaluate("[...document.querySelectorAll('.readnext a.rncard')].map(a => a.pathname)")
        check(nxt == ["/notes/a-note-for-parents-on-ai/", "/notes/outsourced-thinking/"], f"{name}: Next from the lab follows the related slugs {nxt}")

        # CTAs route by prefix, with the profile prefilled.
        ctas = pg.locator("#full [data-cta]"); wrong = []
        for i in range(ctas.count()):
            el = ctas.nth(i); text = el.get_attribute("data-cta")
            el.click(); pg.wait_for_timeout(50)
            expect = "Join the movement" if re.match(r"(Share your story|Join the movement)", text) else "Talk to us"
            if not (pg.is_visible("#dlg") and pg.inner_text("#dlg-h") == expect and pg.inner_text("#dlg-topic b") == text and pg.locator("#dl-sending").count()):
                wrong.append(text)
            pg.keyboard.press("Escape")
        check(ctas.count() >= 3 and not wrong, f"{name}: each of {ctas.count()} CTAs opens the right dialog with its text {wrong or ''}")
        n = len(sent); pg.locator('#full [data-cta^="Share your story"]').first.click(); pg.fill("#dl-msg", "A task that works.")
        pg.click("#dl-send"); pg.wait_for_selector("#dl-done:not([hidden])", timeout=5000)
        b1 = bodies(sent)[-1] if len(sent) > n else {}
        check(b1.get("action") == "cta" and b1.get("item", "").startswith("Share your story") and b1.get("detail") == f"note:{FREE[1]} | A task that works."
              and FIELDS <= set(b1), f"{name}: a CTA sends action cta with its text and note:<slug>")
        pg.keyboard.press("Escape")
        check(form_extras_ok(pg, "#dlg-form", "dl") and honeypot_ok(pg, "#dlg-form"), f"{name}: the dialog has the honeypot, an unticked consent box and the 18+ and privacy lines")
        first = pg.locator("#full [data-cta]").first
        first.click(); pg.check("#dl-keep"); pg.keyboard.press("Escape"); first.click()
        check(not pg.is_checked("#dl-keep"), f"{name}: the dialog's consent box is unticked again each time it opens")
        pg.keyboard.press("Escape")

        # Request piece.
        slug = "ai-briefing-for-school-leaders"
        pg.evaluate("localStorage.clear()"); pg.goto(base + f"/notes/{slug}/"); pg.wait_for_timeout(200)
        check(form_extras_ok(pg, "#requestForm", "rq") and honeypot_ok(pg, "#requestForm") and pg.is_visible("#rq-use"),
              f"{name}: request panel has the profile, the use field, an unticked consent box and the 18+ and privacy lines")
        pg.click('#requestForm [data-talk]')
        check(pg.inner_text("#dlg-h") == "Talk to us" and pg.inner_text("#dlg-topic b") == "A 20 minute conversation", f"{name}: Prefer to talk first opens Talk to us")
        pg.keyboard.press("Escape")
        mock["reply"] = {"ok": False, "error": "server"}
        fill_profile(pg, "rq"); pg.fill("#rq-use", "A staff meeting on homework"); pg.click("#requestForm button[type=submit]")
        pg.wait_for_selector("#rq-err:not([hidden])", timeout=5000)
        check(pg.inner_text("#rq-err").startswith("That didn't go through. Please try again, or email us at") and pg.is_hidden("#requestDone"),
              f"{name}: a failed request shows the error and no success panel")
        mock["reply"] = {"ok": True}; n = len(sent)
        pg.click("#requestForm button[type=submit]"); pg.wait_for_selector("#requestDone:not([hidden])", timeout=5000)
        b2 = bodies(sent)[-1] if len(sent) > n else {}
        check(b2.get("action") == "request" and b2.get("item") == slug and b2.get("detail") == "A staff meeting on homework" and FIELDS <= set(b2),
              f"{name}: request sends action request with the slug and the use text")
        done = pg.inner_text("#requestDone")
        links = pg.evaluate("[...document.querySelectorAll('#requestDone a')].map(a => a.pathname)")
        check("Request received." in done and "We read every request ourselves and will reply within three working days after the conference." in done
              and links == [f"/notes/{s}/" for s in FREE], f"{name}: request success panel with links to the three free pieces")

        # A failed sign-up POST still reveals the text.
        ctx.close(); ctx, sent, mock = mocked(w, h, "abort")
        pg = ctx.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(base + f"/notes/{FREE[2]}/"); pg.wait_for_timeout(200)
        fill_profile(pg, "su"); pg.click("#signupForm button[type=submit]"); pg.wait_for_timeout(500)
        check(sent and pg.is_visible("#full"), f"{name}: a failed sign-up POST still reveals the text")
        check(not errs, f"{name}: no script errors on lab pages {errs or ''}")
        ctx.close()

    # ---------- every page at 360px, and homepage links ----------
    pg = b.new_page(viewport={"width": 360, "height": 740})
    pages = [URL, base + "/notes/"] + [base + f"/notes/{s}/" for s in pieces]
    wide = []
    for u in pages:
        pg.goto(u); pg.wait_for_timeout(150)
        if pg.evaluate("document.documentElement.scrollWidth") > 360: wide.append(u)
    check(not wide, f"360px: no horizontal scroll on {len(pages)} pages {wide or ''}")
    pg.goto(URL); pg.wait_for_timeout(200)
    nav = pg.evaluate("[...document.querySelectorAll('#nav a')].map(a => [a.textContent.trim(), a.getAttribute('href')])")
    check(["How we work", "#lab"] in nav and ["From the lab", "/notes/"] in nav and not any(t == "The lab" for t, _ in nav), "homepage: nav shows How we work and From the lab (to /notes/)")
    engine = pg.evaluate("(() => { const a = document.querySelector('.engine-link a'); return [a.textContent.trim(), a.getAttribute('href')]; })()")
    check(engine == ["See the engine at work: The question has changed", "/notes/the-question-has-changed/"], f"homepage: engine link goes to The question has changed {engine}")
    linking = [k for k, v in served.items() if k.endswith(".html") and k != f"public/notes/{UNLISTED}/index.html" and UNLISTED in v]
    check(not linking, f"lab: no page links to the unlisted {UNLISTED} {linking or ''}")
    links = pg.evaluate("[...document.querySelectorAll('#nav a[href=\"/notes/\"], .engine-link a')].map(a => a.href)")
    ok = [urllib.request.urlopen(u).status == 200 for u in links] if URL.startswith("http://localhost") else [True]
    check(len(links) == 2 and all(ok), "homepage: nav and engine links resolve")
    pg.close()
    b.close()

print(f"\n{len(failures)} failure(s)")
sys.exit(1 if failures else 0)
