"""FASE 1 (regra: base de layout = humanizada do LANCAMENTO): gera a planta do pavimento na geometria do APROVADO.

- Quadro de saida = sistema de coordenadas da prancha aprovada (escala fixa, cm/px): a proporcao e a do aprovado.
- Layout/interiores = humanizada do lancamento (sem texto):
    1. alinhamento global lancamento -> aprovado (envelope do predio + ajuste fino pelas divisas);
    2. por unidade, encaixe RIGIDO (so deslocamento, sem escala nem deformacao) do interior do lancamento dentro
       do contorno do aprovado, escolhendo o deslocamento que melhor casa as paredes do lancamento com as divisas;
    3. areas comuns: lancamento com o alinhamento global.
- Paredes: divisas do aprovado desenhadas onde o lancamento nao tem parede (trechos > vao maximo; portas ficam).
- Encaixe ruim (divisas do aprovado longe das paredes do lancamento) -> unidade SINALIZADA para desenho:
  recebe piso neutro + paredes do aprovado, sem mobiliario (nada e inventado).

Uso: python gera_humanizada_lancamento_r06.py <aprovado.pdf> <celulas.json> <lancamento_sem_texto.png> <saida.png>
        [--escala 100] [--cm-px 0.9] [--limite-cm 25] [--forcar-sinalizar 505,506]
"""
import json, argparse
import fitz, cv2, numpy as np
from scipy.optimize import minimize

ap = argparse.ArgumentParser()
for k in ('pdf', 'celulas', 'lancamento', 'saida'): ap.add_argument(k)
ap.add_argument('--escala', type=float, default=100)
ap.add_argument('--cm-px', type=float, default=0.9)
ap.add_argument('--limite-cm', type=float, default=25, help='distancia mediana maxima divisa x parede do lancamento para aceitar o encaixe')
ap.add_argument('--cobertura-min', type=float, default=0.7, help='fracao minima da divisa aprovada com parede do lancamento a ate 15 cm')
ap.add_argument('--busca-cm', type=float, default=120, help='deslocamento maximo procurado por unidade')
ap.add_argument('--parede-cm', type=float, default=14)
ap.add_argument('--vao-max-cm', type=float, default=120)
ap.add_argument('--forcar-sinalizar', default='')
ap.add_argument('--restringir-comodos', action='store_true', help='experimental: copia so os comodos do lancamento que caem no contorno (falha em banheiros pequenos)')
a = ap.parse_args()

C = json.load(open(a.celulas, encoding='utf-8'))
clip = fitz.Rect(*C['clip_pt'])
cmpx = a.cm_px; ESC = (2.54 / 72 * a.escala) / cmpx
W, H = int(clip.width * ESC), int(clip.height * ESC)
px = lambda cm: max(1, int(round(cm / cmpx)))

# --- aprovado: areas, predio, unidades -------------------------------------------------------------
pg = fitz.open(a.pdf)[C['pagina'] - 1]
pix = pg.get_pixmap(matrix=fitz.Matrix(ESC, ESC), clip=clip)
pim = np.frombuffer(pix.samples, np.uint8).reshape(pix.h, pix.w, pix.n)[:, :, :3][:, :, ::-1]
pim = cv2.resize(pim, (W, H), interpolation=cv2.INTER_NEAREST).astype(int)
b, g, r = pim[:, :, 0], pim[:, :, 1], pim[:, :, 2]
mx, mn = np.maximum(np.maximum(b, g), r), np.minimum(np.minimum(b, g), r)
area = ((mx > 150) & (mx - mn > 12) & (mn > 60)) | ((abs(b - 240) <= 4) & (abs(g - 240) <= 4) & (abs(r - 240) <= 4))
area = cv2.morphologyEx(area.astype(np.uint8), cv2.MORPH_OPEN, np.ones((px(30),) * 2, np.uint8))
area = cv2.morphologyEx(area, cv2.MORPH_CLOSE, np.ones((px(20),) * 2, np.uint8))
nf, lf, sf, _ = cv2.connectedComponentsWithStats(area, 8)
predio = (lf == 1 + int(np.argmax(sf[1:, 4]))).astype(np.uint8)
cs_p, _ = cv2.findContours(predio, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
predio = np.zeros_like(predio); cv2.drawContours(predio, cs_p, -1, 1, -1)
creme = (abs(g - 232) < 15) & (abs(r - 254) < 15) & (abs(b - 200) < 20)

unid = {}
for code, cel in C['celulas'].items():
    m = np.zeros((H, W), np.uint8)
    for poly in cel.get('poligonos_pt', []):
        cv2.fillPoly(m, [np.array([[(x - clip.x0) * ESC, (y - clip.y0) * ESC] for x, y in poly], np.int32)], 255)
    if m.any(): unid[code] = m
todas = np.zeros((H, W), np.uint8)
for m in unid.values(): todas |= m
comum = ((predio > 0) & (todas == 0)).astype(np.uint8)

# divisas internas (unidade x unidade e unidade x area comum)
t = px(a.parede_cm)
divisas = np.zeros((H, W), np.uint8)
borda_u = {}
for code, m in unid.items():
    cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    bd = np.zeros((H, W), np.uint8); cv2.drawContours(bd, cs, -1, 255, t)
    outros = ((todas > 0) & (m == 0)) | (comum > 0)
    viz = cv2.dilate(outros.astype(np.uint8), np.ones((t * 2 + 1,) * 2, np.uint8)) > 0
    bd[~viz] = 0
    borda_u[code] = bd
    divisas |= bd

# --- lancamento: paredes ---------------------------------------------------------------------------
L = cv2.imread(a.lancamento, cv2.IMREAD_UNCHANGED)
if L.shape[2] == 3: L = np.dstack([L, np.full(L.shape[:2], 255, np.uint8)])
gl = cv2.cvtColor(L[:, :, :3], cv2.COLOR_BGR2GRAY)
inkL = ((gl < 70) & (L[:, :, 3] > 0)).astype(np.uint8)
n2, lab2, st2, _ = cv2.connectedComponentsWithStats(inkL, 8)
k2 = np.zeros(n2, bool); k2[1:] = np.maximum(st2[1:, 2], st2[1:, 3]) > L.shape[1] * 0.02
parL = (k2[lab2] * 255).astype(np.uint8)
# comodos do lancamento: espaco livre fechado pelas paredes (vaos de porta ate ~1 m fechados so ao longo das paredes)
kk = max(3, int(100 / (cmpx) ))  # provisorio; recalculado apos a escala global
ys, xs = np.where(parL > 0); ext_L = np.array([xs.min(), ys.min(), xs.max(), ys.max()], float)
ys, xs = np.where(predio > 0); ext_P = np.array([xs.min(), ys.min(), xs.max(), ys.max()], float)

# alinhamento global: saida -> lancamento (x_L = s*x + tx), escala unica, ajuste pelas divisas
pys, pxs = np.where(divisas > 0)
sel = np.random.default_rng(0).choice(len(pxs), min(15000, len(pxs)), replace=False)
Pts = np.stack([pxs[sel], pys[sel]], 1).astype(np.float64)
distL = cv2.distanceTransform(255 - parL, cv2.DIST_L2, 5)

def custo(q, teto):
    s_, tx_, ty_ = q
    X = Pts[:, 0] * s_ + tx_; Y = Pts[:, 1] * s_ + ty_
    ok = (X >= 0) & (Y >= 0) & (X < L.shape[1] - 1) & (Y < L.shape[0] - 1)
    if ok.mean() < 0.7: return 1e9
    return float(np.minimum(distL[Y[ok].astype(int), X[ok].astype(int)], teto).mean())

s0 = np.sqrt((ext_L[2] - ext_L[0]) / (ext_P[2] - ext_P[0]) * (ext_L[3] - ext_L[1]) / (ext_P[3] - ext_P[1]))
melhor = (1e18, None)
for ds in np.linspace(-0.15, 0.15, 31):
    s_ = s0 * (1 + ds)
    for dx in np.linspace(-0.06, 0.06, 13) * L.shape[1]:
        for dy in np.linspace(-0.06, 0.06, 13) * L.shape[0]:
            q = np.array([s_, ext_L[0] - s_ * ext_P[0] + dx, ext_L[1] - s_ * ext_P[1] + dy])
            c = custo(q, 0.03 * L.shape[1])
            if c < melhor[0]: melhor = (c, q)
q = minimize(custo, melhor[1], args=(0.03 * L.shape[1],), method='Nelder-Mead').x
q = minimize(custo, q, args=(0.01 * L.shape[1],), method='Nelder-Mead').x
s_g, tx_g, ty_g = q
cm_por_px_L = cmpx / s_g   # escala real do lancamento (so informativa)

def warp(dx=0.0, dy=0.0):
    M = np.array([[s_g, 0, tx_g + dx], [0, s_g, ty_g + dy]], np.float32)   # saida -> lancamento (pixels do lancamento)
    return cv2.warpAffine(L, M, (W, H), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255, 0))

base_g = warp()
cmL = cmpx / s_g                                   # cm por pixel do lancamento
kd = max(3, int(round(100 / cmL)))
fech = cv2.morphologyEx(parL, cv2.MORPH_CLOSE, np.ones((1, kd), np.uint8))
fech = cv2.morphologyEx(fech, cv2.MORPH_CLOSE, np.ones((kd, 1), np.uint8))
livre = ((fech == 0) & (L[:, :, 3] > 0)).astype(np.uint8)
nR, labR = cv2.connectedComponents(livre, connectivity=4)
areaR = np.bincount(labR.ravel(), minlength=nR)
def warp_lab(dx, dy):
    M = np.array([[s_g, 0, tx_g + dx], [0, s_g, ty_g + dy]], np.float32)
    return cv2.warpAffine(labR.astype(np.float32), M, (W, H), flags=cv2.INTER_NEAREST | cv2.WARP_INVERSE_MAP, borderValue=0).astype(np.int32)
def warp_par(dx, dy):
    M = np.array([[s_g, 0, tx_g + dx], [0, s_g, ty_g + dy]], np.float32)
    return cv2.warpAffine(parL, M, (W, H), flags=cv2.INTER_NEAREST | cv2.WARP_INVERSE_MAP, borderValue=0) > 0
out = base_g.copy()
distO = None

# --- encaixe rigido por unidade ----------------------------------------------------------------------
forcar = {c.strip() for c in a.forcar_sinalizar.split(',') if c.strip()}
passo = px(5) * s_g; busca = px(a.busca_cm) * s_g
cinza_piso = np.array([226, 229, 232, 255], np.uint8)
relatorio = {}
for code, m in unid.items():
    ys, xs = np.where(borda_u[code] > 0)
    if len(xs) < 20:
        ys, xs = np.where(cv2.morphologyEx(m, cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)) > 0)
    Bx = xs * s_g + tx_g; By = ys * s_g + ty_g
    best = (1e18, 0, 0)
    for ddx in np.arange(-busca, busca + 1e-6, passo):
        for ddy in np.arange(-busca, busca + 1e-6, passo):
            X = Bx + ddx; Y = By + ddy
            ok = (X >= 0) & (Y >= 0) & (X < L.shape[1] - 1) & (Y < L.shape[0] - 1)
            if ok.mean() < 0.9: continue
            c = float(np.median(np.minimum(distL[Y[ok].astype(int), X[ok].astype(int)], 200)))
            if c < best[0]: best = (c, ddx, ddy)
    med_cm = best[0] / s_g * cmpx
    X = Bx + best[1]; Y = By + best[2]
    ok = (X >= 0) & (Y >= 0) & (X < L.shape[1] - 1) & (Y < L.shape[0] - 1)
    cobertura = float((distL[Y[ok].astype(int), X[ok].astype(int)] / s_g * cmpx <= 15).mean())
    aceito = med_cm <= a.limite_cm and cobertura >= a.cobertura_min and code not in forcar
    mi = cv2.erode(m, np.ones((3, 3), np.uint8)) > 0
    if aceito:
        shifted = warp(best[1], best[2])
        if not a.restringir_comodos:
            out[mi] = shifted[mi]; relatorio_extra = 0.0
        else:
          lr = warp_lab(best[1], best[2]); pr = warp_par(best[1], best[2])
          ids, cnt = np.unique(lr[mi], return_counts=True)
          proprios = [i for i, c in zip(ids, cnt) if i > 0 and c * (s_g ** 2) >= 0.5 * areaR[i]]   # comodo majoritariamente dentro do contorno
          own = mi & (np.isin(lr, proprios) | pr)
          own = cv2.dilate(own.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool) & mi
          out[own] = shifted[own]
          resto = mi & ~own
          if resto.any():
              piso = np.median(shifted[own & (cv2.cvtColor(shifted[:, :, :3], cv2.COLOR_BGR2GRAY) > 150)], axis=0) if (own & (cv2.cvtColor(shifted[:, :, :3], cv2.COLOR_BGR2GRAY) > 150)).any() else cinza_piso
              out[resto] = np.asarray(piso, np.uint8)
          relatorio_extra = round(float(resto.sum()) / max(1, mi.sum()) * 100, 1)
    else:
        out[mi] = cinza_piso
        mg = mi & (cv2.morphologyEx(creme.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((px(60),) * 2, np.uint8)) > 0)
        out[mg] = base_g[mg]   # gardens/deck do lancamento mantidos (sem mobiliario interno)
    relatorio[code] = dict(cobertura_divisa=round(cobertura, 2), area_sem_layout_pct=relatorio_extra if aceito else 100.0, distancia_mediana_cm=round(med_cm, 1), deslocamento_cm=[round(best[1] / s_g * cmpx), round(best[2] / s_g * cmpx)],
                           status='layout do lancamento encaixado' if aceito else 'SINALIZADA: layout do lancamento nao cabe no contorno aprovado')

# --- paredes do aprovado onde faltam -----------------------------------------------------------------
go = cv2.cvtColor(out[:, :, :3], cv2.COLOR_BGR2GRAY)
parede_out = ((go < 70) & (out[:, :, 3] > 0)).astype(np.uint8)
coberto = cv2.dilate(parede_out, np.ones((px(16) * 2 + 1,) * 2, np.uint8)) > 0
falta = ((divisas > 0) & ~coberto).astype(np.uint8)
n, lab, st, _ = cv2.connectedComponentsWithStats(falta, 8)
sinal = np.zeros((H, W), bool)
for code, rr in relatorio.items():
    if rr['status'].startswith('SINAL'): sinal |= unid[code] > 0
sinal_b = cv2.dilate(sinal.astype(np.uint8), np.ones((t * 2 + 1,) * 2, np.uint8)) > 0
desenhar = np.zeros((H, W), bool)
for i in range(1, n):
    comp = lab == i
    if max(st[i, 2], st[i, 3]) * cmpx > a.vao_max_cm or (comp & sinal_b).any():
        desenhar |= comp
out[desenhar] = (34, 34, 34, 255)
fora = cv2.dilate(predio, np.ones((px(150),) * 2, np.uint8)) == 0
out[fora] = (255, 255, 255, 0)
cv2.imwrite(a.saida, out)

dbg = out[:, :, :3].copy(); a_ = out[:, :, 3:] / 255.0; dbg = (dbg * a_ + 255 * (1 - a_)).astype(np.uint8)
dbg[desenhar] = (0, 0, 255)
for code, rr in relatorio.items():
    if rr['status'].startswith('SINAL'):
        cs, _ = cv2.findContours(unid[code], cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        cv2.drawContours(dbg, cs, -1, (0, 140, 255), 5)
cv2.imwrite(a.saida.rsplit('.', 1)[0] + '_conferencia.jpg', cv2.resize(dbg, (2000, int(2000 * H / W))), [cv2.IMWRITE_JPEG_QUALITY, 88])
log = dict(pagina=C['pagina'], lancamento=a.lancamento, cm_por_px=cmpx, largura=W, altura=H,
           custo_alinhamento_global_px=round(custo(q, 0.01 * L.shape[1]), 2),
           unidades=len(unid), encaixadas=sum(1 for v in relatorio.values() if not v['status'].startswith('SINAL')),
           sinalizadas=sorted(k for k, v in relatorio.items() if v['status'].startswith('SINAL')),
           metros_parede_aprovado=round(float(desenhar.sum()) * cmpx / max(1, t) / 100, 1), por_unidade=relatorio)
json.dump(log, open(a.saida.rsplit('.', 1)[0] + '_log.json', 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print(json.dumps({k: v for k, v in log.items() if k != 'por_unidade'}, ensure_ascii=False))
