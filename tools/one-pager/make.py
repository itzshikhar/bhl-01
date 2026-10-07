"""RETIRED: the one-pager is no longer served; "Save my card" downloads the card image (tools/card/).
Kept for reference. It now writes tools/one-pager/be-human-labs-one-pager.pdf, never public/.
Was: builds the one-pager PDF (A4, one page). Edit CONTACT and the copy below, then run: python3 tools/one-pager/make.py"""
import json, base64, os
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..', '..')
from playwright.sync_api import sync_playwright
T = json.load(open(os.path.join(ROOT, 'tools', 'logo', 'build', 'mark-paths.json')))
mark = lambda color: (f'<svg viewBox="-372 -372 744 744" aria-hidden="true"><g fill="{color}"><path fill-rule="evenodd" d="{T["frame"]}"/>'
        + ''.join(f'<path d="{T["strand"]}" transform="rotate({45*k})"/>' for k in range(8)) + '</g></svg>')
f64 = lambda p: base64.b64encode(open(p,'rb').read()).decode()
CONTACT = {"name": "Shikhar Anand", "role": "Founder, BE Human Labs", "email": "behumanlabs@zohomail.in", "web": "behumanlabs.com"}
html = f'''<!DOCTYPE html><html><head><meta charset="utf-8"><title>BE Human Labs one-pager</title><style>
@font-face{{font-family:Gloock;src:url(data:font/ttf;base64,{f64(os.path.join(ROOT, 'tools', 'fonts', 'Gloock-Regular.ttf'))})}}
@font-face{{font-family:Hanken;font-weight:100 900;src:url(data:font/ttf;base64,{f64(os.path.join(ROOT, 'tools', 'fonts', 'HankenGrotesk.ttf'))})}}
@page{{size:A4;margin:0}}
*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{width:210mm;height:297mm;overflow:hidden}}
body{{background:#E7DDD2;color:#000100;font-family:Hanken,sans-serif;font-size:8.6pt;line-height:1.45;display:flex;flex-direction:column}}
h1,h2,h3,.num{{font-family:Gloock,serif;font-weight:400;letter-spacing:-.01em;line-height:1.05}}
.pad{{padding:0 16mm}}
.soft{{color:#563C2D}}
.rule{{border-top:.6pt solid rgba(54,30,30,.35)}}
header{{display:flex;justify-content:space-between;align-items:center;padding-top:10mm}}
.brand{{display:flex;align-items:center;gap:3mm;font-family:Gloock,serif;font-size:11pt;letter-spacing:.06em}}
.brand svg{{width:9mm;height:9mm}}
.tag{{font-size:7.6pt;color:#563C2D}}
.hero{{display:grid;grid-template-columns:1fr 40mm;gap:10mm;align-items:center;padding-top:6mm;padding-bottom:6mm}}
h1{{font-size:24pt;max-width:16ch}}
.lede{{font-size:9.6pt;color:#563C2D;margin-top:4mm;max-width:105mm}}
.hero svg{{width:40mm;height:40mm}}
section{{padding-top:7mm;padding-bottom:2.5mm}}
h2{{font-size:14pt;margin-bottom:3mm}}
.label{{font-weight:600;font-size:7.4pt;color:#563C2D;margin-bottom:2mm;letter-spacing:.02em}}
.why{{background:#C5B7AA;padding-top:6mm;padding-bottom:6mm}}
.why .grid{{display:grid;grid-template-columns:1.05fr 1fr 1fr;gap:8mm;align-items:start}}
.num{{font-size:30pt;line-height:.95}}
.why p{{margin-top:2mm}}
.why cite{{display:block;font-style:normal;font-size:6.8pt;color:#361E1E;margin-top:1.5mm}}
.cols{{display:grid;gap:6mm}}
.c3{{grid-template-columns:repeat(3,1fr)}} .c4{{grid-template-columns:repeat(4,1fr)}}
.cols h3{{font-size:11.5pt;margin-bottom:1mm}}
.cols .n{{font-family:Gloock,serif;font-size:8pt;color:#563C2D}}
.q{{font-size:8.2pt;margin-bottom:1mm}}
.dark{{background:#361E1E;color:#E7DDD2;padding-top:6mm;padding-bottom:6mm;margin-top:auto}}
.dark .soft,.dark .label{{color:#C5B7AA}}
.dark .rule{{border-color:rgba(197,183,170,.3)}}
.spheres{{display:grid;grid-template-columns:repeat(3,1fr);gap:6mm}}
.spheres b{{font-family:Gloock,serif;font-weight:400;font-size:11.5pt;display:block}}
footer{{background:#563C2D;color:#efe6db;padding:6mm 16mm 7mm;display:grid;grid-template-columns:1fr auto;gap:8mm;align-items:end}}
footer h2{{font-size:16pt;margin-bottom:1.5mm}}
footer .soft{{color:#d5c7b8}}
footer .contact{{text-align:right;line-height:1.6}}
footer .contact b{{font-family:Gloock,serif;font-weight:400;font-size:11pt}}
</style></head><body>
<header class="pad"><div class="brand">{mark('#361E1E')}BE HUMAN LABS</div><div class="tag">A human transformation lab</div></header>
<div class="hero pad"><div><h1>A lab that develops humans into Forward Thinkers and Active Shapers.</h1>
<p class="lede">BE Human Labs uses research, innovation and transformation to build people's awareness, capability, connection and contribution, so more of them shape what comes next instead of absorbing it.</p></div>{mark('#361E1E')}</div>
<section class="why pad"><div class="grid">
<div><div class="label">Why we exist</div><h2>A few people are shaping the future. Everyone else is absorbing it.</h2><p class="soft">The gap isn't about talent. It's about who has been prepared to see what is coming and act on it.</p></div>
<div><span class="num">2 in 5</span><p>people have had any AI training, though two in three already use AI regularly.</p><cite>University of Melbourne and KPMG, 48,000 people in 47 countries, 2025</cite></div>
<div><span class="num">55%</span><p>of Indian IT firms saw entry-level employment fall after adopting AI. At mid level, only 25% did.</p><cite>ICRIER, AI and Jobs: This Time is No Different. 651 IT firms in 10 Indian cities, surveyed Nov 2025 to Jan 2026. Supported by OpenAI.</cite></div>
</div></section>
<section class="pad"><div class="label">How the lab works</div><h2>Research, innovation and transformation, run as one engine.</h2>
<div class="cols c3 rule" style="padding-top:3mm">
<div><span class="n">01</span><h3>Research</h3><p class="soft">Learns what is changing, in humans, society, technology and the future.</p></div>
<div><span class="n">02</span><h3>Innovation</h3><p class="soft">Builds a response: new ideas, models and tools grounded in what research found.</p></div>
<div><span class="n">03</span><h3>Transformation</h3><p class="soft">Changes how people live, for individuals and for groups.</p></div></div></section>
<section class="pad"><div class="label">What it transforms</div><h2>Four dimensions, developed together.</h2>
<div class="cols c4 rule" style="padding-top:3mm">
<div><h3>Awareness</h3><p class="q">Who am I, and how am I connected to the world around me?</p></div>
<div><h3>Capability</h3><p class="q">What can I do, and how can I do it better?</p></div>
<div><h3>Connection</h3><p class="q">Who can I do this with?</p></div>
<div><h3>Contribution</h3><p class="q">What will I actually change, and will I see it through?</p></div></div></section>
<section class="dark pad"><div class="cols" style="grid-template-columns:1fr 1.25fr;gap:10mm">
<div><div class="label">Where it matters</div><h2>Every Active Shaper widens the circle.</h2>
<div class="spheres rule" style="padding-top:3mm"><div><b>Human</b><span class="soft">The individual</span></div><div><b>Society</b><span class="soft">How people live and work together</span></div><div><b>Humanity</b><span class="soft">The larger human journey</span></div></div></div>
<div><div class="label">Through what</div><h2>Four offerings, each doing something the others can't.</h2>
<div class="cols c4 rule" style="padding-top:3mm;gap:4mm">
<div><h3>People</h3><p class="soft">guide change</p></div><div><h3>Products</h3><p class="soft">scale it</p></div><div><h3>Programs</h3><p class="soft">structure it</p></div><div><h3>Systems</h3><p class="soft">sustain it</p></div></div></div>
</div></section>
<footer><div><h2>Let's shape what comes next.</h2><p class="soft">For a conversation, a pilot, or to bring this to your team.</p></div>
<div class="contact"><b>{CONTACT["name"]}</b><br>{CONTACT["role"]}<br>{CONTACT["email"]}<br>{CONTACT["web"]}</div></footer>
</body></html>'''
open(os.path.join(HERE, 'one-pager.html'), 'w').write(html)
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(); pg.set_content(html); pg.wait_for_timeout(500)
    pg.pdf(path=os.path.join(HERE, 'be-human-labs-one-pager.pdf'), format='A4', print_background=True, margin={'top':'0','bottom':'0','left':'0','right':'0'}, prefer_css_page_size=True)
    b.close()
