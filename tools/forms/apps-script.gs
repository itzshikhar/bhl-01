// BE Human Labs: website form submissions go into this Sheet.
// Update with Deploy > Manage deployments > edit > New version (keeps the same URL).

const NOTIFY_EMAIL = 'behumanlabs@zohomail.in';
const SHEET_NAME = 'Leads';
const HEADERS = ['Received', 'Email', 'Path', 'Option', 'Topic', 'Message',
                 'Keep me posted', 'Source', 'Site', 'Sent at'];

// Run once from the editor: creates the Leads tab and sends a test email.
function setup() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  Logger.log('Attached to: ' + ss.getName() + ' | ' + ss.getUrl());
  sheet();
  Logger.log('Leads tab ready');
  MailApp.sendEmail(NOTIFY_EMAIL, 'BE Human Labs form is connected',
    'Leads from behumanlabs.com will be added to: ' + ss.getUrl());
  Logger.log('Test email sent to ' + NOTIFY_EMAIL);
}

function doPost(e) {
  try {
    const d = JSON.parse((e && e.postData && e.postData.contents) || '{}');

    // Honeypot: a hidden field people never see. Bots fill it; we quietly ignore them.
    if (d.company_website) return reply({ ok: true });

    const email = String(d.email || '').trim();
    if (email.length > 254 || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      return reply({ ok: false, error: 'email' });
    }

    const row = [new Date(), email, d.path, d.option, d.chip, d.message,
                 d.keep_me_posted ? 'Yes' : 'No', d.source, d.site, d.time].map(clean);

    const lock = LockService.getScriptLock();
    lock.waitLock(10000);
    try { sheet().appendRow(row); } finally { lock.releaseLock(); }

    // The lead is saved even if the email alert fails.
    try {
      MailApp.sendEmail({
        to: NOTIFY_EMAIL,
        replyTo: email,
        subject: 'New lead: ' + (d.option || d.path || 'website') + ' from ' + email,
        body: HEADERS.map((h, i) => h + ': ' + row[i]).join('\n')
      });
    } catch (mailErr) {}

    return reply({ ok: true });
  } catch (err) {
    return reply({ ok: false, error: 'server' });
  }
}

// Opening the web app URL in a browser shows this, so you can check it's live.
function doGet() {
  return reply({ ok: true, service: 'bhl-leads' });
}

function sheet() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let s = ss.getSheetByName(SHEET_NAME) || ss.insertSheet(SHEET_NAME);
  if (s.getLastRow() === 0) { s.appendRow(HEADERS); s.setFrozenRows(1); }
  return s;
}

// Keeps values short, and stops text that starts like a formula from running in the Sheet.
function clean(v) {
  if (v instanceof Date) return v;
  let s = v == null ? '' : String(v).slice(0, 2000);
  if (/^[=+\-@]/.test(s)) s = "'" + s;
  return s;
}

function reply(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}
