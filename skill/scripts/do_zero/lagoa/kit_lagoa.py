"""Kit de texturas REAIS da humanizada de lancamento do Lagoa Spot (terreo R00, 0,4022 cm/px = escala da planta nova).
Cada recorte foi escolhido em area limpa (sem objeto, texto ou sombra)."""
import os, numpy as np
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
AQUI = os.path.dirname(os.path.abspath(__file__))
LANC = os.path.join(AQUI, '../../00_entradas/originais/humanizada_lancamento/LAGOASPOT-AP-ARQ-IMG-TER-000-R00.png')
_L = None
def lanc():
    global _L
    if _L is None: _L = np.array(Image.open(LANC).convert('RGBA'))
    return _L
def rc(x0, y0, x1, y1): return lanc()[y0:y1, x0:x1, :3].copy()

def madeira(): return rc(1453, 2001, 1588, 2215)          # regua de madeira (Aloj 10), sem moveis
def porcelanato(): return rc(3326, 1524, 3774, 1972)      # 2 x 2 placas 90 x 90 (circulacao), cortado nas juntas
def asfalto(): return rc(5000, 250, 6000, 750)            # piso do estacionamento
def grama(): return rc(7520, 1120, 7760, 1460)            # garden do Aloj 04 (sem texto)
PERIODO_PORC = 224                                         # 90 cm

# reguas reais (45 px = 18 cm de largura), recortadas entre juntas de trechos limpos do assoalho do lancamento
PASSO_REGUA = 45
TRECHOS_REGUA = [  # (x0, y0, largura, altura, juntas x relativas ja conferidas)
    (1365, 1747, 267, 521, [44, 90, 135, 180]), (4731, 2932, 277, 851, [44, 89, 131]),
    (1590, 1780, 310, 496, [45, 89, 131, 175, 226]), (4595, 1323, 147, 715, [46, 93]),
    (6077, 1568, 277, 431, [131, 175]), (6839, 1706, 177, 641, [46, 94]), (1903, 1780, 177, 399, [46, 91]),
    (5941, 1760, 147, 306, [46, 91]), (6839, 2651, 134, 561, [46, 91]), (1590, 2493, 92, 226, [46, 89]),
    (4595, 2006, 133, 179, [47, 92]), (7275, 1156, 151, 783, [58, 103]), (6092, 3348, 224, 477, [116, 160]),
]
def reguas():
    """Trechos de regua 100% madeira: cada linha do trecho tem de ser madeira (cor) e sem traco escuro."""
    L = lanc()[..., :3]; out = []
    for x0, y0, w, h, js in TRECHOS_REGUA:
        for a, b in zip(js, js[1:]):
            if not 40 <= b - a <= 50: continue
            st = L[y0:y0 + h, x0 + a:x0 + b].astype(np.int16)
            R, G, B = st[..., 0], st[..., 1], st[..., 2]; lum = st.mean(2)
            ok_px = (R - B > 22) & (R - B < 80) & (lum > 95) & (lum < 190) & (G >= B)
            ok_lin = ok_px[:, 3:-3].mean(axis=1) > 0.995
            y = 0
            while y < h:
                if ok_lin[y]:
                    r = y
                    while r < h and ok_lin[r]: r += 1
                    if r - y >= 150: out.append(cv2_resize(L[y0 + y:y0 + r, x0 + a:x0 + b], PASSO_REGUA))
                    y = r
                else: y += 1
    return out
def cv2_resize(strip, w):
    import cv2
    return cv2.resize(strip, (w, strip.shape[0]), interpolation=cv2.INTER_AREA)
def assoalho(H, W, seed=3):
    """Assoalho de reguas verticais: cada coluna empilha trechos reais de regua (comprimento 0,6-1,6 m) com emenda de
    topo escurecida, como no lancamento."""
    rng = np.random.default_rng(seed); R = reguas(); out = np.zeros((H, W, 3), np.uint8)
    for x in range(0, W, PASSO_REGUA):
        y = -int(rng.integers(0, 300))
        while y < H:
            s = R[int(rng.integers(len(R)))]; h = s.shape[0]
            L = int(min(h, rng.integers(150, 400)))
            s0 = int(rng.integers(0, h - L + 1)); seg = s[s0:s0 + L].copy()
            seg[:2] = (seg[:2] * 0.72).astype(np.uint8)          # emenda de topo
            a, b = max(y, 0), min(y + L, H)
            if b > a: out[a:b, x:x + PASSO_REGUA] = seg[a - y:b - y, :min(PASSO_REGUA, W - x)]
            y += L
        out[:, x:x + 1] = (out[:, x:x + 1] * 0.8).astype(np.uint8)   # junta lateral
    return out
