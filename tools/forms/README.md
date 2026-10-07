# Forms: Google Sheet via Apps Script

Every form on the site (the homepage Get involved forms, the sign-up wall on free pieces, the request panel on request pieces, and the Talk to us and Join dialogs on the notes) posts to one Google Apps Script web app. The script adds one row per submission to the **Activity** tab of a Google Sheet. It sends no email per submission. Once a day, in the evening, it emails one summary of the last 24 hours.

`apps-script.gs` in this folder is a copy of the script, kept for reference and review. The live copy runs in Google, not from this repo: editing this file changes nothing until you paste it into the editor and deploy a new version.

## Where it lives

Open the **"BE Human Labs leads"** Google Sheet, then **Extensions > Apps Script**. Submissions go to the **Activity** tab. The older **Leads** tab, from before October 2026, is no longer written to; keep it for the history.

## Deploy settings

Deploy as a **Web app** with:

- **Execute as:** Me
- **Who has access:** Anyone

The web app URL ends in `/exec` and is set as `CONFIG.formEndpoint` in `public/index.html`. Opening it in a browser returns `{"ok":true,"service":"bhl-leads"}`, which is a quick way to check it is live.

## Time zone

Set it once: **Project Settings > Time zone > (GMT+05:30) India Standard Time**. The Received column and the evening summary use it.

## Run setup() once after a permissions change

After the first deploy of this version, and after any change that needs new permissions, select `setup` in the editor's function menu and click **Run**, then approve the permissions prompt. It creates the Activity tab if needed and schedules the evening summary (a daily trigger at about 21:00 in the project's time zone). Running it again replaces the trigger rather than adding a second one.

## Updating the script: New version, same URL

Always update through **Deploy > Manage deployments**, click the edit (pencil) icon on the existing deployment, set **Version** to **New version**, then **Deploy**. This keeps the same `/exec` URL.

Never use **Deploy > New deployment** for an update. It creates a different URL, and the site keeps posting to the old one until `CONFIG.formEndpoint` is changed and the site redeployed.

## Contract with the site

The site sends a simple `POST` (header `Content-Type: text/plain;charset=utf-8`, no other custom headers, so the browser does not send a CORS preflight, which Apps Script cannot answer). The body is a JSON string:

```
{ name, email, org, role, whatsapp, action, item, detail, keep_me_posted, source, site, time, company_website }
```

- `action` is one of `signup` (first read of a free piece), `open` (a known reader opens another free piece, once per piece per device), `request` (access to a request piece), `talk` (Talk to us), `join` (Join the movement) or `cta` (a call to action inside a piece).
- `item` is the article slug, the chosen option or the call to action's text. `detail` is the message, or for calls to action, `note:<slug>` plus any message.
- `source` is the `?src=` value the visitor arrived with (for example `edl` for Ed Leadership), or `site`. `site` is the hostname, so preview builds (`*.workers.dev`) can be told apart from `behumanlabs.com`.
- `company_website` is a hidden honeypot field: if it has a value, the script replies `{"ok":true}` and saves nothing.

The script replies `{"ok":true}`, or `{"ok":false,"error":"email"}` for an invalid email, or `{"ok":false,"error":"server"}` for anything else. Older pages that still send `path` and `option` are mapped onto `action` and `item` (`read` becomes `signup`), so nothing is lost while caches update.

## The Activity tab

Columns: Received, Name, Email, Organisation, Role, WhatsApp, Action, Article or topic, Detail, Keep me posted, Source, Site, Status, Emailed. The script leaves **Status** and **Emailed** blank: they are for you, to track a request ("approved", "sent") and when you replied.

## The evening summary

One email a day to `NOTIFY_EMAIL`, subject "BE Human Labs today: N people, N requests", covering the last 24 hours: people, new readers, article opens, access requests, conversations and joins, the top five articles, every access request and every conversation, with a link to the Sheet. No activity, no email. Apps Script's daily email quota is no longer a concern, since the site sends at most one email a day.

Preview builds of the site post to the same Sheet. The **Site** column tells production (`behumanlabs.com`) apart from previews (`*.workers.dev`).
