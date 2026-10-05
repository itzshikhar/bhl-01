"""Step 2: derive the hidden centre lines used for the draw-in motion."""
import os
HERE = os.path.dirname(os.path.abspath(__file__)); B = os.path.join(HERE, "build"); os.makedirs(B, exist_ok=True)
import numpy as np, json
from skimage.morphology import skeletonize
from scipy import ndimage as nd
t = json.load(open(os.path.join(B, 'mark-paths.json'))); C, S = t['C'], t['S']

def graph(sk):
    pts = set(zip(*np.nonzero(sk)))
    nb = lambda p: [(p[0]+dy, p[1]+dx) for dy in (-1,0,1) for dx in (-1,0,1) if (dy or dx) and (p[0]+dy, p[1]+dx) in pts]
    return pts, nb

def longest_path(sk):
    pts, nb = graph(sk)
    def bfs(s):
        prev = {s: None}; q = [s]; last = s
        for p in q:
            for n in nb(p):
                if n not in prev: prev[n] = p; q.append(n); last = n
        return last, prev
    a, _ = bfs(next(iter(pts))); b, prev = bfs(a)
    path = [b]
    while prev[path[-1]] is not None: path.append(prev[path[-1]])
    return path

def loop_path(sk):
    pts, nb = graph(sk)
    # remove spurs by repeatedly pruning endpoints
    changed = True
    while changed:
        ends = [p for p in pts if len(nb(p)) <= 1]
        changed = bool(ends); pts -= set(ends)
    start = min(pts, key=lambda p: p[0])            # topmost
    path = [start]; seen = {start}
    while True:
        cand = [n for n in nb(path[-1]) if n not in seen]
        if not cand: break
        # prefer 4-neighbours to keep a clean walk
        cand.sort(key=lambda n: abs(n[0]-path[-1][0]) + abs(n[1]-path[-1][1]))
        path.append(cand[0]); seen.add(cand[0])
    return path

def smooth_d(path, step, closed=False, extend=0):
    P = np.array([[(c - C)/S, (r - C)/S] for r, c in path], float)
    # light smoothing then resample
    k = 7
    if closed:
        Pp = np.vstack([P[-k:], P, P[:k]]); Ps = np.array([Pp[i:i+2*k+1].mean(0) for i in range(len(P))])
    else:
        Ps = np.array([P[max(0,i-k):i+k+1].mean(0) for i in range(len(P))])
        Ps[0], Ps[-1] = P[0], P[-1]
    seg = np.r_[0, np.cumsum(np.linalg.norm(np.diff(Ps, axis=0), axis=1))]
    L = seg[-1]; n = max(4, int(L / step))
    R = np.array([np.interp(np.linspace(0, L, n), seg, Ps[:, j]) for j in (0, 1)]).T
    if extend and not closed:              # push both ends out so round caps reach the tips
        for i, j in ((0, 1), (-1, -2)):
            d = R[i] - R[j]; R[i] = R[i] + d / np.linalg.norm(d) * extend
    if closed: R = R[:-1]
    # Catmull-Rom to cubic
    m = len(R); get = (lambda i: R[i % m]) if closed else (lambda i: R[min(max(i, 0), m-1)])
    d = f"M{R[0][0]:.1f} {R[0][1]:.1f}"
    for i in range(m if closed else m-1):
        p0, p1, p2, p3 = get(i-1), get(i), get(i+1), get(i+2)
        c1 = p1 + (p2 - p0)/6; c2 = p2 - (p3 - p1)/6
        d += f" C{c1[0]:.1f} {c1[1]:.1f} {c2[0]:.1f} {c2[1]:.1f} {p2[0]:.1f} {p2[1]:.1f}"
    return d + (" Z" if closed else ""), L

sm = np.load(os.path.join(B, 'strand_mask.npy')); fm = np.load(os.path.join(B, 'frame_mask.npy'))
w_s = 2 * nd.distance_transform_edt(sm).max() / S
w_f = 2 * nd.distance_transform_edt(fm).max() / S
sp = longest_path(skeletonize(sm))
# orient so the strand draws from its inner end outward (inner end = closer to centre)
if np.hypot(sp[0][0]-C, sp[0][1]-C) > np.hypot(sp[-1][0]-C, sp[-1][1]-C): sp = sp[::-1]
strand_line, Ls = smooth_d(sp, 10, extend=w_s*0.6)
fp = []
for a in np.linspace(0, 2*np.pi, 2880, endpoint=False):
    rs = np.arange(200*S, 380*S, 0.5)
    rr = (C - rs*np.cos(a)).round().astype(int); cc = (C + rs*np.sin(a)).round().astype(int)
    hit = fm[rr, cc]
    idx = np.nonzero(hit)[0]
    if not len(idx): continue
    first = idx[0]; run_end = first
    while run_end + 1 < len(hit) and hit[run_end + 1]: run_end += 1
    r = rs[(first + run_end)//2]
    fp.append((C - r*np.cos(a), C + r*np.sin(a)))
frame_line, Lf = smooth_d(fp, 14, closed=True)
print('band widths', round(w_s,1), round(w_f,1), 'lengths', int(Ls), int(Lf), 'frame pts', len(fp))
t.update(strand_line=strand_line, frame_line=frame_line, w_s=w_s, w_f=w_f)
json.dump(t, open(os.path.join(B, 'mark-paths.json'), 'w'))
