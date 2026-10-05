# Forms: Google Sheet via Apps Script

The site's "Get involved" forms post to a Google Apps Script web app, which adds each submission as a row in a Google Sheet and emails a notification.

`apps-script.gs` in this folder is a copy of the script, kept for reference and review. The live copy runs in Google, not from this repo: editing this file changes nothing until you paste it into the editor and deploy a new version.

## Where it lives

Open the **"BE Human Labs leads"** Google Sheet, then **Extensions > Apps Script**. Submissions go to the **Leads** tab.

## Deploy settings

Deploy as a **Web app** with:

- **Execute as:** Me
- **Who has access:** Anyone

The web app URL ends in `/exec` and is set as `CONFIG.formEndpoint` in `public/index.html`. Opening it in a browser returns `{"ok":true,"service":"bhl-leads"}`, which is a quick way to check it is live.

## Run setup() once after a permissions change

After any change that needs new permissions (for example, the first deploy, or new Sheet or email access), select `setup` in the editor's function menu and click **Run**. Approve the permissions prompt. It creates the Leads tab if needed and sends a test email to the notification address.

## Updating the script: New version, same URL

Always update through **Deploy > Manage deployments**, click the edit (pencil) icon on the existing deployment, set **Version** to **New version**, then **Deploy**. This keeps the same `/exec` URL.

Never use **Deploy > New deployment** for an update. It creates a different URL, and the site keeps posting to the old one until `CONFIG.formEndpoint` is changed and the site redeployed.

## Contract with the site

The site sends a simple `POST` (header `Content-Type: text/plain;charset=utf-8`, no other custom headers, so the browser does not send a CORS preflight, which Apps Script cannot answer). The body is a JSON string:

```
{ email, path, option, chip, message, keep_me_posted, source, site, time, company_website }
```

The script replies `{"ok":true}`, or `{"ok":false,"error":"email"}` for an invalid email, or `{"ok":false,"error":"server"}` for anything else. `company_website` is a hidden honeypot field: if it has a value, the script replies `{"ok":true}` and saves nothing.

Preview builds of the site post to the same Sheet. The **Site** column (`location.hostname`) tells production (`behumanlabs.com`) apart from previews (`*.workers.dev`).
