"""Retira os textos (GARDEN/UND./areas, RECEPCAO, CIRCULACAO COMUM, nome da avenida) da humanizada do terreo do
Batel Spot, preenchendo cada letra com um trecho REAL vizinho da mesma textura (grama, madeira, porcelanato, asfalto).
O trecho e escolhido pela menor diferenca com a borda em volta da letra (continua tabuas e juntas). Sem IA, sem
inpainting borrado. A rosa dos ventos (simbolo) e mantida.

Caixas: OCR nativo do Windows em blocos (03_trabalho/entrada/ocr_rotulos.json) + posicoes fixas dos rotulos faltantes.
Uso: py remove_rotulos_terreo.py <entrada.png> <saida.png> [--dx 0 --dy 0] [--debug debug.jpg]
  TER-001: dx=0 dy=0.  TER-000 (estudo solar): dx=-2 dy=997.
"""
import argparse, json
import numpy as np, cv2
from PIL import Image
Image.MAX_IMAGE_PIXELS = None

ap = argparse.ArgumentParser()
ap.add_argument('entrada'); ap.add_argument('saida')
ap.add_argument('--dx', type=int, default=0); ap.add_argument('--dy', type=int, default=0)
ap.add_argument('--debug', default='')
ap.add_argument('--so-113', action='store_true', help='processa so o rotulo da garden 113 (deck | grama)')
ap.add_argument('--manter-und', action='store_true', help='mantem so a numeracao das unidades (linha UND. xxx); tira areas e demais rotulos')
a = ap.parse_args()
im = np.array(Image.open(a.entrada).convert('RGB')).astype(np.float32)
H, W = im.shape[:2]
gray = im.mean(2)

# titulos (x0, y0, x1, y1) no referencial da TER-001; a linha da area fica logo abaixo de cada titulo
gard = [(x, 412, x + 330, 466) for x in (5868, 6656, 7437, 8185, 8974, 9727, 10656)]
gard += [(3156, y, 3484, y + 54) for y in (772, 1563, 2257, 3086, 3778)]
gard += [(10806, 3265, 11134, 3319), (7089, 3838, 7418, 3892), (7089, 4557, 7418, 4611)]
und = [(4499, 772, 4829, 826), (4327, 1567, 4650, 1621), (4332, 2257, 4660, 2311), (4331, 3086, 4662, 3140),
       (4338, 3778, 4650, 3832), (5867, 1830, 6201, 1884), (6657, 1825, 6990, 1879), (7408, 1825, 7742, 1879),
       (8185, 1830, 8520, 1884), (9016, 1830, 9332, 1884), (9727, 1825, 10047, 1879), (10490, 1825, 10800, 1879),
       (9861, 3265, 10168, 3319), (8073, 3265, 8386, 3319), (6179, 4557, 6488, 4611)]
linhas = []
DECK_GRAMA_113 = 11065                                                           # garden 113: rotulo cruza deck | grama
for (x0, y0, x1, y1) in gard + und:
    caixas = ((x0 - 12, y0 - 10, x1 + 12, y1 + 10), (x0 - 12, y1 + 6, x1 + 40, y1 + 104))
    if a.manter_und and (x0, y0, x1, y1) in und:
        caixas = caixas[1:]                                                      # fica o titulo UND. xxx; sai a area
    for (a0, b0, a1, b1) in caixas:
        if a0 < DECK_GRAMA_113 < a1 and 3200 < b0 < 3450:
            linhas.append((a0, b0, DECK_GRAMA_113, b1, 'claro_v'))           # deck: so desloca ao longo das tabuas
            linhas.append((DECK_GRAMA_113, b0, a1, b1, 'claro_g'))           # grama
        else:
            linhas.append((a0, b0, a1, b1, 'claro'))
linhas.sort(key=lambda r: r[4] in ('claro_v', 'claro_g'))                     # garden 113 por ultimo (usa decks ja limpos)
linhas += [(4405, 4385, 4820, 4480, 'escuro'),                                   # RECEPCAO
           (5870, 2828, 6630, 2930, 'escuro'),                                   # CIRCULACAO COMUM
           (515, 2400, 705, 4140, 'claro')]                                      # Av. Visc. de Guarapuava (vertical)
linhas.sort(key=lambda r: r[4] in ('claro_v', 'claro_g'))
if a.so_113:
    linhas = [r for r in linhas if r[4] in ('claro_v', 'claro_g')]
linhas = [(x0 + a.dx, y0 + a.dy, x1 + a.dx, y1 + a.dy, k) for (x0, y0, x1, y1, k) in linhas]

# mascara das letras em cada caixa
texto = np.zeros((H, W), np.uint8)
for (x0, y0, x1, y1, k) in linhas:
    g = gray[y0:y1, x0:x1]
    borda = np.concatenate([g[:4].ravel(), g[-4:].ravel(), g[:, :4].ravel(), g[:, -4:].ravel()])
    bg = np.median(borda)
    if k.startswith('claro'):
        m = (g > max(bg + 45, 205)).astype(np.uint8)
    else:
        m = (g < bg - 16).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    # letra + sombra (rotulos brancos) ou + halo claro (rotulos cinza)
    m = cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (19, 19) if k.startswith('claro') else (17, 17)))
    texto[y0:y1, x0:x1] |= m
proibido = cv2.dilate(texto, np.ones((25, 25), np.uint8))                       # fonte nunca pode conter letra (ainda nao limpa)
mantido = np.zeros((H, W), np.uint8)                                            # titulos UND. que ficam (--manter-und)
if a.manter_und:
    for (x0, y0, x1, y1) in und:
        mantido[y0 - 16 + a.dy:y1 + 14 + a.dy, x0 - 16 + a.dx:x1 + 16 + a.dx] = 1
    proibido |= mantido

out = im.copy()
lisa = cv2.GaussianBlur(out, (0, 0), 4)                                         # versao suave, para comparar fundos
gx = cv2.Sobel(lisa.mean(2), cv2.CV_32F, 1, 0, ksize=3); gy = cv2.Sobel(lisa.mean(2), cv2.CV_32F, 0, 1, ksize=3)
borda_img = cv2.GaussianBlur(np.sqrt(gx ** 2 + gy ** 2), (0, 0), 3)               # forca de borda (objetos)
borda_img[texto.astype(bool)] = 0
log = []
for (x0, y0, x1, y1, k) in linhas:
    m = texto[y0:y1, x0:x1].astype(bool)
    if not m.any(): continue
    ys, xs = np.nonzero(m)
    ys = ys + y0; xs = xs + x0
    anel = cv2.dilate(m.astype(np.uint8), np.ones((15, 15), np.uint8)).astype(bool) & ~m
    ry, rx = np.nonzero(anel); ry = ry + y0; rx = rx + x0
    ok = (~texto[ry, rx].astype(bool) | ~proibido[ry, rx].astype(bool)) & ~mantido[ry, rx].astype(bool)
    ry, rx = ry[ok], rx[ok]
    alvo = out[ry, rx]
    bw, bh = x1 - x0, y1 - y0
    # fundo esperado sob as letras (estimativa suave a partir da borda): a fonte tem de parecer com ele por dentro
    reg = np.clip(out[y0:y1, x0:x1], 0, 255).astype(np.uint8)
    est = cv2.inpaint(reg, m.astype(np.uint8) * 255, 9, cv2.INPAINT_TELEA).astype(np.float32)
    est = cv2.GaussianBlur(est, (0, 0), 4)[m]
    borda_ref = borda_img[ry, rx].mean()                                         # textura normal do fundo em volta
    best, bs = None, np.inf
    if k == 'escuro':                                                            # porcelanato: so multiplos da placa
        P = 187.5
        cands = [(int(round(i * P)), int(round(j * P))) for i in range(-7, 8) for j in range(-3, 4) if (i, j) != (0, 0)]
    elif k == 'claro_v':
        cands = [(0, dy) for dy in range(-420, 421, 4) if abs(dy) >= bh * 0.6 + 8]
        # tambem os decks das gardens 114/115 (mesmas tabuas verticais, x 7000..7440, y 3550..4950), ja limpos
        cands += [(dx, dy) for dx in range(7000 + a.dx - x0, 7440 + a.dx - x1 + 1, 2)
                  for (ya, yb) in ((3560, 3965), (4060, 4950))                  # evita a mureta entre os decks
                  for dy in range(ya + a.dy - y0, yb + a.dy - y1 + 1, 6)]
    else:
        S = 420
        cands = [(dx, dy) for dy in range(-S, S + 1, 8) for dx in range(-S, S + 1, 8)
                 if not (abs(dx) < bw * 0.6 + 8 and abs(dy) < bh * 0.6 + 8)]
    for dx, dy in cands:
        sy0, sx0 = y0 + dy, x0 + dx
        if sy0 < 0 or sx0 < 0 or sy0 + bh > H or sx0 + bw > W: continue
        if proibido[ys + dy, xs + dx].any() or proibido[ry + dy, rx + dx].any(): continue
        e = ((out[ry + dy, rx + dx] - alvo) ** 2).mean()
        e += 2.5 * ((lisa[ys + dy, xs + dx] - est) ** 2).mean()
        e += 6.0 * max(0.0, borda_img[ys + dy, xs + dx].mean() - borda_ref)          # objetos (bordas fortes) dentro da fonte
        if e < bs: bs, best = e, (dx, dy)
    if best is None: continue
    dx, dy = best
    if k in ('claro_v', 'claro_g'):
        # rotulo dividido na linha deck | grama: colagem direta (o gradiente puxaria a cor do outro material)
        fonte = out[y0 + dy:y1 + dy, x0 + dx:x1 + dx].copy()
        ganho = out[ry, rx].mean(0) / np.maximum(out[ry + dy, rx + dx].mean(0), 1)  # mesmo tom do entorno
        fonte *= ganho[None, None]
        m2 = cv2.dilate(m.astype(np.uint8), np.ones((9, 9), np.uint8))
        mm = cv2.GaussianBlur(m2.astype(np.float32), (0, 0), 3.0) * (cv2.GaussianBlur(m2.astype(np.float32), (0, 0), 3.0) > 0.02)
        out[y0:y1, x0:x1] = out[y0:y1, x0:x1] * (1 - mm[..., None]) + fonte * mm[..., None]
        lisa[y0:y1, x0:x1] = cv2.GaussianBlur(out[y0:y1, x0:x1], (0, 0), 4)
        proibido[y0:y1, x0:x1][m] = 0
        log.append(dict(caixa=[x0, y0, x1, y1], tipo=k, desloc=[int(dx), int(dy)], erro_borda=round(float(bs), 1)))
        continue
    # clonagem por gradiente (Poisson) com a mascara no formato das letras: textura da fonte, tom da borda em volta
    M = 20
    if y0 - M + min(dy, 0) < 0 or x0 - M + min(dx, 0) < 0 or y1 + M + max(dy, 0) > H or x1 + M + max(dx, 0) > W: continue
    dst = np.clip(out[y0 - M:y1 + M, x0 - M:x1 + M], 0, 255).astype(np.uint8)
    src = np.clip(out[y0 - M + dy:y1 + M + dy, x0 - M + dx:x1 + M + dx], 0, 255).astype(np.uint8)
    mk = np.zeros(dst.shape[:2], np.uint8); mk[M:M + bh, M:M + bw][m] = 255
    bx, by, bw2, bh2 = cv2.boundingRect(mk)
    res = cv2.seamlessClone(src, dst, mk, (bx + bw2 // 2, by + bh2 // 2), cv2.NORMAL_CLONE)
    out[y0 - M:y1 + M, x0 - M:x1 + M] = res.astype(np.float32)
    lisa[y0 - M:y1 + M, x0 - M:x1 + M] = cv2.GaussianBlur(out[y0 - M:y1 + M, x0 - M:x1 + M], (0, 0), 4)
    proibido[y0:y1, x0:x1][m] = 0                                                # ja limpo: pode servir de fonte
    log.append(dict(caixa=[x0, y0, x1, y1], tipo=k, desloc=[int(dx), int(dy)], erro_borda=round(float(bs), 1)))

Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).save(a.saida)
json.dump(log, open(a.saida.rsplit('.', 1)[0] + '_rotulos_log.json', 'w'), indent=1)
if a.debug:
    d = np.clip(out, 0, 255).astype(np.uint8).copy()
    for (x0, y0, x1, y1, k) in linhas:
        cv2.rectangle(d, (x0, y0), (x1, y1), (255, 0, 0), 4)
    Image.fromarray(d).resize((W // 5, H // 5)).save(a.debug, quality=90)
print('ok', a.saida, len(log), 'linhas')
