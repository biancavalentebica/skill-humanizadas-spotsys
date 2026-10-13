"""REGRA FIXA: o arquivo usado como BASE da humanizada (DWG/IFC/outro) precisa ter as MESMAS AREAS do PDF aprovado (Autodoc).

Para cada rotulo de area do DWG (zona de calculo: APTO, GARDEN, SACADA, MEZANINO, LOJA...), acha o rotulo do PDF aprovado
na mesma posicao da planta (posicao convertida DWG -> prancha pelo registro paredes x divisas) e compara os valores.

Status por rotulo:
  IGUAL        |dif| <= --tol (padrao 0,02 m2: arredondamento)
  DIFERENTE    valor diferente do aprovado -> a base NAO bate nessa unidade
  SEM_PAR      rotulo do DWG sem rotulo do aprovado por perto (area comum, tecnica...) -> informativo
Rotulos do aprovado sem par no DWG tambem sao listados (FALTA_NO_DWG).

Veredito do pavimento: BATE (nenhum DIFERENTE/FALTA_NO_DWG em unidade) ou NAO_BATE (lista as unidades).

Uso: python confere_areas_base_x_aprovado.py <pav.dxf> <quadro.json> <transform.json> <rotulos_aprovado.json> <saida.csv> [--raio-cm 150]
"""
import re, json, csv, argparse
import ezdxf, numpy as np

ap = argparse.ArgumentParser()
for k in ('dxf', 'quadro', 'transform', 'rotulos', 'saida'): ap.add_argument(k)
ap.add_argument('--raio-cm', type=float, default=150)
ap.add_argument('--tol', type=float, default=0.02)
a = ap.parse_args()
Q = json.load(open(a.quadro)); T = json.load(open(a.transform, encoding='utf-8'))
A = np.array(T['A_pdfpx_para_img'] + [[0, 0, 1]]); Ai = np.linalg.inv(A)
esc, clip = T['esc'], T['clip_pt']; pag = T['pagina']
cm_por_pt = 2.54 / 72 * T['escala_planta']

def dwg_para_pt(x, y):
    u, v = (x - Q['X0']) * Q['px_por_mm'], (Q['Y1'] - y) * Q['px_por_mm']
    p = Ai @ [u, v, 1]
    return p[0] / esc + clip[0], p[1] / esc + clip[1]

# rotulos do DWG: blocos de zona (texto "TIPO | 12,34 m2" ou "203 | 20,22 m2")
d = ezdxf.readfile(a.dxf); m = d.modelspace()
rot_dwg = []
for e in m.query('INSERT'):
    if 'ZONA' not in e.dxf.layer.upper(): continue
    txts = [t for t in e.virtual_entities() if t.dxftype() in ('MTEXT', 'TEXT')]
    if not txts: continue
    linhas = [(t.plain_text() if t.dxftype() == 'MTEXT' else t.dxf.text).replace('^', ' ').strip() for t in txts]
    full = ' | '.join(linhas)
    ma = re.search(r'(\d+,\d{2})\s*m', full)
    if not ma: continue
    ta = [t for t, l in zip(txts, linhas) if ma.group(1) in l][0]
    x, y = ta.dxf.insert.x, ta.dxf.insert.y
    mc = re.search(r'\b(\d{3})\b', full.split('|')[0]) or re.search(r'LOJA\s*0?(\d)\b', full, re.I)
    code = (mc.group(1) if len(mc.group(1)) == 3 else 'L' + mc.group(1)) if mc else None
    rot_dwg.append(dict(code=code, texto=full, area=float(ma.group(1).replace(',', '.')), pt=dwg_para_pt(x, y)))

R = [r for r in json.load(open(a.rotulos, encoding='utf-8')) if r['page'] == pag]
for r in R: r['pt'] = ((r['bbox'][0] + r['bbox'][2]) / 2, (r['bbox'][1] + r['bbox'][3]) / 2)
R = [r for r in R if clip[0] <= r['pt'][0] <= clip[2] and clip[1] <= r['pt'][1] <= clip[3]]   # so a planta principal
raio_pt = a.raio_cm / cm_por_pt
usados = set(); linhas = []; par = {}
def dist(z, r): return np.hypot(z['pt'][0] - r['pt'][0], z['pt'][1] - r['pt'][1])
def candidatos(z):
    if z['code'] and any(r['code'] == z['code'] for r in R):
        return [i for i in range(len(R)) if R[i]['code'] == z['code']]
    return list(range(len(R)))
# 1a passada: valor IGUAL (mesma unidade quando o DWG traz o numero; senao em qualquer ponto da planta, o mais proximo)
for k in sorted(range(len(rot_dwg)), key=lambda k: rot_dwg[k]['code'] is None):
    z = rot_dwg[k]
    c = [i for i in candidatos(z) if i not in usados and abs(R[i]['area'] - z['area']) <= a.tol]
    if c:
        i = min(c, key=lambda i: dist(z, R[i])); usados.add(i); par[k] = i
# 2a passada: o que sobrou -> rotulo do aprovado mais proximo (mesma unidade ou ate --raio-cm) = DIFERENTE
for k, z in enumerate(rot_dwg):
    if k in par: continue
    c = [i for i in candidatos(z) if i not in usados and (z['code'] or dist(z, R[i]) <= raio_pt)]
    if c:
        i = min(c, key=lambda i: dist(z, R[i])); usados.add(i); par[k] = i
for k, z in enumerate(rot_dwg):
    if k not in par:
        linhas.append(dict(pavimento_pagina=pag, unidade='', rotulo_dwg=z['texto'], area_dwg=z['area'], area_aprovado='', diferenca='', status='SEM_PAR'))
        continue
    i = par[k]; dif = round(z['area'] - R[i]['area'], 2)
    linhas.append(dict(pavimento_pagina=pag, unidade=R[i]['code'], rotulo_dwg=z['texto'], area_dwg=z['area'], area_aprovado=R[i]['area'],
                       diferenca=dif, status='IGUAL' if abs(dif) <= a.tol else 'DIFERENTE'))
for i, r in enumerate(R):
    if i not in usados:
        linhas.append(dict(pavimento_pagina=pag, unidade=r['code'], rotulo_dwg='', area_dwg='', area_aprovado=r['area'], diferenca='', status='FALTA_NO_DWG'))
with open(a.saida, 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.DictWriter(f, fieldnames=list(linhas[0]), delimiter=';'); w.writeheader(); w.writerows(linhas)
ruins = sorted({l['unidade'] for l in linhas if l['status'] in ('DIFERENTE', 'FALTA_NO_DWG')})
res = dict(pagina=pag, rotulos_aprovado=len(R), iguais=sum(l['status'] == 'IGUAL' for l in linhas),
           diferentes=sum(l['status'] == 'DIFERENTE' for l in linhas), falta_no_dwg=sum(l['status'] == 'FALTA_NO_DWG' for l in linhas),
           veredito='BATE' if not ruins else 'NAO_BATE', unidades_divergentes=ruins)
print(json.dumps(res, ensure_ascii=False))
