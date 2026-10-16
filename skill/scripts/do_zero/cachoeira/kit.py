"""Kit de objetos e texturas REAIS da humanizada de lancamento do Cachoeira Spot, na escala da planta nova (1 cm/px).

Fontes (sem texto, remove_texto.py):
  L2 = 2o pavimento do lancamento (0,98 cm/px): sala (sofa + tapete + puff + mesinha), banheiro, cozinha, mesa, porta, palmeira
  LT = terreo do lancamento (1,535 cm/px): escada (degraus e leque), vidro do garden, conjunto do garden, planta, deck, intertravado
  ES = skill/estilo/lancamento (0,98 cm/px): pecas de porcelanato, deck, elevador, lixeira, poltrona
Cada objeto entra no tamanho real (escala da fonte -> 1 cm/px), nunca esticado para caber.
"""
import glob, os
import cv2, numpy as np

CM = 1.0
L2 = cv2.imread('03_trabalho/lancamento_sem_texto/PAV-02.png')
LT = cv2.imread('03_trabalho/lancamento_sem_texto/PAV-01.png')
ES = 'skill/estilo/lancamento'
K_L2, K_LT = 0.98 / CM, 1.535 / CM


def esc(img, k, interp=None):
    if abs(k - 1) < 0.03: return img.copy()
    return cv2.resize(img, None, fx=k, fy=k, interpolation=interp or (cv2.INTER_CUBIC if k > 1 else cv2.INTER_AREA))


def alfa_borda(sp, tol=14, fecha=5, suave=1.0):
    """Fundo = regiao ligada a borda com cor parecida com a da borda (piso liso em volta do objeto)."""
    g = cv2.GaussianBlur(sp, (0, 0), 1.2).astype(np.float32)
    h, w = g.shape[:2]
    borda = np.concatenate([g[0], g[-1], g[:, 0], g[:, -1]])
    ref = np.median(borda, 0)
    perto = (np.abs(g - ref).max(2) < tol).astype(np.uint8)
    n, lab = cv2.connectedComponents(perto)
    ids = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
    fundo = np.isin(lab, list(ids))
    fg = (~fundo).astype(np.uint8)
    fg = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, np.ones((fecha, fecha), np.uint8))
    return cv2.GaussianBlur(fg.astype(np.float32), (0, 0), suave)


def alfa_verde(sp):
    hsv = cv2.cvtColor(sp, cv2.COLOR_BGR2HSV)
    m = ((hsv[:, :, 0] > 25) & (hsv[:, :, 0] < 95) & (hsv[:, :, 1] > 45)).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(m)
    k = 1 + int(np.argmax(st[1:, 4])); m = (lab == k).astype(np.uint8)
    return cv2.GaussianBlur(m.astype(np.float32), (0, 0), 0.8)


class Sprite:
    def __init__(self, img, alfa=None):
        self.img = img; self.alfa = np.ones(img.shape[:2], np.float32) if alfa is None else alfa

    def girado(self, rot=0, espelho=False):
        im, a = self.img, self.alfa
        if espelho: im, a = im[:, ::-1], a[:, ::-1]
        if rot: im, a = np.rot90(im, rot), np.rot90(a, rot)
        return Sprite(np.ascontiguousarray(im), np.ascontiguousarray(a))


def recorte(src, k, x0, y0, x1, y1, alfa=None, **kw):
    sp = esc(src[y0:y1, x0:x1], k)
    a = None
    if alfa == 'borda': a = alfa_borda(sp, **kw)
    elif alfa == 'verde': a = alfa_verde(sp)
    return Sprite(sp, a)


SALA = recorte(L2, K_L2, 1700, 418, 1913, 568)                           # sofa encostado a direita, de frente para a esquerda
_m = np.zeros(SALA.img.shape[:2], np.uint8)
cv2.circle(_m, (int(72 * K_L2), int(77 * K_L2)), int(76 * K_L2), 1, -1)                  # tapete redondo
_m[int(5 * K_L2):int(150 * K_L2), int(124 * K_L2):] = 1                                   # sofa
SALA.alfa = cv2.GaussianBlur(_m.astype(np.float32), (0, 0), 1.0)
BANHO = recorte(L2, K_L2, 1063, 404, 1232, 601)                          # banheiro com paredes: cuba e chuveiro em cima, porta e vaso embaixo
COZ_COOKTOP = recorte(L2, K_L2, 827, 452, 885, 508)                      # granito com cooktop (fundo da bancada a direita)
COZ_PIA = recorte(L2, K_L2, 827, 522, 885, 592)                          # granito com cuba
COZ_GRANITO = recorte(L2, K_L2, 827, 408, 885, 450)
MESA = recorte(L2, K_L2, 786, 192, 884, 300)            # bancada de madeira com 2 cadeiras a esquerda
_a = alfa_borda(MESA.img, tol=7); _a[:, int(49 * K_L2):] = 1; MESA.alfa = _a
PORTA = recorte(L2, K_L2, 972, 596, 1062, 618)                            # vao de porta com batente e folha (horizontal)
PALMEIRA = recorte(L2, K_L2, 3525, 1740, 3660, 1866, 'verde')
PLANTA = recorte(LT, K_LT, 804, 290, 868, 350, 'verde')
GARDEN_SET = recorte(LT, K_LT, 1245, 150, 1395, 258)   # 2 poltronas + mesinha (deck sai na mascara)
def _alfa_moveis_deck(sp):
    f = sp.astype(np.int32); lum = f.mean(2)
    m = ((lum > 165) | ((f[:, :, 2] - f[:, :, 0] > 30) & (lum > 120) & (f[:, :, 1] > 100))).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)); m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(m)
    m = np.isin(lab, [i for i in range(1, n) if st[i, 4] > 300]).astype(np.uint8)
    for i in range(1, n):
        if st[i, 4] > 300:   # preenche buracos de cada peca
            c = (lab == i).astype(np.uint8); cs, _ = cv2.findContours(c, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE); cv2.drawContours(m, cs, -1, 1, -1)
    return cv2.GaussianBlur(m.astype(np.float32), (0, 0), 1.0)
GARDEN_SET.alfa = _alfa_moveis_deck(GARDEN_SET.img)
# escada (terreo do lancamento): degraus do lance lateral (espelhos horizontais), leque do canto
DEGRAU = esc(LT[343:357, 1228:1267], K_LT)        # um degrau, comprimento na horizontal
LEQUE = esc(LT[294:340, 1226:1271], K_LT)         # leque com o canto no topo-esquerda (garden em cima, parede lateral a esquerda)
VIDRO = esc(LT[283:293, 1240:1420], K_LT)         # caixilho do garden (horizontal)
DECK = esc(LT[1325:1450, 900:1640], K_LT)         # deck da frente das lojas no lancamento (tabuas horizontais, sem moveis)
INTER = esc(LT[1415:1570, 2585:2915], K_LT)       # intertravado do passeio
CONCRETO = cv2.imread(os.path.join(ES, 'externo.png'))
MIOLO = esc(LT[1060:1290, 1199:1207], K_LT)
ELEVADOR = cv2.imread(os.path.join(ES, 'objetos', 'elevador.png'))
LIXEIRA = cv2.imread(os.path.join(ES, 'objetos', 'lixeira.png'))


def pecas_porcelanato(T=115):
    fs = sorted(glob.glob(os.path.join(ES, 'porcelanato_pecas', '*.png')))
    pcs = [cv2.imread(f) for f in fs]
    suav = [float(cv2.GaussianBlur(cv2.cvtColor(q, cv2.COLOR_BGR2GRAY).astype(np.float32), (0, 0), 12).std()) for q in pcs]
    pcs = [q for q, v in sorted(zip(pcs, suav), key=lambda t: t[1])][:4]
    out = []
    for q in pcs:
        f_ = q.astype(np.float32); lz = cv2.GaussianBlur(f_, (0, 0), 9)
        q = np.clip(f_ - lz + lz.reshape(-1, 3).mean(0), 0, 255).astype(np.uint8)
        out.append(cv2.resize(q, (T, T), interpolation=cv2.INTER_AREA))
    return out


def piso_porcelanato(H, W, T=115, ox=0, oy=0, semente=3):
    pcs = pecas_porcelanato(T); rg = np.random.default_rng(semente)
    nH, nW = (H // T + 3) * T, (W // T + 3) * T
    out = np.empty((nH, nW, 3), np.uint8)
    for yy in range(0, nH, T):
        for xx in range(0, nW, T):
            q = pcs[rg.integers(len(pcs))]
            if rg.random() < 0.5: q = q[:, ::-1]
            if rg.random() < 0.5: q = q[::-1]
            out[yy:yy + T, xx:xx + T] = q
    return out[T - oy % T:T - oy % T + H, T - ox % T:T - ox % T + W]


def ladrilha(tex, H, W, sentido_v=False):
    t = np.rot90(tex) if sentido_v else tex
    reps = (H // t.shape[0] + 2, W // t.shape[1] + 2, 1)
    return np.tile(t, reps)[:H, :W]

# cozinha compacta: pedacos reais da bancada do lancamento (cooktop, cuba e granito), costas da bancada a direita
COZ_TOP = esc(L2[452:493, 829:885], K_L2)
COZ_CUBA = esc(L2[524:573, 829:885], K_L2)
COZ_GRAN = esc(L2[494:523, 829:885], K_L2)


def cozinha(L):
    """Bancada de comprimento L (cm) no sentido das linhas: cooktop perto do inicio, cuba perto do fim."""
    w = COZ_TOP.shape[1]; out = np.tile(COZ_GRAN, (L // COZ_GRAN.shape[0] + 2, 1, 1))[:L].copy()
    a, b = COZ_TOP.shape[0], COZ_CUBA.shape[0]
    y1 = max(4, int(L * 0.08)); out[y1:y1 + a] = COZ_TOP
    y2 = L - b - max(4, int(L * 0.06)); out[y2:y2 + b] = COZ_CUBA
    return Sprite(out)


PNE_VASO = recorte(LT, K_LT, 1287, 937, 1346, 988)
PNE_LAV = recorte(LT, K_LT, 1398, 884, 1435, 941)
ESC_NUCLEO = esc(LT[712:897, 1558:2002], K_LT)
ARMARIOS = esc(LT[712:836, 2052:2152], K_LT)
RECEP = recorte(LT, K_LT, 1832, 975, 1931, 1300)
BIKE = Sprite(cv2.imread(os.path.join(ES, 'objetos', 'bicicleta.png')), np.load(os.path.join(ES, 'objetos', 'bicicleta_alfa.npy')).astype(np.float32))
