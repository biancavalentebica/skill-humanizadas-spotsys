"""Tira os rotulos do lancamento (caixas azuis "Aloj NN / area / hospedes" e textos brancos "Garden x m2") da area
externa, ANTES de desenhar o predio do executivo (regra da Rachel, 19/10/2026: so "Unidade NN" dentro do ambiente).
Cada rotulo e preenchido com as MESMAS linhas da imagem, deslocadas na horizontal (faixas horizontais como calcada,
meio-fio, gradil e fachada continuam), com o deslocamento escolhido pela emenda: as colunas de borda da fonte tem de
casar com as colunas vizinhas do rotulo. Fundo transparente volta transparente.
Funcao: tira(rgb, alfa) -> (rgb, alfa, log)"""
import numpy as np, cv2

def mascara(rgb):
    f = rgb.astype(np.int16); R, G, B = f[..., 0], f[..., 1], f[..., 2]
    nav = ((np.abs(R - 57) < 3) & (np.abs(G - 66) < 3) & (np.abs(B - 94) < 3)).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(cv2.morphologyEx(nav, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8)), 8)
    H, W = nav.shape; m = np.zeros((H, W), np.uint8)
    for i in range(1, n):
        x, y, w, h, a = st[i]
        if a > 20000: m[max(y - 3, 0):y + h + 3, max(x - 3, 0):x + w + 3] = 1
    branco = ((np.minimum(np.minimum(R, G), B) > 200) & ((np.maximum(np.maximum(R, G), B) - np.minimum(np.minimum(R, G), B)) < 45)).astype(np.uint8)
    verde = ((G > R + 20) & (G > B + 20))
    n2, lab2, st2, _ = cv2.connectedComponentsWithStats(branco, 8); t = np.zeros((H, W), np.uint8)
    for i in range(1, n2):
        x, y, w, h, a = st2[i]
        if a < 15 or w > 200 or h > 200: continue
        x0, y0, x1, y1 = max(x - 14, 0), max(y - 14, 0), min(x + w + 14, W), min(y + h + 14, H)
        if (verde[y0:y1, x0:x1] & ~(lab2[y0:y1, x0:x1] == i)).mean() > 0.45: t[lab2 == i] = 1
    # texto de garden: retangulo inteiro do bloco de texto (pega o antisserrilhado todo)
    nb, labb, stb, _ = cv2.connectedComponentsWithStats(cv2.dilate(t, np.ones((25, 41), np.uint8)), 8)
    for i in range(1, nb):
        x, y, w, h, a = stb[i]; m[max(y - 4, 0):y + h + 4, max(x - 4, 0):x + w + 4] = 1
    return cv2.dilate(m, np.ones((7, 7), np.uint8))

def tira(rgb, alfa, proib_extra=None):
    rgb = rgb.copy(); alfa = alfa.copy(); H, W = alfa.shape
    m = mascara(rgb); proib = cv2.dilate(m, np.ones((15, 15), np.uint8)).astype(bool)
    if proib_extra is not None: proib |= proib_extra
    n, lab, st, _ = cv2.connectedComponentsWithStats(cv2.dilate(m, np.ones((21, 21), np.uint8)), 8)
    F = rgb.astype(np.float32); log = []
    for i in range(1, n):
        x, y, w, h, _ = st[i]
        reg = (lab[y:y + h, x:x + w] == i) & m[y:y + h, x:x + w].astype(bool)
        ys, xs = np.nonzero(reg); y0, y1 = y + ys.min(), y + ys.max() + 1; x0, x1 = x + xs.min(), x + xs.max() + 1
        sel = m[y0:y1, x0:x1].astype(bool)
        hh, larg = y1 - y0, x1 - x0
        # emenda nos 4 lados: a fonte deslocada tem de continuar as colunas/linhas vizinhas do rotulo
        Lc = F[y0:y1, max(x0 - 2, 0)]; Rc = F[y0:y1, min(x1 + 1, W - 1)]
        Tr = F[max(y0 - 2, 0), x0:x1]; Br = F[min(y1 + 1, H - 1), x0:x1]
        def ok(a0, b0): return a0 >= 1 and a0 + larg + 1 < W and b0 >= 1 and b0 + hh + 1 < H and not proib[b0:b0 + hh, a0:a0 + larg].any()
        def custo(a0, b0):
            c = np.abs(F[b0:b0 + hh, a0 - 1] - Lc).mean() + np.abs(F[b0:b0 + hh, a0 + larg] - Rc).mean()
            c += np.abs(F[b0 - 1, a0:a0 + larg] - Tr).mean() + np.abs(F[b0 + hh, a0:a0 + larg] - Br).mean()
            c += 0.5 * np.abs(alfa[b0:b0 + hh, a0:a0 + larg].astype(np.float32).mean() - (alfa[y0:y1, max(x0 - 2, 0)].mean() + alfa[y0:y1, min(x1 + 1, W - 1)].mean()) / 2)
            return c
        best = None
        cand = [(d, e) for d in range(-4 * larg, 4 * larg + 1, 4) for e in (-6, -3, 0, 3, 6) if abs(d) > larg + 8] +                [(e, d) for d in range(-4 * hh, 4 * hh + 1, 4) for e in (-6, -3, 0, 3, 6) if abs(d) > hh + 8]
        for dx, dy in cand:
            if not ok(x0 + dx, y0 + dy): continue
            c = custo(x0 + dx, y0 + dy)
            if best is None or c < best[0]: best = (c, dx, dy)
        if best is None: log.append(dict(caixa=[int(x0), int(y0), int(x1), int(y1)], erro='sem fonte')); continue
        c, dx, dy = best
        src = rgb[y0 + dy:y1 + dy, x0 + dx:x1 + dx]; srca = alfa[y0 + dy:y1 + dy, x0 + dx:x1 + dx]
        rgb[y0:y1, x0:x1][sel] = src[sel]; alfa[y0:y1, x0:x1][sel] = srca[sel]
        log.append(dict(caixa=[int(x0), int(y0), int(x1), int(y1)], fonte=[int(dx), int(dy)], custo_emenda=round(float(c), 1)))
    return rgb, alfa, log
