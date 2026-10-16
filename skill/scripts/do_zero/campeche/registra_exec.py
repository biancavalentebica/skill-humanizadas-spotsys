"""Registro executivo R01 (TER-012, 1:50) -> legal R00 (prancha 03, 1:100) por similaridade + ajuste fino (chamfer)."""
import fitz, re, json, sys, os
import numpy as np, cv2
from scipy.optimize import minimize
sys.path.insert(0, os.path.dirname(__file__))
from base import raster, px, Z, W, H, CLIP
EX = '00_entradas/originais/executivo/CAMPECHESPOT-PE-ARQ-DCT-TER-XXX-012-R01.pdf'
LP = '00_entradas/originais/projeto_aprovado/CAMPECHESPOT-PL-ARQ-DCT-TOT-XXX-000-R00.pdf'
def studios(f, pg, xmax=2700):
    p = fitz.open(f)[pg]; out = {}
    for b in p.get_text('dict')['blocks']:
        for l in b.get('lines', []):
            s = ' '.join(x['text'] for x in l['spans']).strip().upper(); x0, y0, x1, y1 = l['bbox']
            m = re.match(r'STUDIO\s*(\d{3})', s)
            if m and x0 < xmax: out.setdefault(m.group(1), ((x0 + x1) / 2, (y0 + y1) / 2))
    return out
L = studios(LP, 2); E = studios(EX, 0)
ks = sorted(set(L) & set(E))
src = np.array([E[k] for k in ks], np.float32); dst = np.array([L[k] for k in ks], np.float32)
A0, _ = cv2.estimateAffinePartial2D(src, dst)
s = np.hypot(A0[0, 0], A0[1, 0]); th = np.arctan2(A0[1, 0], A0[0, 0])
print('inicial: escala', s, 'rot', np.degrees(th))
# ajuste fino: linhas pretas do executivo (pt) sobre a distancia as linhas do legal (px a 1 cm/px)
B = raster(); dt = cv2.distanceTransform((~B).astype(np.uint8), cv2.DIST_L2, 5)
pe = fitz.open(EX)[0]; P = []
for d in pe.get_drawings():
    c = d.get('color')
    if d['type'] != 's' or not c or max(c) > 0.05: continue
    for it in d['items']:
        if it[0] == 'l':
            a, b = it[1], it[2]; n = max(2, int(np.hypot(b.x - a.x, b.y - a.y) / 3))
            for t in np.linspace(0, 1, n): P.append((a.x + t * (b.x - a.x), a.y + t * (b.y - a.y)))
P = np.array(P); P = P[(P[:, 0] < 2700)]
P = P[np.random.default_rng(0).choice(len(P), min(60000, len(P)), replace=False)]
def tr(q, p):
    s, th, tx, ty = q; c, sn = np.cos(th), np.sin(th)
    x = s * (c * p[:, 0] - sn * p[:, 1]) + tx; y = s * (sn * p[:, 0] + c * p[:, 1]) + ty
    return (x - CLIP.x0) * Z, (y - CLIP.y0) * Z
def custo(q):
    u, v = tr(q, P); ok = (u >= 0) & (u < W - 1) & (v >= 0) & (v < H - 1)
    d = np.full(len(u), 30.0); d[ok] = dt[v[ok].astype(int), u[ok].astype(int)]
    return np.mean(np.minimum(d, 30))
q0 = [s, th, A0[0, 2], A0[1, 2]]
r = minimize(custo, q0, method='Nelder-Mead', options=dict(xatol=1e-5, fatol=1e-4, maxiter=4000))
print('custo', custo(q0), '->', r.fun, 'q', r.x, 'escala', r.x[0], 'rot', np.degrees(r.x[1]))
json.dump(dict(q=list(r.x)), open('03_trabalho/do_zero/exec2legal.json', 'w'))
