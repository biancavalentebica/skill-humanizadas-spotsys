"""Geometria do aprovado R06 (prancha 04, terreo) em metros/pixels da planta nova (1 cm/px).
Tudo o que a humanizada nova desenha (paredes, unidades, escadas, circulacao, equipamentos) sai daqui."""
import fitz, cv2, numpy as np
from matplotlib.path import Path

PDF = '00_entradas/originais/projeto_aprovado/CACHOEIRASPOT-PL-ARQ-DCT-GER-XXX-000-R06.pdf'
PAG = 4
Z = 2.54 / 72 * 100          # cm por pt na escala 1:100 = px por pt (1 cm/px)
O = (250.0, 100.0)            # pt da origem do quadro
W, H = int((1400 - 250) * Z), int((800 - 100) * Z)
def px(x, y): return ((x - O[0]) * Z, (y - O[1]) * Z)
pg = fitz.open(PDF)[PAG - 1]


def raster(cores=((0, 0, 0),), tol=0.03, larg_min=0.0):
    """So os tracos com essas cores, sem texto, no quadro da planta."""
    doc = fitz.open(); p = doc.new_page(width=pg.rect.width, height=pg.rect.height)
    sh = p.new_shape()
    for d in pg.get_drawings():
        if d['type'] != 's': continue
        c = d.get('color')
        if c is None or not any(all(abs(a - b) < tol for a, b in zip(c, k)) for k in cores): continue
        for it in d['items']:
            if it[0] == 'l': sh.draw_line(it[1], it[2])
            elif it[0] == 're': sh.draw_rect(it[1])
            elif it[0] == 'c': sh.draw_bezier(*it[1:])
        sh.finish(color=(0, 0, 0), width=max(d.get('width') or 0.3, larg_min))
    sh.commit()
    pix = p.get_pixmap(matrix=fitz.Matrix(Z, Z), clip=fitz.Rect(O[0], O[1], O[0] + W / Z, O[1] + H / Z), colorspace=fitz.csGRAY)
    return np.frombuffer(pix.samples, np.uint8).reshape(pix.h, pix.w)[:H, :W] < 128


def rotulos():
    out = []
    for b in pg.get_text('dict')['blocks']:
        for l in b.get('lines', []):
            s = ' '.join(x['text'] for x in l['spans']).strip()
            x0, y0, x1, y1 = l['bbox']
            if s: out.append((s, *px((x0 + x1) / 2, (y0 + y1) / 2)))
    return out


def areas():
    """Poligonos preenchidos (computavel/descoberta/garden) com os rotulos de dentro, em px."""
    R = rotulos(); out = []
    for d in pg.get_drawings():
        if d['type'] != 'f': continue
        pts = []
        for it in d['items']:
            if it[0] == 'l':
                if not pts: pts.append(px(it[1].x, it[1].y))
                pts.append(px(it[2].x, it[2].y))
            elif it[0] == 're':
                r = it[1]; pts += [px(r.x0, r.y0), px(r.x1, r.y0), px(r.x1, r.y1), px(r.x0, r.y1)]
        if not pts or not (0 < np.mean([p[0] for p in pts]) < W and 0 < np.mean([p[1] for p in pts]) < H): continue
        f = d['fill']
        tipo = 'computavel' if f[0] > 0.8 and f[1] < 0.1 else 'descoberta' if abs(f[0] - 0.753) < 0.01 else 'garden' if f[1] > 0.8 else 'outra'
        pa = Path(pts); labs = [s for s, x, y in R if pa.contains_point((x, y))]
        out.append(dict(tipo=tipo, pts=np.array(pts), labs=labs))
    return out


def mascara(pts):
    m = np.zeros((H, W), np.uint8); cv2.fillPoly(m, [np.round(pts).astype(np.int32)], 1); return m.astype(bool)


def unidades():
    """Cada unidade do terreo: poligono, retangulo, lado do garden, lado da circulacao, escada (mascara L)."""
    A = areas(); B = raster()
    circ = [a for a in A if a['tipo'] == 'computavel' and 'ELEVADORES' in a['labs']][0]
    Mc = cv2.dilate(mascara(circ['pts']).astype(np.uint8), np.ones((9, 9), np.uint8)) > 0
    gard = np.zeros((H, W), bool)
    for a in A:
        if a['tipo'] in ('garden', 'descoberta') and any('GARDEN' in s for s in a['labs']): gard |= mascara(a['pts'])
    Mg = cv2.dilate(gard.astype(np.uint8), np.ones((9, 9), np.uint8)) > 0
    R = rotulos(); out = {}
    for a in A:
        if a['tipo'] != 'computavel': continue
        un = [s for s in a['labs'] if s.isdigit() and len(s) == 3]
        lj = [s for s in a['labs'] if s == 'LOJA']
        if not un and not lj: continue
        M = mascara(a['pts'])
        if lj:
            x = a['pts'][:, 0].mean(); un = ['LOJA 0%d' % (1 + int(np.argmin([abs(x - c) for c in (1878, 2215, 2545)])))]
        x0, y0 = a['pts'].min(0); x1, y1 = a['pts'].max(0)
        borda = M & ~cv2.erode(M.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
        lados = dict(N=(borda[:, :] & (np.arange(H)[:, None] < y0 + 8)), S=(borda & (np.arange(H)[:, None] > y1 - 8)),
                     O=(borda & (np.arange(W)[None, :] < x0 + 8)), L=(borda & (np.arange(W)[None, :] > x1 - 8)))
        g = max(lados, key=lambda k: (lados[k] & Mg).sum()); c = max(lados, key=lambda k: (lados[k] & Mc).sum())
        # escada: regiao fechada pelos tracos pretos que contem o rotulo ESCADA dentro da unidade
        esc = None
        for s, x, y in R:
            if s == 'ESCADA' and M[int(y), int(x)]:
                ff = (~B).astype(np.uint8).copy(); ff[~M] = 0
                ff = cv2.morphologyEx(ff, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
                n, lab = cv2.connectedComponents(ff)
                k = lab[int(y), int(x)]
                if k == 0: continue
                esc = lab == k
                if esc.sum() > 0.5 * M.sum(): esc = None
        out[un[0]] = dict(pts=a['pts'], rect=(x0, y0, x1, y1), garden=g if (lados[g] & Mg).sum() > 50 else None,
                          circ=c if (lados[c] & Mc).sum() > 50 else None, escada=esc, area=[s for s in a['labs'] if 'm' in s])
    return out
