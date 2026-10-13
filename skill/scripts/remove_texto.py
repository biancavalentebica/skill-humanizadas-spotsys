"""Remove textos (numeros de unidade, areas, rotulos) de uma planta humanizada raster SEM tocar na geometria.

Principio: o texto e as paredes tem a mesma cor (preto). O texto e separado pela FORMA:
componentes conexos pequenos, de altura parecida, alinhados em linha (horizontal ou vertical).
Paredes sao componentes longos/grandes e nunca entram na mascara.
Somente os pixels das letras (+ borda antialias) sao reconstruidos por inpainting.

Uso: python remove_texto.py <entrada.png> <saida.png> <debug.png> [--limiar 60]
Saidas: imagem sem texto (mesmas dimensoes, mesmo canal alfa) e imagem de depuracao com as linhas
de texto detectadas em vermelho. Escreve um JSON ao lado da saida com as caixas removidas.
"""
import sys, json, argparse
import cv2
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument('entrada'); ap.add_argument('saida'); ap.add_argument('debug')
ap.add_argument('--limiar', type=int, default=12, help='cinza maximo considerado tinta preta (texto renderizado em preto puro)')
ap.add_argument('--hmin', type=int, default=0, help='altura minima de glifo (px); 0 = automatico')
ap.add_argument('--fundo-min', type=int, default=100, help='cinza mediano minimo do fundo de uma linha de texto (grama/deck escuro: 60)')
ap.add_argument('--caixas-manuais', default='', help='x0,y0,x1,y1;... texto que o detector nao pega (ex.: letra colada em esquadria). Linhas que atravessam a caixa inteira sao preservadas.')
ap.add_argument('--hmax', type=int, default=0, help='altura maxima de glifo (px); 0 = automatico')
a = ap.parse_args()

im = cv2.imread(a.entrada, cv2.IMREAD_UNCHANGED)
bgr = im[:, :, :3]
alpha = im[:, :, 3] if im.shape[2] == 4 else np.full(im.shape[:2], 255, np.uint8)
H, W = bgr.shape[:2]
esc = W / 3840.0  # parametros calibrados em 3840 px de largura
hmin = a.hmin or max(6, int(14 * esc))
hmax = a.hmax or int(80 * esc)
gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
gray[alpha == 0] = 255  # transparente conta como fundo claro
ink = ((gray <= a.limiar) & (alpha > 0)).astype(np.uint8)


def glifos(ink_img):
    n, lab, st, cen = cv2.connectedComponentsWithStats(ink_img, 8)
    out = []
    for i in range(1, n):
        x, y, w, h, ar = st[i]
        if h < hmin or h > hmax or w > hmax * 1.6 or ar < 8:
            continue
        fill = ar / float(w * h)
        if fill > 0.85 and h / max(w, 1) < 3:  # blocos solidos (cooktop, pes de movel)
            continue
        out.append((x, y, w, h, i))
    return out, lab


def linhas(gs):
    """agrupa glifos em linhas horizontais: centros alinhados e espacamento curto."""
    gs = sorted(gs, key=lambda g: g[0])
    usados, grupos = set(), []
    for k, g in enumerate(gs):
        if k in usados:
            continue
        grupo = [g]; usados.add(k)
        mudou = True
        while mudou:
            mudou = False
            x1 = max(q[0] + q[2] for q in grupo)
            cy = np.median([q[1] + q[3] / 2 for q in grupo]); hm = np.median([q[3] for q in grupo])
            for j, q in enumerate(gs):
                if j in usados:
                    continue
                if abs((q[1] + q[3] / 2) - cy) < 0.45 * hm and 0.5 < q[3] / hm < 1.8 and q[0] - x1 < 0.9 * hm and q[0] + q[2] > min(p[0] for p in grupo) - 0.9 * hm:
                    grupo.append(q); usados.add(j); mudou = True
        if len(grupo) >= 2:
            hs = np.array([q[3] for q in grupo])
            if hs.std() / hs.mean() >= 0.35:
                # remove glifos-intrusos (ex.: '1' colado a ripa de deck): altura muito acima da mediana
                med = np.median(hs)
                grupo = [q for q in grupo if q[3] <= 1.3 * med]
                hs = np.array([q[3] for q in grupo])
            if len(grupo) >= 2 and hs.std() / hs.mean() < 0.35:
                grupos.append(grupo)
    return grupos


def fundo_claro(gray_img, ink_img, bx, minimo=100):
    """texto de planta fica sobre fundo claro; bancadas/loucas tem fundo escuro ou medio."""
    x0, y0, x1, y1 = max(0, bx[0]), max(0, bx[1]), bx[2], bx[3]
    g = gray_img[y0:y1, x0:x1]; k = ink_img[y0:y1, x0:x1]
    halo = cv2.dilate(k, np.ones((5, 5), np.uint8), iterations=2) > 0
    fundo = g[~halo]
    if fundo.size == 0: return False
    # texto de planta nao fica sobre mancha escura grande (granito, bancada, pe de movel): rejeita
    tinta = float((k > 0).mean())
    if tinta > 0.5: return False  # bloco quase todo preto (granito, pe de movel), nao e texto
    return np.median(fundo) >= minimo and np.percentile(fundo, 20) >= minimo - 45


def mascara_texto(ink_img, min_glifos, gray_img, minimo_fundo=100, sat_img=None, permite_2=True):
    """devolve (mascara dos glifos, caixas). Mascara = so os componentes que formam linhas de texto
    + componentes minusculos (virgula, ponto, expoente) dentro da caixa da linha."""
    gs, lab = glifos(ink_img)
    n, lab_all, st, _ = cv2.connectedComponentsWithStats(ink_img, 8)
    ids, res, parciais = set(), [], []
    for gr in linhas(gs):
        if len(gr) < min_glifos:
            hm_g = float(np.median([q[3] for q in gr]))
            # palavra curta (WC, G., S.): aceita se tiver 2 glifos com a altura tipica do texto da prancha
            if not (permite_2 and len(gr) == 2 and ALTURA_TIPICA and abs(hm_g - ALTURA_TIPICA) / ALTURA_TIPICA < 0.12):
                continue
        x0 = min(q[0] for q in gr); y0 = min(q[1] for q in gr)
        x1 = max(q[0] + q[2] for q in gr); y1 = max(q[1] + q[3] for q in gr)
        hm = float(np.median([q[3] for q in gr]))
        bx = [int(x0 - .35 * hm), int(y0 - .3 * hm), int(x1 + .9 * hm), int(y1 + .35 * hm)]
        if not fundo_claro(gray_img, ink_img, bx, minimo_fundo):
            continue
        if len(gr) <= 3:
            xa_, ya_ = max(0, bx[0]), max(0, bx[1]); sub_ = gray_img[ya_:bx[3], xa_:bx[2]]; k_ = ink_img[ya_:bx[3], xa_:bx[2]]
            f_ = sub_[cv2.dilate(k_, np.ones((5, 5), np.uint8), iterations=2) == 0]
            colorido = sat_img is not None and float(np.median(sat_img[ya_:bx[3], xa_:bx[2]])) > 60  # deck, grama
            if not colorido and f_.size and float(((f_ > 15) & (f_ < 90)).mean()) > 0.15:  # granulado escuro (granito/louca): nao e rotulo
                continue
        ids.update(q[4] for q in gr)
        cy = (y0 + y1) / 2
        for q in gs:  # glifo isolado de mesma altura/baseline a ate 1.8 alturas (ex.: prefixo 'G.')
            if q[4] in ids: continue
            if abs((q[1] + q[3] / 2) - cy) < 0.3 * hm and 0.8 < q[3] / hm < 1.25 and (x0 - 1.8 * hm < q[0] + q[2] <= x0 or x1 <= q[0] < x1 + 1.8 * hm):
                ids.add(q[4]); x0 = min(x0, q[0]); x1 = max(x1, q[0] + q[2])
        bx = [int(x0 - .35 * hm), int(y0 - .3 * hm), int(x1 + .9 * hm), int(y1 + .35 * hm)]
        bp = [int(x0 - .6 * hm), int(y0 - .6 * hm), int(x1 + 1.4 * hm), int(y1 + .45 * hm)]  # busca de sinais pequenos
        sub = lab_all[max(0, bp[1]):bp[3], max(0, bp[0]):bp[2]]
        for i in np.unique(sub):
            if i == 0: continue
            x, y, w, h, ar = st[i]
            if h <= hm * 0.75 and w <= hm and x >= bp[0] and y >= bp[1] and x + w <= bp[2] and y + h <= bp[3]:
                ids.add(int(i))  # virgula, ponto, "2" do m2
            elif hm * 1.3 < h and w <= hm and x < bx[2] and x + w > bx[0]:
                # glifo colado a uma linha fina (ripa de deck, rejunte): apaga so a faixa da linha de texto
                parciais.append((int(i), max(0, bx[0]), max(0, int(y0 - .15 * hm)), bx[2], int(y1 + .15 * hm)))
        res.append(bx + [len(gr), hm])
    m = np.isin(lab_all, list(ids)).astype(np.uint8) * 255
    for i, px0, py0, px1, py1 in parciais:
        sub = lab_all[py0:py1, px0:px1] == i
        m[py0:py1, px0:px1][sub] = 255
    return m, res


ALTURA_TIPICA = None
SAT = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)[:, :, 1]
SAT_ROT = np.ascontiguousarray(np.rot90(SAT))
_, cx_pre = mascara_texto(ink, 3, gray, a.fundo_min, SAT)
if cx_pre: ALTURA_TIPICA = float(np.median([b[5] for b in cx_pre]))
m_h, cx_h = mascara_texto(ink, 3, gray, a.fundo_min, SAT)  # >=3 glifos: evita pares de pecas de moveis; prefixos curtos (G., S.) sao anexados
rot = np.ascontiguousarray(np.rot90(ink))  # rot90 anti-horario
m_v_rot, cx_v_rot = mascara_texto(rot, 3, np.ascontiguousarray(np.rot90(gray)), a.fundo_min, SAT_ROT, permite_2=False)   # vertical exige >=3 glifos (evita loucas/moveis)
m_v = np.ascontiguousarray(np.rot90(m_v_rot, -1))
cx_v = [[W - 1 - y1, x0, W - 1 - y0, x1, n, hm] for x0, y0, x1, y1, n, hm in cx_v_rot]
boxes = [b + ['h'] for b in cx_h] + [b + ['v'] for b in cx_v]

# componentes "parede": grandes; nunca entram na mascara
n, lab, st, _ = cv2.connectedComponentsWithStats(ink, 8)
grande = np.zeros(n, bool)
for i in range(1, n):
    x, y, w, h, ar = st[i]
    grande[i] = (w > hmax * 1.6 or h > hmax * 1.6 or ar > (hmax ** 2))
mask_par = grande[lab]

# halo antialias: dilata 2 px e limita a pixels mais escuros que o fundo local
mask = cv2.dilate(np.maximum(m_h, m_v), np.ones((3, 3), np.uint8), iterations=3)
mask[mask_par] = 0  # garantia: nenhuma parede e alterada
for cx in filter(None, a.caixas_manuais.split(';')):
    x0, y0, x1, y1 = [int(v) for v in cx.split(',')]
    escuro = (gray[y0:y1, x0:x1] <= 150)
    linha_v = escuro.mean(axis=0) > 0.9   # coluna escura de ponta a ponta = linha do desenho, nao letra
    linha_h = escuro.mean(axis=1) > 0.9
    sub = escuro.copy(); sub[:, linha_v] = False; sub[linha_h, :] = False
    sub = cv2.dilate(sub.astype(np.uint8), np.ones((3, 3), np.uint8), iterations=2).astype(bool)
    sub[:, linha_v] = False; sub[linha_h, :] = False
    mask[y0:y1, x0:x1][sub] = 255

def preenche_por_deslocamento(img, alp, msk, caixas_lin):
    """Para cada caixa de texto, procura (matchTemplate com mascara) o deslocamento cuja BORDA ao redor
    das letras melhor combina com a vizinhanca e copia apenas os pixels das letras desse ponto.
    Preserva texturas regulares (deck, piso, ceramica) sem borrar. Nao inventa elementos: so copia
    o fundo adjacente. Retorna imagem, alfa e mascara do que nao achou par (vai para Telea)."""
    out = img.copy(); alo = alp.copy(); falta = msk.copy()
    # zona proibida como FONTE: letras + halo de 3 px (o acerto de tom posterior elimina o 'fantasma')
    proib = cv2.dilate((msk > 0).astype(np.uint8), np.ones((7, 7), np.uint8))
    Hh, Ww = msk.shape
    for bx in caixas_lin:
        x0, y0, x1, y1 = max(0, bx[0]), max(0, bx[1]), min(Ww, bx[2]), min(Hh, bx[3])
        m = msk[y0:y1, x0:x1] > 0
        if not m.any(): continue
        bw, bh = x1 - x0, y1 - y0
        anel = ((cv2.dilate(m.astype(np.uint8), np.ones((9, 9), np.uint8)) > 0) & ~m).astype(np.float32)
        if anel.sum() < 20: continue
        wx0, wy0 = max(0, x0 - bw), max(0, y0 - bh); wx1, wy1 = min(Ww, x1 + bw), min(Hh, y1 + bh)
        win = img[wy0:wy1, wx0:wx1].astype(np.float32); tpl = img[y0:y1, x0:x1].astype(np.float32)
        if win.shape[0] < bh or win.shape[1] < bw: continue
        res = cv2.matchTemplate(win, tpl, cv2.TM_SQDIFF, mask=cv2.merge([anel] * 3))
        npx = anel.sum() * 3
        ring_vals = tpl[anel > 0]
        if float(ring_vals.std()) < 8:  # fundo liso: Telea + acerto de tom fica melhor que copiar (evita fantasma)
            continue
        tol = max(14.0, 0.6 * float(ring_vals.std()))
        ordem = np.argsort(res, axis=None)
        for k in ordem[:400]:
            ry, rx = np.unravel_index(k, res.shape)
            sx0, sy0 = wx0 + rx, wy0 + ry
            if sx0 == x0 and sy0 == y0: continue
            rmse = (max(res[ry, rx], 0) / npx) ** 0.5
            if rmse > tol: break
            if (msk[sy0:sy0 + bh, sx0:sx0 + bw][m] > 0).any() or proib[sy0:sy0 + bh, sx0:sx0 + bw][m].any(): continue
            out[y0:y1, x0:x1][m] = img[sy0:sy0 + bh, sx0:sx0 + bw][m]
            alo[y0:y1, x0:x1][m] = alp[sy0:sy0 + bh, sx0:sx0 + bw][m]
            falta[y0:y1, x0:x1][m] = 0
            break
    return out, alo, falta


base, alpha_desl, falta = preenche_por_deslocamento(bgr, alpha, mask, [b[:4] for b in boxes])
limpo = cv2.inpaint(base, falta, max(3, int(5 * esc)), cv2.INPAINT_TELEA)
# acerto de tom por mancha (cada glifo/grupo de glifos): o preenchido deve ter a media do fundo logo ao redor,
# senao o formato das letras aparece como "fantasma" mais escuro/claro
nm_, lm_, sm_, _ = cv2.connectedComponentsWithStats((mask > 0).astype(np.uint8), 8)
for i_ in range(1, nm_):
    x_, y_, w0, h0, _a = sm_[i_]
    pad = 12
    xa, ya, xb, yb = max(0, x_ - pad), max(0, y_ - pad), min(W, x_ + w0 + pad), min(H, y_ + h0 + pad)
    mk = lm_[ya:yb, xa:xb] == i_
    anel = (cv2.dilate(mk.astype(np.uint8), np.ones((9, 9), np.uint8)) > 0) & ~mk & (mask[ya:yb, xa:xb] == 0) & ~mask_par[ya:yb, xa:xb]
    if anel.sum() < 20: continue
    reg_ = limpo[ya:yb, xa:xb].astype(np.float32)
    delta = np.median(reg_[anel], axis=0) - np.median(reg_[mk], axis=0)
    if np.abs(delta).max() > 40 or np.abs(delta).max() < 1: continue
    w_ = cv2.GaussianBlur(mk.astype(np.float32), (7, 7), 0)[..., None]  # aplica com borda suave
    reg_ = np.clip(reg_ + w_ * delta, 0, 255)
    limpo[ya:yb, xa:xb] = reg_.astype(np.uint8)
n_desl, n_telea = int(((mask > 0) & (falta == 0)).sum()), int((falta > 0).sum())
if im.shape[2] == 4:
    # alfa tambem e reconstruido: texto sobre area transparente volta a ser transparente
    alpha_novo = cv2.inpaint(alpha_desl, falta, max(3, int(5 * esc)), cv2.INPAINT_TELEA)
    alpha_novo[(mask > 0) & (alpha_novo < 235)] = 0  # borda de texto sobre transparente: some por inteiro
    saida = np.dstack([limpo, np.where(mask > 0, alpha_novo, alpha)])
else:
    saida = limpo
cv2.imwrite(a.saida, saida)

dbg = bgr.copy()
dbg[mask > 0] = (0, 0, 255)
for x0, y0, x1, y1, *_ in boxes:
    cv2.rectangle(dbg, (x0, y0), (x1, y1), (0, 0, 255), 2)
cv2.imwrite(a.debug, dbg)
# reverificacao: o mesmo detector na imagem limpa deve achar 0 linhas de texto
g2 = cv2.cvtColor(limpo, cv2.COLOR_BGR2GRAY); a2 = saida[:, :, 3] if saida.ndim == 3 and saida.shape[2] == 4 else alpha
g2[a2 == 0] = 255
ink2 = ((g2 <= a.limiar) & (a2 > 0)).astype(np.uint8)
_, resid_h = mascara_texto(ink2, 3, g2, min(60, a.fundo_min - 10), SAT)
_, resid_v = mascara_texto(np.ascontiguousarray(np.rot90(ink2)), 3, np.ascontiguousarray(np.rot90(g2)), min(60, a.fundo_min - 10), SAT_ROT, permite_2=False)
info = dict(entrada=a.entrada, texto_residual_linhas=len(resid_h) + len(resid_v), caixas_residuais=[b[:4] for b in resid_h] + [b[:4] for b in resid_v], largura=W, altura=H, linhas_texto=len(boxes),
            pixels_alterados=int((mask > 0).sum()), pct_alterado=round(100 * (mask > 0).mean(), 3),
            pixels_parede_alterados=int(((mask > 0) & mask_par).sum()), pixels_por_deslocamento=n_desl, pixels_por_inpainting=n_telea, caixas=boxes)
json.dump(info, open(a.saida.rsplit('.', 1)[0] + '_remocao.json', 'w', encoding='utf-8'), indent=1)
print(json.dumps({k: v for k, v in info.items() if k not in ('caixas', 'caixas_residuais')}))
