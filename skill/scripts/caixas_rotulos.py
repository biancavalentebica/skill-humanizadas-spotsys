"""Localiza os rotulos de uma humanizada (OCR nativo do Windows em blocos, resolucao cheia) e monta o JSON de caixas
para remove_rotulos_terreo.py --caixas: linhas a remover e titulos "UND." a manter. A linha da area logo abaixo de
cada titulo UND. entra para remocao mesmo que o OCR nao a tenha lido.

Uso: py caixas_rotulos.py <humanizada.png> <saida.json> [--pasta 03_trabalho/entrada/ocr_<nome>] [--extra x0,y0,x1,y1;...]
"""
import argparse, json, os, re, subprocess, glob
from PIL import Image
Image.MAX_IMAGE_PIXELS = None

ap = argparse.ArgumentParser()
ap.add_argument('img'); ap.add_argument('saida')
ap.add_argument('--pasta', default='')
ap.add_argument('--extra', default='', help='caixas a remover que o OCR nao leu: x0,y0,x1,y1;...')
a = ap.parse_args()
pasta = a.pasta or os.path.join('03_trabalho', 'entrada', 'ocr_' + os.path.splitext(os.path.basename(a.img))[0])
os.makedirs(pasta, exist_ok=True)
ps1 = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'skill', 'scripts', 'ocr_windows.ps1')
im = Image.open(a.img).convert('RGB')
W, H = im.size
L = []
for x in range(0, W, 2900):
    for y in range(0, H, 2900):
        f = os.path.join(pasta, f't_{x}_{y}.png')
        im.crop((x, y, min(x + 3300, W), min(y + 3300, H))).save(f)
        js = f[:-4] + '.json'
        subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', ps1, f, js, '1.0'],
                       capture_output=True)
        try:
            d = json.load(open(js, encoding='utf-8-sig'))
        except Exception:
            continue
        d = d if isinstance(d, list) else [d]
        for l in d:
            ws = l['palavras'] if isinstance(l['palavras'], list) else [l['palavras']]
            L.append((l['texto'], int(min(w['x'] for w in ws)) + x, int(min(w['y'] for w in ws)) + y,
                      int(max(w['x'] + w['w'] for w in ws)) + x, int(max(w['y'] + w['h'] for w in ws)) + y))
out = []
for t in sorted(L, key=lambda r: (r[2], r[1])):                                  # tira repetidos da sobreposicao
    if any(abs(t[1] - o[1]) < 40 and abs(t[2] - o[2]) < 40 for o in out): continue
    if (t[3] - t[1]) > 1500 or (t[4] - t[2]) > 300: continue                     # nao e rotulo (mancha grande)
    if len(re.sub(r'[^A-Za-z0-9]', '', t[0])) < 2: continue                     # ruido (O, -, .)
    out.append(t)
manter, remover = [], []
for (t, x0, y0, x1, y1) in out:
    h = y1 - y0
    if re.match(r'^\s*UN[DO0]', t, re.I):
        manter.append([x0, y0, x1, y1, t])
        remover.append([x0 - 12, y1 + int(0.12 * h), x1 + 40, y1 + int(1.95 * h), 'auto', 'area de ' + t])
    else:
        remover.append([x0 - 12, y0 - 10, x1 + 12, y1 + 10, 'auto', t])
for e in [c for c in a.extra.split(';') if c.strip()]:
    x0, y0, x1, y1 = map(int, e.split(','))
    remover.append([x0, y0, x1, y1, 'auto', 'manual'])
json.dump(dict(imagem=a.img, manter=manter, remover=remover), open(a.saida, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print(len(manter), 'titulos UND. mantidos;', len(remover), 'linhas a remover')
for m in manter: print('  manter', m)
for r in remover: print('  remover', r)
