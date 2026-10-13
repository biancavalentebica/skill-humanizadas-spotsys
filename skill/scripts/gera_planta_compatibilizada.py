"""FASE 1 sem Revit: planta do pavimento compatibilizada = geometria do APROVADO (PDF Autodoc) + layout do LANCAMENTO (imagem).

Entradas que qualquer pessoa tem: o PDF do projeto aprovado e a humanizada de lancamento (sem texto).
Nao usa Revit, DWG nem IA.

Passos:
1. Quadro de saida na escala da prancha aprovada (cm/px fixo) -> proporcao do aprovado.
2. Alinhamento global lancamento -> aprovado (escala unica + deslocamento, pelas paredes).
3. Para CADA unidade do aprovado: procura a mesma unidade no lancamento ajustando deslocamento e
   escala X/Y independentes (limitadas, padrao +-15%) para casar o contorno aprovado com as paredes do lancamento.
   O interior do lancamento e transferido com esse ajuste e recortado EXATAMENTE no contorno aprovado
   (nada do vizinho entra). Areas comuns: mesmo procedimento por mancha.
4. Paredes do aprovado redesenhadas onde a imagem nao tem parede (vaos de porta ate --vao-max-cm ficam abertos).
5. Log por unidade: escala aplicada (% de esticamento), distancia mediana das divisas as paredes, status.
   Esticamento acima de --esticamento-max ou encaixe ruim -> SINALIZADA (vai para desenho/validacao humana).

Uso: python gera_planta_compatibilizada.py <aprovado.pdf> <celulas.json> <lancamento_sem_texto.png> <saida.png>
        [--escala 100] [--cm-px 0.9]
"""
import json, argparse
import fitz, cv2, numpy as np
from scipy.optimize import minimize

ap = argparse.ArgumentParser()
for k in ('pdf', 'celulas', 'lancamento', 'saida'): ap.add_argument(k)
ap.add_argument('--escala', type=float, default=100)
ap.add_argument('--cm-px', type=float, default=0.9)
ap.add_argument('--busca-cm', type=float, default=150, help='deslocamento maximo procurado por unidade')
ap.add_argument('--escala-max', type=float, default=0.15, help='variacao maxima de escala por eixo (0.15 = +-15%%)')
ap.add_argument('--esticamento-max', type=float, default=0.12, help='acima disso a unidade e sinalizada')
ap.add_argument('--limite-cm', type=float, default=20, help='distancia mediana maxima contorno x parede do lancamento')
ap.add_argument('--ocr', default='', help='JSON do ocr_windows.ps1 sobre a humanizada de lancamento (COM texto): ancora cada unidade pelo numero')
ap.add_argument('--parede-cm', type=float, default=14)
ap.add_argument('--vao-max-cm', type=float, default=110)
ap.add_argument('--margem-cm', type=float, default=60, help='faixa externa ao predio mantida (esquadrias, condensadoras)')
a = ap.parse_args()

C = json.load(open(a.celulas, encoding='utf-8'))
clip = fitz.Rect(*C['clip_pt'])
cmpx = a.cm_px; ESC = (2.54 / 72 * a.escala) / cmpx
W, H = int(clip.width * ESC), int(clip.height * ESC)
px = lambda cm: max(1, int(round(cm / cmpx)))

# --- aprovado ---------------------------------------------------------------------------------------
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

unid = {}
for code, cel in C['celulas'].items():
    m = np.zeros((H, W), np.uint8)
    for poly in cel.get('poligonos_pt', []):
        cv2.fillPoly(m, [np.array([[(x - clip.x0) * ESC, (y - clip.y0) * ESC] for x, y in poly], np.int32)], 255)
    if m.any(): unid[code] = m
todas = np.zeros((H, W), np.uint8)
for m in unid.values(): todas |= m
comum = ((predio > 0) & (todas == 0)).astype(np.uint8) * 255
# manchas de area comum viram "regioes" com o mesmo tratamento das unidades
nc, lc, sc, _ = cv2.connectedComponentsWithStats(comum, 8)
regioes = dict(unid)
for i in range(1, nc):
    if sc[i, 4] * cmpx ** 2 > 2e4: regioes[f'_COMUM{i}'] = ((lc == i) * 255).astype(np.uint8)

t = px(a.parede_cm)
divisas = np.zeros((H, W), np.uint8)
for code, m in regioes.items():
    cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    cv2.drawContours(divisas, cs, -1, 255, t)
divisas[cv2.erode(predio, np.ones((3, 3), np.uint8)) == 0] = 0
cs, _ = cv2.findContours(predio, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
cv2.drawContours(divisas, cs, -1, 255, t)

# --- lancamento: paredes ------------------------------------------------------------------------------
L = cv2.imread(a.lancamento, cv2.IMREAD_UNCHANGED)
if L.shape[2] == 3: L = np.dstack([L, np.full(L.shape[:2], 255, np.uint8)])
gl = cv2.cvtColor(L[:, :, :3], cv2.COLOR_BGR2GRAY)
inkL = ((gl < 70) & (L[:, :, 3] > 0)).astype(np.uint8)
n2, lab2, st2, _ = cv2.connectedComponentsWithStats(inkL, 8)
k2 = np.zeros(n2, bool); k2[1:] = np.maximum(st2[1:, 2], st2[1:, 3]) > L.shape[1] * 0.02
parL = (k2[lab2] * 255).astype(np.uint8)
distL = cv2.distanceTransform(255 - parL, cv2.DIST_L2, 5)
ys, xs = np.where(parL > 0); ext_L = np.array([xs.min(), ys.min(), xs.max(), ys.max()], float)
ys, xs = np.where(predio > 0); ext_P = np.array([xs.min(), ys.min(), xs.max(), ys.max()], float)

def amostra(mask, n=4000):
    ys, xs = np.where(mask > 0)
    if len(xs) > n:
        s = np.random.default_rng(0).choice(len(xs), n, replace=False); xs, ys = xs[s], ys[s]
    return np.stack([xs, ys], 1).astype(np.float64)

def custo_pts(P, sx, sy, tx, ty, teto, estat=np.mean):
    X = P[:, 0] * sx + tx; Y = P[:, 1] * sy + ty
    ok = (X >= 0) & (Y >= 0) & (X < L.shape[1] - 1) & (Y < L.shape[0] - 1)
    if ok.mean() < 0.85: return 1e9
    return float(estat(np.minimum(distL[Y[ok].astype(int), X[ok].astype(int)], teto)))

# rotulos do lancamento (OCR): codigo -> centro do rotulo em pixels do lancamento
import re
rot_L = {}
if a.ocr:
    for ln in json.load(open(a.ocr, encoding='utf-8-sig')):
        ws = ln['palavras'] if isinstance(ln['palavras'], list) else [ln['palavras']]
        txt = ' '.join(w['t'] for w in ws)
        mm = re.search(r'(?:UN|APTO)?\s*(\d{3})\b', txt) or re.search(r'Loja\s*0?(\d)', txt, re.I)
        if not mm: continue
        code = mm.group(1) if len(mm.group(1)) == 3 else 'L' + mm.group(1)
        if code in unid and code not in rot_L:
            rot_L[code] = (np.mean([w['x'] + w['w'] / 2 for w in ws]), np.mean([w['y'] + w['h'] / 2 for w in ws]))
cent = {c: (np.where(m > 0)[1].mean(), np.where(m > 0)[0].mean()) for c, m in unid.items()}

# alinhamento global (escala unica)
Pg = amostra(divisas, 15000)
fg = lambda q, teto: custo_pts(Pg, q[0], q[0], q[1], q[2], teto)
if len(rot_L) >= 4:
    # pares rotulo do lancamento x centro da unidade aprovada; ajuste robusto (descarta unidades que mudaram de lugar)
    ks = sorted(rot_L); A = np.array([cent[k] for k in ks]); B = np.array([rot_L[k] for k in ks]); use = np.ones(len(ks), bool)
    for _ in range(5):
        ax_, bx_ = A[use], B[use]
        s_ = float(np.sum((ax_ - ax_.mean(0)) * (bx_ - bx_.mean(0))) / np.sum((ax_ - ax_.mean(0)) ** 2))
        tq = bx_.mean(0) - s_ * ax_.mean(0)
        res = np.linalg.norm(A * s_ + tq - B, axis=1)
        use = res <= max(2.5 * np.median(res[use]), 1e-6) if use.sum() > 4 else use
    qg = np.array([s_, tq[0], tq[1]])
    qg = minimize(fg, qg, args=(0.015 * L.shape[1],), method='Nelder-Mead').x
    origem_global = f'rotulos OCR ({int(use.sum())}/{len(ks)} pares coerentes)'
else:
    s0 = np.sqrt((ext_L[2] - ext_L[0]) / (ext_P[2] - ext_P[0]) * (ext_L[3] - ext_L[1]) / (ext_P[3] - ext_P[1]))
    best = (1e18, None)
    for ds in np.linspace(-0.1, 0.1, 21):
        s_ = s0 * (1 + ds)
        for dx in np.linspace(-0.05, 0.05, 11) * L.shape[1]:
            for dy in np.linspace(-0.05, 0.05, 11) * L.shape[0]:
                q = (s_, ext_L[0] - s_ * ext_P[0] + dx, ext_L[1] - s_ * ext_P[1] + dy)
                c = fg(q, 0.03 * L.shape[1])
                if c < best[0]: best = (c, q)
    qg = minimize(fg, best[1], args=(0.03 * L.shape[1],), method='Nelder-Mead').x
    qg = minimize(fg, qg, args=(0.01 * L.shape[1],), method='Nelder-Mead').x
    origem_global = 'paredes (sem OCR)'
s_g, tx_g, ty_g = qg

def warp(sx, sy, tx, ty, img=L, interp=cv2.INTER_LINEAR, border=(255, 255, 255, 0)):
    M = np.array([[sx, 0, tx], [0, sy, ty]], np.float32)   # saida -> lancamento
    return cv2.warpAffine(img, M, (W, H), flags=interp | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_CONSTANT, borderValue=border)

# --- encaixe por regiao (deslocamento + escala X/Y limitada) --------------------------------------------
out = warp(s_g, s_g, tx_g, ty_g)
rel = {}
teto = px(60) * s_g
for code, m in regioes.items():
    borda = cv2.morphologyEx(m, cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8))
    P = amostra(borda, 3000)
    cx, cy = P[:, 0].mean(), P[:, 1].mean()
    Pc = P - [cx, cy]                                        # escala em torno do centro da unidade
    base_tx, base_ty = s_g * cx + tx_g, s_g * cy + ty_g      # centro da unidade no lancamento (alinhamento global)
    if code in rot_L:   # ancora pelo numero da unidade no lancamento (o rotulo fica perto do centro)
        base_tx, base_ty = rot_L[code][0] - s_g * (cent[code][0] - cx), rot_L[code][1] - s_g * (cent[code][1] - cy)
    def f(q):
        kx, ky, dx, dy = q
        if abs(kx - 1) > a.escala_max or abs(ky - 1) > a.escala_max: return 1e9
        return custo_pts(Pc, s_g * kx, s_g * ky, base_tx + dx, base_ty + dy, teto) + 0.02 * teto * (abs(kx - 1) + abs(ky - 1)) / a.escala_max
    busca = px(a.busca_cm) * s_g; passo = px(10) * s_g
    cand = []
    for kx in (0.9, 1.0, 1.1):
        for ky in (0.9, 1.0, 1.1):
            for dx in np.arange(-busca, busca + 1e-6, passo):
                for dy in np.arange(-busca, busca + 1e-6, passo):
                    cand.append((f((kx, ky, dx, dy)), (kx, ky, dx, dy)))
    cand.sort(key=lambda z: z[0])
    melhor = min((minimize(f, np.array(c[1]), method='Nelder-Mead', options=dict(xatol=1e-3, fatol=1e-3)) for c in cand[:4]), key=lambda z: z.fun)
    kx, ky, dx, dy = melhor.x
    sx, sy = s_g * kx, s_g * ky
    tx, ty = base_tx + dx - sx * cx, base_ty + dy - sy * cy
    med_cm = custo_pts(P, sx, sy, tx, ty, 1e6, np.median) / s_g * cmpx
    estic = max(abs(kx - 1), abs(ky - 1))
    ok = med_cm <= a.limite_cm and estic <= a.esticamento_max
    mi = m > 0
    w_ = warp(sx, sy, tx, ty)
    out[mi] = w_[mi]
    rel[code] = dict(esticamento_x_pct=round((kx - 1) * 100, 1), esticamento_y_pct=round((ky - 1) * 100, 1),
                     deslocamento_cm=[round(dx / s_g * cmpx), round(dy / s_g * cmpx)], distancia_mediana_cm=round(med_cm, 1),
                     status='OK' if ok else 'SINALIZADA')

# --- paredes do aprovado onde faltam ---------------------------------------------------------------------
go = cv2.cvtColor(out[:, :, :3], cv2.COLOR_BGR2GRAY)
parede_out = ((go < 70) & (out[:, :, 3] > 0)).astype(np.uint8)
# QC no proprio quadro do aprovado: divisas (linha central) x paredes vindas do lancamento
linhas = np.zeros((H, W), np.uint8)
for code, m in regioes.items():
    c3, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE); cv2.drawContours(linhas, c3, -1, 255, 1)
linhas[cv2.erode(predio, np.ones((5, 5), np.uint8)) == 0] = 0
dq = cv2.distanceTransform(255 - parede_out * 255, cv2.DIST_L2, 5)[linhas > 0] * cmpx
qc = dict(divisa_parede_mediana_cm=round(float(np.median(dq)), 1), frac_divisas_ate_15cm=round(float((dq <= 15).mean()), 3))
coberto = cv2.dilate(parede_out, np.ones((px(12) * 2 + 1,) * 2, np.uint8)) > 0
falta = ((divisas > 0) & ~coberto).astype(np.uint8)
n, lab, st, _ = cv2.connectedComponentsWithStats(falta, 8)
desenhar = np.zeros((H, W), bool)
for i in range(1, n):
    comp_, larg_ = max(st[i, 2], st[i, 3]), min(st[i, 2], st[i, 3])
    reto = larg_ <= 2.2 * t or st[i, 4] >= 0.6 * st[i, 2] * st[i, 3]   # so trechos retos (contorno irregular de sacada nao vira parede)
    if comp_ * cmpx > a.vao_max_cm and reto: desenhar |= lab == i
cor_parede = np.median(L[:, :, :3][(parL > 0) & (L[:, :, 3] > 0)], axis=0).astype(np.uint8)
out[desenhar] = (*cor_parede, 255)
fora = cv2.dilate(predio, np.ones((px(a.margem_cm),) * 2, np.uint8)) == 0
out[fora] = (255, 255, 255, 0)
cv2.imwrite(a.saida, out)

dbg = out[:, :, :3].copy(); a_ = out[:, :, 3:] / 255.0; dbg = (dbg * a_ + 255 * (1 - a_)).astype(np.uint8)
cs, _ = cv2.findContours(divisas, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
ov = dbg.copy(); ov[divisas > 0] = (0, 0, 255); dbg = cv2.addWeighted(dbg, 0.6, ov, 0.4, 0)
for code, rr in rel.items():
    if rr['status'] != 'OK' and not code.startswith('_'):
        c2, _ = cv2.findContours(unid[code], cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        cv2.drawContours(dbg, c2, -1, (0, 140, 255), 6)
cv2.imwrite(a.saida.rsplit('.', 1)[0] + '_conferencia.jpg', cv2.resize(dbg, (2400, int(2400 * H / W))), [cv2.IMWRITE_JPEG_QUALITY, 88])
U = {k: v for k, v in rel.items() if not k.startswith('_')}
log = dict(pagina=C['pagina'], lancamento=a.lancamento, cm_por_px=cmpx, largura=W, altura=H,
           alinhamento_global=origem_global, rotulos_ocr=len(rot_L), qc=qc, unidades=len(U), ok=sum(v['status'] == 'OK' for v in U.values()),
           sinalizadas=sorted(k for k, v in U.items() if v['status'] != 'OK'),
           metros_parede_aprovado_desenhada=round(float(desenhar.sum()) * cmpx / t / 100, 1), por_regiao=rel)
json.dump(log, open(a.saida.rsplit('.', 1)[0] + '_log.json', 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print(json.dumps({k: v for k, v in log.items() if k != 'por_regiao'}, ensure_ascii=False))
