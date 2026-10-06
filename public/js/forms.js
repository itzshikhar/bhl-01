/* BE Human Labs: shared form submission, used by the homepage, the lab page and every note.
   The contract with the Apps Script endpoint is in tools/forms/README.md. */
(function () {
  const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  const EMAIL_MSG = "Enter a valid email so we can reply.";
  const esc = s => String(s).replace(/[&<>"']/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));

  // Sends one submission and resolves "ok", "email" (the script rejected the address) or "error"
  // (server error, network failure, a 15 second timeout, or a reply that isn't the expected JSON). Never throws.
  // A text/plain POST with no other custom headers is a simple request, so there is no CORS preflight
  // (Apps Script can't answer one). Fetch follows Apps Script's redirect by default.
  // With a button, it is disabled and reads "Sending" while the request is in flight.
  async function post(endpoint, lead, btn, form) {
    const label = btn && btn.textContent, ctrl = new AbortController(), timer = setTimeout(() => ctrl.abort(), 15000);
    if (btn) { btn.disabled = true; btn.textContent = "Sending"; }
    if (form) form.setAttribute("aria-busy", "true");
    try {
      const r = await fetch(endpoint, {method: "POST", headers: {"Content-Type": "text/plain;charset=utf-8"}, body: JSON.stringify(lead), signal: ctrl.signal});
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

  window.BHL = {EMAIL_RE, EMAIL_MSG, esc, post, failHTML};
})();
