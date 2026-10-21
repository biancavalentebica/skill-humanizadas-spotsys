"""Rasteriza as camadas do PDF Legal (legal_work.pdf) no quadro do lancamento (registro registra_legal.py).
Uso: py legal_masks.py <pagina> <P>  -> legal_<P>_masks.npz"""
import sys, json, fitz, numpy as np, cv2
pn, P = int(sys.argv[1]), sys.argv[2]
A = np.load('../do_zero/' + P + '_amb.npz'); H, W = A['paredes'].shape
R = json.load(open(f'legal_{P}_reg.json')); Mp = np.array(R['pt_rot_para_px'], np.float32)
d = fitz.open('legal_work.pdf'); p = d[pn - 1]
def key(dr):
    c = dr.get('color'); f = dr.get('fill'); w = round(dr.get('width') or 0, 2)
    if f is not None and max(f) < 0.05: return 'fill_preto'
    if c is None: return 'outro'
    if max(c) < 0.05: return f'preto_{w}'
    return 'cor_%.2f_%.2f_%.2f' % tuple(c)
ks = {}
for dr in p.get_drawings():
    k = key(dr); r = dr['rect']
    # texto (fonte de traco do AutoCAD) e cotas: desenhos pequenos -> camada propria "<k>_txt"
    if k != 'preto_1.8' and max(r.width, r.height) < 9: k = k + '_txt'
    if dr.get('dashes') not in (None, '', '[] 0') and not k.endswith('_txt'): k = k + '_tr'      # tracejado (projecoes)
    if k == 'preto_1.8':
        import math
        diag = [it for it in dr['items'] if it[0] == 'l' and 10 < math.degrees(math.atan2(abs(it[2].y - it[1].y), abs(it[2].x - it[1].x))) < 80]
        if diag and len(diag) == len(dr['items']):
            import numpy as _np, cv2 as _cv
            pts = _np.array([[q.x, q.y] for it in dr['items'] for q in (it[1], it[2])], _np.float32)
            (_, _), (a_, b_), _ = _cv.minAreaRect(pts)
            if min(a_, b_) < 0.10 * 56.69 and max(a_, b_) > 0.5 * 56.69: k = 'preto_1.8_diag'   # folha de porta (barra fina)
    ks.setdefault(k, []).append(dr)
SS = 2; out = {}
for k, v in ks.items():
    t = fitz.open(); q = t.new_page(width=p.mediabox.width, height=p.mediabox.height); sh = q.new_shape()
    for dr in v:
        for it in dr['items']:
            if it[0] == 'l': sh.draw_line(it[1], it[2])
            elif it[0] == 're': sh.draw_rect(it[1])
            elif it[0] == 'c': sh.draw_bezier(*it[1:])
            elif it[0] == 'qu': sh.draw_quad(it[1])
        sh.finish(color=(0, 0, 0), fill=(0, 0, 0) if k == 'fill_preto' else None, width=0.5)
    sh.commit(); q.set_rotation(p.rotation)
    s = float(np.hypot(*Mp[:, 0]))      # px por pt
    pix = q.get_pixmap(matrix=fitz.Matrix(s * SS, s * SS)); a = np.frombuffer(pix.samples, np.uint8).reshape(pix.h, pix.w, pix.n)[..., 0]
    M2 = Mp.copy(); M2[:, :2] /= (s * SS) / 1.0; M2[:, :2] *= s / s     # pt*sSS -> px: px = Mp @ (u/(s*SS))
    M2 = Mp.copy(); M2[:, :2] = Mp[:, :2] / (s * SS)
    w = cv2.warpAffine((255 - a), M2, (W, H), flags=cv2.INTER_AREA)
    out[k.replace('.', '_')] = w
    print(k, int((w > 60).sum()))
np.savez_compressed(f'legal_{P}_masks.npz', **out)
