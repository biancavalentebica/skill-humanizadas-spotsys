"""Campeche Spot, terreo: humanizada DO ZERO sobre o legal aprovado R00 (Autodoc, prancha 03), orientada como a
humanizada de lancamento (legal girado -45 graus), 0,5 cm/px. Layout das unidades = interiores "Unidades mezanino com
38 m2" (mesmo arranjo do lancamento): banheiro e copa no fundo (lado da porta), bancada ao longo da parede, sofa-cama e
escada junto ao garden. Objetos e texturas: recortes reais do lancamento (kit.py), na escala real.

Uso: py 03_trabalho/do_zero/gera_terreo.py <saida.png>
"""
import sys, os, json
import cv2, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, '../03_trabalho/conforme_R06')
import kit
from remonta_lib import quilt

saida = sys.argv[1] if len(sys.argv) > 1 else '03_trabalho/do_zero/terreo.png'
IDS = np.load('03_trabalho/do_zero/ids_rot.npy')
NOM = {int(k): v for k, v in json.load(open('03_trabalho/do_zero/nomes.json')).items()}
ys, xs = np.nonzero(IDS)
X0, Y0, X1, Y1 = xs.min() - 150, ys.min() - 150, xs.max() + 150, ys.max() + 150
ids = IDS[Y0:Y1, X0:X1].copy(); H, W = ids.shape
def nome(k): return NOM.get(int(k), 'FORA')
def m_de(*nomes): return np.isin(ids, [k for k, v in NOM.items() if v in nomes])
TIPO = {}
for k, v in NOM.items():
    TIPO[k] = ('unidade' if v.startswith('U') else 'garden' if v.startswith('G') else 'loja' if v.startswith('LOJA')
               else 'verde' if v in ('JARDIM', 'CANTEIRO') else 'fora' if v == 'FORA' else 'comum')
img = np.full((H, W, 3), 255, np.uint8)

# ---------------- pisos ----------------
interno = np.isin(ids, [k for k, t in TIPO.items() if t in ('unidade', 'loja', 'comum')])
PISO = quilt(kit.PISO, (H, W), bloco=96, sobre=24); img[interno] = PISO[interno]


def eixo_garden(u):
    """Para a unidade u: centro, (eu, ev) com ev apontando para o garden, largura e profundidade (px)."""
    m = (ids == [k for k, v in NOM.items() if v == u][0]).astype(np.uint8)
    pts = np.column_stack(np.nonzero(m)[::-1]).astype(np.float32)
    (cx, cy), (a, b), ang = cv2.minAreaRect(pts)
    t = np.deg2rad(ang); e1 = np.array([np.cos(t), np.sin(t)]); e2 = np.array([-np.sin(t), np.cos(t)])
    g = m_de('G' + u[1:]); gy, gx = np.nonzero(g); gc = np.array([gx.mean(), gy.mean()]) - (cx, cy)
    if abs(gc @ e1) > abs(gc @ e2): ev, D, Wd = e1 * np.sign(gc @ e1), a, b
    else: ev, D, Wd = e2 * np.sign(gc @ e2), b, a
    eu = np.array([-ev[1], ev[0]])
    return np.array([cx, cy]), eu, ev, Wd, D


def cola_local(tile, alfa, c, eu, ev, Wd, D):
    """tile (D x Wd px, garden embaixo) -> planta, centrado em c com eixos eu (colunas) e ev (linhas)."""
    o = c - eu * Wd / 2 - ev * D / 2
    src = np.float32([[0, 0], [Wd, 0], [0, D]])
    dst = np.float32([o, o + eu * Wd, o + ev * D])
    A = cv2.getAffineTransform(src, dst)
    T = cv2.warpAffine(tile, A, (W, H), flags=cv2.INTER_LINEAR, borderValue=0)
    Ma = cv2.warpAffine(alfa.astype(np.float32), A, (W, H), flags=cv2.INTER_LINEAR, borderValue=0)[:, :, None]
    img[:] = (T * Ma + img * (1 - Ma)).astype(np.uint8)
    return A


def poe(tile, alfa, sp, x, y):
    h, w = sp.shape[:2]; x, y = int(round(x)), int(round(y))
    h = min(h, tile.shape[0] - y); w = min(w, tile.shape[1] - x)
    tile[y:y + h, x:x + w] = sp[:h, :w]; alfa[y:y + h, x:x + w] = 1


def unidade(u, espelho):
    c, eu, ev, Wd, D = eixo_garden(u)
    Wd, D = int(round(Wd)), int(round(D))
    tile = np.zeros((D, Wd, 3), np.uint8); alfa = np.zeros((D, Wd), np.float32)
    B, C, BC, S = kit.BANHO, kit.COZINHA, kit.BANCADA, kit.SOFA_ESC
    poe(tile, alfa, B, 0, 0)                                           # banheiro: canto do fundo, lado esquerdo
    poe(tile, alfa, C, Wd - C.shape[1], 0)                             # copa: canto do fundo, lado direito
    poe(tile, alfa, BC, Wd - BC.shape[1], C.shape[0] + 10)             # bancada ao longo da parede direita
    poe(tile, alfa, S, 0, D - S.shape[0] - 30)                         # sofa-cama + escada junto ao garden
    if espelho: tile, alfa = tile[:, ::-1].copy(), alfa[:, ::-1].copy()
    cola_local(tile, alfa, c, eu, ev, Wd, D)
    return c, eu, ev, Wd, D


GEO = {}
for i, u in enumerate(['U101', 'U102', 'U103', 'U104', 'U105', 'U106', 'U107', 'U108', 'U109', 'U110']):
    GEO[u] = unidade(u, espelho=(i % 2 == 1))


# ---------------- WCs (PCD das lojas e do hall): vaso e bancada com cuba do lancamento ----------------
EXR0 = np.load('03_trabalho/do_zero/exec_rot.npz'); PX = EXR0['parede'][:H, :W]
livre = (~PX).astype(np.uint8); nW_, lW_, sW_, _ = cv2.connectedComponentsWithStats(livre, 4)
for w in ('WC1', 'WC2', 'WC_HALL'):
    mm0 = m_de(w)
    if not mm0.any(): continue
    # recinto do executivo que mais se sobrepoe ao WC do legal (ou o menor recinto fechado dentro da loja)
    cand = [(int((lW_[mm0] == i).sum()), i) for i in np.unique(lW_[mm0]) if i and 50000 < sW_[i, 4] < 400000]
    mm = (lW_ == max(cand)[1]) if cand else mm0
    if not mm.any(): continue
    pts = np.column_stack(np.nonzero(mm)[::-1]).astype(np.float32)
    (cx, cy), (a, b), ang = cv2.minAreaRect(pts)
    t = np.deg2rad(ang); eu = np.array([np.cos(t), np.sin(t)]); ev = np.array([-np.sin(t), np.cos(t)])
    Wd, D = int(a) - 30, int(b) - 30
    tile = PISO[:D, :Wd].copy(); al = np.ones((D, Wd), np.float32)
    v = kit.VASO; tile[10:10 + v.shape[0], 0:v.shape[1]] = v
    l = kit.LAVAT; tile[D - l.shape[0]:D, Wd - l.shape[1]:Wd] = l
    cola_local(tile, al, np.array([cx, cy]), eu, ev, Wd, D)

# ---------------- gardens: deck com tabuas perpendiculares a fachada ----------------
for u, (c, eu, ev, Wd, D) in GEO.items():
    g = m_de('G' + u[1:])
    ang = np.degrees(np.arctan2(ev[1], ev[0])) - 90           # tabuas ao longo de ev
    big = np.tile(kit.DECK, (40, 4, 1))
    M = cv2.getRotationMatrix2D((big.shape[1] / 2, big.shape[0] / 2), -ang, 1.0)
    rot = cv2.warpAffine(big, M, (big.shape[1], big.shape[0]))
    gy, gx = np.nonzero(g); cy, cx = int(gy.mean()), int(gx.mean()); hh, ww = rot.shape[0] // 2, rot.shape[1] // 2
    ys_, xs_ = gy - cy + hh, gx - cx + ww
    ok = (ys_ >= 0) & (ys_ < rot.shape[0]) & (xs_ >= 0) & (xs_ < rot.shape[1])
    img[gy[ok], gx[ok]] = rot[ys_[ok], xs_[ok]]


# ---------------- areas externas, canteiros, nucleo ----------------
fora = ids == 0
n_, lab_, st_, _ = cv2.connectedComponentsWithStats(fora.astype(np.uint8), 4)
borda_ids = set(np.unique(np.concatenate([lab_[0], lab_[-1], lab_[:, 0], lab_[:, -1]])))
vazios = np.isin(lab_, [i for i in range(1, n_) if i not in borda_ids])          # buracos dentro do predio (nucleo, shafts)
# lote: casco convexo do predio + 6 m de calcada
pred = ~fora; cs, _ = cv2.findContours(pred.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
casco = np.zeros((H, W), np.uint8); cv2.fillPoly(casco, [cv2.convexHull(np.vstack(cs))], 1)
casco = cv2.dilate(casco, np.ones((241, 241), np.uint8)).astype(bool)
ext = fora & ~vazios & casco
CAL = quilt(kit.CALCADA, (H, W), bloco=120, sobre=30); img[ext] = CAL[ext]
verde = m_de('JARDIM', 'CANTEIRO')
GR = quilt(kit.GRAMA, (H, W), bloco=80, sobre=20); img[verde] = GR[verde]
AR = quilt(kit.ARBUSTO, (H, W), bloco=120, sobre=30); arb = cv2.erode(verde.astype(np.uint8), np.ones((31, 31), np.uint8)).astype(bool); img[arb] = AR[arb]
# nucleo (escada + elevador): hachura da prancha (componente da densidade de tracos) -> degraus do lancamento
nuc = np.load('03_trabalho/do_zero/nucleo.npy')[:H, :W]   # contorno da hachura ESCADA/ELEVADOR (linhas a 45 graus da prancha)
ny, nx = np.nonzero(nuc); by0, by1, bx0, bx1 = ny.min(), ny.max() + 1, nx.min(), nx.max() + 1
EXR = np.load('03_trabalho/do_zero/exec_rot.npz')
EXG = EXR['exec_rgb_gray'][:H, :W]
img[nuc] = PISO[nuc]
# degraus: faixas entre os tracos do executivo recebem o tom do degrau do lancamento, tracos viram espelhos
nuc_in = cv2.erode(nuc.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool)
tr = (EXG < 200) & nuc_in
tr = cv2.dilate(tr.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
DEG = np.array(kit.DEGRAUS.reshape(-1, 3).mean(0)); img[nuc_in] = (img[nuc_in] * 0.55 + DEG * 0.45).astype(np.uint8)
img[tr] = (img[tr] * 0.25 + np.array([90, 88, 96]) * 0.75).astype(np.uint8)
NUCLEO = nuc
# buracos fechados: grandes = area coberta aberta (piso); pequenos = shaft (parede cheia)
for i in range(1, n_):
    if i in borda_ids: continue
    mm = (lab_ == i) & ~nuc
    if mm.sum() > 40000: img[mm] = PISO[mm]
    elif mm.sum(): img[mm] = kit.MIOLO.reshape(-1, 3).mean(0)

# ---------------- frente e acessos pelo legal R00: rua, floreiras/canteiros, gramado, fruicao, plataforma PCD ----------------
EXT = np.load('03_trabalho/do_zero/externo_rot.npz'); EP = json.load(open('03_trabalho/do_zero/externo_pts.json', encoding='utf-8'))
def em(k): return EXT[k][:H, :W]
fora_lote = fora & ~vazios
yy_, xx_ = np.mgrid[0:H, 0:W]
# ruas pelo meio-fio da prancha: Rua Pequi abaixo do canteiro longo; Rua Mogno a esquerda do gramado elevado
cl = em('verde'); ny_, nx_ = np.nonzero(cl & (yy_ > 5600)); yfio = int(np.percentile(ny_, 99)) + 8 if len(ny_) else 6010
(x1_, y1_), (x2_, y2_) = (875, 4450), (1500, 5250)
esq = ((x2_ - x1_) * (yy_ - y1_) - (y2_ - y1_) * (xx_ - x1_)) > 0
ruaM = fora_lote & ((yy_ > yfio) | (esq & (yy_ > 3000)))
PAS = quilt(kit.PASSEIO, (H, W), bloco=160, sobre=40)
# lote: frente (Rua Pequi) e lado da Rua Mogno; acima das alas e a direita da Loja 2 e vizinho (fundo branco)
(xa, ya), (xb, yb) = (7025, 3450), (8150, 5150)
dir_loja = ((xb - xa) * (yy_ - ya) - (yb - ya) * (xx_ - xa)) < 0
lote = ((yy_ > 3900) | ((xx_ < 2200) & (yy_ > 3000))) & ~(dir_loja & (yy_ < 5150))
passeio = fora_lote & ~ruaM & ~nuc & lote
img[passeio] = PAS[passeio]
img[fora_lote & ~lote & ~ruaM & ~nuc] = 255
RU = quilt(kit.RUA, (H, W), bloco=120, sobre=30); img[ruaM] = RU[ruaM]
jd = EXR['jardim'][:H, :W] & fora & ~vazios & ~em('rua')
img[jd] = GR[jd]
rng_ = np.random.default_rng(5); jy, jx = np.nonzero(cv2.erode(jd.astype(np.uint8), np.ones((181, 181), np.uint8)))
ARV_JD = [(jx[i], jy[i]) for i in rng_.choice(len(jx), min(9, len(jx)), replace=False)] if len(jx) else []
gr = (em('grama') | em('verde')) & ~interno; img[gr] = GR[gr]
fl = em('verde') & ~interno
fl_in = cv2.erode(fl.astype(np.uint8), np.ones((15, 15), np.uint8)).astype(bool); img[fl_in] = AR[fl_in]
fr = em('fruicao') & ~interno   # area de fruicao = alargamento do passeio (textura de passeio)
pl = em('plataforma') & ~interno; img[pl] = (img[pl] * 0.4 + np.array([205, 205, 210]) * 0.6).astype(np.uint8)
# sem linhas da prancha (carros, cotas, vagas): so os degraus da escada de acesso, no estilo do lancamento (faixas claras)
esc_zona = cv2.dilate(pl.astype(np.uint8), np.ones((501, 501), np.uint8)).astype(bool) & ~pl & fora & ~vazios & ~gr
deg = em('linhas') & esc_zona
n3, l3, s3, _ = cv2.connectedComponentsWithStats(deg.astype(np.uint8), 8)
deg = np.isin(l3, [i for i in range(1, n3) if 120 < max(s3[i, 2], s3[i, 3]) < 700])   # so tracos do tamanho de um degrau
deg = cv2.dilate(deg.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
sh = cv2.dilate(deg.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool) & ~deg
img[sh] = (img[sh] * 0.9).astype(np.uint8); img[deg] = (244, 242, 246)
# meio-fio: borda da rua
mf = cv2.morphologyEx(ruaM.astype(np.uint8), cv2.MORPH_GRADIENT, np.ones((7, 7), np.uint8)).astype(bool) & ~interno
img[mf] = (242, 240, 244)
# arvores (copa real do lancamento) e bicicletas (paraciclos BR/BC)
def cola_sp(sp, al, cx, cy, d):
    k = d / sp.shape[1]; s2 = cv2.resize(sp, None, fx=k, fy=k, interpolation=cv2.INTER_AREA); a2 = cv2.resize(al, None, fx=k, fy=k)[:, :, None]
    h, w = s2.shape[:2]; x0, y0 = int(cx - w / 2), int(cy - h / 2)
    if x0 < 0 or y0 < 0 or x0 + w > W or y0 + h > H: return
    reg = img[y0:y0 + h, x0:x0 + w].astype(np.float32); sh = cv2.GaussianBlur(a2[:, :, 0], (0, 0), 6)[:, :, None]
    reg = reg * (1 - 0.35 * np.roll(np.roll(sh, 10, 0), 10, 1))
    img[y0:y0 + h, x0:x0 + w] = (s2 * a2 + reg * (1 - a2)).astype(np.uint8)
for x, y, r in EP['arvores']: cola_sp(kit.ARVORE, kit.ARVORE_A, x, y, 2 * r * 1.15)
for x, y in ARV_JD: cola_sp(kit.ARVORE, kit.ARVORE_A, x, y, 300)
BK = cv2.imread('../skill/estilo/lancamento/objetos/bicicleta.png'); BKa = np.load('../skill/estilo/lancamento/objetos/bicicleta_alfa.npy').astype(np.float32)
BK = cv2.resize(BK, None, fx=1.96, fy=1.96); BKa = cv2.resize(BKa, None, fx=1.96, fy=1.96)
Mb = cv2.getRotationMatrix2D((BK.shape[1] / 2, BK.shape[0] / 2), 45, 1.0)
for x, y, t in EP['bicis']:
    S = int(max(BK.shape[:2]) * 1.5); pad = np.zeros((S, S, 3), np.uint8); pa = np.zeros((S, S), np.float32)
    oy, ox = (S - BK.shape[0]) // 2, (S - BK.shape[1]) // 2; pad[oy:oy + BK.shape[0], ox:ox + BK.shape[1]] = BK; pa[oy:oy + BK.shape[0], ox:ox + BK.shape[1]] = BKa
    Mr = cv2.getRotationMatrix2D((S / 2, S / 2), -32.6 if t.startswith('BR') else 0, 1.0)
    pad = cv2.warpAffine(pad, Mr, (S, S)); pa = cv2.warpAffine(pa, Mr, (S, S))[:, :, None]
    x0, y0 = int(x - S / 2), int(y - S / 2); reg = img[y0:y0 + S, x0:x0 + S].astype(np.float32)
    img[y0:y0 + S, x0:x0 + S] = (pad * pa + reg * (1 - pa)).astype(np.uint8)

# ---------------- paredes ----------------
def regra(a, b):
    na, nb, ta, tb = nome(a), nome(b), TIPO.get(int(a), 'fora'), TIPO.get(int(b), 'fora')
    if na == nb: return None
    if {ta, tb} == {'unidade', 'garden'}: return 'vidro'
    if 'garden' in (ta, tb) or 'verde' in (ta, tb): return 'muro'
    if 'fora' in (ta, tb): return 'ext'
    return 'int'
paredes = {k: np.zeros((H, W), bool) for k in ('int', 'ext', 'muro', 'vidro')}
cache = {}
for eixo in (0, 1):
    a = ids[:, :-1] if eixo else ids[:-1]; b = ids[:, 1:] if eixo else ids[1:]
    yy, xx = np.nonzero(a != b)
    pa, pb = a[yy, xx], b[yy, xx]
    for ia, ib in set(zip(pa.tolist(), pb.tolist())):
        key = (min(ia, ib), max(ia, ib))
        if key not in cache: cache[key] = regra(ia, ib)
    rr = np.array([cache[(min(i, j), max(i, j))] or '' for i, j in zip(pa.tolist(), pb.tolist())])
    for k in paredes:
        s = rr == k; paredes[k][yy[s], xx[s]] = True
# vitrine: fachada das lojas voltada para a rua (fora logo abaixo da loja)
lojas = np.isin(ids, [k for k, t in TIPO.items() if t == 'loja'])
vit = np.zeros((H, W), bool); vit[:-1] |= lojas[:-1] & (ids[1:] == 0)
paredes['ext'] &= ~cv2.dilate(vit.astype(np.uint8), np.ones((5, 41), np.uint8)).astype(bool)
paredes['vidro'] |= vit
ESP = {'int': 28, 'ext': 34, 'muro': 22, 'vidro': 10}
for k in paredes:
    r = ESP[k] // 2; paredes[k] = cv2.dilate(paredes[k].astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))).astype(bool)

# paredes reais (espessura, pilares, vaos de porta) do executivo registrado sobre o legal
unid = np.isin(ids, [k for k, t in TIPO.items() if t == 'unidade'])
PAR = EXR['parede'][:H, :W] | (EXR['parede_fina'][:H, :W] & ~unid)
PAR = cv2.morphologyEx(PAR.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8)).astype(bool)
# tira simbolos (marcas de corte, norte) e pecas soltas fora do predio
predio_d = cv2.dilate((~fora).astype(np.uint8), np.ones((61, 61), np.uint8)).astype(bool)
n2, l2, s2, _ = cv2.connectedComponentsWithStats(PAR.astype(np.uint8), 8)
for i in range(1, n2):
    comp = l2 == i if s2[i, 4] < 20000 else None
    if comp is not None and not (comp & predio_d).any(): PAR[comp] = False
    elif comp is not None and s2[i, 4] < 1500: PAR[comp] = False

NAVY = kit.MIOLO.reshape(-1, 3).mean(0)
def pinta_parede(m, cor_borda=(235, 236, 236)):
    m8 = m.astype(np.uint8); dout = cv2.distanceTransform(1 - m8, cv2.DIST_L2, 3)
    sombra = (m8 == 0) & (dout <= 8); img[sombra] = (img[sombra] * 0.85).astype(np.uint8)
    img[m] = NAVY
    borda = (m8 == 0) & (dout <= 2.5); img[borda] = cor_borda
pinta_parede(PAR)
mu = paredes['muro'] & ~cv2.dilate(PAR.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool); img[mu] = (226, 228, 229); img[cv2.morphologyEx(mu.astype(np.uint8), cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)) > 0] = (170, 172, 174)
vi = paredes['vidro'] & ~cv2.dilate(PAR.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool); img[vi] = (236, 238, 240); img[cv2.morphologyEx(vi.astype(np.uint8), cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)) > 0] = (150, 155, 160)


# ---------------- textos (letras dos proprios rotulos do lancamento, caixa branca 65% como no lancamento) ----------------
cv2.imwrite(saida.replace('.png', '_SEM-TEXTO.png'), img)
from glifos import Fonte
FT = Fonte()
def linha(t, cx, cy):
    A, b = FT.render(t); A = np.clip(cv2.resize(A, None, fx=kit.K, fy=kit.K, interpolation=cv2.INTER_CUBIC), 0, 1); b *= kit.K
    h, w = A.shape; x0, y0 = int(cx - w / 2), int(cy - h / 2)
    p = 12; box = img[y0 - p:y0 + h + p, x0 - p:x0 + w + p].astype(np.float32)
    img[y0 - p:y0 + h + p, x0 - p:x0 + w + p] = (box * 0.35 + 255 * 0.65).astype(np.uint8)
    reg = img[y0:y0 + h, x0:x0 + w].astype(np.float32); al = A[:, :, None]
    img[y0:y0 + h, x0:x0 + w] = (reg * (1 - al)).astype(np.uint8)
def rotulo(l1, l2, c):
    linha(l1, c[0], c[1] - 55); linha(l2, c[0], c[1] + 55)
AREA = {'U101': '22,87', 'U107': '19,37'}
GA = {'G101': '9,28', 'G107': '10,50', 'G108': '6,80', 'G109': '6,80', 'G110': '6,80'}
for u, (c, eu, ev, Wd, D) in GEO.items():
    rotulo('UN ' + u[1:], AREA.get(u, '18,82') + ' m²', c + ev * D * 0.12)
    g = 'G' + u[1:]; gy, gx = np.nonzero(m_de(g))
    rotulo('Garden', GA.get(g, '10,20') + ' m²', (gx.mean(), gy.mean()))
for nm, a in (('LOJA 1', '33,58'), ('LOJA 2', '34,98')):
    yy, xx = np.nonzero(m_de(nm)); rotulo(nm.replace('LOJA ', 'LOJA 0'), a + ' m²', (xx.mean(), yy.mean() + 120))

ROT = EP['rotulos']
if 'acesso pedestres' in ROT: linha('Acesso', ROT['acesso pedestres'][0], ROT['acesso pedestres'][1] + 140)
if 'ACESSO FRUIÇÃO PÚBLICA' in ROT: linha('Acesso as lojas', ROT['ACESSO FRUIÇÃO PÚBLICA'][0], ROT['ACESSO FRUIÇÃO PÚBLICA'][1] + 120)

cv2.imwrite(saida, img)
json.dump(dict(X0=int(X0), Y0=int(Y0)), open(os.path.splitext(saida)[0] + '_quadro.json', 'w'))
print('ok', saida, img.shape)
