"""Extrai, da prancha aprovada (PDF vetorial de areas legais), a regiao de cada unidade.

Metodo: watershed com sementes nos rotulos.
- Area privativa = rosa (coberta), creme (garden), cinza claro (faixa de sacadas/A.T.) e demais manchas
  coloridas claras da prancha; cotas vermelhas/azuis dentro dela nao cortam a celula.
- Sementes de UNIDADE: posicao da palavra do codigo em cada rotulo (APTO/GARDEN/Sacada/MEZANINO NNN, LOJA 0N).
  Todos os rotulos do mesmo codigo usam a mesma semente-id -> a regiao final une coberta + garden + sacada.
- Sementes de AREA COMUM: palavras como CIRCULACAO, ELEVADORES, TECNICA, MEDIDORES, DEPOSITO, A.T. etc.
- Fundo: fora da area privativa.
As fronteiras ficam nas linhas de divisa (gradiente), inclusive tracejadas, sem vazamento.

Uso: python celulas_pdf.py <aprovado.pdf> <pagina> <rotulos.json> <saida.json> <debug.png> [--janela x0,y0,x1,y1] [--esc 3]
"""
import sys, json, argparse, re, unicodedata
import fitz, cv2, numpy as np

ap = argparse.ArgumentParser()
for k in ('pdf', 'pagina', 'rotulos', 'saida', 'debug'): ap.add_argument(k)
ap.add_argument('--janela', default=''); ap.add_argument('--correcoes', default='', help='JSON: [{"pagina":7,"de":"317","para":"316","tipo":"SACADA","area":1.15,"evidencia":"..."}]'); ap.add_argument('--esc', type=float, default=3.0)
a = ap.parse_args()
pagina = int(a.pagina); ESC = a.esc
pg = fitz.open(a.pdf)[pagina - 1]
rot = [r for r in json.load(open(a.rotulos, encoding='utf-8')) if r['page'] == pagina]
if a.janela:
    clip = fitz.Rect(*[float(v) for v in a.janela.split(',')])
    rot = [r for r in rot if fitz.Rect(r['bbox']).intersects(clip)]
else:
    cx = np.array([(r['bbox'][0] + r['bbox'][2]) / 2 for r in rot]); cy = np.array([(r['bbox'][1] + r['bbox'][3]) / 2 for r in rot])
    mx, my = np.median(cx), np.median(cy)
    rot = [r for r, x, y in zip(rot, cx, cy) if abs(x - mx) < 700 and abs(y - my) < 450]
    clip = fitz.Rect(min(r['bbox'][0] for r in rot) - 120, min(r['bbox'][1] for r in rot) - 90,
                     max(r['bbox'][2] for r in rot) + 120, max(r['bbox'][3] for r in rot) + 90)
correcoes_aplicadas = []
if a.correcoes:
    for c in json.load(open(a.correcoes, encoding='utf-8')):
        if c['pagina'] != pagina: continue
        for rr in rot:
            if rr['code'] == c['de'] and rr.get('tipo') == c.get('tipo') and abs(rr['area'] - c['area']) < 0.005:
                rr['code_original'] = rr['code']; rr['code'] = c['para']; correcoes_aplicadas.append(c)
pix = pg.get_pixmap(matrix=fitz.Matrix(ESC, ESC), clip=clip)
im = np.frombuffer(pix.samples, np.uint8).reshape(pix.h, pix.w, pix.n)[:, :, :3][:, :, ::-1].copy()
b, g, r = [im[:, :, i].astype(int) for i in range(3)]
mx_, mn_ = np.maximum(np.maximum(b, g), r), np.minimum(np.minimum(b, g), r)
# area privativa: qualquer mancha clara/colorida (prancha colore unidades), exceto branco puro e linhas escuras
colorida = (mx_ > 150) & (mx_ - mn_ > 12) & (mn_ > 60)
faixa = (abs(b - 240) <= 4) & (abs(g - 240) <= 4) & (abs(r - 240) <= 4)
vermelho = (r > 150) & (g < 120) & (b < 120); azul = (b > 150) & (r < 120) & (g < 160)
base = (colorida | faixa) & ~vermelho & ~azul
priv = base | ((vermelho | azul) & (cv2.dilate(base.astype(np.uint8), np.ones((7, 7), np.uint8)) > 0))
priv = priv.astype(np.uint8)


def pt2px(x, y):
    return int(round((x - clip.x0) * ESC)), int(round((y - clip.y0) * ESC))


def norm(t):
    return unicodedata.normalize('NFKD', t).encode('ascii', 'ignore').decode().upper()

palavras = [w for w in pg.get_text('words') if fitz.Rect(w[:4]).intersects(clip)]
COMUNS = {'CIRCULACAO', 'CIRC.', 'ELEVADORES', 'TECNICA', 'MEDIDORES', 'DEPOSITO', 'SEGREGADOR', 'COMUM',
          'INTERMEDIARIO', 'ATINGIMENTO', 'A.T.', 'RESERVATORIO', 'BARRILETE', 'LIXO', 'VAGA',
          'LAZER', 'PISCINA', 'FLOREIRA', 'INT.', 'FECHADO', 'COBERTO', 'ABERTO', 'HALL', 'RECEPCAO'}
sementes = []  # (codigo, x_px, y_px)
for rr in rot:
    cod_palavra = rr.get('code_original', rr['code'])
    alvo = cod_palavra[1:] if cod_palavra.startswith('L') else cod_palavra
    bx = rr['bbox']
    cand = [w for w in palavras if w[4].lstrip('0') == alvo.lstrip('0') and w[0] >= bx[0] - 3 and w[2] <= bx[2] + 3 and w[1] >= bx[1] - 3 and w[3] <= bx[3] + 3]
    w = cand[0] if cand else bx
    sementes.append((rr['code'], *pt2px((w[0] + w[2]) / 2, (w[1] + w[3]) / 2)))
for i, w in enumerate(palavras):
    t = norm(w[4])
    if t == 'LOJA' and i + 1 < len(palavras) and re.fullmatch(r'0?\d', palavras[i + 1][4]):
        w2 = palavras[i + 1]; sementes.append(('L' + w2[4][-1], *pt2px((w2[0] + w2[2]) / 2, (w2[1] + w2[3]) / 2)))
    elif t in COMUNS:
        sementes.append(('_COMUM', *pt2px((w[0] + w[2]) / 2, (w[1] + w[3]) / 2)))

ids = {}
markers = np.zeros(priv.shape, np.int32)
fundo = cv2.dilate(priv, np.ones((9, 9), np.uint8)) == 0
markers[fundo] = 1
# sementes so em regioes reais (>= 0,5 m2); evita cair no miolo de algarismos ('0', '8', '9')
nc, lc, sc, _ = cv2.connectedComponentsWithStats(priv, 4)
min_px = (0.5 / (0.0254 / 72 * 100) ** 2) * ESC ** 2
grande = np.zeros(nc, bool); grande[1:] = sc[1:, 4] >= min_px
ys_p, xs_p = np.where((priv > 0) & grande[lc])
for code, x, y in sementes:
    if code not in ids: ids[code] = len(ids) + 2
    # semente no pixel privativo mais proximo (o texto em si e escuro)
    k = np.argmin((xs_p - x) ** 2 + (ys_p - y) ** 2)
    if (xs_p[k] - x) ** 2 + (ys_p[k] - y) ** 2 > (12 * ESC) ** 2: continue
    cv2.circle(markers, (int(xs_p[k]), int(ys_p[k])), max(2, int(ESC)), ids[code], -1)
    markers[(markers == ids[code]) & (priv == 0)] = 0
# regioes fechadas (pelas linhas) sem nenhuma semente de unidade = area comum (corredor, hall, escada...)
if '_COMUM' not in ids: ids['_COMUM'] = len(ids) + 2
tem_unid = set(np.unique(lc[(markers > 1) & (markers != ids['_COMUM'])]))
for c in range(1, nc):
    if c not in tem_unid and sc[c, 4] >= min_px:
        markers[(lc == c) & (markers == 0)] = ids['_COMUM']
ws = cv2.watershed(im, markers.copy())

celulas = {}
for code, idx in ids.items():
    if code == '_COMUM': continue
    m = ((ws == idx) & (priv > 0)).astype(np.uint8)
    if m.sum() == 0:
        celulas[code] = dict(erro='sem_regiao'); continue
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    polys = [[[float(p[0][0] / ESC + clip.x0), float(p[0][1] / ESC + clip.y0)] for p in c] for c in cs if cv2.contourArea(c) > 30 * ESC]
    areas_rot = sorted({(x.get('tipo', 'COBERTA'), x['area']) for x in rot if x['code'] == code})
    celulas[code] = dict(poligonos_pt=polys, area_poligono_papel_cm2=round(float(m.sum()) / ESC ** 2 * (2.54 / 72) ** 2, 2),
                         rotulos=[list(t) for t in areas_rot], n_partes=len(polys))
json.dump(dict(pagina=pagina, clip_pt=[clip.x0, clip.y0, clip.x1, clip.y1], esc=ESC, celulas=celulas, correcoes_aplicadas=correcoes_aplicadas),
          open(a.saida, 'w', encoding='utf-8'), indent=1)
dbg = im.copy(); rng = np.random.default_rng(3)
for code, idx in ids.items():
    col = np.array((200, 200, 200) if code == '_COMUM' else rng.integers(30, 230, 3))
    sel = (ws == idx) & (priv > 0)
    dbg[sel] = (0.45 * dbg[sel] + 0.55 * col).astype(np.uint8)
    if code != '_COMUM':
        ys, xs = np.where(ws == idx)
        if len(xs): cv2.putText(dbg, code, (int(np.median(xs)) - 20, int(np.median(ys))), cv2.FONT_HERSHEY_SIMPLEX, 0.5 * ESC / 2, (0, 0, 0), max(1, int(ESC / 2)))
dbg[ws == -1] = (0, 0, 255)
cv2.imwrite(a.debug, dbg)
print(json.dumps(dict(pagina=pagina, unidades=len([c for c in celulas]), sem_regiao=[c for c, v in celulas.items() if 'erro' in v],
                      partes={c: v.get('n_partes') for c, v in celulas.items() if v.get('n_partes', 1) > 3})))
