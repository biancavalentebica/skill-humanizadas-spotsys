"""Funcoes comuns: carregar planta, frame de trabalho (2000 px), rotacao exata e mascaras.

Coordenadas do config.json sempre no FRAME DE TRABALHO: a planta reduzida para 2000 px
de largura. Frame "o" = planta original (sem girar). Frame "r" = planta girada pelo
`angulo` do config (para alinhar alas inclinadas com os eixos).
"""
import json, numpy as np, cv2
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
WORK_W = 2000


def carregar(caminho):
    """Retorna (rgb_full com fundo branco, alpha_full)."""
    im = Image.open(caminho)
    if im.mode != 'RGBA':
        im = im.convert('RGBA')
    alpha = np.array(im)[..., 3]
    bg = Image.new('RGBA', im.size, (255, 255, 255, 255))
    bg.alpha_composite(im)
    return np.array(bg.convert('RGB')), alpha


def trabalho(rgb):
    """Reduz para o frame de trabalho. Retorna (img_trabalho, fator full/trabalho)."""
    H, W = rgb.shape[:2]
    f = W / WORK_W
    small = cv2.resize(rgb, (WORK_W, round(H / f)), interpolation=cv2.INTER_AREA)
    return small, f


def matriz_rot(W, H, angulo):
    """Matriz afim 2x3 (cv2) que gira uma imagem WxH por `angulo` graus
    (negativo = horario) expandindo a tela. Retorna (M, novo_W, novo_H)."""
    c = (W / 2, H / 2)
    M = cv2.getRotationMatrix2D(c, angulo, 1.0)
    cos, sin = abs(M[0, 0]), abs(M[0, 1])
    nW, nH = int(round(H * sin + W * cos)), int(round(H * cos + W * sin))
    M[0, 2] += nW / 2 - c[0]
    M[1, 2] += nH / 2 - c[1]
    return M, nW, nH


def girar(img, angulo, borda=255):
    H, W = img.shape[:2]
    M, nW, nH = matriz_rot(W, H, angulo)
    flags = cv2.INTER_CUBIC if img.ndim == 3 else cv2.INTER_NEAREST
    bv = (borda,) * 3 if img.ndim == 3 else borda
    return cv2.warpAffine(img, M, (nW, nH), flags=flags, borderValue=bv), M


def r2o(pts, angulo, Wt, Ht):
    """Pontos do frame girado (trabalho) -> frame original (trabalho)."""
    M, _, _ = matriz_rot(Wt, Ht, angulo)
    Mi = cv2.invertAffineTransform(M)
    p = np.array(pts, float)
    return p @ Mi[:, :2].T + Mi[:, 2]


def pontos_o(poli, angulo, Wt, Ht):
    pts = poli['pts']
    return r2o(pts, angulo, Wt, Ht) if poli.get('frame', 'o') == 'r' else np.array(pts, float)


def mascara_unidade(un, angulo, Wt, Ht, shape, f):
    """Mascara (uint8 0/255) no tamanho `shape` (full ou trabalho, conforme f)."""
    m = np.zeros(shape[:2], np.uint8)
    for poli in un['poligonos']:
        p = pontos_o(poli, angulo, Wt, Ht) * f
        cv2.fillPoly(m, [np.round(p).astype(np.int32)], 255)
    return m


def ler_config(caminho):
    with open(caminho, encoding='utf-8') as fh:
        return json.load(fh)
