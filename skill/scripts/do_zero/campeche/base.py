"""Geometria do legal aprovado R00 do Campeche Spot (prancha 03, Pavimento 1) a 1 cm/px.
Ambientes = regioes fechadas pelos tracos pretos, semeadas nos rotulos da prancha."""
import fitz, cv2, numpy as np
PDF = '00_entradas/originais/projeto_aprovado/CAMPECHESPOT-PL-ARQ-DCT-TOT-XXX-000-R00.pdf'
PAG = 3
Z = 2.54 / 72 * 100
CLIP = fitz.Rect(370, 180, 1500, 1110)
W, H = int(CLIP.width * Z), int(CLIP.height * Z)
pg = fitz.open(PDF)[PAG - 1]
def px(x, y): return ((x - CLIP.x0) * Z, (y - CLIP.y0) * Z)


def raster(cores=((0, 0, 0),), tol=0.03, sem_texto=True):
    doc = fitz.open(); p = doc.new_page(width=pg.rect.width, height=pg.rect.height); sh = p.new_shape()
    for d in pg.get_drawings():
        if d['type'] != 's': continue
        c = d.get('color')
        if c is None or not any(all(abs(a - b) < tol for a, b in zip(c, k)) for k in cores): continue
        for it in d['items']:
            if it[0] == 'l': sh.draw_line(it[1], it[2])
            elif it[0] == 're': sh.draw_rect(it[1])
            elif it[0] == 'c': sh.draw_bezier(*it[1:])
            elif it[0] == 'qu': sh.draw_quad(it[1])
        sh.finish(color=(0, 0, 0), width=max(d.get('width') or 0.3, 0.3))
    sh.commit()
    pix = p.get_pixmap(matrix=fitz.Matrix(Z, Z), clip=CLIP, colorspace=fitz.csGRAY)
    return np.frombuffer(pix.samples, np.uint8).reshape(pix.h, pix.w)[:H, :W] < 140


def rotulos():
    out = []
    for b in pg.get_text('dict')['blocks']:
        for l in b.get('lines', []):
            s = ' '.join(x['text'] for x in l['spans']).strip(); x0, y0, x1, y1 = l['bbox']
            cx, cy = px((x0 + x1) / 2, (y0 + y1) / 2)
            if s and 0 <= cx < W and 0 <= cy < H: out.append((s, cx, cy, l.get('dir', (1, 0))))
    return out
