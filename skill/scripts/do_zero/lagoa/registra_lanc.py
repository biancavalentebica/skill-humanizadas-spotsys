"""Registra o raster do executivo (raster_exec.py) na humanizada de lancamento: mesma escala; acha translacao (e
rotacao pequena) por correlacao das paredes. Saida <prefixo>_reg.json com a matriz exec_px -> lanc_px e um overlay.
Uso: py registra_lanc.py <prefixo> <lancamento.png>"""
import sys, json, numpy as np, cv2
from PIL import Image; Image.MAX_IMAGE_PIXELS = None
pref, lanc = sys.argv[1:3]
M = np.load(pref + '_masks.npz')
par = ((M['parede_ext'] > 60) | (M['parede_int'] > 60)).astype(np.float32)
L = np.array(Image.open(lanc).convert('RGB')).astype(np.int16)
lum = L.mean(axis=2)
# paredes do lancamento: preto/cinza escuro
pl = (lum < 70).astype(np.float32)
H = max(par.shape[0], pl.shape[0]); W = max(par.shape[1], pl.shape[1])
def pad(a): z = np.zeros((H, W), np.float32); z[:a.shape[0], :a.shape[1]] = a; return z
A, B = pad(par), pad(pl)
f = 0.25
a, b = cv2.resize(A, None, fx=f, fy=f, interpolation=cv2.INTER_AREA), cv2.resize(B, None, fx=f, fy=f, interpolation=cv2.INTER_AREA)
(dx, dy), r = cv2.phaseCorrelate(cv2.GaussianBlur(a, (0, 0), 3), cv2.GaussianBlur(b, (0, 0), 3))
dx, dy = dx / f, dy / f
print('fase', round(dx, 1), round(dy, 1), round(r, 3))
warp = np.array([[1, 0, dx], [0, 1, dy]], np.float32)
try:
    a2 = cv2.resize(A, None, fx=0.5, fy=0.5); b2 = cv2.resize(B, None, fx=0.5, fy=0.5)
    w2 = warp.copy(); w2[:, 2] /= 2
    _, w2 = cv2.findTransformECC(cv2.GaussianBlur(b2, (0, 0), 2), cv2.GaussianBlur(a2, (0, 0), 2), w2, cv2.MOTION_EUCLIDEAN,
                                 (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 200, 1e-6), None, 5)
    warp = w2.copy(); warp[:, 2] *= 2
except cv2.error as e: print('ecc falhou', e)
print('matriz', warp.tolist(), 'rot', round(np.degrees(np.arctan2(warp[1, 0], warp[0, 0])), 3))
json.dump(dict(exec_para_lanc=warp.tolist()), open(pref + '_reg.json', 'w'), indent=1)
pw = cv2.warpAffine(par, warp, (L.shape[1], L.shape[0]))
ov = (L * 0.5 + 127).astype(np.uint8); ov[pw > 0.5] = (220, 0, 0)
Image.fromarray(ov).resize((ov.shape[1] // 3, ov.shape[0] // 3)).save(pref + '_reg_overlay.jpg', quality=85)
inter = ((pw > .5) & (pl > .5)).sum() / max((pw > .5).sum(), 1); print('paredes do exec sobre parede do lanc', round(inter, 3))
