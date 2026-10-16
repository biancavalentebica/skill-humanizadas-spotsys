"""Corrige o VALOR de area escrito em rotulos da humanizada (ex.: "GARDEN / 8,88 m2" -> "9,36 m2") sem mexer no render.

- Acha cada rotulo perto da posicao aproximada (texto branco), separa a linha do titulo e a linha do valor.
- Biblioteca de glifos: recorta os caracteres dos proprios rotulos da imagem (mesma fonte, tamanho e antialias).
- Apaga a linha antiga com textura do mesmo garden (faixa logo abaixo/acima, sem texto) com borda suave.
- Escreve o valor novo com os glifos, centralizado onde estava o antigo.

Uso: py corrige_rotulos_area.py <imagem.png> <rotulos.json> <saida.png> [--debug pasta]
rotulos.json: {"rotulos": [{"id": "101", "xy": [x, y], "atual": "8,88", "novo": "9,36"}, ...]}  (xy em px da imagem)
"""
import argparse, json, os
import cv2, numpy as np

ap = argparse.ArgumentParser()
ap.add_argument('imagem'); ap.add_argument('rotulos'); ap.add_argument('saida')
ap.add_argument('--debug', default='')
ap.add_argument('--janela', type=int, default=260)
a = ap.parse_args()

im = cv2.imread(a.imagem, cv2.IMREAD_UNCHANGED)
if im.shape[2] == 4:
    al = im[:, :, 3:4] / 255.0
    im = (im[:, :, :3] * al + 255 * (1 - al)).astype(np.uint8)
out = im.copy()
R = json.load(open(a.rotulos, encoding='utf-8'))['rotulos']


def linhas_do_rotulo(x, y):
    J = a.janela
    x0, y0 = max(0, x - 2 * J), max(0, y - J)
    c = im[y0:y + J, x0:x + 2 * J]
    cf = c.astype(int)
    branco = ((cf.min(axis=2) > 215) & (cf.max(axis=2) - cf.min(axis=2) < 30)).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(branco, 8)
    comps = [i for i in range(1, n) if 30 < st[i, 4] < 20000 and 8 < st[i, 3] < 120]
    if not comps:
        raise SystemExit(f'sem texto perto de {x},{y}')
    # agrupa por linha (centro y)
    cy = sorted(comps, key=lambda i: st[i, 1] + st[i, 3] / 2)
    linhas, atual = [], [cy[0]]
    for i in cy[1:]:
        if abs((st[i, 1] + st[i, 3] / 2) - (st[atual[-1], 1] + st[atual[-1], 3] / 2)) < 25: atual.append(i)
        else: linhas.append(atual); atual = [i]
    linhas.append(atual)
    # fica com as linhas mais perto do ponto dado, cada uma ordenada em x
    res = []
    for L in linhas:
        L = sorted(L, key=lambda i: st[i, 0])
        res.append([(int(st[i, 0] + x0), int(st[i, 1] + y0), int(st[i, 2]), int(st[i, 3]), lab == i, x0, y0) for i in L])
    return res


def glifo(comp):
    gx, gy, w, h, mask, x0, y0 = comp
    p = 4
    X0, Y0 = gx - p, gy - p
    patch = im[Y0:Y0 + h + 2 * p, X0:X0 + w + 2 * p].astype(float)
    m = mask[gy - y0 - p:gy - y0 + h + p, gx - x0 - p:gx - x0 + w + p].astype(np.uint8)
    m = cv2.dilate(m, np.ones((5, 5), np.uint8)).astype(bool)
    lum = patch.min(axis=2)
    fundo = np.median(lum[~m]) if (~m).any() else 80
    alpha = np.clip((lum - fundo) / (250 - fundo), 0, 1) * m
    return dict(alpha=alpha, w=w, h=h, top=gy, cor=np.array([255, 255, 255.0]))


# 1) acha linhas e monta biblioteca de glifos com os valores atuais conhecidos
lib, info = {}, []
for r in R:
    linhas = linhas_do_rotulo(*r['xy'])
    alvo = r['atual'].replace(' ', '') + 'm²'
    val = None
    # linha do titulo: a de mais caracteres altos e parecidos; o valor e a linha logo abaixo, dentro da largura do titulo
    def nota_titulo(L):  # "GARDEN": varias letras altas com a MESMA altura
        hs = np.array([c[3] for c in L]); md = np.median(hs)
        return int(((abs(hs - md) <= 0.08 * md) & (hs > 30)).sum()) + md / 1000
    tit = max(range(len(linhas)), key=lambda i: nota_titulo(linhas[i]))
    T = linhas[tit]; tx0 = min(c[0] for c in T) - 60; tx1 = max(c[0] + c[2] for c in T) + 60
    tb = max(c[1] + c[3] for c in T); th = int(np.median([c[3] for c in T]))
    todos = [c for L in linhas for c in L]
    # valor: caracteres que comecam logo abaixo do titulo (faixa de ~1 altura de letra), dentro da largura do titulo
    cand = [c for c in todos if tb + 2 <= c[1] <= tb + 1.4 * th and c[0] >= tx0 and c[0] + c[2] <= tx1]
    dig = [c for c in cand if 0.65 * th <= c[3] <= 0.95 * th]
    if dig:
        t0 = min(c[1] for c in dig); hd = float(np.median([c[3] for c in dig]))
        L = sorted([c for c in cand if t0 - 6 <= c[1] <= t0 + 0.8 * hd and c[1] + c[3] <= t0 + hd + 16], key=lambda c: c[0])
        if len(L) == len(alvo): val = L
    if val is None:
        for L in linhas:
            if len(L) == len(alvo) and L[alvo.index(',')][3] < 0.6 * max(c[3] for c in L): val = L
    if val is None:
        raise SystemExit(f"{r['id']}: nao achei a linha '{r['atual']} m²' (linhas com {[len(L) for L in linhas]} caracteres)")
    for ch, comp in zip(alvo, val):
        lib.setdefault(ch, []).append(glifo(comp))
    info.append((r, val))

base = min(c[1] + c[3] for _, v in info for c in v if True)  # nao usado; linha base vem de cada rotulo
log = []
for r, val in info:
    if r['novo'] == r['atual']:
        continue  # so serviu de fonte de glifos
    xs =[c[0] for c in val]; xe = [c[0] + c[2] for c in val]
    ys = [c[1] for c in val]; ye = [c[1] + c[3] for c in val]
    bx0, bx1, by0, by1 = min(xs), max(xe), min(ys), max(ye)
    linha_base = int(np.median([c[1] + c[3] for c, k in zip(val, r['atual'].replace(' ', '') + 'm²') if k.isdigit()]))  # base dos algarismos (sem virgula, m e 2)
    cx = (bx0 + bx1) / 2
    # espacamento medio entre caracteres e espaco antes de m
    gaps = [val[i + 1][0] - (val[i][0] + val[i][2]) for i in range(len(val) - 3)]
    gap = float(np.median(gaps)) if gaps else 6
    gap_m = val[-2][0] - (val[-3][0] + val[-3][2])
    # 2) apaga a linha antiga com textura vizinha (faixa de mesma altura logo abaixo, senao acima)
    pad = 10
    X0, X1, Y0, Y1 = bx0 - pad, bx1 + pad, by0 - pad, by1 + pad
    h = Y1 - Y0
    # escolhe o deslocamento cuja moldura (anel de 8 px) mais combina com a moldura do lugar do texto
    w_ = X1 - X0; anel = np.ones((h, w_), bool); anel[8:-8, 8:-8] = False
    alvo_anel = im[Y0:Y1, X0:X1][anel].astype(float)
    melhor = None
    for dy in list(range(-3 * h, -h - 4, 6)) + list(range(h + 4, 3 * h, 6)) + [0]:
        for dx in (0, -w_ // 3, w_ // 3, -w_ // 2, w_ // 2) if dy else (-w_ - 10, w_ + 10):
            src = im[Y0 + dy:Y1 + dy, X0 + dx:X1 + dx]
            if src.shape[:2] != (h, w_): continue
            sf = src.astype(int)
            branco = ((sf.min(axis=2) > 215) & (sf.max(axis=2) - sf.min(axis=2) < 30)).mean()
            nota = np.abs(src[anel].astype(float) - alvo_anel).mean() + branco * 400
            if melhor is None or nota < melhor[0]: melhor = (nota, dy, dx)
    _, dy, dx = melhor
    src = im[Y0 + dy:Y1 + dy, X0 + dx:X1 + dx].astype(float)
    pena = np.ones((h, X1 - X0), np.float32)
    pena = cv2.copyMakeBorder(np.ones((h - 12, X1 - X0 - 12), np.float32), 6, 6, 6, 6, cv2.BORDER_CONSTANT, value=0)
    pena = cv2.GaussianBlur(pena, (0, 0), 3)[:, :, None]
    out[Y0:Y1, X0:X1] = (src * pena + out[Y0:Y1, X0:X1] * (1 - pena)).astype(np.uint8)
    # 3) escreve o valor novo
    texto = r['novo'].replace(' ', '') + 'm²'
    gl = [lib[ch][0] for ch in texto]
    larg = sum(g['w'] for g in gl) + gap * (len(gl) - 3) + gap_m
    x = cx - larg / 2
    for i, (ch, g) in enumerate(zip(texto, gl)):
        if ch in 'm²':
            ref = [c for c, k in zip(val, r['atual'].replace(' ', '') + 'm²') if k == ch][0]
            top = ref[1]
        elif ch == ',':
            ref = [c for c, k in zip(val, r['atual'].replace(' ', '') + 'm²') if k == ','][0]
            top = ref[1]
        else:
            top = linha_base - g['h']
        p = 4
        xi, yi = int(round(x)) - p, int(top) - p
        A = g['alpha'][:, :, None]
        reg = out[yi:yi + A.shape[0], xi:xi + A.shape[1]].astype(float)
        out[yi:yi + A.shape[0], xi:xi + A.shape[1]] = (g['cor'] * A + reg * (1 - A)).astype(np.uint8)
        x += g['w'] + (gap_m if i == len(gl) - 3 else gap)
    log.append(dict(id=r['id'], de=r['atual'], para=r['novo'], caixa=[X0, Y0, X1, Y1], textura_dy=int(dy), textura_dx=int(dx)))
    if a.debug:
        os.makedirs(a.debug, exist_ok=True)
        m = 160
        antes = im[Y0 - m:Y1 + m, X0 - m:X1 + m]; depois = out[Y0 - m:Y1 + m, X0 - m:X1 + m]
        cv2.imwrite(os.path.join(a.debug, f"rotulo_{r['id']}.png"), np.hstack([antes, np.full((antes.shape[0], 8, 3), 255, np.uint8), depois]))

cv2.imwrite(a.saida, out)
json.dump(log, open(os.path.splitext(a.saida)[0] + '_log.json', 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print(json.dumps(log, ensure_ascii=False))
