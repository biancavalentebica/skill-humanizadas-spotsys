"""A partir do OCR, gera itens 'apagar' (modo caixa): toda linha de area (12,34 m2) e,
se a linha de cima for rotulo de S./T./VRN/Garden, ela tambem. A linha 'UN 101 A' fica."""
import json, re
AREA = re.compile(r'^\d{1,2}[,.]\d{1,2}')
PREF = re.compile(r'^(S\.|T\.|VRN|Garden|GARDEN|Gard|T\.UN|S\.UN|s\.)', re.I)
def linha(tok, toks, gap=30):
    """tokens na mesma linha e encostados (em x) ao token."""
    L = [tok]; mudou = True
    while mudou:
        mudou = False
        x0 = min(t['x'] for t in L); x1 = max(t['x'] + t['w'] for t in L); yc = tok['y'] + tok['h'] / 2
        for t in toks:
            if t in L: continue
            if abs(t['y'] + t['h'] / 2 - yc) < max(tok['h'], 3) * 0.6 and t['x'] < x1 + gap * tok['h'] / 8 and t['x'] + t['w'] > x0 - gap * tok['h'] / 8:
                L.append(t); mudou = True
    return L
def caixa(L, obs, px=6, py=1.5):
    x0 = min(t['x'] for t in L) - px; x1 = max(t['x'] + t['w'] for t in L) + px
    y0 = min(t['y'] for t in L) - py; y1 = max(t['y'] + t['h'] for t in L) + py
    return {"frame": "o", "centro": [round((x0 + x1) / 2, 1), round((y0 + y1) / 2, 1)], "largura": round(x1 - x0, 1),
            "altura": round(y1 - y0, 1), "caixa": True, "obs": obs}
def gerar(ocr, verbose=False):
    toks = json.load(open(ocr, encoding='utf-8')) if isinstance(ocr, str) else ocr
    toks = [t for t in toks if re.search(r'[A-Za-z0-9]{1}', t['t']) and not re.fullmatch(r'[\W_]*[A-Za-z]?[\W_]*', t['t']) or AREA.match(t['t']) or t['t'] in ('A', 'S.', 'T.', 'm?', 'm²')]
    import statistics
    hs = [t['h'] for t in toks if AREA.match(t['t'])]
    if hs:
        hm = statistics.median(hs)
        toks = [t for t in toks if t['h'] <= 1.6 * hm and t['w'] <= 12 * hm]
    toks = [t for t in toks if t['t'] not in ('|', 'JE', 'eu', '“', '+', '==')]
    itens, usados = [], set()
    for t in toks:
        if not AREA.match(t['t']) or id(t) in usados: continue
        L = [x for x in linha(t, toks, gap=12)]
        for x in L: usados.add(id(x))
        h = t['h']; yc = t['y']
        cima = [x for x in toks if 0.6 * h < yc - x['y'] < 2.6 * h and x['x'] < max(a['x'] + a['w'] for a in L) + 15 and x['x'] + x['w'] > min(a['x'] for a in L) - 15]
        rot = ''
        if cima:
            prox = min(cima, key=lambda x: yc - x['y'])
            LC = linha(prox, toks, gap=12); rot = ' '.join(x['t'] for x in sorted(LC, key=lambda x: x['x']))
            if PREF.match(rot.replace(' ', '')) or PREF.match(rot):
                itens.append(caixa(LC + L, 'rotulo+area: ' + rot, px=14, py=3)); continue
        itens.append(caixa(L, 'area de: ' + rot))
    return itens
if __name__ == '__main__':
    import sys
    for it in gerar(sys.argv[1]): print(it['obs'], it['centro'], it['largura'], it['altura'])
