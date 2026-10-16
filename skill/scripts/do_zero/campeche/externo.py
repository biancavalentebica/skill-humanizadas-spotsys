"""Frente e acesso pelo legal R00 (prancha 03): mascaras no quadro do legal (1 cm/px) e depois no quadro da planta.
Classes: rua, verde (canteiro/floreira/jardim), grama (gramado e bicicletarios), fruicao (area de fruicao publica),
plataforma PCD, arvores (simbolos), bicicletas (rotulos BR/BC), linhas externas (meio-fio, escada, vagas, muros)."""
import sys, os, json
import fitz, cv2, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from base import pg, px, Z, W, H, CLIP, raster, rotulos
from mapa import gira

def poly_pts(d):
    out, cur = [], []
    for it in d['items']:
        if it[0] == 'l':
            if not cur: cur.append(px(it[1].x, it[1].y))
            cur.append(px(it[2].x, it[2].y))
        elif it[0] == 'c':
            if not cur: cur.append(px(it[1].x, it[1].y))
            cur.append(px(it[4].x, it[4].y))
        elif it[0] == 're':
            r = it[1]; out.append([px(r.x0, r.y0), px(r.x1, r.y0), px(r.x1, r.y1), px(r.x0, r.y1)])
        elif it[0] == 'qu':
            q = it[1]; out.append([px(q.ul.x, q.ul.y), px(q.ur.x, q.ur.y), px(q.lr.x, q.lr.y), px(q.ll.x, q.ll.y)])
    if cur: out.append(cur)
    return [np.array(p, np.float32) for p in out if len(p) >= 3]

def fill(polys):
    m = np.zeros((H, W), np.uint8)
    for p in polys: cv2.fillPoly(m, [np.round(p * 4).astype(np.int32)], 1, shift=2)
    return m.astype(bool)

R = rotulos()
def lab_in(m, *keys):
    return any(any(s.startswith(k) for k in keys) and 0 <= int(y) < H and 0 <= int(x) < W and m[int(y), int(x)] for s, x, y, d in R)

verde, grama, plat, arv = [np.zeros((H, W), bool) for _ in range(4)]
arvores = []
for d in pg.get_drawings():
    if d['type'] not in ('f', 'fs'): continue
    f = tuple(round(v, 2) for v in d['fill']); r = fitz.Rect(d['rect'])
    if f == (0.31, 0.53, 0.25):
        m = fill(poly_pts(d))
        if lab_in(m, 'BR', 'BC', 'GRAMADO'): grama |= m
        else: verde |= m
    elif f == (0.75, 0.75, 0.75) and r.width < 80: plat |= fill(poly_pts(d))
    elif f == (1.0, 1.0, 1.0) and len(d['items']) > 20 and 25 < r.width < 50 and abs(r.width - r.height) < 3:
        c = px((r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2); arvores.append((c[0], c[1], r.width * Z / 2))
# area de fruicao publica: regiao fechada pelos tracos que contem o rotulo (mais a faixa dos paraciclos BC3-5)
Bf = raster(((0, 0, 0), (0.54, 0.54, 0.54)))
Bfc = cv2.dilate(Bf.astype(np.uint8), np.ones((5, 5), np.uint8))
n, lab, st, _ = cv2.connectedComponentsWithStats((1 - Bfc).astype(np.uint8), connectivity=4)
fru = np.zeros((H, W), bool)
for s_, x, y, d in R:
    if s_.startswith('ÁREA FRUIÇÃO') or s_.startswith('BC3'):
        k = lab[int(y), int(x)]
        if k and st[k, 4] < 600000: fru |= lab == k
fru = cv2.dilate(fru.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
print('fruicao m2', fru.sum() / 1e4)
# rua: alem do meio-fio atual (borda externa do canteiro da Rua Pequi) e alem do gramado elevado (Rua Mogno)
def semiplano(p0, p1, longe_de):
    (x0, y0), (x1, y1) = p0, p1; yy, xx = np.mgrid[0:H, 0:W]
    s = (x1 - x0) * (yy - y0) - (y1 - y0) * (xx - x0); s0 = (x1 - x0) * (longe_de[1] - y0) - (y1 - y0) * (longe_de[0] - x0)
    return np.sign(s) != np.sign(s0)
ref = px(700, 600)   # um ponto dentro do predio
B = raster()
def borda_externa(m):
    cs, _ = cv2.findContours(m.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    c = max(cs, key=cv2.contourArea).reshape(-1, 2).astype(np.float32)
    rect = cv2.minAreaRect(c); box = cv2.boxPoints(rect)
    # lado do retangulo mais longe do predio
    lados = [(box[i], box[(i + 1) % 4]) for i in range(4)]
    return max(lados, key=lambda l: np.hypot(*(((l[0] + l[1]) / 2) - ref)))
cant = verde.copy(); n, lab, st, _ = cv2.connectedComponentsWithStats(cant.astype(np.uint8))
big = lab == (1 + int(np.argmax(st[1:, 4])))                     # canteiro longo da Rua Pequi
a, b = borda_externa(big); rua = semiplano(a, b, ref)
gm = grama.copy(); n, lab, st, _ = cv2.connectedComponentsWithStats(gm.astype(np.uint8))
gram = np.isin(lab, [i for i in range(1, n) if lab_in(lab == i, 'GRAMADO')])
if gram.any():
    a2, b2 = borda_externa(gram); xx_ = np.arange(W)[None, :]
    rua |= semiplano(a2, b2, ref) & (xx_ < px(560, 0)[0])   # Rua Mogno: so do lado esquerdo do lote
# linhas externas (escada de acesso, vagas, meio-fio, muros, carros) = tracos pretos
LIN = raster(((0, 0, 0), (0.29, 0.29, 0.29)))
cls = dict(rua=rua, verde=verde, grama=grama, fruicao=fru, plataforma=plat, linhas=LIN)
q = json.load(open('03_trabalho/do_zero/t1_quadro.json'))
_, Mg = gira(np.zeros((H, W), np.float32))
out = {}
for k, m in cls.items():
    g, _ = gira(m.astype(np.float32), cv2.INTER_LINEAR); out[k] = g[q['Y0']:, q['X0']:] > 0.5
def leva(x, y):
    v = Mg @ np.array([x, y, 1.0]); return float(v[0] - q['X0']), float(v[1] - q['Y0'])
s = abs(Mg[0, 0] / np.cos(np.deg2rad(45)))   # escala (2 px/cm)
out_pts = dict(arvores=[(*leva(x, y), r * 2.0) for x, y, r in arvores],
               bicis=[(*leva(x, y), t) for t, x, y, d in [(s_, x_, y_, d_) for s_, x_, y_, d_ in R if s_[:2] in ('BR', 'BC') and s_[2:3].isdigit()]],
               rotulos={k: leva(x, y) for k, x, y in [(s_, x_, y_) for s_, x_, y_, d_ in R if s_ in ('acesso pedestres', 'acesso veículo', 'ACESSO FRUIÇÃO PÚBLICA', 'ÁREA FRUIÇÃO PÚBLICA', 'EMBARQUE/ DESEMBARQUE', 'DEP. TEMP. DE LIXO', 'CANTEIRO', 'JARDIM', 'EIXO RUA PEQUI', 'CALÇADA')]})
np.savez_compressed('03_trabalho/do_zero/externo_rot.npz', **out)
json.dump(out_pts, open('03_trabalho/do_zero/externo_pts.json', 'w', encoding='utf-8'), ensure_ascii=False)
print({k: int(v.sum()) for k, v in out.items()}, len(arvores), 'arvores', len(out_pts['bicis']), 'bicis')
