// BE Human Labs: every website form writes one row to the Activity tab.
// No emails go out per submission. One summary email goes out each evening.
// After editing: Deploy > Manage deployments > edit > New version (keeps the same URL).
// Set the time zone once: Project Settings > Time zone > (GMT+05:30) India Standard Time.

const NOTIFY_EMAIL = 'behumanlabs@zohomail.in';
const ACTIVITY = 'Activity';
const HEADERS = ['Received', 'Name', 'Email', 'Organisation', 'Role', 'WhatsApp',
                 'Action', 'Article or topic', 'Detail', 'Keep me posted',
                 'Source', 'Site', 'Status', 'Emailed'];
const ACTIONS = ['signup', 'open', 'request', 'talk', 'join', 'cta'];
const SUMMARY_HOUR = 21; // 9pm, in the project's time zone

// Run once from the editor: creates the Activity tab and switches on the evening summary.
function setup() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  Logger.log('Attached to: ' + ss.getName() + ' | ' + ss.getUrl());
  activity();
  Logger.log('Activity tab ready');
  ScriptApp.getProjectTriggers()
    .filter(t => t.getHandlerFunction() === 'dailySummary')
    .forEach(t => ScriptApp.deleteTrigger(t));
  ScriptApp.newTrigger('dailySummary').timeBased().everyDays(1).atHour(SUMMARY_HOUR).create();
  Logger.log('Evening summary scheduled for about ' + SUMMARY_HOUR + ':00, time zone ' + Session.getScriptTimeZone());
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

    // Older pages sent "path" and "option"; map them so nothing is lost.
    let action = String(d.action || d.path || '').toLowerCase();
    if (action === 'read') action = 'signup';
    if (ACTIONS.indexOf(action) === -1) action = 'talk';
    const item = d.item || d.option || '';
    const detail = d.detail || d.message || d.chip || '';

    const row = [new Date(), d.name, email, d.org, d.role, d.whatsapp,
                 action, item, detail, d.keep_me_posted ? 'Yes' : 'No',
                 d.source, d.site, '', ''].map(clean);

    const lock = LockService.getScriptLock();
    lock.waitLock(10000);
    try { activity().appendRow(row); } finally { lock.releaseLock(); }

    return reply({ ok: true });
  } catch (err) {
    return reply({ ok: false, error: 'server' });
  }
}

// One email a day: what happened since the last summary.
function dailySummary() {
  const sh = activity();
  const last = sh.getLastRow();
  if (last < 2) return;
  const rows = sh.getRange(2, 1, last - 1, HEADERS.length).getValues();
  const since = new Date(Date.now() - 24 * 60 * 60 * 1000);
  const today = rows.filter(r => r[0] instanceof Date && r[0] >= since);
  if (!today.length) return;

  const count = a => today.filter(r => r[6] === a).length;
  const people = new Set(today.map(r => String(r[2]).toLowerCase())).size;
  const reads = {};
  today.filter(r => r[6] === 'signup' || r[6] === 'open')
       .forEach(r => { reads[r[7]] = (reads[r[7]] || 0) + 1; });
  const top = Object.keys(reads).sort((a, b) => reads[b] - reads[a]).slice(0, 5)
       .map(k => '  ' + reads[k] + '  ' + k);
  const requests = today.filter(r => r[6] === 'request')
       .map(r => '  ' + r[1] + ', ' + r[4] + ', ' + r[3] + ': ' + r[7]);
  const talks = today.filter(r => r[6] === 'talk' || r[6] === 'cta')
       .map(r => '  ' + r[1] + ', ' + r[4] + ', ' + r[3] + ': ' + r[7]);

  const body = [
    'Last 24 hours on behumanlabs.com',
    '',
    'People: ' + people,
    'New readers: ' + count('signup') + '   Article opens: ' + count('open'),
    'Access requests: ' + count('request') + '   Conversations: ' + (count('talk') + count('cta')) +
      '   Joined: ' + count('join'),
    '',
    'Top articles', top.length ? top.join('\n') : '  none',
    '',
    'Access requests', requests.length ? requests.join('\n') : '  none',
    '',
    'Want to talk', talks.length ? talks.join('\n') : '  none',
    '',
    'Full log: ' + SpreadsheetApp.getActiveSpreadsheet().getUrl()
  ].join('\n');

  MailApp.sendEmail(NOTIFY_EMAIL, 'BE Human Labs today: ' + people + ' people, ' +
    count('request') + ' requests', body);
}

// Opening the web app URL in a browser shows this, so you can check it's live.
function doGet() {
  return reply({ ok: true, service: 'bhl-leads' });
}

function activity() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let s = ss.getSheetByName(ACTIVITY) || ss.insertSheet(ACTIVITY);
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
