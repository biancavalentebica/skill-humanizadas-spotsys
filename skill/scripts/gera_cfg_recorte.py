"""Ponte com a skill da Raquel (seazone-tech/plantas-humanizadas): gera o cfg_<PAV>.json do
recortar_tipologias.py AUTOMATICAMENTE a partir do DWG aprovado, sem marcar sementes a mao.

Cada zona do DWG (rotulo "203 | 20,22 m2", "201 Sacada | 1,29 m2"...) vira semente da unidade;
CIRCULACAO / ESCADA / AREA TECNICA / HALL viram common_seeds. As sementes caem em piso aberto
(longe de parede e de movel) dentro do poligono da zona, no quadro da planta gerada por gera_humanizada_dwg.py.
Zona sem numero no DWG (terreo/mezanino: "APTO", "MEZANINO", "GARDEN") recebe o numero pela etiqueta do
PDF aprovado (rotulos_aprovado.json) que cai dentro dela, levada ao quadro pelo transform do registro.

Tambem grava <saida>_zonas.json: {codigo: [{tipo, area_m2, pts_mm}]} (para as pecas da Planta Viva).

Uso: python gera_cfg_recorte.py <pav.dxf> <planta.png> <planta_quadro.json> <saida_cfg.json> <out_dir>
        [--rotulos rotulos_aprovado.json --transform <PAV>_transform.json --transform-cm-px 0.6]
"""
import re, sys, json, argparse
import ezdxf, cv2, numpy as np
from matplotlib.path import Path as MPath

ap = argparse.ArgumentParser()
for k in ('dxf', 'planta', 'quadro', 'saida', 'out_dir'): ap.add_argument(k)
ap.add_argument('--rotulos', default=''); ap.add_argument('--transform', default='')
ap.add_argument('--transform-cm-px', type=float, default=0.6)
a = ap.parse_args()
Q = json.load(open(a.quadro))
img = cv2.imdecode(np.fromfile(a.planta, np.uint8), cv2.IMREAD_COLOR); H, W = img.shape[:2]   # aceita acentos no caminho
para_img = lambda x, y: ((x - Q['X0']) * Q['px_por_mm'], (Q['Y1'] - y) * Q['px_por_mm'])
d = ezdxf.readfile(a.dxf); m = d.modelspace()

# etiquetas do PDF aprovado levadas ao quadro (numero das unidades onde o DWG nao escreve)
etiq = []
if a.rotulos and a.transform:
    T = json.load(open(a.transform, encoding='utf-8'))
    A = np.array(T['A_pdfpx_para_img'] + [[0, 0, 1]])
    A[:2] *= a.transform_cm_px / (1.0 / (Q['px_por_mm'] * 10))
    for r in json.load(open(a.rotulos, encoding='utf-8')):
        if r['page'] != T['pagina']: continue
        cx, cy = (r['bbox'][0] + r['bbox'][2]) / 2, (r['bbox'][1] + r['bbox'][3]) / 2
        u, v, _ = A @ [(cx - T['clip_pt'][0]) * T['esc'], (cy - T['clip_pt'][1]) * T['esc'], 1]
        etiq.append((r['code'], u, v))

rot = []
for e in m.query('INSERT'):
    if 'ZONA' not in e.dxf.layer.upper(): continue
    ts = [t for t in e.virtual_entities() if t.dxftype() in ('MTEXT', 'TEXT')]
    if ts:
        txt = ' '.join((t.plain_text() if t.dxftype() == 'MTEXT' else t.dxf.text).replace('^', ' ') for t in ts)
        rot.append((txt, ts[0].dxf.insert.x, ts[0].dxf.insert.y))

# piso aberto: cinza claro pouco saturado e liso (sem movel, sem parede)
g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
sat = img.max(2).astype(int) - img.min(2).astype(int)
liso = cv2.blur((g - cv2.blur(g, (9, 9))) ** 2, (9, 9)) < 40
piso = ((g > 170) & (g < 235) & (sat < 18) & liso).astype(np.uint8)
piso = cv2.morphologyEx(piso, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))

escala = W / 1800.0
units, common, zonas = {}, [], {}
poli_unid, poli_comum = [], []
for e in m.query('LWPOLYLINE'):
    if 'ZONA' not in e.dxf.layer.upper() or len(e) < 3: continue
    pts = [(p[0], p[1]) for p in e.get_points('xy')]
    dentro = [r for r in rot if MPath(pts).contains_point((r[1], r[2]))]
    if not dentro: continue
    txt = dentro[0][0]
    mc = re.match(r'\s*(\d{3})\b', txt)
    code = mc.group(1) if mc else None
    if not code and re.match(r'\s*(APTO|MEZANINO|GARDEN|LOJA)', txt, re.I) and etiq:
        pimg = MPath([para_img(x, y) for x, y in pts])
        cand = [c for c, u, v in etiq if pimg.contains_point((u, v))]
        cand = [c for c in cand if re.fullmatch(r'\d{3}|L\d', c)]
        if cand: code = max(set(cand), key=cand.count)
    comum = re.search(r'CIRCULA|ESCADA|HALL|T.CNICA|\bA\.T\.?|PISO INTERMEDI', txt, re.I) and not code
    if not code and not comum: continue
    mz = np.zeros((H, W), np.uint8)
    cv2.fillPoly(mz, [np.array([para_img(x, y) for x, y in pts], np.int32)], 1)
    alvo = (mz & piso) if (mz & piso).sum() > 200 else mz
    dist = cv2.distanceTransform(alvo, cv2.DIST_L2, 5)
    externo = re.search(r'SACADA|GARDEN', txt, re.I)
    sementes = []
    for _ in range(1 if externo else 2):
        if dist.max() < 3: break
        yy, xx = np.unravel_index(np.argmax(dist), dist.shape)
        sementes.append([round(xx / escala, 1), round(yy / escala, 1)])
        cv2.circle(dist, (int(xx), int(yy)), int(dist.max() * 2.5) + 20, 0, -1)
    if comum:
        common += sementes; poli_comum.append(MPath(pts))
    else:
        units.setdefault(code, []).extend(sementes)
        if not externo: poli_unid.append(pts)
        ma = re.search(r'(\d+,\d{2})\s*m', txt)
        tipo = 'garden' if re.search('GARDEN', txt, re.I) else 'sacada' if re.search('SACADA', txt, re.I) else \
               'mezanino' if re.search('MEZANINO', txt, re.I) else 'unidade'
        zonas.setdefault(code, []).append(dict(tipo=tipo, area_m2=float(ma.group(1).replace(',', '.')) if ma else None,
                                               pts_mm=[[round(x, 1), round(y, 1)] for x, y in pts]))

# vaos de porta: a divisa unidade x corredor (zona comum) vira extra_wall -> a porta fica fechada no recorte
extra = []
off = 300.0   # mm para fora da divisa
for pts in poli_unid:
    pu = MPath(pts)
    for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]):
        L = np.hypot(x1 - x0, y1 - y0)
        if L < 500: continue
        nx, ny = -(y1 - y0) / L, (x1 - x0) / L
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        for sgn in (1, -1):
            q = (mx + sgn * nx * off, my + sgn * ny * off)
            if not pu.contains_point(q) and any(pc.contains_point(q) for pc in poli_comum):
                a_, b_ = para_img(x0, y0), para_img(x1, y1)
                extra.append([round(a_[0] / escala, 1), round(a_[1] / escala, 1), round(b_[0] / escala, 1), round(b_[1] / escala, 1)])
                break
cfg = dict(semtexto=a.planta.replace('\\', '/'), out_dir=a.out_dir.replace('\\', '/'), seed_scale=round(escala, 4),
           common_seeds=common, units=dict(sorted(units.items())), extra_walls=extra, pad=20,
           origem='gerado automaticamente do DWG aprovado (gera_cfg_recorte.py)')
json.dump(cfg, open(a.saida, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
json.dump(dict(quadro=Q, zonas=zonas), open(a.saida[:-5] + '_zonas.json', 'w', encoding='utf-8'), ensure_ascii=False)
print('unidades', len(units), '| sementes comuns', len(common), '| paredes de porta', len(extra), '| escala', round(escala, 3))
