"""Geometria do R06 (prancha 04) no referencial da humanizada de lancamento do terreo (4000x2000)."""
import fitz, numpy as np, cv2
PDF = '00_entradas/originais/projeto_aprovado/CACHOEIRASPOT-PL-ARQ-DCT-GER-XXX-000-R06.pdf'
LANC = '00_entradas/originais/humanizada_lancamento_2024/1 - terreo.png'
K = 2.299
def px(x, y): return 813 + (x - 301) * K, 55 + (y - 141.5) * K
def pt(u, v): return 301 + (u - 813) / K, 141.5 + (v - 55) / K
CORES = {'preto': (0, 0, 0), 'cinza': (0.3647, 0.3647, 0.3647), 'roxo': (0.502, 0, 1), 'vermelho': (0.792, 0, 0)}
def classe(c):
    if c is None: return None
    for k, v in CORES.items():
        if all(abs(a - b) < 0.02 for a, b in zip(c, v)): return k
    return 'outra'
def segmentos(pagina=4, clip=(290, 120, 1320, 700)):
    p = fitz.open(PDF)[pagina - 1]; r = fitz.Rect(*clip); out = []
    for d in p.get_drawings():
        if not fitz.Rect(d['rect']).intersects(r) or d['type'] != 's': continue
        k = classe(d.get('color'))
        for it in d['items']:
            if it[0] == 'l': out.append((k, it[1].x, it[1].y, it[2].x, it[2].y, d.get('dashes')))
            elif it[0] == 're':
                R = it[1]
                for a, b in [((R.x0, R.y0), (R.x1, R.y0)), ((R.x1, R.y0), (R.x1, R.y1)), ((R.x1, R.y1), (R.x0, R.y1)), ((R.x0, R.y1), (R.x0, R.y0))]:
                    out.append((k, a[0], a[1], b[0], b[1], d.get('dashes')))
    return out

def poligonos(pagina=4, clip=(290, 120, 1320, 700)):
    """Areas preenchidas do aprovado (contorno de cada ambiente computavel/garden/descoberta)."""
    p = fitz.open(PDF)[pagina - 1]; r = fitz.Rect(*clip); out = []
    for d in p.get_drawings():
        if d['type'] != 'f' or not fitz.Rect(d['rect']).intersects(r): continue
        pts = []
        for it in d['items']:
            if it[0] == 'l':
                if not pts: pts.append((it[1].x, it[1].y))
                pts.append((it[2].x, it[2].y))
            elif it[0] == 're':
                R = it[1]; pts += [(R.x0, R.y0), (R.x1, R.y0), (R.x1, R.y1), (R.x0, R.y1)]
        f = d['fill']; tipo = 'computavel' if f[0] > 0.8 and f[1] < 0.1 else 'descoberta' if abs(f[0] - 0.753) < 0.01 else 'garden' if f[1] > 0.8 else 'outra'
        out.append(dict(tipo=tipo, pts=pts, rect=list(d['rect']), opac=d.get('fill_opacity')))
    return out

def rotulos(pagina=4, clip=(290, 120, 1320, 700)):
    p = fitz.open(PDF)[pagina - 1]; out = []
    for b in p.get_text('dict')['blocks']:
        for l in b.get('lines', []):
            s = ' '.join(x['text'] for x in l['spans']).strip()
            x0, y0, x1, y1 = l['bbox']
            if s and clip[0] < x0 < clip[2] and clip[1] < y0 < clip[3]: out.append((s, (x0 + x1) / 2, (y0 + y1) / 2))
    return out
