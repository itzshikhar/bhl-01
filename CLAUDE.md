# BE Human Labs website

A single-page brand site for BE Human Labs, a human transformation lab. Static HTML, no build step, hosted on Cloudflare Workers (static assets) and deployed from GitHub. The audience is primarily Indian.

Live at https://behumanlabs.com, served by the Cloudflare Worker `bhl-01`. The `name` in `wrangler.jsonc` must stay `bhl-01`, or a push deploys to a different Worker. Custom domains are managed in the Cloudflare dashboard, not in `wrangler.jsonc`.

Read this file before every task. Read `docs/brand-core.md` before changing any copy.

## Commands

```bash
python3 -m http.server 8000 -d public          # preview at http://localhost:8000
python3 tests/pressure_test.py                  # run with the preview server up; must print "0 failure(s)"
python3 tools/card/make.py                      # rebuild the card image and the vCard (after changing CONFIG contact fields)
python3 tools/notes/build.py                    # rebuild public/notes/ from content/notes/
npx wrangler deploy                             # manual deploy (normally a push to main deploys)
```

Test setup, once: `pip install -r tests/requirements.txt && python3 -m playwright install chromium` (this also installs the note build's requirements from `tools/notes/requirements.txt`).

**Run the pressure test after any change to HTML structure, CSS layout, or the script, and fix failures before committing.** After any change to `content/notes/`, `tools/notes/` or the homepage `CONFIG`, run the note build first: the test fails if `public/` is out of date. After changing the contact fields in `CONFIG`, run `tools/card/make.py` too: the test fails if the vCard is out of date.

## Layout

```
public/                  everything that is served
  index.html             the whole site: CSS, markup, and script in one file
  404.html
  be-human-labs-mark.svg the logo, exact vector
  favicon.svg
  shikhar-anand-be-human-labs.png   "Save my card": both sides of the business card, built by tools/card/make.py
  shikhar-anand-be-human-labs.vcf   "Save my contact": vCard 3.0 built from CONFIG by tools/card/make.py
  connect/index.html     the business card QR's landing page (see Business card below)
  og-image.png           social preview (1200x630)
  fonts/                 Gloock and Hanken Grotesk as Latin-subset WOFF2, self-hosted (OFL licences alongside)
  _redirects             Cloudflare redirects: /lab/ to /notes/ (301)
  _headers               Cloudflare headers: the vCard is served as text/vcard, as a download
  css/lab.css            styles for the From the lab index and pieces (part 1 copies the homepage tokens and skins)
  js/forms.js            the shared profile and form submission, used by every form on every page
  js/lab.js              index and piece behaviour: filter, sign-up wall, request panel, Talk to us and Join dialog, share
  notes/index.html       GENERATED: the From the lab index
  notes/<slug>/index.html  GENERATED: one page per piece
content/notes/<slug>.html  the pieces: HTML with front matter (source for public/notes/)
tests/pressure_test.py   scroll-motion, content, form and lab checks (Playwright)
tools/logo/              how the logo vector was made; source PNG; build/mark-paths.json
tools/card/              make.py, both sides of the printed card (card-front.png, card-back.png) and the contact photo
tools/one-pager/make.py  RETIRED: the old one-pager PDF; kept for reference, writes only into tools/one-pager/
tools/forms/             Apps Script for form submissions (reference copy) and its setup notes
tools/notes/             build.py, its templates and requirements: turns content/notes/ into public/notes/
tools/fonts/             full TTF sources of both fonts; the served WOFF2 files are built from these
docs/                    brand core (content source)
wrangler.jsonc           Cloudflare config
```

`index.html` is the source of truth for the homepage. There is no template or bundler. Edit it directly. From the lab is the one exception: it is generated from `content/notes/` by `tools/notes/build.py` (see From the lab below). Never edit `public/notes/` by hand.

To rebuild the served fonts (needs `pip install fonttools brotli`), keeping the Latin range and Hanken's full weight axis:

```bash
U="U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,U+20AC,U+20B9,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD"
for f in Gloock-Regular HankenGrotesk; do pyftsubset tools/fonts/$f.ttf --unicodes="$U" --layout-features='*' --flavor=woff2 --output-file=public/fonts/$f.woff2; done
```

## Content rules

- **Source of copy:** `docs/brand-core.md`. Its L0 to L2 lines are locked; do not reword them unless asked.
- **Audience is Indian.** Every figure must be Indian or genuinely global (multi-country). Never label single-country data as "global". If a figure only exists for one country, name the country or leave it out, and tell the user.
- **Never round beyond the source.** The source says 39%, so the page says "2 in 5" (the study's own phrasing). Writing 40% is not allowed.
- **Every big number has a `<cite>` line**, and every evidence item has a `<small>` source. The test checks the big numbers.
- **Figures in use.** Every figure on the page, with its source and scope. Keep this list in step with the page.
  - *Big numbers (`<cite>`)*
    - **2 in 5** people have had any AI training; two in three use AI regularly. University of Melbourne and KPMG, 48,000 people, 47 countries, 2025. Multi-country.
    - **55%** of Indian IT firms saw entry-level employment fall after adopting AI; 25% at mid level. ICRIER, *AI and Jobs: This Time is No Different*, 651 IT firms, 10 Indian cities, surveyed Nov 2025 to Jan 2026, supported by OpenAI (all named in the cite). India. Researchers frame it as slower hiring, not job losses; keep the wording "saw entry-level employment fall".
  - *Divide section evidence (`<small>`)*
    - Industry produced about 91% of notable AI models in 2025. Stanford AI Index 2026. Global count.
    - Almost half of people say they have limited knowledge of AI; only 40% of employees say their workplace has a policy or guidance on generative AI use. University of Melbourne and KPMG, 2025. Multi-country. The 40% is a share of employees, not of all respondents; keep "employees" in the wording. Verified against Melbourne Business School's 2025 impact report: https://www.mbs.edu/2025-impact-report/impact-stories/Global-study-reveals-trust-of-AI-remains-a-critical-challenge
    - Across 25 countries, awareness of and enthusiasm for AI are higher among the highly educated and in wealthier countries. Pew Research Center, October 2025. Multi-country.
    - In India only 19% are more concerned than excited about AI. Pew Research Center, October 2025. India.
  - *Growing section evidence (`<small>`)*
    - 39% of workers' core skills expected to change by 2030; 63% of employers name skill gaps as the biggest barrier. World Economic Forum, Future of Jobs Report 2025. Global.
    - 59 in 100 workers will need training by 2030; 11 of those are not expected to get it. World Economic Forum, Future of Jobs Report 2025. Global.
    - Adult literacy stagnated or declined across 31 countries over the past decade. OECD Survey of Adult Skills, December 2024. Multi-country.
    - 4% of Indian IT firms trained more than half their workforce in AI-related skills. ICRIER, same study. India.
    - Indian IT net hiring about 6 lakh (FY22) to about 1.4 lakh (FY26). Xpheno, cited by Nomura, August 2026. India.
    - Fresher hiring in India up 17% YoY, February 2026, led by non-IT. Naukri JobSpeak. India. Keep this counterpoint directly after the hiring figure.
  - *Systems evidence (`<small>`)*
    - Meta-analysis of 89 studies: the work environment shapes whether training is applied. Blume, Ford, Baldwin and Huang, *Journal of Management*, 2010. Research synthesis, not country data.
    - Peer, supervisor and organisational support each predict whether training lasts; peer support most. Hughes, Zajac, Woods and Salas, *Human Factors*, 2020. Research synthesis, not country data.
- **Excluded on purpose:** the MIT "95% of pilots" figure (disputed), Bhava × Ekatva (parked), LinkedIn (removed for now), the sources list and the "Where do the figures come from" FAQ (removed by request), the Upwork Research Institute 2024 workload and training figures (96% / 77% / 26%; four Western countries only), and the Stanford Digital Economy Lab early-career 19% finding (US data only).
- **Style:** plain, warm, evidence-led. Sentence case. No em dashes or en dashes (the test fails on them). One message per section: one headline, one supporting line, one visual. Detail goes behind "Read more" or "See the evidence".
- **Opt-in wording:** "Keep me posted on future updates and opportunities. You can opt out any time."
- **Wordmark:** always "BE HUMAN LABS" in the header and footer. In running text, "BE Human Labs".

## Design rules

- **Tokens** live on `:root`. Pale Oak `#C5B7AA`, Black `#000100`, Dark Coffee `#361E1E`, Deep Walnut `#563C2D`, Olive Wood `#8D6D42`, ground `#E7DDD2`.
- **Skins** (`.skin`, `.skin-pale`, `.skin-black`, `.skin-coffee`, `.skin-walnut`) re-point the same variables (`--bg --ink --soft --line --mark --btn --btn-ink`). Use a skin; never hard-code colours in a section. Neighbouring sections must use different skins.
- Display font Gloock, body Hanken Grotesk, both self-hosted in `public/fonts`. Do not add Google Fonts links.
- Square corners (2px max), hairline rules, no shadows, no gradients. Spacing scale 8, 16, 24, 40, 64, 96.
- **Actions:** one filled button and one text link per section at most.
- **Icons:** plus that turns into a minus for accordions (`.pm`); chevron down that flips up for options that expand in place; up-right arrow for links that leave the page. Do not use logo strands as icons.
- Mobile first. Check 360px and 390px widths; the header must stay on one line. The nav has five links (Why, How we work, From the lab, Get involved, Save my card), so from 760px to 959px the header uses tighter gaps, 20px side padding and a 15px wordmark to stay on one line (same rule in `index.html` and `lab.css`). Check 760px after changing anything in the header.

### Exceptions for notes

The From the lab pages (`public/css/lab.css`, part 2) follow the approved library design, which departs from the rules above in these places only. Do not spread them to the homepage.
- **The fade gradient.** The opening of a free or request piece fades out over the sign-up wall or request panel (`.fade::after`, a linear gradient to the ground colour).
- **Round bullets and dots.** List bullets (`ul.plain`), timeline dots (`ol.road`) and score dots (`.score`) are circles, not square.
- **More than one action per section.** Pieces carry several calls to action (nudges, offer cards, the three-path panel), as approved.

## Logo rules

- **Never redraw or approximate the logo.** It is an exact trace of `tools/logo/source/logo.png`, symmetrised over 8 rotations. Paths are in `tools/logo/build/mark-paths.json`.
- Structure: one frame plus **8 identical strands**, each rotated 45°. Strands do not cross.
- In `index.html`:
  - `<symbol id="bhl-mark">` near the top of `<body>` is the static logo. Use `<use href="#bhl-mark">` for every static instance (header, footer, tiles, pattern).
  - The `MARK` module in the script builds the animated version. Each strand has a hidden centre line that draws in, clipped by the exact outline, then the exact shape fades in.
- Always use the full mark, even small. Never the frame outline alone.
- To regenerate after a logo change: run `tools/logo/1_trace.py`, `2_centrelines.py`, `3_build_mark.py`, then replace the `MARK` module in `index.html` with `tools/logo/build/mark.js` and the `<symbol>` contents with the new paths.

## Motion rules

- **Hero:** strands draw in one by one, then the frame closes. Once, on load.
- **Four dimensions:** each step adds a pair of opposite strands (0, 2, 4, 6, 8). The fourth step closes the frame and the knot turns 45° to settle.
- **Where it matters:** one mark, then neighbours, then the full tiled field.
- **Engine:** a line fills as you read down the three rows.
- `story()` decides the active step from scroll position on every frame. The active step is the last one whose heading has crossed the trigger line: 72% of the viewport on phones, 66% on desktop. This keeps scrolling down and up in sync. **Do not switch back to IntersectionObserver.**
- Steps already reached stay at full opacity; only steps further down are dimmed.
- Respect `prefers-reduced-motion`: everything shows in its final state.

## Business card

- **The QR code** on the printed card points to `go.behumanlabs.com/connect`. A Cloudflare redirect rule (in the dashboard) sends it to `/connect/`, which goes on to `/` at once (`location.replace` on load, with a meta refresh for browsers without script). It is a real page, not a `_redirects` rule, so Cloudflare Web Analytics counts each visit to `/connect` as a card scan. It is `noindex` and adds no query tag.
- **To change where the card goes, edit `public/connect/index.html`, never the card.**
- **Save my card** (header and phone menu, on every page) downloads `shikhar-anand-be-human-labs.png`: the contact side on top, the logo side below, a small gap in the ground colour, at full resolution, under about 1 MB. Rebuild it with `tools/card/make.py` from `tools/card/card-front.png` and `card-back.png`.
- **Save my contact** opens `shikhar-anand-be-human-labs.vcf`: vCard 3.0, CRLF line endings, lines folded at 75 octets, with the mark as its photo (`tools/card/contact-photo.png`: 256px, Dark Coffee mark on Pale Oak, rendered from `be-human-labs-mark.svg`; `make.py --photo` re-renders it). Never redraw the logo for it.
- **The one-pager is retired.** `tools/one-pager/` stays for reference; nothing links to the PDF and the test checks that.

## Forms and settings

`CONFIG` at the top of the script:
- `name`, `title`, `org`, `phone`, `email`, `website`, `note`: the saved contact. `tools/card/make.py` builds `public/shikhar-anand-be-human-labs.vcf` from them (`email` is also the fallback address in form errors).
- `linkedinUrl`: optional; shows the LinkedIn option in Get involved.
- `bookingUrl`: shows "Pick a time" after a "Let's talk" or "Collaborate" submission.
- `formEndpoint`: the Google Apps Script web app that adds each submission to the "BE Human Labs leads" Sheet: `https://script.google.com/macros/s/AKfycbyzvvUjOMvt9-it4gJlwyAEVs8Mm8MyGAyuIkV818dBAS7ihMEE9X_CwTJWOX9VMXZe8g/exec`. Blank keeps submissions in the page only (logged to console).
- `events`: `?src=<key>` shows "Met at <name>? Welcome." and tags each lead with its source.

**One profile for every form.** Every form on every page (homepage Talk to us and Join the movement, the sign-up wall, the request panel, the Talk to us and Join dialogs on the pieces) uses the same profile, rendered and read by `public/js/forms.js` (`BHL.mount`, `BHL.readProfile`):
- **Fields:** Name, Email, School or organisation, Role (all required; Role is free text, placeholder "e.g. Principal, Teacher, Parent, Founder", no dropdown), WhatsApp (optional, hint "We'll only use this to reply to you").
- **Errors:** "Add your name.", "Enter a valid email so we can reply.", "Add your school or organisation.", "Add your role, for example Principal or Teacher."
- **Remembered** in `localStorage` (`bhl-profile`, wrapped in try/catch) after a successful submission, or at once for a sign-up. When known, the fields are replaced by "Sending as <Name>, <Role> at <Organisation> · Change"; Change forgets it on this device and shows empty fields.
- **Consent:** "Keep me posted on future updates and opportunities. You can opt out any time." on every form, **unticked by default**, and unticked again every time the Talk to us or Join dialog opens. The one exception is the homepage "Keep me updated" option: choosing it is the consent, so it shows "You'll get occasional updates. You can opt out any time." instead of the checkbox and always sends `keep_me_posted` true.
- **Under every form:** "You need to be 18 or over to sign up." and "We use your details to understand who reads our work, to reply to you, and, if you tick the box, to send updates. You can ask us to delete them any time."
- **Honeypot:** every form has a hidden `company_website` field (class `.hp`, off-screen rather than `display:none`, `aria-hidden="true"`, `tabindex="-1"`, `autocomplete="off"`). The script quietly drops any submission where it is filled.

**Submissions (Google Sheet).**
- **Request:** `POST` to `formEndpoint` (`BHL.post`), body `JSON.stringify(payload)`, header `Content-Type: text/plain;charset=utf-8` and no other custom headers. That keeps it a simple request with no CORS preflight, which Apps Script cannot answer. Do not switch to `application/json` or add headers.
- **Payload, every form:** `{ name, email, org, role, whatsapp, action, item, detail, keep_me_posted, source, site, time, company_website }` (`BHL.lead`).
- **Actions:**
  - `signup`: first read of a free piece; `item` = slug.
  - `open`: a known profile opens another free piece; `item` = slug; sent once per piece per device (`bhl-opened` in `localStorage`).
  - `request`: Request access on a request piece; `item` = slug; `detail` = "What would you use it for?".
  - `talk`: homepage Talk to us (`item` = the option, plus the chip, e.g. "Ask or suggest: Question"; `detail` = the message), and "Prefer to talk first? Book 20 minutes" on a request piece (`item` "A 20 minute conversation").
  - `join`: homepage Join the movement (`item` = the option and chip; `detail` = the message).
  - `cta`: a call to action inside a piece; `item` = the `data-cta` text; `detail` = "note:<slug>", then " | " and the message if there is one.
- **source:** the `?src=` value the visitor arrived with this visit (kept in `sessionStorage`), or "site". `site` is `location.hostname`.
- **Conference key:** `CONFIG.events` has `conf` (18th Ed Leadership International Roundtable) and `edl` (Ed Leadership). `?src=edl` shows "Met at Ed Leadership? Welcome." on the homepage and tags every submission that visit with source `edl`.
- **Reply:** `{"ok":true}`, `{"ok":false,"error":"email"}` or `{"ok":false,"error":"server"}`. While sending, the button is disabled and reads "Sending"; the request times out after 15 seconds.
- **On anything but ok** (except the sign-up wall, which opens regardless): no confirmation, everything typed stays, and "That didn't go through. Please try again, or email us at <CONFIG.email>." with a prefilled `mailto:` link. `error:"email"` shows the email message instead.

**The Activity tab.** The script (`tools/forms/apps-script.gs`, live copy in the "BE Human Labs leads" Sheet under Extensions > Apps Script, deployed as a web app: Execute as Me, access Anyone) writes one row per submission to the **Activity** tab: Received, Name, Email, Organisation, Role, WhatsApp, Action, Article or topic, Detail, Keep me posted, Source, Site, Status, Emailed. Status and Emailed are for us to fill in. No email goes out per submission; one summary goes out each evening at about 21:00 IST. Run `setup()` once after deploying (it schedules the summary) and set the project time zone to India Standard Time. Old `path`/`option` payloads are still accepted (`read` maps to `signup`). Details in `tools/forms/README.md`.
- **New version, same URL.** Update the script only through Deploy > Manage deployments > edit > New version. A new deployment changes the URL and silently breaks the forms until `formEndpoint` is updated.
- **Previews post to the same Sheet.** The Site column (`behumanlabs.com` or `*.workers.dev`) tells them apart.
- **Tests never hit the real endpoint.** `tests/pressure_test.py` intercepts every `script.google.com` and `script.googleusercontent.com` request and answers it with a mock.

## From the lab

A library of pieces for school leaders, teachers and parents, at `/notes/` (`/lab/` redirects there permanently). Pieces are written in `content/notes/<slug>.html` and built into static pages; the generated pages are committed, so Cloudflare still just serves `public/`.

**Access and status.** Each piece has an `access` and a `status`:
- `access: free` + `status: published`: listed on the index under "Free to read". The full text is in the page, behind the sign-up wall.
- `access: request` + `status: published`: listed under "Shared with schools on request" with a lock. **Only the opening is built**: the opening, a fade (the first section's kicker and heading over placeholder lines) and the request panel, which lists every one of the piece's section headings. Its sources list sits after `<!-- more -->`, so it stays locked too; the stats in the opening carry their own `.cite` lines.
- `status: unlisted`: built at its URL with `noindex`, listed nowhere, and linked from nowhere (the pressure test checks that no other page links to it). Learning when answers are free is free and unlisted. The homepage engine link ("See the engine at work: The question has changed") points to a published free piece.
- `status: draft`: not built.

**Never build locked text.** For a request piece, nothing after `<!-- more -->` may be written to `public/`: not in the page, not in the fade, not in a data attribute. The text stays in the repo for Phase B. Only the `h2` section headings leave the file (they are listed in the request panel on purpose). The build checks every paragraph, and the pressure test checks every sentence of locked text against every served file. If you add a teaser, build it from the opening or the headings, never from the text after the marker.

**The sign-up wall (free pieces).** Opening, fade, then the profile form with "Read the full article". On submit it sends `signup` and reveals the text at once, even if the request fails (failures are logged to the console). Any later free piece opens directly for a known profile and sends `open` once per piece per device. **The full text is in the page source: this is a sign-up wall for reaching readers, not access control.** Never put anything confidential in a free piece.

**The request panel (request pieces).** Opening, fade, then the profile (prefilled when known), "What would you use it for?" (optional) and "Request access". Success shows "Request received." with "We read every request ourselves and will reply within three working days after the conference." and links to the free pieces. "Prefer to talk first? Book 20 minutes" opens Talk to us.

**Calls to action.** A `data-cta="<text>"` button anywhere in a piece opens a dialog, routed by the text's prefix: "Share your story..." and "Join the movement..." open **Join the movement**; everything else ("Talk to us...", "Request...") opens **Talk to us**. Both send `action` "cta", `item` = the text, `detail` = "note:<slug>" plus any message, with the profile prefilled. Start every new `data-cta` with one of those four prefixes. "Share with a colleague" copies the production URL. A `data-jump` link scrolls to its target, or to the wall or panel when the reader cannot see it yet.

**Front matter** (YAML between `---` lines, then the body as plain HTML):
- Required: `title`, `dek` (one or two sentences for the card), `type` (`research`, `deep-dive` or `pov`), `access` (`free` or `request`), `status` (`draft`, `unlisted` or `published`), `date` (e.g. "October 2026"), `author` ("Shikhar Anand, Founder"), `related` (list of slugs; shown as "Next from the lab" on free pieces).
- Optional: `lead` (the page's standfirst, if different from `dek`), `eyebrow` (e.g. "Deep dive · Edition one"), `order` (position on the index), `jump_label` and `jump_to` (a "skip to" link and the id it targets).

**Body rules.**
- Put `<!-- more -->` on its own line where the open opening ends, normally just before the first "Part one" kicker. (In A note for parents on AI it sits after the paragraph ending "if someone tells them what to look for.")
- Components are HTML blocks using the classes in `lab.css`: `.stats` (`.two` for two), `.bars`/`.brow`, `.shift` (from and to), `.matrix` (2x2), `.vtrack` (ladder), `ol.road` (timelines), `.four` (`.three`), `.paths` inside `.cta` (three paths), `.letter`, `.try`, `.rows`, `.offer`, `.nudge`, `.sources` (always last).
- Editor's notes go in `<p class="ednote">`. The build strips them and fails if one survives.
- Reading time is calculated at build time (about 220 words a minute, minimum three).
- Never redraw the logo in a piece; reuse `<use href="#bhl-mark">` (see the tiled field in School as a place to practise being human).

**Fact-check rule for new pieces.** Every figure in public text (a free piece in full, or a request piece's opening) is checked against its source before it is published:
- **Name the country** for single-country data (e.g. "US public school teachers", "in the UK"). Never present US or other single-country data as Indian or global.
- **Never round beyond the source** (if the source says 39%, write what it says).
- **Mark unverified figures**: if a figure cannot be found in a public source, replace it with only what is confirmed (e.g. "Many children..."), or leave it out, until the original report confirms it with a page reference.
- Every stat has a `.cite` line, and every piece ends with its sources.

**Build.** `python3 tools/notes/build.py` clears and rewrites `public/notes/` (and removes the old `public/lab/`). It reads `CONFIG.formEndpoint`, `CONFIG.email`, the canonical site URL and the logo `<symbol>` from `public/index.html`. It refuses em or en dashes, surviving editor's notes, a missing `<!-- more -->` and locked text in a request page. The pressure test builds into a temp folder and fails if `public/` differs.

**To add a piece:** copy the front matter from an existing piece, write the body with `<!-- more -->`, set `status: draft` while writing, fact-check the public part, then publish. Run the build, start the preview server, run the pressure test, and commit the source and the generated pages together.

**Styles.** `public/css/lab.css` part 1 is copied from the homepage (fonts, tokens, skins, base, header, footer, buttons, form fields) and must stay identical; the pressure test compares `:root` and the skins. Part 2 is the From the lab design. Change a token in both files.

## Open items

- [x] Real name, email and role in `CONFIG` (the one-pager that also carried them is retired).
- [x] Conference name in `CONFIG.events` (`conf`: 18th Ed Leadership International Roundtable).
- [x] Domain in `og:url`, `og:image` and the canonical link (behumanlabs.com).
- [x] `formEndpoint`: Google Apps Script writing to the "BE Human Labs leads" Sheet (see `tools/forms/`).
- [ ] Optional `bookingUrl`.
- [ ] Add the brand core as `docs/brand-core.md`.
- [ ] Roadmap PDF for leadership: Learning when answers are free offers "Get the roadmap as a PDF" (a Talk to us request today); make the PDF when ready.
- [ ] **Phase B** of the library:
  - [ ] `/library/` behind Cloudflare Access, for approved readers of the request pieces.
  - [ ] A follow-up email function for approved requests (the Status and Emailed columns in the Activity tab are ready for it).
  - [ ] Fact-check all locked text in the 12 request pieces (only the public openings are checked so far), including the ICRIER wording against the original publication.
  - [ ] Confirm the Tele-MANAS number (14416) in Belonging in the age of chatbots.
  - [ ] A counsellor's review of Belonging in the age of chatbots before it is shared.

## Git

- `main` deploys to production. Use a branch for anything experimental; Cloudflare builds preview URLs for branches.
- Pushes to `main` run `npx wrangler deploy`; pushes to other branches run `npx wrangler preview`, which needs the top-level `"previews": {}` block in `wrangler.jsonc`. Do not remove the block.
- Small commits with plain messages, e.g. "Swap divide stat to Melbourne/KPMG 2 in 5".
- Never commit secrets. Local secrets go in `.dev.vars` (ignored).
