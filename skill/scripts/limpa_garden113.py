"""Garden 113 (terreo Batel Spot): o rotulo cruza deck | grama entre duas cadeiras, e o preenchimento letra a letra
deixa contorno. Aqui o trecho e refeito em dois retangulos reais: deck (tabuas do deck da garden 114, alinhadas
pixel a pixel as tabuas da 113 e com o tom do entorno) e grama (grama da propria 113). Bordas suaves.

Uso: py limpa_garden113.py <imagem_com_texto.png> <imagem_destino.png> [--dx 0 --dy 0]
  Le o rotulo na <imagem_com_texto>, grava o trecho limpo dentro de <imagem_destino> (sobrescreve).
"""
import argparse
import numpy as np, cv2
from PIL import Image
Image.MAX_IMAGE_PIXELS = None

ap = argparse.ArgumentParser()
ap.add_argument('fonte'); ap.add_argument('destino')
ap.add_argument('--dx', type=int, default=0); ap.add_argument('--dy', type=int, default=0)
a = ap.parse_args()
F = np.array(Image.open(a.fonte).convert('RGB')).astype(np.float32)
D = np.array(Image.open(a.destino).convert('RGB')).astype(np.float32)
DX, DY = a.dx, a.dy
def R(x0, y0, x1, y1): return slice(y0 + DY, y1 + DY), slice(x0 + DX, x1 + DX)

LIM = 11065                                                                      # deck | grama
# 1) deck: retangulo x 10776..LIM, y 3242..3426
TX0, TY0, TX1, TY1 = 10776, 3242, LIM + 3, 3426
tw, th = TX1 - TX0, TY1 - TY0
borda_esq = F[R(TX0 - 14, TY0 + 20, TX0, TY1 - 20)].mean(2)                    # tabuas logo a esquerda (sem texto)
alvo_cols = (borda_esq - borda_esq.mean(1, keepdims=True)).mean(0)              # perfil das tabuas
best, bs = None, np.inf
for (ya, yb) in ((3560, 3800), (3990, 3990), (4120, 4520)):                     # deck da 114 longe do rotulo e da mureta
    for sy in range(ya, yb - th + 1, 8):
        for sx in range(7030, 7395 - tw + 1):                               # longe das bordas do deck 114
            fx = F[R(sx - 14, sy + 20, sx, sy + th - 20)].mean(2)
            if fx.size == 0: continue
            pc = (fx - fx.mean(1, keepdims=True)).mean(0)
            e = ((pc - alvo_cols) ** 2).mean() + 0.02 * F[R(sx, sy, sx + tw, sy + th)].mean(2).std()
            if e < bs: bs, best = e, (sx, sy)
sx, sy = best
print('deck de', best)
deck = F[R(sx, sy, sx + tw, sy + th)].copy()
anel_t = np.concatenate([F[R(10965, 3226, LIM - 4, TY0 - 2)].reshape(-1, 3),     # deck livre de cadeira, texto e sombra
                         F[R(11030, TY1 + 2, LIM - 4, TY1 + 12)].reshape(-1, 3)])
anel_s = deck.reshape(-1, 3)
deck *= (anel_t.mean(0) / np.maximum(anel_s.mean(0), 1))[None, None]
# variacao vertical de luz do proprio deck 113 (coluna a esquerda do rotulo), aplicada ao recorte
luz = cv2.GaussianBlur(F[R(TX0 - 30, TY0, TX0 - 6, TY1)].mean((1, 2)).astype(np.float32)[:, None], (0, 0), 12)[:, 0]
luz = luz / luz.mean()
deck *= luz[:, None, None]
m = np.zeros((th, tw), np.float32); m[:, :] = 1
m = cv2.GaussianBlur(np.pad(m, 0), (0, 0), 1)
fy = np.minimum(np.minimum(np.arange(th) / 10.0, (th - 1 - np.arange(th)) / 10.0), 1)[:, None]
fx = np.minimum(np.arange(tw) / 8.0, 1)[None]
m = fy * fx
D[R(TX0, TY0, TX1, TY1)] = D[R(TX0, TY0, TX1, TY1)] * (1 - m[..., None]) + deck * m[..., None]

# 2) grama: retangulo LIM..11190, mesma altura, com grama da propria garden 113 (abaixo/acima do rotulo)
GX0, GX1 = LIM - 1, 11205
TY0 -= 10                                                                        # grama: pega tambem o topo do N
gw = GX1 - GX0
best, bs = None, np.inf
th = TY1 - TY0
fy = np.minimum(np.minimum(np.arange(th) / 8.0, (th - 1 - np.arange(th)) / 10.0), 1)[:, None]
for sy in list(range(3460, 3700 - th, 6)) + list(range(2950, 3240 - th, 6)):
    for sx in range(LIM + 20, 11240 - gw, 4):
        src = F[R(sx, sy, sx + gw, sy + th)]
        if src.mean(2).max() > 215 or src.mean(2).min() < 25: continue          # sem divisa branca nem sombra dura
        e = abs(src.mean() - F[R(GX0 + 6, TY0 - 20, GX1, TY0)].mean()) + 0.5 * abs(src[..., 1].mean() - src[..., 0].mean() - 30)
        if e < bs: bs, best = e, (sx, sy)
sx, sy = best
gr = F[R(sx, sy, sx + gw, sy + th)].copy()
viz = np.concatenate([F[R(GX0 + 10, TY0 - 30, GX1, TY0)].reshape(-1, 3), F[R(GX0 + 10, TY1, GX1, TY1 + 30)].reshape(-1, 3)])
gr *= (viz.mean(0) / np.maximum(gr.reshape(-1, 3).mean(0), 1))[None, None]       # mesmo tom da grama em volta
fx = np.minimum((gw - 1 - np.arange(gw)) / 22.0, 1)[None]                   # divisa deck|grama: emenda seca
mg = fy * fx
D[R(GX0, TY0, GX1, TY1)] = D[R(GX0, TY0, GX1, TY1)] * (1 - mg[..., None]) + gr * mg[..., None]

Image.fromarray(np.clip(D, 0, 255).astype(np.uint8)).save(a.destino)
print('ok', a.destino, 'grama de', best)
