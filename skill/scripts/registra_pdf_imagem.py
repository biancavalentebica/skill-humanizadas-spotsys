"""Registra a prancha aprovada (PDF) sobre a humanizada (raster) e mede a aderencia geometrica.

Geometria do PDF: bordas das manchas de area (unidades, gardens, areas comuns) na janela do JSON de celulas.
Geometria da imagem: paredes (componentes pretos grandes).
Ajuste: transformacao sem rotacao (escala x, escala y, deslocamento) que minimiza a distancia media das
bordas do PDF ate a parede mais proxima (chamfer robusto). Testa duas definicoes de mancha e duas
etapas (escala unica -> escalas livres) e fica com o menor custo.

Metricas de QC (gravadas no JSON):
- anisotropia = escala_x / escala_y. Planta sem distorcao ~ 1,00. Fora de [0,98; 1,02] -> conferir.
- chamfer_mediana_cm / p90: distancia real (cm) das divisas do aprovado ate as paredes da humanizada.
- frac_divisas_ate_15cm: fracao das divisas do aprovado que tem parede da humanizada a ate 15 cm.

Uso: python registra_pdf_imagem.py <aprovado.pdf> <celulas.json> <humanizada.png> <saida_prefixo> [--escala 100]
"""
import sys, json, argparse
import fitz, cv2, numpy as np
from scipy.optimize import minimize

ap = argparse.ArgumentParser()
for k in ('pdf', 'celulas', 'imagem', 'prefixo'): ap.add_argument(k)
ap.add_argument('--herdar', default='', help='transform.json de outro pavimento (mesma folha/enquadramento): reaproveita a transformacao em vez de otimizar')
ap.add_argument('--escala', type=float, default=100, help='denominador da escala da planta usada (1:100 -> 100)')
a = ap.parse_args()
CM_POR_PT = 2.54 / 72 * a.escala
C = json.load(open(a.celulas, encoding='utf-8'))
clip = fitz.Rect(*C['clip_pt']); ESC = C['esc']
pg = fitz.open(a.pdf)[C['pagina'] - 1]
pix = pg.get_pixmap(matrix=fitz.Matrix(ESC, ESC), clip=clip)
pim = np.frombuffer(pix.samples, np.uint8).reshape(pix.h, pix.w, pix.n)[:, :, :3][:, :, ::-1].astype(int)
b, g, r = pim[:, :, 0], pim[:, :, 1], pim[:, :, 2]
mxc = np.maximum(np.maximum(b, g), r); mnc = np.minimum(np.minimum(b, g), r)
colorida = (mxc > 150) & (mxc - mnc > 12) & (mnc > 60)
faixa = (abs(b - 240) <= 4) & (abs(g - 240) <= 4) & (abs(r - 240) <= 4)
cinza_claro = (mxc - mnc <= 8) & (mnc >= 200) & (mxc <= 246)
BASES = {'estrita': colorida | faixa, 'ampliada': colorida | cinza_claro}

im = cv2.imread(a.imagem, cv2.IMREAD_UNCHANGED)
gi = cv2.cvtColor(im[:, :, :3], cv2.COLOR_BGR2GRAY)
alpha = im[:, :, 3] if im.shape[2] == 4 else np.full(gi.shape, 255, np.uint8)
ink = ((gi <= 40) & (alpha > 0)).astype(np.uint8)
n2, lab2, st2, _ = cv2.connectedComponentsWithStats(ink, 8)
k2 = np.zeros(n2, bool); k2[1:] = np.maximum(st2[1:, 2], st2[1:, 3]) > im.shape[1] * 0.02
par = (k2[lab2] * 255).astype(np.uint8)
ys2, xs2 = np.where(par > 0); ext_paredes = np.array([xs2.min(), ys2.min(), xs2.max(), ys2.max()], float)
ya, xa = np.where(alpha > 0); ext_visivel = np.array([xa.min(), ya.min(), xa.max(), ya.max()], float)
EXTS = {'paredes': ext_paredes, 'area_visivel': ext_visivel}  # rooftop/decks sem parede no perimetro
dist = cv2.distanceTransform(255 - par, cv2.DIST_L2, 5)


def bordas(base):
    bm = base.astype(np.uint8)
    nh, lh, sh, _ = cv2.connectedComponentsWithStats((1 - bm).astype(np.uint8), 4)
    furo = np.zeros(nh, bool); furo[1:] = sh[1:, 4] < (1.2 * ESC) ** 2 * 60  # letras dentro das manchas
    bm[furo[lh]] = 1
    fech = cv2.morphologyEx(bm, cv2.MORPH_CLOSE, np.ones((int(3 * ESC), int(3 * ESC)), np.uint8))
    nf, lf, sf, _ = cv2.connectedComponentsWithStats(fech, 8)
    laje = lf == 1 + int(np.argmax(sf[1:, 4]))
    bm[~laje] = 0
    lin = (cv2.morphologyEx(bm, cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)) * 255).astype(np.uint8)
    ys, xs = np.where(laje)
    return lin, np.array([xs.min(), ys.min(), xs.max(), ys.max()], float)


def ajusta(lin, pext, iext):
    pys, pxs = np.where(lin > 0)
    sel = np.random.default_rng(0).choice(len(pxs), min(20000, len(pxs)), replace=False)
    P = np.stack([pxs[sel], pys[sel]], 1).astype(np.float64)

    def custo(q, teto):
        sx_, sy_, tx_, ty_ = q
        X = P[:, 0] * sx_ + tx_; Y = P[:, 1] * sy_ + ty_
        ok = (X >= 0) & (Y >= 0) & (X < im.shape[1] - 1) & (Y < im.shape[0] - 1)
        if ok.mean() < 0.8: return 1e9
        return float(np.minimum(dist[Y[ok].astype(int), X[ok].astype(int)], teto).mean())

    s = np.sqrt((iext[2] - iext[0]) / (pext[2] - pext[0]) * (iext[3] - iext[1]) / (pext[3] - pext[1]))
    pc = (pext[:2] + pext[2:]) / 2; ic = (iext[:2] + iext[2:]) / 2
    T1, T2 = 0.02 * im.shape[1], 0.006 * im.shape[1]
    melhor = (1e18, None)
    for ds in np.linspace(-0.35, 0.35, 36):  # varredura grossa, escala unica (+-35%)
        ss = s * (1 + ds)
        for dx in np.linspace(-0.08, 0.08, 13) * im.shape[1]:
            for dy in np.linspace(-0.08, 0.08, 13) * im.shape[0]:
                q = np.array([ss, ss, ic[0] - ss * pc[0] + dx, ic[1] - ss * pc[1] + dy])
                c = custo(q, T1)
                if c < melhor[0]: melhor = (c, q)
    # etapa 1: escala unica (3 parametros)
    iso = lambda v, t: custo(np.array([v[0], v[0], v[1], v[2]]), t)
    r_iso = minimize(iso, [melhor[1][0], melhor[1][2], melhor[1][3]], args=(T1,), method='Nelder-Mead', options=dict(xatol=0.01, fatol=1e-3, maxiter=3000))
    r_iso = minimize(iso, r_iso.x, args=(T2,), method='Nelder-Mead', options=dict(xatol=0.005, fatol=1e-4, maxiter=3000))
    # etapa 2: escalas livres (mede anisotropia real)
    q = np.array([r_iso.x[0], r_iso.x[0], r_iso.x[1], r_iso.x[2]])
    r_ani = minimize(custo, q, args=(T2,), method='Nelder-Mead', options=dict(xatol=0.005, fatol=1e-4, maxiter=4000))
    return r_ani.fun, r_ani.x, r_iso.fun

resultados = []
if a.herdar:
    H = json.load(open(a.herdar, encoding='utf-8'))
    Ah = np.vstack([np.array(H['A_pdfpx_para_img']), [0, 0, 1]])
    eh, ch = H['esc'], H['clip_pt']
    # pdf px (esta janela) -> pt -> pdf px (janela herdada) -> imagem
    M = np.array([[eh / ESC, 0, (clip.x0 - ch[0]) * eh], [0, eh / ESC, (clip.y0 - ch[1]) * eh], [0, 0, 1]])
    Aq = (Ah @ M)
    lin, _ = bordas(BASES['estrita'])
    resultados.append((-1, 'herdado:' + a.herdar, np.array([Aq[0, 0], Aq[1, 1], Aq[0, 2], Aq[1, 2]]), lin, -1))
for nome, base in ({} if a.herdar else BASES).items():
    lin, pext = bordas(base)
    for nome_e, iext in EXTS.items():
        c, q, c_iso = ajusta(lin, pext, iext)
        resultados.append((c, nome + '+' + nome_e, q, lin, c_iso))
c, nome, q, lin, c_iso = min(resultados, key=lambda t: t[0])
sx, sy, tx, ty = q
Apx = np.array([[sx, 0, tx], [0, sy, ty]])
lin_img = cv2.warpAffine(lin, Apx.astype(np.float32), (im.shape[1], im.shape[0]), flags=cv2.INTER_NEAREST)
dv = dist[lin_img > 0]
cm_px = CM_POR_PT / (np.sqrt(sx * sy) * ESC)
res = dict(pagina=C['pagina'], imagem=a.imagem, clip_pt=C['clip_pt'], esc=ESC, escala_planta=a.escala,
           A_pdfpx_para_img=Apx.tolist(), base_escolhida=nome,
           custo_por_base={t[1]: round(t[0], 3) for t in resultados}, custo_escala_unica=round(c_iso, 3),
           anisotropia=round(sx / sy, 4), cm_por_px_imagem=round(cm_px, 3),
           chamfer_mediana_cm=round(float(np.median(dv)) * cm_px, 1), chamfer_p90_cm=round(float(np.percentile(dv, 90)) * cm_px, 1),
           frac_divisas_ate_15cm=round(float((dv * cm_px <= 15).mean()), 3))
json.dump(res, open(a.prefixo + '_transform.json', 'w', encoding='utf-8'), indent=1)
bimg = im[:, :, :3].astype(float)
if im.shape[2] == 4:
    al = im[:, :, 3:] / 255.0; bimg = bimg * al + 255 * (1 - al)
ov = bimg.astype(np.uint8)
ov[cv2.dilate(lin_img, np.ones((3, 3), np.uint8)) > 0] = (0, 0, 255)
cv2.imwrite(a.prefixo + '_overlay.jpg', cv2.resize(ov, (1920, int(1920 * ov.shape[0] / ov.shape[1])), interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY, 88])
print(json.dumps({k: v for k, v in res.items() if k not in ('A_pdfpx_para_img', 'clip_pt')}))
