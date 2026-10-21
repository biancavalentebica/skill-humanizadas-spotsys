"""Sobrepoe as divisas do PDF aprovado (preto, sem texto e sem hachura) na humanizada publicada e mede a aderencia.

Ajuste: escala x/y + deslocamento que minimiza a distancia (chamfer) das linhas do aprovado ate as paredes escuras
da humanizada. Saida: overlay (aprovado em vermelho) + json com escala, anisotropia e distancias em cm.

Uso: py sobrepoe_aprovado.py <aprovado.pdf> <pagina> <x0,y0,x1,y1 pt> <humanizada.png> <saida_prefixo> [--escala 100]
"""
import argparse, json
import fitz, cv2, numpy as np
from scipy.optimize import minimize

ap = argparse.ArgumentParser()
ap.add_argument('pdf'); ap.add_argument('pagina', type=int); ap.add_argument('clip')
ap.add_argument('imagem'); ap.add_argument('prefixo')
ap.add_argument('--escala', type=float, default=100)
ap.add_argument('--zoom', type=float, default=2.0, help='px por pt na rasterizacao do PDF')
ap.add_argument('--limiar', type=int, default=70, help='cinza maximo da parede na humanizada')
ap.add_argument('--cm-px-img', type=float, default=0, help='cm por px da humanizada original, se conhecido (fixa a escala)')
a = ap.parse_args()

doc = fitz.open(a.pdf); pg = doc[a.pagina - 1]
for b in pg.get_text('dict')['blocks']:
    for l in b.get('lines', []):
        for s in l['spans']:
            pg.add_redact_annot(fitz.Rect(s['bbox']))
pg.apply_redactions(images=0, graphics=0)
clip = fitz.Rect(*[float(v) for v in a.clip.split(',')])
pix = pg.get_pixmap(matrix=fitz.Matrix(a.zoom, a.zoom), clip=clip, colorspace=fitz.csGRAY)
P = np.frombuffer(pix.samples, np.uint8).reshape(pix.h, pix.w)
linhas = P < 60
ys, xs = np.nonzero(linhas)
pts = np.c_[xs, ys].astype(float)
if len(pts) > 40000:
    pts = pts[np.random.default_rng(0).choice(len(pts), 40000, replace=False)]

im = cv2.imread(a.imagem, cv2.IMREAD_UNCHANGED)
g = cv2.cvtColor(im[:, :, :3], cv2.COLOR_BGR2GRAY)
fat = 2400 / max(g.shape)  # trabalha em ~2400 px
gs = cv2.resize(g, None, fx=fat, fy=fat, interpolation=cv2.INTER_AREA)
parede = (gs < a.limiar).astype(np.uint8)
parede = cv2.morphologyEx(parede, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
dt = cv2.distanceTransform(1 - parede, cv2.DIST_L2, 5)
H, W = dt.shape

def custo(p):
    sx, sy, tx, ty = p
    u = pts[:, 0] * sx + tx; v = pts[:, 1] * sy + ty
    ok = (u >= 0) & (u < W - 1) & (v >= 0) & (v < H - 1)
    dd = np.full(len(u), 40.0)
    dd[ok] = dt[v[ok].astype(int), u[ok].astype(int)]
    return np.mean(np.minimum(dd, 40.0))

# inicio: caixa das paredes x caixa das linhas
wy, wx = np.nonzero(parede)
bx = (np.percentile(wx, 1), np.percentile(wx, 99)); by = (np.percentile(wy, 1), np.percentile(wy, 99))
lx = (np.percentile(pts[:, 0], 1), np.percentile(pts[:, 0], 99)); ly = (np.percentile(pts[:, 1], 1), np.percentile(pts[:, 1], 99))
s0 = ((bx[1] - bx[0]) / (lx[1] - lx[0]) + (by[1] - by[0]) / (ly[1] - ly[0])) / 2
FAIXA = np.linspace(0.85, 1.15, 13)
if a.cm_px_img:  # escala conhecida (cm por px da imagem ORIGINAL): so procura o deslocamento
    s0 = (2.54 / 72 * a.escala / a.zoom) / (a.cm_px_img / fat); FAIXA = np.linspace(0.98, 1.02, 3)
    bx, by = (0, W), (0, H)
    lx = (pts[:, 0].min(), pts[:, 0].max()); ly = (pts[:, 1].min(), pts[:, 1].max())
melhor = None
for ds in FAIXA:
    s = s0 * ds
    tx0 = (bx[0] + bx[1]) / 2 - s * (lx[0] + lx[1]) / 2; ty0 = (by[0] + by[1]) / 2 - s * (ly[0] + ly[1]) / 2
    passo = np.linspace(-W / 3, W / 3, 41) if a.cm_px_img else np.linspace(-60, 60, 7)
    passo_y = np.linspace(-H / 3, H / 3, 21) if a.cm_px_img else np.linspace(-60, 60, 7)
    for dx in passo:
        for dy in passo_y:
            c = custo((s, s, tx0 + dx, ty0 + dy))
            if melhor is None or c < melhor[0]: melhor = (c, (s, s, tx0 + dx, ty0 + dy))
r = minimize(lambda q: custo((q[0], q[0], q[1], q[2])), [melhor[1][0], melhor[1][2], melhor[1][3]], method='Nelder-Mead',
             options=dict(xatol=1e-4, fatol=1e-4, maxiter=3000))
s, tx, ty = r.x
r2 = minimize(custo, [s, s, tx, ty], method='Nelder-Mead', options=dict(xatol=1e-4, fatol=1e-4, maxiter=4000))
sx, sy, tx, ty = r2.x

cm_por_px_pdf = 2.54 / 72 * a.escala / a.zoom
cm_por_px_img = cm_por_px_pdf / ((sx + sy) / 2)
u = pts[:, 0] * sx + tx; v = pts[:, 1] * sy + ty
ok = (u >= 0) & (u < W - 1) & (v >= 0) & (v < H - 1)
dist_cm = dt[v[ok].astype(int), u[ok].astype(int)] * cm_por_px_img
res = dict(imagem=a.imagem, pagina=a.pagina, clip_pt=list(clip), anisotropia=round(sx / sy, 4),
           cm_por_px_img_reduzida=round(cm_por_px_img, 3), fator_reducao=fat,
           chamfer_mediana_cm=round(float(np.median(dist_cm)), 1), chamfer_p90_cm=round(float(np.percentile(dist_cm, 90)), 1),
           frac_divisas_ate_15cm=round(float(np.mean(dist_cm <= 15)), 3), A=[[sx, 0, tx], [0, sy, ty]],
           parametros=dict(pdf=a.pdf, escala=a.escala, zoom=a.zoom, limiar=a.limiar, cm_px_img=a.cm_px_img))  # reproduzir o QC
json.dump(res, open(a.prefixo + '_registro.json', 'w'), indent=1)

ov = cv2.cvtColor(gs, cv2.COLOR_GRAY2BGR)
ov = (ov * 0.55 + 255 * 0.45).astype(np.uint8)
M = np.float32([[sx, 0, tx], [0, sy, ty]])
L = cv2.warpAffine(linhas.astype(np.uint8) * 255, M, (W, H), flags=cv2.INTER_NEAREST)
L = cv2.dilate(L, np.ones((2, 2), np.uint8))
ov[L > 0] = (0, 0, 230)
# divisas longe das paredes (> 15 cm) em azul
far = np.zeros((H, W), np.uint8)
uu, vv = u[ok].astype(int), v[ok].astype(int)
sel = dist_cm > 15
far[vv[sel], uu[sel]] = 255
far = cv2.dilate(far, np.ones((5, 5), np.uint8))
ov[far > 0] = (230, 120, 0)
cv2.imwrite(a.prefixo + '_overlay.jpg', ov, [cv2.IMWRITE_JPEG_QUALITY, 88])
print(json.dumps({k: v for k, v in res.items() if k != 'A'}))
