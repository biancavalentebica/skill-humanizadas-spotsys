"""Registra cada pagina do legal_work.pdf (paredes = traco preto 1,8) no quadro do lancamento/executivo
(do_zero/<P>_amb.npz paredes): escala 1/50 conhecida (56,69 pt/m; lancamento 248,6 px/m), translacao por correlacao
de fase e ajuste fino ECC (euclidiano). Saida legal_<P>_reg.json: matriz pt_rotacionado -> px lancamento.
Uso: py registra_legal.py <pagina 1-based> <P>"""
import sys, json, fitz, numpy as np, cv2
pn, P = int(sys.argv[1]), sys.argv[2]
A = np.load('../do_zero/' + P + '_amb.npz'); par = A['paredes'].astype(np.float32); H, W = par.shape
S = 248.6 / 56.69
d = fitz.open('legal_work.pdf'); p = d[pn - 1]
t = fitz.open(); q = t.new_page(width=p.mediabox.width, height=p.mediabox.height); sh = q.new_shape()
for dr in p.get_drawings():
    if abs((dr.get('width') or 0) - 1.8) > 0.03 or not dr.get('color') or max(dr['color']) > 0.05: continue
    for it in dr['items']:
        if it[0] == 'l': sh.draw_line(it[1], it[2])
        elif it[0] == 're': sh.draw_rect(it[1])
        elif it[0] == 'qu': sh.draw_quad(it[1])
    sh.finish(color=(0, 0, 0), width=1.8)
sh.commit(); q.set_rotation(p.rotation)
pix = q.get_pixmap(matrix=fitz.Matrix(S, S)); a = np.frombuffer(pix.samples, np.uint8).reshape(pix.h, pix.w, pix.n)[..., 0]
leg = (a < 128).astype(np.uint8)
# paredes do legal sao contornos: fecha para massa
leg = cv2.morphologyEx(leg, cv2.MORPH_CLOSE, np.ones((25, 25), np.uint8)).astype(np.float32)
HH, WW = max(H, leg.shape[0]), max(W, leg.shape[1])
def pad(x): z = np.zeros((HH, WW), np.float32); z[:x.shape[0], :x.shape[1]] = x; return z
f = 0.25
sm = lambda x: cv2.GaussianBlur(cv2.resize(pad(x), None, fx=f, fy=f, interpolation=cv2.INTER_AREA), (0, 0), 2)
(dx, dy), r = cv2.phaseCorrelate(sm(leg), sm(par))
M = np.float32([[1, 0, dx / f], [0, 1, dy / f]])
Ms = M.copy(); Ms[:, 2] *= f
try:
    _, Ms = cv2.findTransformECC(sm(par), sm(leg), Ms, cv2.MOTION_EUCLIDEAN, (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 300, 1e-6), None, 5)
except cv2.error as e: print('ecc', e)
M = Ms.copy(); M[:, 2] /= f
w = cv2.warpAffine(leg, M, (W, H)) > 0.5
print('fase', round(dx / f), round(dy / f), round(r, 3), 'M', np.round(M, 4).tolist(), 'coincide', round(float((w & (par > 0)).sum() / max(w.sum(), 1)), 3))
Mp = (np.vstack([M, [0, 0, 1]]) @ np.diag([S, S, 1]))[:2]          # pt rotacionado -> px
json.dump(dict(pt_rot_para_px=Mp.tolist(), rot=p.rotation, mediabox=[p.mediabox.width, p.mediabox.height]), open(f'legal_{P}_reg.json', 'w'), indent=1)
ov = np.full((H, W, 3), 255, np.uint8); ov[par > 0] = (150, 150, 150); ov[w] = (220, 0, 0)
cv2.imwrite(f'legal_{P}_reg.jpg', cv2.resize(ov, (W // 4, H // 4)))
