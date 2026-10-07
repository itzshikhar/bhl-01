// BE Human Labs: website form submissions go into this Sheet.
// Update with Deploy > Manage deployments > edit > New version (keeps the same URL).

const NOTIFY_EMAIL = 'behumanlabs@zohomail.in';
const REPLY_TO = 'behumanlabs@zohomail.in';
const SHEET_NAME = 'Leads';
const HEADERS = ['Received', 'Email', 'Path', 'Option', 'Topic', 'Message',
                 'Keep me posted', 'Source', 'Site', 'Sent at'];
// Reader emails only ever link to pages on this site.
const NOTE_URL_PREFIX = 'https://behumanlabs.com/notes/';

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

    // Alert to us. The lead is saved even if this fails.
    try {
      MailApp.sendEmail({
        to: NOTIFY_EMAIL,
        replyTo: email,
        subject: (d.path === 'read' ? 'New reader: ' : 'New lead: ') +
                 (d.option || d.path || 'website') + ' from ' + email,
        body: HEADERS.map((h, i) => h + ': ' + row[i]).join('\n')
      });
    } catch (mailErr) {}

    // Reader copy: only for note sign-ups, only to our own note pages,
    // and at most once per address per note every six hours.
    if (d.path === 'read') {
      try { sendReaderCopy(email, d.note_title, d.note_url); } catch (readerErr) {}
    }

    return reply({ ok: true });
  } catch (err) {
    return reply({ ok: false, error: 'server' });
  }
}

function sendReaderCopy(email, title, url) {
  url = String(url || '');
  title = String(title || 'our latest note').slice(0, 120);
  if (url.indexOf(NOTE_URL_PREFIX) !== 0 || /\s/.test(url) || url.length > 300) return;

  const cache = CacheService.getScriptCache();
  const key = 'r:' + Utilities.base64EncodeWebSafe(
    Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256, email.toLowerCase() + '|' + url));
  if (cache.get(key)) return;
  cache.put(key, '1', 21600); // 6 hours, the longest the cache allows

  MailApp.sendEmail({
    to: email,
    replyTo: REPLY_TO,
    name: 'BE Human Labs',
    subject: 'Your copy: ' + title,
    body:
      'Thank you for reading ' + title + '.\n\n' +
      'Here is your link, to come back to it or pass it on:\n' + url + '\n\n' +
      'If something in it sparked a thought, or you would like to try it at your institution, ' +
      'just reply to this email. It comes straight to us.\n\n' +
      'BE Human Labs\nhttps://behumanlabs.com'
  });
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
