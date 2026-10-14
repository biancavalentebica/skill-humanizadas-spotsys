"""Recorta cada unidade de uma planta humanizada em uma imagem separada.

Uso:
  python recortar.py planta.json                 # todas as unidades
  python recortar.py planta.json 505 512         # so algumas (teste)
  python recortar.py planta.json --folha f.png   # gera tambem folha de conferencia

O que faz, na ordem:
  1. Apaga os textos listados em "apagar" (ex.: linha "17,43 m2"), letra por letra:
     so pixels quase pretos e sem cor (texto), com tamanho de letra -> nao apaga moveis.
  2. Recorta cada unidade pelo contorno (poligonos do config), fundo branco, sem girar.
  3. (opcional) "ampliar_ia": true -> amplia 4x com Real-ESRGAN (so p/ planta pequena).
Tudo em resolucao original da planta: nenhum redimensionamento se ampliar_ia = false.
"""
import sys, os, argparse, numpy as np, cv2
sys.path.insert(0, os.path.dirname(__file__))
from plantas import *
from PIL import Image

ap = argparse.ArgumentParser()
ap.add_argument('config')
ap.add_argument('ids', nargs='*')
ap.add_argument('--folha', default=None)
a = ap.parse_args()
cfg = ler_config(a.config)
ANG = cfg.get('angulo', 0)
LARG = cfg.get('largura_area', 56)      # largura do texto a apagar (frame trabalho)
ALT = cfg.get('altura_texto', 11)       # altura de uma linha de texto (frame trabalho)
FOLGA = cfg.get('folga', 18)            # quanto alem da largura ainda procura letras
LIM_ESCURO = cfg.get('limiar_escuro', 95)
LIM_COR = cfg.get('limiar_cor', 22)
LETRA_L = cfg.get('letra_max_larg', 16)  # tamanho maximo de uma letra/grupo de letras (frame trabalho)
LETRA_A = cfg.get('letra_max_alt', 14)

A, alpha = carregar(cfg['planta'])
FH, FW = A.shape[:2]
work, f = trabalho(A)
Ht, Wt = work.shape[:2]
G = cv2.cvtColor(A, cv2.COLOR_RGB2GRAY)


def integral(gray):
    return cv2.integral((gray < 110).astype(np.float32))


def melhor(ii, cx, cy, w, h, rx, ry):
    """Desliza uma janela w x h e acha onde ha mais pixels escuros (= o texto)."""
    b = None
    w, h = int(w), int(h)
    for dy in range(-ry, ry + 1):
        for dx in range(-rx, rx + 1):
            x0 = int(cx + dx - w / 2); y0 = int(cy + dy - h / 2)
            if x0 < 0 or y0 < 0 or x0 + w >= ii.shape[1] or y0 + h >= ii.shape[0]:
                continue
            s = ii[y0 + h, x0 + w] - ii[y0, x0 + w] - ii[y0 + h, x0] + ii[y0, x0]
            if b is None or s > b[0]:
                b = (s, cx + dx, cy + dy)
    return (b[1], b[2]) if b else (cx, cy)


def mascara_letras(img, gray, cx, cy, w, h, vertical, caixa=False, base_min=None):
    """Mascara das letras na caixa (coords full) centrada em cx,cy.
    caixa=True: apaga TODO pixel escuro e sem cor dentro da caixa exata (w x h), sem filtro
    de tamanho de letra. Para texto encostado em movel/parede, em planta pequena."""
    hw = (w / 2 + (0 if caixa else FOLGA)) * f; hh = (h / 2 + (0 if caixa else 4)) * f
    if vertical:
        hw, hh = hh, hw
    x0, y0, x1, y1 = int(cx - hw), int(cy - hh), int(cx + hw), int(cy + hh)
    x0, y0 = max(x0, 0), max(y0, 0)
    sub = img[y0:y1, x0:x1]; gs = gray[y0:y1, x0:x1]
    sat = sub.max(2).astype(int) - sub.min(2)
    band = ((gs < LIM_ESCURO) & (sat < LIM_COR)).astype(np.uint8)
    m = np.zeros(gray.shape, np.uint8)
    if caixa:
        if base_min is not None:
            # 'base_min' (frame de trabalho): so apaga tracos cuja BASE fica abaixo dessa linha -> a caixa pode subir
            # para pegar o '2' sobrescrito sem cortar a base das letras da linha de cima ("Unidade 201")
            n, lab, st, _ = cv2.connectedComponentsWithStats(band, 8)
            lim = base_min * f - y0
            ok = np.zeros(n, bool); ok[1:] = (st[1:, 1] + st[1:, 3]) > lim
            band = ok[lab].astype(np.uint8)
        m[y0:y1, x0:x1] = band * 255
        return cv2.dilate(m, np.ones((5, 5), np.uint8))
    n, lab, st, cen = cv2.connectedComponentsWithStats(band, 8)
    for i in range(1, n):
        x, y, ww, hh_, ar = st[i]
        if not (ww <= LETRA_L * f and hh_ <= LETRA_A * f and ar >= 4):
            continue
        # letra que encosta na borda de cima/baixo (ou lados, se vertical) e da linha vizinha
        H_, W_ = band.shape
        if vertical and (x == 0 or x + ww >= W_):
            continue
        if not vertical and (y == 0 or y + hh_ >= H_):
            continue
        m[y0:y1, x0:x1][lab == i] = 255
    return cv2.dilate(m, np.ones((7, 7), np.uint8))


def mascara_bloco(img, gray, cx, cy, rx=90, ry=34, linha=False):
    """Modo 'bloco': a partir do ponto (coords full), junta todas as letras encostadas
    (componentes escuros, sem cor, do tamanho de letra) e devolve a mascara do bloco inteiro.
    Pega o rotulo completo ('S. UN 411 A' + '5,15m2') mesmo que o OCR so tenha achado um pedaco.
    linha=True: so cresce na horizontal (mesma linha) -> apaga '22,54m2' sem tocar 'UN 401 A' acima."""
    x0, y0 = max(int(cx - rx * f), 0), max(int(cy - ry * f), 0)
    x1, y1 = int(cx + rx * f), int(cy + ry * f)
    sub = img[y0:y1, x0:x1]; gs = gray[y0:y1, x0:x1]
    sat = sub.max(2).astype(int) - sub.min(2)
    band = ((gs < LIM_ESCURO) & (sat < LIM_COR)).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(band, 8)
    comps = [i for i in range(1, n) if st[i][2] <= LETRA_L * f and st[i][3] <= LETRA_A * f and st[i][4] >= 4]
    if not comps:
        return np.zeros(gray.shape, np.uint8)
    pcx, pcy = cx - x0, cy - y0
    def dist(i):
        x, y, w, h, _ = st[i]
        return max(x - pcx, pcx - (x + w), 0) + max(y - pcy, pcy - (y + h), 0)
    sem = min(comps, key=dist)
    if dist(sem) > 12 * f:
        return np.zeros(gray.shape, np.uint8)
    hl = st[sem][3]; gx, gy = 1.2 * hl, 0.9 * hl     # folga entre letras / entre linhas
    bx0, by0, bx1, by1 = st[sem][0], st[sem][1], st[sem][0] + st[sem][2], st[sem][1] + st[sem][3]
    dentro = {sem}; mudou = True
    while mudou:
        mudou = False
        for i in comps:
            if i in dentro: continue
            x, y, w, h, _ = st[i]
            if linha:
                ok = x < bx1 + gx and x + w > bx0 - gx and min(y + h, by1) - max(y, by0) > 0.5 * min(h, by1 - by0)
            else:
                ok = x < bx1 + gx and x + w > bx0 - gx and y < by1 + gy and y + h > by0 - gy
            if ok and h < 2.2 * hl:
                dentro.add(i); mudou = True
                bx0, by0, bx1, by1 = min(bx0, x), min(by0, y), max(bx1, x + w), max(by1, y + h)
    m = np.zeros(gray.shape, np.uint8)
    m[y0:y1, x0:x1][np.isin(lab, list(dentro))] = 255
    return cv2.dilate(m, np.ones((7, 7), np.uint8))


def inpaint_regiao(img, m):
    ys, xs = np.where(m > 0)
    if len(xs) == 0:
        return img
    P = 25
    x0, y0 = max(xs.min() - P, 0), max(ys.min() - P, 0)
    x1, y1 = min(xs.max() + P, img.shape[1]), min(ys.max() + P, img.shape[0])
    img[y0:y1, x0:x1] = cv2.inpaint(img[y0:y1, x0:x1].copy(), m[y0:y1, x0:x1], 5, cv2.INPAINT_TELEA)
    return img


# ---------- 1. apagar textos ----------
lista = cfg.get('apagar', [])
ii_o = integral(cv2.cvtColor(work, cv2.COLOR_RGB2GRAY))
precisa_r = any(x.get('frame', 'o') == 'r' for x in lista)
if precisa_r:
    work_r, _ = girar(work, ANG)
    ii_r = integral(cv2.cvtColor(work_r, cv2.COLOR_RGB2GRAY))
    Mf, nW, nH = matriz_rot(FW, FH, ANG)
    Mfi = cv2.invertAffineTransform(Mf)
    A_r = cv2.warpAffine(A, Mf, (nW, nH), flags=cv2.INTER_CUBIC, borderValue=(255, 255, 255))
    G_r = cv2.cvtColor(A_r, cv2.COLOR_RGB2GRAY)
mask_o = np.zeros((FH, FW), np.uint8)
mask_r = np.zeros((nH, nW), np.uint8) if precisa_r else None
for item in lista:
    cx, cy = item['centro']; vert = item.get('vertical', False)
    w = item.get('largura', LARG); h = item.get('altura', ALT)
    ww, hh = (h, w) if vert else (w, h)
    rx, ry = (4, 10) if vert else (10, 4)
    if item.get('frame', 'o') == 'r':
        cx, cy = melhor(ii_r, cx, cy, ww, hh, rx, ry)
        mask_r |= mascara_letras(A_r, G_r, cx * f, cy * f, w, h, vert)
    elif item.get('bloco'):
        mask_o |= mascara_bloco(A, G, cx * f, cy * f, linha=item.get('bloco') == 'linha')
    else:
        cx_ = item.get('caixa')
        if not cx_:
            cx, cy = melhor(ii_o, cx, cy, ww, hh, rx, ry)
        mask_o |= mascara_letras(A, G, cx * f, cy * f, w, h, vert, bool(cx_), item.get('base_min'))
if precisa_r:
    mask_o |= cv2.warpAffine(mask_r, Mfi, (FW, FH), flags=cv2.INTER_NEAREST)
# inpaint por blocos conectados (rapido em imagem grande)
n, lab, st, _ = cv2.connectedComponentsWithStats(cv2.dilate(mask_o, np.ones((41, 41), np.uint8)), 8)
for i in range(1, n):
    x, y, w, h, _ = st[i]
    sub_m = mask_o[y:y + h, x:x + w]
    A[y:y + h, x:x + w] = inpaint_regiao(A[y:y + h, x:x + w].copy(), sub_m)

# ---------- 2. recortar ----------
up = None
if cfg.get('ampliar_ia'):
    from esrgan import upscale as up
out_dir = cfg['saida']; os.makedirs(out_dir, exist_ok=True)
nome = cfg.get('nome', '{id}.png')
feitos = []
for k, un in sorted(cfg['unidades'].items()):
    if a.ids and k not in a.ids:
        continue
    m = mascara_unidade(un, ANG, Wt, Ht, (FH, FW), f)
    m[alpha == 0] = 0
    ys, xs = np.where(m > 0)
    if len(xs) == 0:
        print('AVISO: unidade', k, 'sem area'); continue
    x0, y0, x1, y1 = xs.min(), ys.min(), xs.max() + 1, ys.max() + 1
    crop = A[y0:y1, x0:x1]; mk = cv2.GaussianBlur(m[y0:y1, x0:x1], (3, 3), 0)
    if up:
        crop = up(crop.copy())
        mk = cv2.resize(mk, (crop.shape[1], crop.shape[0]), interpolation=cv2.INTER_LINEAR)
    a_ = mk[..., None] / 255.0
    out = (crop * a_ + 255 * (1 - a_)).astype(np.uint8)
    p = os.path.join(out_dir, nome.format(id=k))
    Image.fromarray(out).save(p, optimize=True)
    feitos.append(p); print(k, out.shape[1], 'x', out.shape[0], flush=True)

# ---------- 3. folha de conferencia ----------
if a.folha and feitos:
    cw, ch, cols = 500, 420, 4
    rows = (len(feitos) + cols - 1) // cols
    sh = Image.new('RGB', (cols * cw, rows * ch), (204, 204, 204))
    from PIL import ImageDraw
    d = ImageDraw.Draw(sh)
    for i, p in enumerate(feitos):
        im = Image.open(p); im.thumbnail((cw - 10, ch - 30))
        x, y = (i % cols) * cw, (i // cols) * ch
        sh.paste(im, (x + 5, y + 25)); d.text((x + 5, y + 5), os.path.basename(p), fill=(220, 0, 0))
    sh.save(a.folha); print('folha', a.folha)
print('FIM', len(feitos), 'imagens em', out_dir)
