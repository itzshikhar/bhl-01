/* BE Human Labs: shared forms for every page (homepage, From the lab index, every note).
   One profile for every form: name, email, school or organisation, role, WhatsApp.
   The contract with the Apps Script endpoint is in tools/forms/README.md. */
(function () {
  const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  const EMAIL_MSG = "Enter a valid email so we can reply.";
  const KEY = "bhl-profile", SRC_KEY = "bhl-src";
  const esc = s => String(s == null ? "" : s).replace(/[&<>"']/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
  const $$ = (s, r) => [...(r || document).querySelectorAll(s)];

  /* ---------- the remembered profile (this device only) ---------- */
  function getProfile() {
    try {
      const p = JSON.parse(localStorage.getItem(KEY) || "null");
      return p && p.name && EMAIL_RE.test(p.email || "") && p.org && p.role ? p : null;
    } catch (e) { return null; }
  }
  function saveProfile(p) { try { localStorage.setItem(KEY, JSON.stringify(p)); } catch (e) { /* private mode: nothing remembered */ } }
  function clearProfile() { try { localStorage.removeItem(KEY); } catch (e) { /* nothing to clear */ } }

  /* ---------- markup ---------- */
  const FIELDS = [
    {k: "name", label: "Name", type: "text", ac: "name", ph: ""},
    {k: "email", label: "Email", type: "email", ac: "email", ph: "you@school.edu.in", im: "email"},
    {k: "org", label: "School or organisation", type: "text", ac: "organization", ph: "Your school"},
    {k: "role", label: "Role", type: "text", ac: "organization-title", ph: "e.g. Principal, Teacher, Parent, Founder"},
    {k: "wa", label: "WhatsApp", type: "tel", ac: "tel", ph: "+91", optional: true, hint: "We'll only use this to reply to you"}
  ];
  function profileHTML(prefix) {
    const p = getProfile();
    if (p) return `<p class="sending" id="${prefix}-sending">Sending as <b>${esc(p.name)}</b>, ${esc(p.role)} at ${esc(p.org)} &#183; <button type="button" class="change" data-bhl-change>Change</button></p>`;
    return FIELDS.map(f => `<div class="field${f.k === "wa" ? " full-w" : ""}"><label class="lbl" for="${prefix}-${f.k}">${f.label}${f.optional ? ' <span class="optional">(optional)</span>' : ""}</label>` +
      `<input id="${prefix}-${f.k}" name="${f.k}" type="${f.type}" autocomplete="${f.ac}"${f.hint ? ` aria-describedby="${prefix}-${f.k}-hint"` : ""}${f.im ? ` inputmode="${f.im}"` : ""}${f.ph ? ` placeholder="${esc(f.ph)}"` : ""}${f.optional ? "" : " required"}>` +
      `${f.hint ? `<span class="hint" id="${prefix}-${f.k}-hint">${f.hint}</span>` : ""}</div>`).join("");
  }
  const keepHTML = prefix => `<label class="check"><input type="checkbox" id="${prefix}-keep"><span>Keep me posted on future updates and opportunities. You can opt out any time.</span></label>`;
  const NOTICE = `<p class="note age">You need to be 18 or over to sign up.</p>` +
    `<p class="note privacy">We use your details to understand who reads our work, to reply to you, and, if you tick the box, to send updates. You can ask us to delete them any time.</p>`;

  // Fills every profile, consent and notice slot inside root. Safe to call again after a re-render.
  function mount(root) {
    $$("[data-bhl-profile]", root).forEach(el => { el.innerHTML = profileHTML(el.dataset.bhlProfile); });
    $$("[data-bhl-keep]", root).forEach(el => { if (!el.firstChild) el.innerHTML = keepHTML(el.dataset.bhlKeep); });
    $$("[data-bhl-notice]", root).forEach(el => { if (!el.firstChild) el.innerHTML = NOTICE; });
  }
  // "Change" forgets the profile on this device and shows empty fields in every form on the page.
  document.addEventListener("click", e => {
    const b = e.target.closest("[data-bhl-change]");
    if (!b) return;
    const slot = b.closest("[data-bhl-profile]");
    clearProfile();
    $$("[data-bhl-profile]").forEach(el => { el.innerHTML = profileHTML(el.dataset.bhlProfile); });
    if (slot) { const first = slot.querySelector("input"); if (first) first.focus(); }
  });

  // Reads the profile from a form's fields, or the remembered one. Returns {profile} or {error, el}.
  function readProfile(prefix) {
    const field = k => document.getElementById(`${prefix}-${k}`);
    if (!field("name")) {
      const p = getProfile();
      return p ? {profile: p} : {error: "Add your name.", el: null};
    }
    const v = k => field(k).value.trim();
    const p = {name: v("name"), email: v("email"), org: v("org"), role: v("role"), whatsapp: v("wa")};
    if (!p.name) return {error: "Add your name.", el: field("name")};
    if (!EMAIL_RE.test(p.email)) return {error: EMAIL_MSG, el: field("email")};
    if (!p.org) return {error: "Add your school or organisation.", el: field("org")};
    if (!p.role) return {error: "Add your role, for example Principal or Teacher.", el: field("role")};
    return {profile: p};
  }

  // Where the visitor came from: the ?src= value they first arrived with this visit, or "site".
  function source() {
    const fromUrl = new URLSearchParams(location.search).get("src");
    try {
      if (fromUrl) sessionStorage.setItem(SRC_KEY, fromUrl);
      return fromUrl || sessionStorage.getItem(SRC_KEY) || "site";
    } catch (e) { return fromUrl || "site"; }
  }

  // The one payload every form sends.
  function lead(p, action, item, detail, keep, honeypot) {
    return {name: p.name, email: p.email, org: p.org, role: p.role, whatsapp: p.whatsapp || "", action, item: item || "",
      detail: detail || "", keep_me_posted: !!keep, source: source(), site: location.hostname, time: new Date().toISOString(),
      company_website: honeypot || ""};
  }

  // Sends one submission and resolves "ok", "email" (the script rejected the address) or "error"
  // (server error, network failure, a 15 second timeout, or a reply that isn't the expected JSON). Never throws.
  // A text/plain POST with no other custom headers is a simple request, so there is no CORS preflight
  // (Apps Script can't answer one). Fetch follows Apps Script's redirect by default.
  // With a button, it is disabled and reads "Sending" while the request is in flight.
  async function post(endpoint, payload, btn, form) {
    const label = btn && btn.textContent, ctrl = new AbortController(), timer = setTimeout(() => ctrl.abort(), 15000);
    if (btn) { btn.disabled = true; btn.textContent = "Sending"; }
    if (form) form.setAttribute("aria-busy", "true");
    try {
      const r = await fetch(endpoint, {method: "POST", headers: {"Content-Type": "text/plain;charset=utf-8"}, body: JSON.stringify(payload), signal: ctrl.signal});
      const res = r.ok ? await r.json() : null;
      return res && res.ok === true ? "ok" : res && res.error === "email" ? "email" : "error";
    } catch (x) { return "error"; }
    finally {
      clearTimeout(timer);
      if (btn) { btn.disabled = false; btn.textContent = label; }
      if (form) form.removeAttribute("aria-busy");
    }
  }

  // The inline message for any failure other than a bad email, with a prefilled mailto link.
  function failHTML(to, subject, body) {
    const href = `mailto:${to}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body || "")}`;
    return `That didn't go through. Please try again, or email us at <a href="${esc(href)}">${esc(to)}</a>.`;
  }

  window.BHL = {EMAIL_RE, EMAIL_MSG, esc, post, failHTML, getProfile, saveProfile, clearProfile, mount, readProfile, source, lead};
})();
