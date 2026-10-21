"""Separa o PDF Legal (vetorial, texto em curvas) em camadas por cor/espessura e rasteriza cada camada na pagina
girada (como se ve a prancha). Uso: py legal_camadas.py <pagina 1-based> <dpi> <prefixo> [x0f y0f x1f y1f]"""
import sys, fitz, numpy as np
from PIL import Image
pn, dpi, pref = int(sys.argv[1]), float(sys.argv[2]), sys.argv[3]
fr = [float(v) for v in sys.argv[4:8]] if len(sys.argv) > 4 else [0, 0, 1, 1]
src = fitz.open('../../00_entradas/originais/executivo/LAGOA SPOT - Legal.pdf'); p = src[pn - 1]
mb = p.mediabox; rot = p.rotation
def key(d):
    c = d.get('color'); f = d.get('fill'); w = round(d.get('width') or 0, 2)
    if f is not None and max(f) < 0.05: return 'fill_preto'
    if c is None: return 'outro'
    if max(c) < 0.05: return f'preto_{w}'
    return 'cor_%.2f_%.2f_%.2f' % tuple(c)
ks = {}
for d in p.get_drawings(): ks.setdefault(key(d), []).append(d)
out = {}
for k, v in ks.items():
    doc = fitz.open(); q = doc.new_page(width=mb.width, height=mb.height); sh = q.new_shape()
    for d in v:
        for it in d['items']:
            if it[0] == 'l': sh.draw_line(it[1], it[2])
            elif it[0] == 're': sh.draw_rect(it[1])
            elif it[0] == 'c': sh.draw_bezier(*it[1:])
            elif it[0] == 'qu': sh.draw_quad(it[1])
        sh.finish(color=(0, 0, 0), fill=(0, 0, 0) if k == 'fill_preto' else None, width=max(d.get('width') or 0.3, 0.3))
    sh.commit(); q.set_rotation(rot)
    pix = q.get_pixmap(matrix=fitz.Matrix(dpi / 72, dpi / 72)); a = np.frombuffer(pix.samples, np.uint8).reshape(pix.h, pix.w, pix.n)[..., 0]
    H, W = a.shape; a = a[int(fr[1] * H):int(fr[3] * H), int(fr[0] * W):int(fr[2] * W)]
    out[k] = (255 - a)
np.savez_compressed(pref + '.npz', **out)
print({k: int((v > 60).sum()) for k, v in out.items()}, a.shape)
