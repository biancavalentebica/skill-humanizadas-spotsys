"""Apaga restos de rotulo do vizinho que ficaram na BORDA do recorte (grupos de letras a < M px da
borda), preservando o rotulo da unidade (maior grupo). uso: limpar_bordas.py config.json"""
import sys, os, glob, json, numpy as np, cv2
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from grupos import grupos
c = json.load(open(sys.argv[1], encoding='utf-8'))
Image.MAX_IMAGE_PIXELS = None
W = Image.open(c['planta']).width; f = W / 2000
M = 30 * f
for k in c['unidades']:
    p = c['saida'] + '/' + c['nome'].format(id=k)
    im = np.array(Image.open(p).convert('RGB')); H, Wc = im.shape[:2]
    gs = grupos(im.astype(int), lim=c.get('limiar_escuro', 62), f=f)
    if not gs: continue
    cand = [g for g in gs if g[4] >= 4] or gs
    principal = min(cand, key=lambda g: ((g[0] + g[2]) / 2 - Wc / 2) ** 2 + ((g[1] + g[3]) / 2 - H / 2) ** 2)
    mask = np.zeros((H, Wc), np.uint8); n = 0
    for g in gs:
        if g is principal and g[4] >= 4: continue
        x0, y0, x1, y1, _ = g
        if min(x0, y0, Wc - x1, H - y1) > M: continue
        px0, py0, px1, py1, _ = principal; hp = py1 - py0
        if min(y1, py1) - max(y0, py0) > 0.5 * min(y1 - y0, hp) and (x0 - px1 < 2.5 * hp and px0 - x1 < 2.5 * hp):
            continue   # mesma linha do rotulo da unidade (ex.: o 'B' de 'UN 211 B')
        sub = im[y0:y1, x0:x1].astype(int)
        esc = sub.mean(2)[sub.mean(2) < 62]
        if esc.size == 0 or np.median(esc) < 15: continue   # preto puro = objeto (alca, eletro), nao texto
        mk = ((sub.mean(2) < c.get('limiar_escuro', 62) + 30) & (sub.max(2) - sub.min(2) < 30)).astype(np.uint8) * 255
        mask[y0:y1, x0:x1] |= mk; n += 1
    if n:
        mask = cv2.dilate(mask, np.ones((7, 7), np.uint8))
        out = cv2.inpaint(im, mask, 5, cv2.INPAINT_TELEA)
        Image.fromarray(out).save(p, optimize=True); print('limpo', k, n, 'grupos')
