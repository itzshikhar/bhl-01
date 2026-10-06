/* BE Human Labs: behaviour for the From the lab page and every note. Needs js/forms.js.
   Page settings (endpoint, email, note slug, title and URL) come from #page-data, written by tools/notes/build.py. */
(() => {
  const $ = s => document.querySelector(s), $$ = s => [...document.querySelectorAll(s)];
  const PAGE = JSON.parse($("#page-data").textContent);
  const KEY = "bhl-reader";
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const scrollToEl = el => el.scrollIntoView({behavior: reduce ? "auto" : "smooth", block: "start"});
  const src = new URLSearchParams(location.search).get("src");

  // The reader, once they have signed up on any gated note. A sign-up wall, not access control.
  let reader = null;
  try { reader = JSON.parse(localStorage.getItem(KEY) || "null"); } catch (e) { reader = null; }
  if (!reader || !BHL.EMAIL_RE.test(reader.email || "")) reader = null;
  let lastEmail = "";

  // phone menu, as on the homepage
  const mb = $(".menu-btn"), nav = $("#nav");
  mb.addEventListener("click", () => { const o = nav.classList.toggle("open"); mb.setAttribute("aria-expanded", o); });
  nav.addEventListener("click", e => { if (e.target.closest("a")) { nav.classList.remove("open"); mb.setAttribute("aria-expanded", false); } });

  let toastTimer;
  function toast(text) {
    const el = $("#toast"); el.textContent = text; el.hidden = false;
    clearTimeout(toastTimer); toastTimer = setTimeout(() => { el.hidden = true; }, 3200);
  }

  /* ---------- lab page ---------- */
  $$("[data-f]").forEach(b => b.addEventListener("click", () => {
    const f = b.dataset.f;
    $$("[data-f]").forEach(x => x.setAttribute("aria-pressed", String(x === b)));
    let shown = 0;
    $$(".list .card").forEach(c => { c.hidden = !(f === "all" || c.dataset.type === f); if (!c.hidden) shown++; });
    const empty = $("#empty"); if (empty) empty.hidden = shown > 0;
  }));
  if (reader) $$("[data-access] span").forEach(s => { s.textContent = "Open to you"; });

  /* ---------- note: the sign-up gate ---------- */
  function setOpen(open) {
    $("#full").hidden = !open; $("#gate").hidden = open; $("#teaser").hidden = open;
    $("#stateChip").textContent = open ? "Full note" : "Opening only";
  }
  if (PAGE.gated) setOpen(!!reader);

  const req = $("#reqForm");
  if (req) req.addEventListener("submit", e => {
    e.preventDefault();
    const email = $("#rq-email").value.trim(), org = $("#rq-org").value.trim(), role = $("#rq-role").value, err = $("#rq-err");
    const bad = !BHL.EMAIL_RE.test(email) ? ["Enter a valid email so we can send you the link.", "#rq-email"]
              : !org ? ["Add your organisation.", "#rq-org"]
              : !role ? ["Choose the role closest to yours.", "#rq-role"] : null;
    if (bad) { err.textContent = bad[0]; err.hidden = false; $(bad[1]).focus(); return; }
    err.hidden = true;

    const lead = {email, path: "read", option: PAGE.title, chip: role, message: `Organisation: ${org}`, keep_me_posted: false,
      source: src || "note", site: location.hostname, time: new Date().toISOString(), company_website: $("#rq-cw").value,
      note_title: PAGE.title, note_url: PAGE.url};
    console.log("[BE Human Labs]", lead);
    // The note opens straight away, whether or not the request gets through.
    if (PAGE.endpoint) BHL.post(PAGE.endpoint, lead).then(r => { if (r !== "ok") console.warn("[BE Human Labs] sign-up not recorded:", r, lead); });

    reader = {email, org, role};
    try { localStorage.setItem(KEY, JSON.stringify(reader)); } catch (x) { /* private mode: the note still opens */ }
    setOpen(true);
    const w = $("#welcomeLine");
    w.textContent = `Thanks. The rest of the note is below, and a link is on its way to ${email}.`;
    w.hidden = false; w.focus({preventScroll: true}); scrollToEl(w);
  });

  /* ---------- note: skip to a section, share ---------- */
  $$("[data-jump]").forEach(b => b.addEventListener("click", () => {
    const target = document.getElementById(b.dataset.jump);
    if (PAGE.gated && !reader) {
      scrollToEl($("#gate")); $("#rq-email").focus({preventScroll: true});
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

  /* ---------- Talk to us dialog: every data-cta, and data-notify ---------- */
  const dlg = $("#dlg"), form = $("#dlg-form"), err = $("#dl-err");
  let mode = "talk", topic = "";
  function openDialog(m, t) {
    mode = m; topic = t;
    const join = m === "join";
    $("#dlg-h").textContent = join ? "Tell me when the next note is out" : "Talk to us";
    $("#dlg-topic").hidden = join; $("#dlg-topic b").textContent = t;
    $("#dl-msg-row").hidden = join; $("#dl-keep-row").hidden = join;
    $("#dl-send").textContent = join ? "Keep me updated" : "Send";
    err.hidden = true; form.hidden = false; $("#dl-done").hidden = true;
    const em = $("#dl-em");
    if (!em.value) em.value = (reader && reader.email) || lastEmail;
    dlg.showModal();
    (em.value && !join ? $("#dl-msg") : em).focus();
  }
  document.addEventListener("click", e => {
    const t = e.target.closest("[data-cta],[data-notify],[data-close]");
    if (!t) return;
    if (t.dataset.cta) openDialog("talk", t.dataset.cta);
    else if (t.hasAttribute("data-notify")) openDialog("join", "Next note");
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
    const btn = $("#dl-send"), el = $("#dl-em"), email = el.value.trim(), join = mode === "join";
    const badEmail = () => { err.textContent = BHL.EMAIL_MSG; err.hidden = false; el.focus(); };
    if (!BHL.EMAIL_RE.test(email)) { badEmail(); return; }
    err.hidden = true;
    const message = join ? "" : $("#dl-msg").value.trim();
    const lead = {email, path: join ? "join" : "talk", option: topic, chip: null, message,
      keep_me_posted: join ? true : $("#dl-keep").checked, source: PAGE.source, site: location.hostname,
      time: new Date().toISOString(), company_website: $("#dl-cw").value};
    if (PAGE.endpoint) {
      const result = await BHL.post(PAGE.endpoint, lead, btn, form);   // js/forms.js
      if (result !== "ok") {
        if (result === "email") { badEmail(); return; }
        // Nothing is cleared: the email and message stay in the form.
        err.innerHTML = BHL.failHTML(PAGE.email, `BE Human Labs: ${topic}`, message);
        err.hidden = false;
        return;
      }
    }
    console.log("[BE Human Labs]", lead);
    lastEmail = email; $("#dl-msg").value = "";
    const done = $("#dl-done");
    done.querySelector("h3").textContent = join ? "You're on the list." : "Thanks. We'll reply within 48 hours.";
    done.querySelector("b").textContent = email;
    form.hidden = true; done.hidden = false; done.focus();
  });
})();
