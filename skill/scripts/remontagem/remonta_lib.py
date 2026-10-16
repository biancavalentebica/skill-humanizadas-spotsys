"""Ferramentas para remontar a humanizada de lancamento sobre a geometria do aprovado, so com pixels da propria imagem.

- piso_*: preenche uma mascara com placas reais recortadas da imagem, alinhadas a paginacao original (grade).
- quilt: preenche com blocos reais de uma textura (deck, intertravado, concreto), costurados pelo caminho de menor erro.
- paredes: desenha paredes a partir de uma mascara com o perfil real das paredes da imagem (miolo, filete escuro,
  filete branco e sombra medidos numa parede do lancamento).
- cola: copia um elemento real (recorte retangular ou com mascara), com espelho/rotacao de 90 graus, borda suave.
"""
import cv2, numpy as np

RNG = np.random.default_rng(7)


def carrega(caminho):
    im = cv2.imread(caminho, cv2.IMREAD_UNCHANGED)
    if im.shape[2] == 4:
        al = im[:, :, 3:4] / 255.0
        im = (im[:, :, :3] * al + 255 * (1 - al)).astype(np.uint8)
    return im


# ---------- piso em placas (grade) ----------
class Placas:
    """Placas reais de uma paginacao com periodo P (px) e origem (ox, oy) de uma linha de junta."""

    def __init__(self, img, P, ox, oy, celulas, Py=None):
        self.P, self.Py, self.ox, self.oy = P, Py or P, ox, oy
        self.amostras = []
        for (i, j) in celulas:  # indices de celula (coluna, linha) relativos a origem
            x0 = int(round(ox + i * self.P)); y0 = int(round(oy + j * self.Py))
            self.amostras.append(img[y0:y0 + int(np.ceil(self.Py)) + 1, x0:x0 + int(np.ceil(self.P)) + 1].copy())

    def pinta(self, canvas, mascara, ox=None, oy=None):
        ox = self.ox if ox is None else ox; oy = self.oy if oy is None else oy
        ys, xs = np.nonzero(mascara)
        if len(xs) == 0: return
        ci = np.floor((xs - ox) / self.P).astype(int); cj = np.floor((ys - oy) / self.Py).astype(int)
        u = np.clip(np.round(xs - ox - ci * self.P).astype(int), 0, None); v = np.clip(np.round(ys - oy - cj * self.Py).astype(int), 0, None)
        h = (ci * 73856093 ^ cj * 19349663) % len(self.amostras)
        for k, a in enumerate(self.amostras):
            s = h == k
            uu = np.clip(u[s], 0, a.shape[1] - 1); vv = np.clip(v[s], 0, a.shape[0] - 1)
            canvas[ys[s], xs[s]] = a[vv, uu]


# ---------- quilting ----------
def quilt(fonte, alvo_hw, bloco=64, sobre=16, tentativas=60):
    """Sintese por blocos reais da fonte (Efros-Freeman)."""
    H, W = alvo_hw; fh, fw = fonte.shape[:2]; passo = bloco - sobre
    out = np.zeros((H + bloco, W + bloco, 3), np.uint8)
    for y in range(0, H, passo):
        for x in range(0, W, passo):
            melhor = None
            for _ in range(tentativas):
                sy = RNG.integers(0, fh - bloco); sx = RNG.integers(0, fw - bloco)
                cand = fonte[sy:sy + bloco, sx:sx + bloco].astype(int)
                e = 0
                if x > 0: e += ((cand[:, :sobre] - out[y:y + bloco, x:x + sobre]) ** 2).sum()
                if y > 0: e += ((cand[:sobre] - out[y:y + sobre, x:x + bloco]) ** 2).sum()
                if melhor is None or e < melhor[0]: melhor = (e, cand)
            c = melhor[1].astype(np.uint8)
            m = np.ones((bloco, bloco), bool)
            if x > 0:  # corte vertical de menor erro
                err = ((c[:, :sobre].astype(int) - out[y:y + bloco, x:x + sobre]) ** 2).sum(2)
                caminho = _corte(err)
                for r in range(bloco): m[r, :caminho[r]] = False
            if y > 0:
                err = ((c[:sobre].astype(int) - out[y:y + sobre, x:x + bloco]) ** 2).sum(2).T
                caminho = _corte(err)
                for col in range(bloco): m[:caminho[col], col] = False
            reg = out[y:y + bloco, x:x + bloco]; reg[m] = c[m]
    return out[:H, :W]


def _corte(err):
    n, w = err.shape; E = err.astype(float).copy()
    for i in range(1, n):
        for j in range(w):
            E[i, j] += E[i - 1, max(0, j - 1):min(w, j + 2)].min()
    caminho = [int(np.argmin(E[-1]))]
    for i in range(n - 2, -1, -1):
        j = caminho[-1]; lo = max(0, j - 1); caminho.append(lo + int(np.argmin(E[i, lo:min(w, j + 2)])))
    return caminho[::-1]


def pinta_quilt(canvas, mascara, fonte, **kw):
    ys, xs = np.nonzero(mascara)
    if len(xs) == 0: return
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    t = quilt(fonte, (y1 - y0, x1 - x0), **kw)
    sub = mascara[y0:y1, x0:x1]
    canvas[y0:y1, x0:x1][sub] = t[sub]


def pinta_faixa_repetida(canvas, mascara, fonte, eixo):
    """Repete uma faixa real (ex.: tabua de deck) ao longo de um eixo, com fase continua."""
    ys, xs = np.nonzero(mascara)
    fh, fw = fonte.shape[:2]
    if eixo == 'x':
        canvas[ys, xs] = fonte[ys % fh, xs % fw]
    else:
        canvas[ys, xs] = fonte[ys % fh, xs % fw]


# ---------- paredes ----------
PERFIL = dict(miolo=None, borda=(57, 58, 57), filete=(245, 246, 245), trans=(150, 152, 150), sombra=0.86)


def paredes(canvas, mascara, miolo_fonte):
    """Renderiza paredes com o perfil real: miolo (textura real repetida), filete escuro interno, filete branco e sombra."""
    m = mascara.astype(np.uint8)
    din = cv2.distanceTransform(m, cv2.DIST_L2, 3)
    dout = cv2.distanceTransform(1 - m, cv2.DIST_L2, 3)
    ys, xs = np.nonzero(m)
    fh, fw = miolo_fonte.shape[:2]
    canvas[ys, xs] = miolo_fonte[ys % fh, xs % fw]
    canvas[(m > 0) & (din <= 1.0)] = PERFIL['borda']
    anel1 = (m == 0) & (dout <= 1.0); anel2 = (m == 0) & (dout > 1.0) & (dout <= 2.2); anel3 = (m == 0) & (dout > 2.2) & (dout <= 4.5)
    canvas[anel1] = PERFIL['trans']; canvas[anel2] = PERFIL['filete']
    canvas[anel3] = (canvas[anel3] * PERFIL['sombra']).astype(np.uint8)


def retangulo(mascara, x0, y0, x1, y1, val=True):
    mascara[int(round(min(y0, y1))):int(round(max(y0, y1))), int(round(min(x0, x1))):int(round(max(x0, x1)))] = val


def parede_seg(mascara, x0, y0, x1, y1, esp):
    """Parede centrada no segmento (horizontal ou vertical)."""
    h = esp / 2
    if abs(y1 - y0) < abs(x1 - x0):
        retangulo(mascara, min(x0, x1) - h, y0 - h, max(x0, x1) + h, y0 + h)
    else:
        retangulo(mascara, x0 - h, min(y0, y1) - h, x0 + h, max(y0, y1) + h)


# ---------- colar elementos ----------
def cola(canvas, fonte, src, dst, flip=None, rot=0, mascara=None, borda=0):
    """src=(x0,y0,x1,y1) na fonte; dst=(x,y) canto superior esquerdo. flip: 'h'|'v'; rot: k*90 graus (anti-horario)."""
    x0, y0, x1, y1 = src
    p = fonte[y0:y1, x0:x1].copy(); mk = None if mascara is None else mascara[y0:y1, x0:x1].copy()
    if flip == 'h': p = p[:, ::-1]; mk = None if mk is None else mk[:, ::-1]
    if flip == 'v': p = p[::-1]; mk = None if mk is None else mk[::-1]
    if rot:
        p = np.rot90(p, rot); mk = None if mk is None else np.rot90(mk, rot)
    h, w = p.shape[:2]; X, Y = int(dst[0]), int(dst[1])
    a = np.ones((h, w), float) if mk is None else mk.astype(float)
    if borda:
        a = cv2.GaussianBlur((a > 0).astype(np.float32), (0, 0), borda) * (a > 0) if mk is not None else _rampa(h, w, borda)
    reg = canvas[Y:Y + h, X:X + w]
    a = a[:reg.shape[0], :reg.shape[1], None]
    reg[:] = (p[:reg.shape[0], :reg.shape[1]] * a + reg * (1 - a)).astype(np.uint8)


def _rampa(h, w, b):
    yy = np.minimum(np.arange(h), np.arange(h)[::-1])[:, None]; xx = np.minimum(np.arange(w), np.arange(w)[::-1])[None, :]
    return np.clip(np.minimum(yy, xx) / b, 0, 1)
