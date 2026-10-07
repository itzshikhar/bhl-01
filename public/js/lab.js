/* BE Human Labs: behaviour for the From the lab index and every piece. Needs js/forms.js.
   Page settings (endpoint, email, slug, title, URL, access) come from #page-data, written by tools/notes/build.py.
   Free pieces: the full text is in the page behind a sign-up wall (not access control).
   Request pieces: only the opening is in the page; the rest is never published. */
(() => {
  const $ = s => document.querySelector(s), $$ = s => [...document.querySelectorAll(s)];
  const PAGE = JSON.parse($("#page-data").textContent);
  const OPENED = "bhl-opened";   // free pieces this device has already logged as read
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const scrollToEl = el => el.scrollIntoView({behavior: reduce ? "auto" : "smooth", block: "start"});
  const send = (lead, btn, form) => PAGE.endpoint ? BHL.post(PAGE.endpoint, lead, btn, form) : Promise.resolve("ok");

  BHL.mount(document);

  // phone menu, as on the homepage
  const mb = $(".menu-btn"), nav = $("#nav");
  mb.addEventListener("click", () => { const o = nav.classList.toggle("open"); mb.setAttribute("aria-expanded", o); });
  nav.addEventListener("click", e => { if (e.target.closest("a")) { nav.classList.remove("open"); mb.setAttribute("aria-expanded", false); } });

  let toastTimer;
  function toast(text) {
    const el = $("#toast"); el.textContent = text; el.hidden = false;
    clearTimeout(toastTimer); toastTimer = setTimeout(() => { el.hidden = true; }, 3600);
  }
  const showErr = (el, msg, focus) => { el.textContent = msg; el.hidden = false; if (focus) focus.focus(); };

  /* ---------- index: type filter on the request shelf ---------- */
  $$("[data-f]").forEach(b => b.addEventListener("click", () => {
    const f = b.dataset.f;
    $$("[data-f]").forEach(x => x.setAttribute("aria-pressed", String(x === b)));
    let shown = 0;
    $$("#reqShelf .card").forEach(c => { c.hidden = !(f === "all" || c.dataset.type === f); if (!c.hidden) shown++; });
    $("#empty").hidden = shown > 0;
  }));

  /* ---------- free pieces: the sign-up wall ---------- */
  const opened = () => { try { return JSON.parse(localStorage.getItem(OPENED) || "{}") || {}; } catch (e) { return {}; } };
  const markOpened = slug => { try { localStorage.setItem(OPENED, JSON.stringify(Object.assign(opened(), {[slug]: true}))); } catch (e) { /* private mode */ } };
  const unlocked = () => PAGE.access === "free" && !!$("#full") && !$("#full").hidden;
  function setOpen(open) {
    if (!$("#full")) return;
    $("#full").hidden = !open; $("#gate").hidden = open; $("#teaser").hidden = open;
  }
  if (PAGE.kind === "note" && PAGE.access === "free") {
    const p = BHL.getProfile();
    setOpen(!!p);
    // A known reader opening another free piece: log it once per piece per device.
    if (p && !opened()[PAGE.slug]) {
      markOpened(PAGE.slug);
      send(BHL.lead(p, "open", PAGE.slug, "", false, "")).then(r => { if (r !== "ok") console.warn("[BE Human Labs] open not recorded:", r); });
    }
  }
  const signup = $("#signupForm");
  if (signup) signup.addEventListener("submit", e => {
    e.preventDefault();
    const err = $("#su-err"), read = BHL.readProfile("su");
    if (read.error) { showErr(err, read.error, read.el); return; }
    err.hidden = true;
    const lead = BHL.lead(read.profile, "signup", PAGE.slug, "", $("#su-keep").checked, $("#su-cw").value);
    console.log("[BE Human Labs]", lead);
    // The text opens straight away, whether or not the request gets through.
    send(lead).then(r => { if (r !== "ok") console.warn("[BE Human Labs] sign-up not recorded:", r, lead); });
    BHL.saveProfile(read.profile); markOpened(PAGE.slug);
    BHL.mount(document);
    setOpen(true);
    const w = $("#welcomeLine");
    w.textContent = `Thanks, ${read.profile.name}. The rest of the article is below.`;
    w.hidden = false; w.focus({preventScroll: true}); scrollToEl(w);
  });

  /* ---------- request pieces: the request panel ---------- */
  const req = $("#requestForm");
  if (req) req.addEventListener("submit", async e => {
    e.preventDefault();
    const err = $("#rq-err"), btn = req.querySelector('button[type="submit"]'), read = BHL.readProfile("rq");
    if (btn.disabled) return;
    if (read.error) { showErr(err, read.error, read.el); return; }
    err.hidden = true;
    const use = $("#rq-use").value.trim();
    const lead = BHL.lead(read.profile, "request", PAGE.slug, use, $("#rq-keep").checked, $("#rq-cw").value);
    const result = await send(lead, btn, req);
    if (result !== "ok") {
      if (result === "email") { showErr(err, BHL.EMAIL_MSG, document.getElementById("rq-email")); return; }
      err.innerHTML = BHL.failHTML(PAGE.email, `Request: ${PAGE.title}`, use); err.hidden = false;
      return;
    }
    console.log("[BE Human Labs]", lead);
    BHL.saveProfile(read.profile); BHL.mount(document);
    req.hidden = true;
    const done = $("#requestDone"); done.hidden = false; done.focus({preventScroll: true});
    done.scrollIntoView({block: "center", behavior: reduce ? "auto" : "smooth"});
  });

  /* ---------- skip to a section, share ---------- */
  $$("[data-jump]").forEach(b => b.addEventListener("click", () => {
    const target = document.getElementById(b.dataset.jump);
    if (PAGE.access === "request" || !unlocked()) {
      scrollToEl($("#gate"));
      if (b.dataset.hint) toast(b.dataset.hint);
      return;
    }
    if (target) { scrollToEl(target); target.focus({preventScroll: true}); }
  }));
  $$("[data-share]").forEach(b => b.addEventListener("click", () => {
    const fallback = () => toast(`Copy this link: ${PAGE.url}`);
    try { navigator.clipboard.writeText(PAGE.url).then(() => toast("Link copied. Paste it to a colleague."), fallback); }
    catch (x) { fallback(); }
  }));

  /* ---------- calls to action: the Talk to us and Join dialog ----------
     data-cta routes by its text: "Share your story..." and "Join the movement..." open Join;
     everything else ("Talk to us...", "Request...") opens Talk to us. data-talk is a plain Talk to us. */
  const dlg = $("#dlg"), form = $("#dlg-form"), err = $("#dl-err");
  let current = null;   // {mode: "talk" | "join", action: "cta" | "talk", item}
  const routeOf = text => /^(Share your story|Join the movement)/i.test(text) ? "join" : "talk";
  function openDialog(mode, action, item) {
    current = {mode, action, item};
    $("#dlg-h").textContent = mode === "join" ? "Join the movement" : "Talk to us";
    $("#dlg-topic b").textContent = item;
    err.hidden = true; form.hidden = false; $("#dl-done").hidden = true;
    BHL.mount(dlg);
    $("#dl-keep").checked = false;   // unticked by default, every time the dialog opens
    dlg.showModal();
    ($("#dl-name") || $("#dl-msg")).focus();
  }
  document.addEventListener("click", e => {
    const t = e.target.closest("[data-cta],[data-talk],[data-close]");
    if (!t) return;
    if (t.dataset.cta) openDialog(routeOf(t.dataset.cta), "cta", t.dataset.cta);
    else if (t.dataset.talk) openDialog("talk", "talk", t.dataset.talk);
    else dlg.close();
  });
  // A click on the dimmed backdrop closes the dialog.
  dlg.addEventListener("click", e => {
    if (e.target !== dlg) return;
    const r = dlg.getBoundingClientRect();
    if (e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom) dlg.close();
  });

  form.addEventListener("submit", async e => {
    e.preventDefault();
    const btn = $("#dl-send"), read = BHL.readProfile("dl");
    if (btn.disabled) return;
    if (read.error) { showErr(err, read.error, read.el); return; }
    err.hidden = true;
    const message = $("#dl-msg").value.trim();
    const where = PAGE.slug ? `note:${PAGE.slug}` : "notes";
    const detail = current.action === "cta" ? (message ? `${where} | ${message}` : where) : message;
    const lead = BHL.lead(read.profile, current.action, current.item, detail, $("#dl-keep").checked, $("#dl-cw").value);
    const result = await send(lead, btn, form);
    if (result !== "ok") {
      if (result === "email") { showErr(err, BHL.EMAIL_MSG, document.getElementById("dl-email")); return; }
      // Nothing is cleared: the profile and message stay in the form.
      err.innerHTML = BHL.failHTML(PAGE.email, `BE Human Labs: ${current.item}`, message); err.hidden = false;
      return;
    }
    console.log("[BE Human Labs]", lead);
    BHL.saveProfile(read.profile); BHL.mount(document);
    $("#dl-msg").value = "";
    const done = $("#dl-done");
    done.querySelector("h3").textContent = current.mode === "join" ? "Thank you for joining." : "Thanks. We'll reply within 48 hours.";
    done.querySelector("b").textContent = read.profile.email;
    form.hidden = true; done.hidden = false; done.focus();
  });
})();
