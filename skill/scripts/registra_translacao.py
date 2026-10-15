"""Registro PDF aprovado -> planta gerada quando a ESCALA e conhecida (planta gerada a cm/px fixo, prancha 1:N):
procura so o deslocamento (correlacao das bordas das areas do aprovado com as paredes da planta).
Mais robusto que o registro livre em pranchas com muito entorno (terreo com calcada/jardins).

Uso: python registra_translacao.py <aprovado.pdf> <celulas.json> <paredes_qc.png> <cm_px> <saida_transform.json> [--escala 100]
"""
import sys, json, argparse
import fitz, cv2, numpy as np
ap = argparse.ArgumentParser()
for k in ('pdf', 'celulas', 'imagem', 'cm_px', 'saida'): ap.add_argument(k)
ap.add_argument('--escala', type=float, default=100)
a = ap.parse_args()
C = json.load(open(a.celulas, encoding='utf-8')); clip = fitz.Rect(*C['clip_pt']); ESC = C['esc']
pg = fitz.open(a.pdf)[C['pagina'] - 1]
pix = pg.get_pixmap(matrix=fitz.Matrix(ESC, ESC), clip=clip)
pim = np.frombuffer(pix.samples, np.uint8).reshape(pix.h, pix.w, pix.n)[:, :, :3].astype(int)
r, g, b = pim[:, :, 0], pim[:, :, 1], pim[:, :, 2]
mx, mn = np.maximum(np.maximum(r, g), b), np.minimum(np.minimum(r, g), b)
area = ((mx > 150) & (mx - mn > 12) & (mn > 60)).astype(np.uint8)
s = (2.54 / 72 * a.escala / ESC) / float(a.cm_px)          # pdf px -> img px
area = cv2.resize(area, (int(pix.w * s), int(pix.h * s)), interpolation=cv2.INTER_NEAREST)
borda = cv2.morphologyEx(area, cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)).astype(np.float32)
im = cv2.imdecode(np.fromfile(a.imagem, np.uint8), cv2.IMREAD_GRAYSCALE)
par = (im < 100).astype(np.uint8)
par = cv2.dilate(par, np.ones((7, 7), np.uint8)).astype(np.float32)
red = 4
P = cv2.resize(par, (par.shape[1] // red, par.shape[0] // red), interpolation=cv2.INTER_AREA)
B = cv2.resize(borda, (borda.shape[1] // red, borda.shape[0] // red), interpolation=cv2.INTER_AREA)
pad = max(B.shape) // 2
Pp = cv2.copyMakeBorder(P, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=0)
res = cv2.matchTemplate(Pp, B, cv2.TM_CCORR)
_, mv, _, ml = cv2.minMaxLoc(res)
tx, ty = (ml[0] - pad) * red, (ml[1] - pad) * red
# refino fino +-2*red px
best = (-1, tx, ty)
for dx in range(-2 * red, 2 * red + 1, 2):
    for dy in range(-2 * red, 2 * red + 1, 2):
        x0, y0 = tx + dx, ty + dy
        ys, xs = np.nonzero(borda)
        X, Y = xs + x0, ys + y0
        ok = (X >= 0) & (Y >= 0) & (X < par.shape[1]) & (Y < par.shape[0])
        sc = par[Y[ok], X[ok]].sum() / max(1, len(xs))
        if sc > best[0]: best = (sc, x0, y0)
_, tx, ty = best
dist = cv2.distanceTransform((1 - (im < 100)).astype(np.uint8), cv2.DIST_L2, 5)
ys, xs = np.nonzero(borda); X, Y = xs + tx, ys + ty
ok = (X >= 0) & (Y >= 0) & (X < im.shape[1]) & (Y < im.shape[0])
med = float(np.median(dist[Y[ok], X[ok]])) * float(a.cm_px)
out = dict(pagina=C['pagina'], clip_pt=C['clip_pt'], esc=ESC, escala_planta=a.escala,
           A_pdfpx_para_img=[[s, 0.0, float(tx)], [0.0, s, float(ty)]], anisotropia=1.0, cm_por_px_imagem=float(a.cm_px),
           chamfer_mediana_cm=round(med, 1), frac_divisas_ate_15cm=round(float((dist[Y[ok], X[ok]] * float(a.cm_px) <= 15).mean()), 3),
           metodo='translacao (escala fixa)')
json.dump(out, open(a.saida, 'w', encoding='utf-8'), indent=1)
print(json.dumps({k: out[k] for k in ('chamfer_mediana_cm', 'frac_divisas_ate_15cm')}))
