"""Step 1: symmetrise the logo PNG over 8 rotations and trace exact outlines."""
import os
HERE = os.path.dirname(os.path.abspath(__file__)); B = os.path.join(HERE, "build"); os.makedirs(B, exist_ok=True)
import numpy as np, json
from PIL import Image
from scipy import ndimage
import potrace

S = 2                                     # work at 2x
src = Image.open(os.path.join(HERE, 'source', 'logo.png')).convert('L')
big = src.resize((1024*S, 1024*S), Image.BICUBIC)
C = 511.5*S + (S-1)/2                     # centre in big pixel coords
dark = lambda im: (255 - np.asarray(im, dtype=np.float32)) / 255
acc = np.zeros((1024*S, 1024*S), np.float32)
for k in range(8):
    acc += dark(big.rotate(45*k, center=(C, C), resample=Image.BICUBIC, fillcolor=255))
sym = (acc / 8) > 0.5
np.save(os.path.join(B, 'sym.npy'), sym)

lab, n = ndimage.label(sym)
sizes = ndimage.sum(sym, lab, range(1, n+1))
order = np.argsort(sizes)[::-1] + 1
frame_id = order[0]
strands = [i for i in order[1:9]]
cents = {i: ndimage.center_of_mass(lab == i) for i in strands}
print('pieces', n, [int(sizes[i-1]) for i in order[:10]])
# pick the strand whose centroid is closest to straight up
top = min(strands, key=lambda i: abs(np.degrees(np.arctan2(cents[i][1]-C, -(cents[i][0]-C)))))
print('top strand centroid', [c/S - 511.5 for c in cents[top]])

def trace(mask):
    bm = potrace.Bitmap(~mask)
    plist = bm.trace(turdsize=10, turnpolicy=potrace.POTRACE_TURNPOLICY_MINORITY, alphamax=1.0, opticurve=True, opttolerance=0.2)
    f = lambda p: f"{(p[0]-C)/S:.2f} {(p[1]-C)/S:.2f}"
    out = []
    for curve in plist:
        d = 'M' + f((curve.start_point.x, curve.start_point.y))
        for seg in curve.segments:
            if seg.is_corner:
                d += ' L' + f((seg.c.x, seg.c.y)) + ' L' + f((seg.end_point.x, seg.end_point.y))
            else:
                d += ' C' + f((seg.c1.x, seg.c1.y)) + ' ' + f((seg.c2.x, seg.c2.y)) + ' ' + f((seg.end_point.x, seg.end_point.y))
        out.append(d + 'Z')
    return ' '.join(out)

frame_d = trace(lab == frame_id)
strand_d = trace(lab == top)
np.save(os.path.join(B, 'frame_mask.npy'), lab == frame_id); np.save(os.path.join(B, 'strand_mask.npy'), lab == top)
json.dump({'frame': frame_d, 'strand': strand_d, 'C': C, 'S': S}, open(os.path.join(B, 'mark-paths.json'), 'w'))
print(len(frame_d), len(strand_d), frame_d.count('M'), strand_d.count('M'))
