"""Cachoeira Spot, terreo: humanizada desenhada DO ZERO sobre o aprovado R06 (prancha 04), com o layout de cada
unidade readequado do projeto de interiores (tabela de tipologias) e o estilo/objetos reais da humanizada de lancamento.

Uso: py 03_trabalho/do_zero/gera_terreo.py <saida.png>
Escala: 1 cm/px. Quadro = r06_base (pt -> px).
"""
import sys, os, json
import cv2, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from r06_base import *
from mapa_ids import mapa
import kit, motor
from motor import Quadro

saida = sys.argv[1] if len(sys.argv) > 1 else '03_trabalho/do_zero/terreo.png'
ids, nomes, tipos, caixas, amb = mapa()
N2I = {v: k for k, v in nomes.items()}
INTER = ('unidade', 'loja', 'circ', 'tecnica', 'servico', 'nucleo')

# nucleo: escada e elevadores como ambientes proprios dentro da circulacao
def caixa_real(c): x, y, w, h = [int(v) for v in c[:4]]; return x + 7, y + 7, x + w - 7, y + h - 7
ESC = caixa_real(caixas[0]); ELV = caixa_real(caixas[1])
for nome, (x0, y0, x1, y1) in (('ESC', ESC), ('ELEV', ELV)):
    k = max(nomes) + 1; nomes[k] = nome; tipos[k] = 'nucleo'; N2I[nome] = k
    ids[y0:y1, x0:x1] = k
WCS = sorted([caixa_real(c) for c in caixas[3:6]])   # WC PCD das lojas (1,85 x 1,70)
for i, (x0, y0, x1, y1) in enumerate(WCS):
    k = max(nomes) + 1; nomes[k] = 'WC%d' % (i + 1); tipos[k] = 'wc'; N2I[nomes[k]] = k
    ids[y0:y1, x0:x1] = k
INTER = INTER + ('wc',)

img = np.full((H, W, 3), 255, np.uint8)
T = np.vectorize(lambda k: tipos[k])(np.arange(max(nomes) + 1))
tipo_px = T[ids]
nome_px = np.array([nomes[k] for k in range(max(nomes) + 1)], dtype=object)

# ---------------- pisos ----------------
PORC = kit.piso_porcelanato(H, W)
interno = np.isin(tipo_px, INTER) | np.isin(ids, [k for k, v in nomes.items() if v == 'COBERTA'])
img[interno] = PORC[interno]
gard = tipo_px == 'garden'
sys.path.insert(0, '03_trabalho/conforme_R06'); from remonta_lib import quilt
DECK = quilt(kit.DECK, (H, W), bloco=96, sobre=24); img[gard] = DECK[gard]
conc = np.isin(ids, [N2I[n] for n in ('MED', 'PCD', 'LIXO_T')])
from remonta_lib import quilt as _q
CON = _q(kit.esc(kit.LT[1120:1240, 3010:3150], kit.K_LT), (H, W), bloco=64, sobre=16); img[conc] = CON[conc]
passeio = np.zeros((H, W), bool); passeio[2052:, 140:3770] = True; passeio &= ids == 0
sys.path.insert(0, '03_trabalho/conforme_R06'); from remonta_lib import quilt
INT = quilt(kit.INTER, (H - 2040, W), bloco=80, sobre=20); img[2040:][passeio[2040:]] = INT[passeio[2040:]]

# ---------------- paredes pelas fronteiras entre ambientes ----------------
def regra(a, b):
    na, nb, ta, tb = nomes[a], nomes[b], tipos[a], tipos[b]
    if na == nb: return None
    par = {ta, tb}
    num = lambda n: n.lstrip('G')
    if par == {'unidade', 'garden'}: return 'vidro' if num(na) == num(nb) else 'int'
    if 'COBERTA' in (na, nb):
        o = nb if na == 'COBERTA' else na; to = tb if na == 'COBERTA' else ta
        if to in ('loja', 'circ'): return 'vitrine'
        if o in ('COBERTA',) or to == 'fora': return None
        return 'muro'
    if ta in INTER and tb in INTER: return 'int'
    if (ta in INTER and tb == 'fora') or (tb in INTER and ta == 'fora'): return 'ext'
    if (ta in INTER) != (tb in INTER): return 'int'
    return 'muro'

ESP = {'int': 14, 'ext': 20, 'muro': 12}
mw = {k: np.zeros((H, W), bool) for k in ('int', 'ext', 'muro')}
vid = np.zeros((H, W), bool); vit = np.zeros((H, W), bool)
cache = {}
for eixo in (0, 1):
    a = ids[:, :-1] if eixo else ids[:-1]; b = ids[:, 1:] if eixo else ids[1:]
    d = a != b
    ys, xs = np.nonzero(d)
    for y, x in zip(ys, xs):
        ia, ib = int(a[y, x]), int(b[y, x])
        key = (min(ia, ib), max(ia, ib))
        if key not in cache: cache[key] = regra(ia, ib)
        r = cache[key]
        if r is None: continue
        tgt = vid if r == 'vidro' else vit if r == 'vitrine' else mw[r]
        tgt[y, x] = True
for k, m in mw.items():
    r = ESP[k] // 2
    mw[k] = cv2.dilate(m.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_RECT, (2 * r + 1, 2 * r + 1))).astype(bool)
PAREDE = mw['int'] | mw['ext']

# ---------------- portas (vaos na fronteira com a circulacao, pelo R06) ----------------
PORTAS = [  # (x0, y0, x1, y1) no eixo da parede
    (2315, 1437, 2405, 1437), (2552, 1437, 2632, 1437), (2815, 1489, 2905, 1489), (2913, 1385, 2913, 1475),
    (2794, 1255, 2794, 1345), (2914, 945, 2914, 1035), (2815, 927, 2905, 927), (2663, 927, 2743, 927),
    (2223, 927, 2303, 927), (2172, 980, 2172, 1070), (1338, 908, 1338, 998), (1243, 901, 1333, 901),
    (900, 939, 990, 939), (660, 939, 750, 939), (655, 980, 655, 1070),
    (2045, 1285, 2125, 1285),            # area tecnica
    (1202, 1300, 1202, 1390),            # deposito permanente de lixo
]
for (x0, y0, x1, y1) in WCS:
    PORTAS.append((x0 + 45, y1, x0 + 135, y1))   # WC PCD: porta para dentro da loja
coladas = [motor.porta(img, PAREDE, *p) for p in PORTAS]

# nucleo: abertura da escada para o corredor (sul) e portas dos elevadores (norte)
x0, y0, x1, y1 = ESC; PAREDE[y1 - 10:y1 + 10, x0 + 60:x1 - 160] = False
x0, y0, x1, y1 = ELV
for cx in (x0 + (x1 - x0) * 0.25, x0 + (x1 - x0) * 0.75):
    coladas.append(motor.porta(img, PAREDE, cx - 45, y0, cx + 45, y0))

motor.muro(img, mw['muro'] & ~PAREDE)
motor.paredes(img, PAREDE)
for (o, x, y, sp) in coladas: img[y:y + sp.shape[0], x:x + sp.shape[1]] = sp

# vidros: trechos retos da fronteira unidade x garden (horizontais e verticais separados)
def trechos(m, eixo):
    m8 = cv2.dilate(m.astype(np.uint8), np.ones((3, 3), np.uint8))
    k = np.ones((1, 31), np.uint8) if eixo == 'h' else np.ones((31, 1), np.uint8)
    r = cv2.morphologyEx(m8, cv2.MORPH_OPEN, k)
    n, lab, st, _ = cv2.connectedComponentsWithStats(r)
    return [st[i] for i in range(1, n) if st[i, 4] > 30]
for alvo, folga in ((vid, 14), (vit, 10)):
    for (x, y, w, h, _) in trechos(alvo, 'h'): motor.vidro(img, x + folga, y + h / 2, x + w - folga, y + h / 2)
    for (x, y, w, h, _) in trechos(alvo, 'v'): motor.vidro(img, x + w / 2, y + folga, x + w / 2, y + h - folga)


# =============================== MOBILIARIO (layout do interiores na divisa do R06) ===============================
from escadas import escadas
IMG = Quadro((0, 0), (1, 0), (0, 1))     # referencial absoluto: u = x, v = y
motor.OCUPADO = np.zeros((H, W), bool)
Q = Quadro

def tipo_A(q, Wd, Dk, Db, Us, ua=70):
    """Tipologia A do interiores (101, 102, 108, 109, 112, 113, 114) na divisa do R06: escada em Γ junto a parede
    lateral, copa ao lado da porta (fundo, lado da escada), banheiro no canto do fundo oposto, sala junto a parede
    oposta a escada, de frente para o garden."""
    q.objeto(img, kit.cozinha(int(Dk - Us - 8)), Us + 8, 0, '-v', '+u')
    q.objeto(img, kit.BANHO, Db - 197, Wd - 169, '+v', '-u')
    q.objeto(img, kit.SALA, ua, Wd - 213, '+v', '+u', ocupa=False)

tipo_A(Q((2803, 447), (0, 1), (-1, 0)), 320, 480, 480, 373)      # 108
tipo_A(Q((2163, 447), (0, 1), (1, 0)), 320, 470, 480, 373)       # 109
tipo_A(Q((1160, 447), (0, 1), (1, 0)), 335, 492, 445, 373)       # 112
tipo_A(Q((825, 447), (0, 1), (1, 0)), 335, 492, 492, 373)        # 113
tipo_A(Q((825, 447), (0, 1), (-1, 0)), 335, 492, 482, 373)       # 114
tipo_A(Q((2480, 1977), (0, -1), (-1, 0)), 340, 540, 540, 400)    # 101
tipo_A(Q((2480, 1977), (0, -1), (1, 0)), 322, 540, 489, 369)     # 102

def tipo_D(q, Wd):
    """D (104, 106): porta no fundo junto a escada; banheiro no meio da parede oposta, copa no fundo dela."""
    q.objeto(img, kit.cozinha(136), 400, Wd - 57, '+v', '+u')
    q.objeto(img, kit.BANHO, 203, Wd - 169, '+v', '+u')
    q.objeto(img, kit.SALA, 30, Wd - 213, '+v', '+u', ocupa=False)
tipo_D(Q((3458, 1358), (-1, 0), (0, 1)), 331)    # 104
tipo_D(Q((3458, 1083), (-1, 0), (0, -1)), 331)   # 106

q = Q((3458, 1358), (-1, 0), (0, -1))            # 105 (E): vestibulo de entrada a oeste
q.objeto(img, kit.cozinha(150), 407, 0, '-v', '+u')
q.objeto(img, kit.BANHO, 400, 275 - 169, '+v', '+u')
q.objeto(img, kit.SALA, 30, 275 - 213, '+v', '+u', ocupa=False)

q = Q((3458, 752), (-1, 0), (0, -1))             # 107 (C): entrada pelo corredor ao sul do canto oeste
q.objeto(img, kit.cozinha(156), 380, 0, '-v', '+u')
q.objeto(img, kit.BANHO, 458, 305 - 169, '+v', '-u')
q.objeto(img, kit.SALA, 30, 305 - 213, '+v', '+u', ocupa=False)
q.objeto(img, kit.MESA, 240, 305 - 98, '+v', '+u')

q = Q((3458, 1689), (-1, 0), (0, 1))             # 103 (B): entrada pelo corredor ao norte do canto oeste
q.objeto(img, kit.cozinha(159), 377, 0, '-v', '+u')
q.objeto(img, kit.BANHO, 459, 288 - 169, '+v', '-u')
q.objeto(img, kit.SALA, 30, 288 - 213, '+v', '+u', ocupa=False)
q.objeto(img, kit.MESA, 240, 288 - 98, '+v', '+u')

# 115 (G): faixa de baixo = entrada (porta a leste), banheiro a oeste, copa na parede sul
IMG.objeto(img, kit.BANHO, 172, 929, '+v', '+u')
IMG.objeto(img, kit.cozinha(180), 390, 1096 - 57, '+v', '+u')
IMG.objeto(img, kit.SALA, 180, 520, '-u', '+v', ocupa=False)
IMG.objeto(img, kit.MESA, 180, 700, '-u', '+v')

# 110 / 111 (F): banheiro no canto do fundo, copa no corredor de entrada
q = Q((2163, 447), (0, 1), (-1, 0))              # 110
q.objeto(img, kit.BANHO, 557 - 197, 330 - 169, '+v', '-u')
q.objeto(img, kit.SALA, 70, 330 - 213, '+v', '+u', ocupa=False)
q.objeto(img, kit.MESA, 240, 330 - 98, '+v', '+u')
IMG.objeto(img, kit.cozinha(150), 2012, 917, '-v', '+u')
q = Q((1495, 447), (0, 1), (1, 0))               # 111
q.objeto(img, kit.BANHO, 557 - 197, 338 - 169, '+v', '-u')
q.objeto(img, kit.SALA, 70, 338 - 213, '+v', '+u', ocupa=False)
q.objeto(img, kit.MESA, 240, 338 - 98, '+v', '+u')
IMG.objeto(img, kit.cozinha(145), 1345, 892, '-v', '+u')

# escadas das unidades e lojas: pegada do R06
EE = escadas(ids, nomes, tipos)
for nm, m in EE.items():
    ys, xs = np.nonzero(m); r = ids == N2I[nm]; ry, rx = np.nonzero(r)
    eixo = 'y' if (ys.max() - ys.min()) > (xs.max() - xs.min()) else 'x'
    if eixo == 'y':
        sx = -1 if xs.mean() < rx.mean() else 1
        sy = 1 if (nm.startswith('LOJA') or nm in ('101', '102')) else -1
    else:
        sx = 1; sy = -1 if ys.mean() < ry.mean() else 1
    motor.escada(img, m, eixo, (sx, sy)); motor.OCUPADO |= m

# nucleo, area tecnica, servicos
x0, y0, x1, y1 = ESC; img[y0:y0 + kit.ESC_NUCLEO.shape[0], x0:x0 + kit.ESC_NUCLEO.shape[1]] = kit.ESC_NUCLEO[:y1 - y0, :x1 - x0]
x0, y0, x1, y1 = ELV
for xe in (x0 + 6, x0 + (x1 - x0) // 2 + 6):
    e = kit.ELEVADOR; img[y0 + 6:y0 + 6 + e.shape[0], xe:xe + e.shape[1]] = e
img[1093:1093 + kit.ARMARIOS.shape[0], 2008:2008 + kit.ARMARIOS.shape[1]] = kit.ARMARIOS[:, :min(kit.ARMARIOS.shape[1], 2150 - 2008)] if False else img[1093:1093 + kit.ARMARIOS.shape[0], 2008:2008 + kit.ARMARIOS.shape[1]]
a_ = kit.ARMARIOS[:, :140]; img[1092:1092 + a_.shape[0], 2010:2010 + a_.shape[1]] = a_
for x in (700, 810, 920, 1030): img[1102:1182, x:x + 92] = kit.LIXEIRA
for y in (1470, 1580): img[y:y + 92, 560:640] = np.rot90(kit.LIXEIRA)
for (x0, y0, x1, y1) in WCS:
    IMG.objeto(img, kit.PNE_VASO, x0 + 4, y0 + 18, '+u', '+v')
    IMG.objeto(img, kit.PNE_LAV, x1 - 61, y0 + 4, '+u', '+v')
# vaga PCD: faixa hachurada de 1,20 (hachura real do lancamento) e simbolo
H_ = kit.esc(kit.LT[1150:1393, 2922:3004], kit.K_LT); faixa = np.vstack([H_, H_])[:500, 3:123]
img[1540:2040, 424:544] = faixa
sim = kit.recorte(kit.LT, kit.K_LT, 3032, 1252, 3102, 1330, 'borda', tol=20); IMG.objeto(img, sim, 250, 1730, '+u', '+v')
# recepcao: sofa curvo e plantas do lancamento junto a parede oeste
IMG.objeto(img, kit.RECEP, 1832, 1490, '+u', '+v')

# gardens: conjunto de poltronas do lancamento; palmeiras no garden grande
for gx0, gx1 in ((180, 490), (490, 825), (825, 1160), (1160, 1495), (1495, 1833), (1833, 2163), (2163, 2483), (2483, 2803)):
    IMG.objeto(img, kit.GARDEN_SET, (gx0 + gx1) / 2 - 115, 255, '+u', '+v')
IMG.objeto(img, kit.GARDEN_SET, 3020, 190, '+u', '+v')
for yc in (917, 1220, 1523, 1866):
    IMG.objeto(img, kit.GARDEN_SET, 3570, yc - 115, '+v', '-u')
IMG.objeto(img, kit.GARDEN_SET, 3570, 420, '+v', '-u')
for (x, y) in ((3640, 150), (2830, 150)): IMG.objeto(img, kit.PALMEIRA, x, y, '+u', '+v')

# bicicletas nas vagas BR do R06 (bicicleta recortada do lancamento)
for s_, x, y in rotulos():
    if not (s_.startswith('BR ') and s_[3:].isdigit() and 0 < x < W and 0 < y < H): continue
    n = int(s_[3:])
    if n <= 8: IMG.objeto(img, kit.BIKE, x - 29, 150, '+u', '+v')
    else: IMG.objeto(img, kit.BIKE, 3640, y - 29, '+v', '-u')

SEM_TEXTO = img.copy()
# =============================== TEXTOS (letras da propria humanizada de lancamento) ===============================
sys.path.insert(0, '03_trabalho/conforme_R06')
from rotulos_glifos import Fonte
FT = Fonte()
def texto(t, cx, base_y):
    A, b = FT.render(t); A = cv2.resize(A, None, fx=kit.K_LT, fy=kit.K_LT, interpolation=cv2.INTER_CUBIC); b *= kit.K_LT
    A = np.clip(A, 0, 1); h, w = A.shape; x0, y0 = int(round(cx - w / 2)), int(round(base_y - b))
    reg = img[y0:y0 + h, x0:x0 + w].astype(np.float32); al = A[:reg.shape[0], :reg.shape[1], None]
    img[y0:y0 + h, x0:x0 + w] = (reg * (1 - al)).astype(np.uint8)
def rotulo(l1, l2, cx, cy):
    if l2: texto(l1, cx, cy - 6); texto(l2, cx, cy - 6 + 47)
    else: texto(l1, cx, cy + 15)
AREA = {'101': '18,40', '102': '16,66', '103': '21,33', '104': '17,84', '105': '18,84', '106': '17,86', '107': '22,10',
        '108': '15,36', '109': '15,36', '110': '19,89', '111': '20,59', '112': '15,35', '113': '16,48', '114': '16,32', '115': '23,24'}
LIVRE = ~(motor.OCUPADO | cv2.dilate(PAREDE.astype(np.uint8), np.ones((25, 25), np.uint8)).astype(bool))
def acha_lugar(regiao, alvo, w=200, h=90):
    """Centro do retangulo w x h, todo em piso livre dentro da regiao, mais perto do alvo."""
    regiao = cv2.erode(regiao.astype(np.uint8), np.ones((41, 41), np.uint8)).astype(bool)
    ok = (LIVRE & regiao).astype(np.float32)
    k = np.ones((h, w), np.float32)
    cheio = cv2.filter2D(ok, -1, k / k.sum(), borderType=cv2.BORDER_CONSTANT) > 0.999
    ys, xs = np.nonzero(cheio)
    if not len(xs): return alvo
    i = int(np.argmin((xs - alvo[0]) ** 2 + (ys - alvo[1]) ** 2)); return (int(xs[i]), int(ys[i]))
for u in AREA:
    r = ids == N2I[u]; ry, rx = np.nonzero(r)
    x, y = acha_lugar(r, (rx.mean(), ry.mean()))
    rotulo('UN ' + u, AREA[u] + ' m²', x, y)
GA = {'115': '9,31', '114': '10,18', '113': '10,27', '112': '10,36', '111': '10,54', '110': '10,38', '109': '10,17', '108': '10,24'}
for (gx0, gx1), u in zip(((180, 490), (490, 825), (825, 1160), (1160, 1495), (1495, 1833), (1833, 2163), (2163, 2483), (2483, 2803)),
                         ('115', '114', '113', '112', '111', '110', '109', '108')):
    rotulo('Garden', GA[u] + ' m²', (gx0 + gx1) / 2, 195)
rotulo('Garden', '41,08 m²', 3330, 195)
for u, a in (('106', '10,22'), ('105', '8,44'), ('104', '10,04'), ('103', '15,19')):
    r = np.isin(ids, [k for k, v in nomes.items() if v == 'G' + u]) & (np.arange(W)[None, :] > 3520); ry, rx = np.nonzero(r); x, y = acha_lugar(r, (rx.mean(), ry.mean()), 190, 90); rotulo('Garden', a + ' m²', x, y)
texto('Garden 2,43 m²', 2310, 2030); texto('Garden 2,26 m²', 2641, 2030)
for nm, a, x in (('Loja 01', '20,07', 1060), ('Loja 02', '19,26', 1390), ('Loja 03', '19,26', 1600)):
    rotulo(nm, a + ' m²', x, 1800)
for (x0, y0, x1, y1) in WCS: texto('PNE', (x0 + x1) / 2 + 20, y1 - 30)
x_, y_ = acha_lugar(np.isin(ids, [N2I['CIRC']]) & (np.arange(W)[None, :] > 1822) & (np.arange(H)[:, None] > 1440), (1990, 1700), 260, 60); texto('Recepção', x_, y_ + 15); texto('Medidores', 330, 1320); texto('Lixeiras', 940, 1300); texto('Lixeiras', 690, 1780)

cv2.imwrite(saida.replace('.png', '_SEM-TEXTO.png'), SEM_TEXTO)
np.save(os.path.splitext(saida)[0] + '_ids.npy', ids)
json.dump({str(k): v for k, v in nomes.items()}, open(os.path.splitext(saida)[0] + '_nomes.json', 'w'))
cv2.imwrite(saida, img)
print('ok', saida)
