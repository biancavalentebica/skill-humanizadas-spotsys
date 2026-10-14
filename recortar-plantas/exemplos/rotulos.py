"""Campeche Spot: apaga rótulos de área (texto + o fundo branco translúcido do rótulo) antes do recorte.
(Exemplo real, out/2026. Copie para "<pasta do empreendimento>/configs/" ao lado do s_<PAV>.py que o importa.)

Nas plantas do Campeche Spot cada linha de rótulo tem um retângulo branco translúcido por trás
(branco com opacidade ~0,655). Só apagar as letras deixaria um retângulo claro vazio. Aqui:
  1. acha a linha de texto perto do ponto dado (letras pretas);
  2. acha o retângulo do fundo (degrau de claridade nas bordas; altura fixa por planta);
  3. desfaz a mistura com o branco: u = (obs - a*255) / (1 - a)  -> volta o piso/deck original;
  4. inpaint só nas letras e na borda de 1-2 px do retângulo.
Gera uma cópia limpa da planta (RGBA) que é usada no config ("planta") com "apagar": [].

Uso (no s_<PAV>.py):
    from rotulos import limpar
    limpar(planta, saida_png, [(cx, cy), ...])     # pontos (frame de trabalho) sobre a linha a apagar
"""
import os, numpy as np, cv2
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
A_OV = 0.655          # opacidade do fundo branco do rótulo


def _linha(rgb, cx, cy, f, rx=60, ry=30):
    """caixa (px cheios) da linha de texto preto que passa perto de (cx, cy) [trabalho] + topo/base das letras grandes."""
    x0, y0 = int((cx - rx) * f), int((cy - ry) * f)
    sub = rgb[y0:int((cy + ry) * f), x0:int((cx + rx) * f)].astype(int)
    gsub = sub.mean(2)
    band = ((gsub < 80) & (sub.max(2) - sub.min(2) < 25)).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(band, 8)
    comps = [st[i] for i in range(1, n) if 2 * f <= st[i][3] <= 16 * f and st[i][2] <= 16 * f and st[i][4] >= 15
             and st[i][0] > 0 and st[i][1] > 0 and st[i][0] + st[i][2] < band.shape[1] and st[i][1] + st[i][3] < band.shape[0]
             and np.median(gsub[st[i][1]:st[i][1] + st[i][3], st[i][0]:st[i][0] + st[i][2]][
                 lab[st[i][1]:st[i][1] + st[i][3], st[i][0]:st[i][0] + st[i][2]] == i]) < 30]   # letra = preto puro
    if not comps:
        return None
    # componentes da mesma linha do ponto
    pcy = cy * f - y0
    perto = min(comps, key=lambda s: abs(s[1] + s[3] / 2 - pcy))
    yc = perto[1] + perto[3] / 2
    L = [s for s in comps if abs(s[1] + s[3] / 2 - yc) < 5 * f]
    L.sort(key=lambda s: s[0])
    # corta grupos separados (> 10 px de trabalho) do grupo mais perto do ponto
    grp = [[L[0]]]
    for s in L[1:]:
        if s[0] - max(q[0] + q[2] for q in grp[-1]) > 7 * f: grp.append([s])
        else: grp[-1].append(s)
    pcx = cx * f - x0
    G = min(grp, key=lambda g: max(g[0][0] - pcx, pcx - (g[-1][0] + g[-1][2]), 0))
    hmax = max(s[3] for s in G)
    big = [s for s in G if s[3] > 0.7 * hmax]
    top = min(s[1] for s in big); base = np.median([s[1] + s[3] for s in big])
    X0 = min(s[0] for s in G); X1 = max(s[0] + s[2] for s in G)
    return x0 + X0, y0 + top, x0 + X1, y0 + base


def _degrau(p, a, b, sinal):
    best, bi = 0, None
    for i in range(max(a, 1), min(b, len(p))):
        if np.isnan(p[i]) or np.isnan(p[i - 1]): continue
        d = (p[i] - p[i - 1]) * sinal
        if d > best: best, bi = d, i
    return bi, best


def _retangulo(rgb, ln, f, H, pads):
    """retângulo [x0,x1) x [y0,y1) (px cheios) do fundo branco do rótulo."""
    X0, T, X1, Bs = ln
    pl, pt, pr = pads
    m = rgb[int(T - 6 * f):int(Bs + 6 * f), int(X0 - 4 * f):int(X1 + 4 * f)].astype(float)
    oy, ox = int(T - 6 * f), int(X0 - 4 * f)
    txt = cv2.dilate((m.mean(2) < 130).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    mm = np.where(txt, np.nan, m.min(2))
    with np.errstate(all='ignore'):
        cols = np.nanmedian(mm[int(T - oy + 2 * f):int(Bs - oy - 2 * f), :], 0)
        rows = np.nanmedian(mm[:, int(X0 - ox + 0.2 * (X1 - X0)):int(X1 - ox - 0.2 * (X1 - X0))], 1)
    # posição esperada (padrão da planta) e busca de +-1,5 px de trabalho em volta
    el, et, er = X0 + pl * f, T + pt * f, X1 + pr * f
    w = int(1.5 * f)
    l, dl = _degrau(cols, int(el - ox) - w, int(el - ox) + w + 1, +1)
    r, dr = _degrau(cols, int(er - ox) - w, int(er - ox) + w + 1, -1)
    t, dt = _degrau(rows, int(et - oy) - w, int(et - oy) + w + 1, +1)
    x0 = ox + l if l is not None and dl > 8 else int(round(el))
    x1 = ox + r if r is not None and dr > 8 else int(round(er))
    y0 = oy + t if t is not None and dt > 8 else int(round(et))
    return x0, y0, x1, y0 + int(round(H * f))



def _direcional(img, mk, v, N=120):
    """preenche os pixels de mk copiando a textura ao longo da direção v (ex.: tábuas do deck):
    interpola entre o 1º pixel livre para trás e para frente na direção v."""
    H, W = mk.shape
    ys, xs = np.nonzero(mk)
    if len(xs) == 0:
        return img
    vx, vy = v; n_ = (vx * vx + vy * vy) ** 0.5; vx, vy = vx / n_, vy / n_
    res = img.astype(float).copy()
    achou = []
    for sinal in (-1, 1):
        dist = np.full(len(xs), np.nan); val = np.zeros((len(xs), 3))
        pend = np.ones(len(xs), bool)
        for k in range(1, N + 1):
            if not pend.any(): break
            px = np.round(xs + sinal * k * vx).astype(int); py = np.round(ys + sinal * k * vy).astype(int)
            dentro = (px >= 0) & (px < W) & (py >= 0) & (py < H)
            ok = pend & dentro
            ok[ok] = mk[py[ok], px[ok]] == 0
            val[ok] = img[py[ok], px[ok]]; dist[ok] = k; pend &= ~ok
            pend &= dentro
        achou.append((dist, val))
    (d1, v1), (d2, v2) = achou
    a = np.isfinite(d1); b = np.isfinite(d2)
    both = a & b
    w1 = np.where(both, d2 / (d1 + d2 + 1e-9), 0)[:, None]
    out = np.zeros((len(xs), 3))
    out[both] = (w1 * v1 + (1 - w1) * v2)[both]
    out[a & ~b] = v1[a & ~b]; out[b & ~a] = v2[b & ~a]
    resto = ~(a | b)
    res[ys[~resto], xs[~resto]] = out[~resto]
    img2 = np.clip(res, 0, 255).astype(np.uint8)
    if resto.any():
        m2 = np.zeros(mk.shape, np.uint8); m2[ys[resto], xs[resto]] = 255
        img2 = cv2.inpaint(img2, m2, 4, cv2.INPAINT_TELEA)
    return img2

def limpar_arr(rgb, pontos, H=17.17, pads=(-0.85, -0.33, 0.72)):
    """apaga os rótulos direto no array RGB (uint8, altera no lugar). Devolve [(ponto, retângulo em trabalho)]."""
    f = rgb.shape[1] / 2000
    feitos = []
    for pt in pontos:
        cx, cy = pt[0], pt[1]
        v = pt[2] if len(pt) > 2 else None   # direção da textura (tábuas) p/ preencher as letras
        ret = pt[3] if len(pt) > 3 else None # retângulo do fundo medido à mão (trabalho), quando a detecção falha
        if ret:
            x0, y0, x1, y1 = [int(round(c * f)) for c in ret]
        else:
            ln = _linha(rgb, cx, cy, f)
            if ln is None:
                feitos.append(((cx, cy), None)); continue
            x0, y0, x1, y1 = _retangulo(rgb, ln, f, H, pads)
        P = 12
        X0, Y0, X1, Y1 = x0 - P, y0 - int(4 * f), x1 + P, y1 + P
        crop = rgb[Y0:Y1, X0:X1].astype(float)
        out = crop.copy()
        ix0, iy0, ix1, iy1 = x0 - X0, y0 - Y0, x1 - X0, y1 - Y0
        g = crop.mean(2); sat = crop.max(2) - crop.min(2)
        esc = ((g < 140) & (sat < 45)).astype(np.uint8)
        inner = out[iy0:iy1, ix0:ix1]
        livre = cv2.dilate(esc, np.ones((9, 9), np.uint8))[iy0:iy1, ix0:ix1] == 0
        ruim = ((inner.min(2) < A_OV * 255 - 8) & livre)[2:-2, 2:-2].mean()
        ok = ruim < 0.01
        if ok:      # o retângulo é mesmo o fundo branco do rótulo -> desfaz a mistura
            out[iy0:iy1, ix0:ix1] = np.clip((inner - A_OV * 255) / (1 - A_OV), 0, 255)
        else:
            print('AVISO rotulos: fundo nao confirmado em', (cx, cy), 'ruim=%.3f -> so apaga as letras' % ruim)
        # máscara: letras (pretas) que tocam o retângulo + borda do retângulo
        n, lab, st, _ = cv2.connectedComponentsWithStats(esc, 8)
        mk = np.zeros(esc.shape, np.uint8)
        dentro = np.unique(lab[iy0:iy1, ix0:ix1])
        for i in dentro:
            if i == 0: continue
            x, y, w, h, a = st[i]
            if w > 16 * f or h > 16 * f: continue
            mk[lab == i] = 1
        # letras pretas encostadas em objeto escuro (componente grande): pega só o preto do texto em volta do retângulo
        # (inclui o "²", que passa um pouco acima do fundo do rótulo)
        E = np.zeros(esc.shape, np.uint8)
        E[max(iy0 - int(3.5 * f), 0):iy1, max(ix0 - int(1.5 * f), 0):ix1 + int(1.5 * f)] = 1
        preto = (((g < 70) & (sat < 35)) & (E > 0)).astype(np.uint8)
        n2, lab2 = cv2.connectedComponents(preto, connectivity=8)
        ids = [i for i in np.unique(lab2[iy0:iy1, ix0:ix1]) if i != 0]
        if ids and ok:
            mk[np.isin(lab2, ids)] = 1
        mk = cv2.dilate(mk, np.ones((5, 5), np.uint8))
        if ok:
            for (a_, b_) in ((iy0 - 1, iy0 + 1), (iy1 - 1, iy1 + 1)):
                mk[a_:b_, ix0 - 1:ix1 + 1] = 1
            for (a_, b_) in ((ix0 - 1, ix0 + 1), (ix1 - 1, ix1 + 1)):
                mk[iy0 - 1:iy1 + 1, a_:b_] = 1
        if v is not None:
            res = _direcional(np.clip(out, 0, 255).astype(np.uint8), mk, v)
        else:
            res = cv2.inpaint(np.clip(out, 0, 255).astype(np.uint8), mk * 255, 4, cv2.INPAINT_TELEA)
        rgb[Y0:Y1, X0:X1] = res
        feitos.append(((cx, cy), (round(x0 / f, 2), round(y0 / f, 2), round(x1 / f, 2), round(y1 / f, 2))))
    return feitos


def limpar(planta, saida, pontos, log=None, **kw):
    """gera a cópia limpa da planta (RGBA) em `saida`."""
    im = Image.open(planta).convert('RGBA')
    arr = np.array(im)
    rgb = np.ascontiguousarray(arr[..., :3])
    feitos = limpar_arr(rgb, pontos, **kw)
    arr[..., :3] = rgb
    os.makedirs(os.path.dirname(os.path.abspath(saida)), exist_ok=True)
    Image.fromarray(arr, 'RGBA').save(saida, compress_level=1)
    if log:
        with open(log, 'w', encoding='utf-8') as fh:
            for p, r in feitos: fh.write(f'{p} -> {r}\n')
    return feitos
