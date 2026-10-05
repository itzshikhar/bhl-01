# BE Human Labs website

A single-page brand site for BE Human Labs, a human transformation lab. Static HTML, no build step, hosted on Cloudflare Workers (static assets) and deployed from GitHub. The audience is primarily Indian.

Read this file before every task. Read `docs/brand-core.md` before changing any copy.

## Commands

```bash
python3 -m http.server 8000 -d public          # preview at http://localhost:8000
python3 tests/pressure_test.py                  # run with the preview server up; must print "0 failure(s)"
python3 tools/one-pager/make.py                 # rebuild public/be-human-labs-one-pager.pdf
npx wrangler deploy                             # manual deploy (normally a push to main deploys)
```

Test setup, once: `pip install -r tests/requirements.txt && python3 -m playwright install chromium`.

**Run the pressure test after any change to HTML structure, CSS layout, or the script, and fix failures before committing.**

## Layout

```
public/                  everything that is served
  index.html             the whole site: CSS, markup, and script in one file
  404.html
  be-human-labs-mark.svg the logo, exact vector
  favicon.svg
  be-human-labs-one-pager.pdf   downloaded by "Save my card"
  og-image.png           social preview (1200x630)
  fonts/                 Gloock and Hanken Grotesk, self-hosted (OFL licences alongside)
tests/pressure_test.py   scroll-motion and content checks (Playwright)
tools/logo/              how the logo vector was made; source PNG; build/mark-paths.json
tools/one-pager/make.py  builds the one-pager PDF from HTML
docs/                    brand core (content source)
wrangler.jsonc           Cloudflare config
```

`index.html` is the source of truth. There is no template or bundler. Edit it directly.

## Content rules

- **Source of copy:** `docs/brand-core.md`. Its L0 to L2 lines are locked; do not reword them unless asked.
- **Audience is Indian.** Every figure must be Indian or genuinely global (multi-country). Never label single-country data as "global". If a figure only exists for one country, name the country or leave it out, and tell the user.
- **Never round beyond the source.** The source says 39%, so the page says "2 in 5" (the study's own phrasing). Writing 40% is not allowed.
- **Every big number has a `<cite>` line**, and every evidence item has a `<small>` source. The test checks the big numbers.
- **Figures in use, with caveats:**
  - 2 in 5 people have had any AI training; two in three use AI regularly. University of Melbourne and KPMG, 48,000 people, 47 countries, 2025.
  - 55% of Indian IT firms saw entry-level employment fall after adopting AI; 25% at mid level. ICRIER, *AI and Jobs: This Time is No Different*, 651 IT firms, 10 cities, Nov 2025 to Jan 2026. Supported by OpenAI. Researchers frame it as slower hiring, not job losses; keep the wording "saw entry-level employment fall".
  - 4% of Indian IT firms trained more than half their workforce in AI. ICRIER, same study.
  - Indian IT net hiring about 6 lakh (FY22) to about 1.4 lakh (FY26). Xpheno, cited by Nomura, Aug 2026.
  - Naukri: fresher hiring up 17% YoY, Feb 2026, led by non-IT. Keep this counterpoint next to the hiring figures.
  - Early-career 19% finding is **US data** (Stanford Digital Economy Lab). It is phrased without a country. Do not promote it to a headline number.
  - Upwork workload and training figures cover four Western countries; phrased without a country.
- **Excluded on purpose:** the MIT "95% of pilots" figure (disputed), Bhava × Ekatva (parked), LinkedIn (removed for now), the sources list and the "Where do the figures come from" FAQ (removed by request).
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
- Mobile first. Check 360px and 390px widths; the header must stay on one line.

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

## Forms and settings

`CONFIG` at the top of the script:
- `name`, `email`, `role`, `phone`, `linkedinUrl`: used for the saved contact (vCard).
- `bookingUrl`: shows "Pick a time" after a "Let's talk" or "Collaborate" submission.
- `formEndpoint`: where submissions are POSTed as JSON. Blank keeps them in the page only (logged to console).
- `onePagerUrl`: the "Save my card" download.
- `events`: `?src=<key>` shows "Met at <name>? Welcome." and tags each lead with its source.

Payload: `{ email, path, option, chip, message, keep_me_posted, source, time }`.

## Open items

- [ ] Real name, email and role in `CONFIG` and in `tools/one-pager/make.py` (`CONTACT`), then rebuild the PDF.
- [ ] Conference name in `CONFIG.events`.
- [ ] Domain in `og:url` and `og:image` (currently `yourdomain.com`).
- [ ] `formEndpoint`: a Cloudflare Worker route, Formspree, or Google Apps Script.
- [ ] Optional `bookingUrl`.
- [ ] Add the brand core as `docs/brand-core.md`.

## Git

- `main` deploys to production. Use a branch for anything experimental; Cloudflare builds preview URLs for branches.
- Small commits with plain messages, e.g. "Swap divide stat to Melbourne/KPMG 2 in 5".
- Never commit secrets. Local secrets go in `.dev.vars` (ignored).
