"""Step 3: write build/mark.js (the MARK module embedded in index.html) and public/be-human-labs-mark.svg."""
import os
HERE = os.path.dirname(os.path.abspath(__file__)); B = os.path.join(HERE, "build"); os.makedirs(B, exist_ok=True)
import json
t = json.load(open(os.path.join(B, 'mark-paths.json')))
sw_s = round(t['w_s']*1.15, 1); sw_f = round(t['w_f']*1.15, 1)
js = f'''/* BE Human Labs mark: traced from the logo PNG, symmetrised over 8 rotations.
   Shapes are exact outlines; each strand and the frame also carry a hidden centre line
   that draws in, clipped by the exact outline, so the finished mark matches the logo. */
const MARK = (() => {{
  const strand = "{t['strand']}";
  const frame = "{t['frame']}";
  const strandLine = "{t['strand_line']}";
  const frameLine = "{t['frame_line']}";
  let uid = 0;
  function svg(opts = {{}}) {{
    const id = "mk" + (++uid);
    const st = [0,1,2,3,4,5,6,7].map(k =>
      `<g class="st st-${{k}}" transform="rotate(${{k * 45}})"><path class="fl" d="${{strand}}"/><path class="ln" d="${{strandLine}}" stroke-width="{sw_s}" pathLength="1" clip-path="url(#${{id}}s)"/></g>`).join("");
    return `<svg class="mark ${{opts.cls || ""}}" viewBox="-372 -372 744 744" role="img" aria-label="BE Human Labs mark">` +
      `<defs><clipPath id="${{id}}s"><path d="${{strand}}"/></clipPath><clipPath id="${{id}}f"><path d="${{frame}}" clip-rule="evenodd"/></clipPath></defs>` +
      `<g class="frame"><path class="fl" d="${{frame}}" fill-rule="evenodd"/><path class="ln fr" d="${{frameLine}}" stroke-width="{sw_f}" pathLength="1" clip-path="url(#${{id}}f)"/></g>` +
      `<g class="knot">${{st}}</g></svg>`;
  }}
  return {{ svg, strand, frame, strandLine, frameLine }};
}})();'''
open(os.path.join(B, 'mark.js'), 'w').write(js)
# standalone logo SVG (exact outlines) for the brand kit
g = ''.join(f'<path d="{t["strand"]}" transform="rotate({45*k})"/>' for k in range(8))
open(os.path.join(HERE, '..', '..', 'public', 'be-human-labs-mark.svg'), 'w').write(
  f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="-372 -372 744 744"><title>BE Human Labs</title><g fill="#361E1E"><path d="{t["frame"]}" fill-rule="evenodd"/>{g}</g></svg>')
print(sw_s, sw_f)
