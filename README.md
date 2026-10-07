# BE Human Labs website

Static site for BE Human Labs, hosted on Cloudflare and deployed from this repo.

## Preview locally

```bash
python3 -m http.server 8000 -d public
```

Open http://localhost:8000. Add `?src=conf` to see the conference welcome.

## First-time setup

### 1. GitHub
Create a new repository (private is fine), then from this folder:

```bash
git init
git add .
git commit -m "First version of the site"
git branch -M main
git remote add origin https://github.com/<you>/be-human-labs.git
git push -u origin main
```

### 2. Cloudflare
1. In the Cloudflare dashboard, open **Workers & Pages** and choose **Create**.
2. Choose to import a Git repository, connect GitHub, and pick this repo.
3. Leave the build command empty. The deploy command is `npx wrangler deploy`. It reads `wrangler.jsonc`, which serves the `public` folder.
4. Deploy. You get a `*.workers.dev` address to check first.

From then on, every push to `main` deploys automatically. Other branches get preview links.

### 3. Domain
The site is live at https://behumanlabs.com on the Worker `bhl-01`. The domain is managed in the Cloudflare dashboard: open the Worker and go to **Settings → Domains & Routes** (add `www.behumanlabs.com` there too if you want it). Cloudflare sets up DNS and HTTPS for you.

`og:url`, `og:image` and the canonical link in `public/index.html` already point to `https://behumanlabs.com/`, so link previews on WhatsApp and LinkedIn show the right image. Update them if the domain ever changes.

### 4. Forms
Submissions stay in the page until you set `formEndpoint` in the `CONFIG` block of `public/index.html`. Options: a Formspree form, a Google Apps Script web app that writes to a Sheet, or a small Worker route in this same project.

## Working with Claude Code

Open this folder in Claude Code. `CLAUDE.md` holds the project rules: content sourcing, design system, logo, motion and tests. Ask for changes in plain language; Claude Code edits `public/index.html`, runs `tests/pressure_test.py`, and commits.

## Files

| Path | What it is |
|---|---|
| `public/index.html` | The homepage |
| `content/notes/` | From the lab notes (Markdown). Run `python3 tools/notes/build.py` after editing, and commit the result |
| `tools/notes/` | Builds `public/lab/` and `public/notes/` from the notes |
| `public/css/lab.css`, `public/js/` | Styles and scripts for the lab pages; `forms.js` is shared with the homepage |
| `public/be-human-labs-mark.svg` | Logo, exact vector |
| `public/be-human-labs-one-pager.pdf` | One-pager behind "Save my card" |
| `public/og-image.png` | Link preview image |
| `tests/pressure_test.py` | Scroll and content checks |
| `tools/logo/` | Logo trace pipeline and source PNG |
| `tools/one-pager/make.py` | Rebuilds the one-pager |
| `wrangler.jsonc` | Cloudflare config |
| `CLAUDE.md` | Rules for Claude Code |
