"""OCR nos recortes finais; texto de area/S./T. que sobrou vira item 'apagar' (caixa) no config.
uso: corrigir.py config.json  -> imprime ids a regerar"""
import sys, json, re, numpy as np, pytesseract
from PIL import Image
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from plantas import carregar, mascara_unidade, ler_config
from auto_apagar import gerar
from grupos import grupos
Image.MAX_IMAGE_PIXELS = None
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
RUIM = re.compile(r'(\d[,.]\d{2})|m[²2?*]$|^\d?[²]$|^(S|T)\.|VRN|Garden', re.I)
cp = sys.argv[1]; c = ler_config(cp)
_, alpha = carregar(c['planta']); FH, FW = alpha.shape; f = FW / 2000
novos, refazer = [], []
for k, un in c['unidades'].items():
    m = mascara_unidade(un, c.get('angulo', 0), 2000, round(FH / f), (FH, FW), f); m[alpha == 0] = 0
    ys, xs = np.where(m > 0); x0, y0 = xs.min(), ys.min()
    im = Image.open(c['saida'] + '/' + c['nome'].format(id=k)).convert('RGB'); a = np.array(im).astype(int)
    bw = np.where((a.mean(2) < 110) & (a.max(2) - a.min(2) < 30), 0, 255).astype(np.uint8)
    toks = []
    for esc in (0.5, 0.75):
        b = Image.fromarray(bw); b = b.resize((int(b.width * esc), int(b.height * esc)), Image.LANCZOS)
        d = pytesseract.image_to_data(b, config='--psm 11', output_type=pytesseract.Output.DICT)
        for i, t in enumerate(d['text']):
            t = t.strip()
            if not t or float(d['conf'][i]) < 20: continue
            X = (d['left'][i] / esc + x0) / f; Y = (d['top'][i] / esc + y0) / f
            if any(abs(X - o['x']) < 4 and abs(Y - o['y']) < 4 for o in toks): continue
            toks.append(dict(t=t, x=X, y=Y, w=d['width'][i] / esc / f, h=d['height'][i] / esc / f))
    ruins = [t for t in toks if RUIM.search(t['t'])]
    if not ruins: continue
    gs = [g for g in grupos(a, lim=c.get('limiar_escuro', 62), f=f) if g[4] >= 4]
    H_, W_ = a.shape[:2]
    pr = min(gs, key=lambda g: ((g[0] + g[2]) / 2 - W_ / 2) ** 2 + ((g[1] + g[3]) / 2 - H_ / 2) ** 2) if gs else None
    def no_principal(t):
        if not pr: return False
        X = t['x'] * f - x0 + t['w'] * f / 2; Y = t['y'] * f - y0 + t['h'] * f / 2; hh = pr[3] - pr[1]
        return pr[0] - hh < X < pr[2] + hh and pr[1] - hh < Y < pr[3] + hh
    # pega a linha da area + rotulo S./T. acima (mesma logica do auto) e tambem tokens S./T. sozinhos
    its = gerar(toks)
    its += [{"frame": "o", "centro": it["centro"], "obs": "bloco3 " + it["obs"],
             "bloco": True if it["obs"].startswith("rotulo") else "linha"} for it in list(its)]
    for t in ruins:
        if re.match(r'^(S|T)\.|VRN|Garden', t['t'], re.I) or re.match(r'^(S|T)\.', t['t']):
            its.append({"frame": "o", "centro": [t['x'] + t['w'] / 2, t['y'] + t['h'] / 2], "bloco": True, "obs": 'bloco solto: ' + t['t']})
        if not any(abs(it['centro'][0] - (t['x'] + t['w'] / 2)) < it.get('largura', 0) / 2 + 2 and abs(it['centro'][1] - (t['y'] + t['h'] / 2)) < it.get('altura', 0) / 2 + 2 for it in its):
            its.append({"frame": "o", "centro": [t['x'] + t['w'] / 2, t['y'] + t['h'] / 2], "largura": t["w"] + 20, "altura": t["h"] + 5, "caixa": True, "obs": 'solto: ' + t['t']})
            its.append({"frame": "o", "centro": [t['x'] + t['w'] / 2, t['y'] + t['h'] / 2], "bloco": "linha", "obs": 'bloco2 solto: ' + t['t']})
    for it in its: it['obs'] = f'corr {k}: ' + it['obs']
    novos += its; refazer.append(k)
    print(k, [t['t'] for t in ruins], file=sys.stderr)
c['apagar'] += novos
json.dump(c, open(cp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(' '.join(f'"{k}"' for k in refazer))
