"""Overlay da prancha aprovada sobre a humanizada com transformacao fixa por ancoras (px = x0 + (pt - p0) * k).
Uso: py overlay_ancoras.py <pdf> <pagina> <clip pt> <imagem> <prefixo> --k K --ancora pt_x,pt_y,px_x,px_y [--tiles 3x2]"""
import argparse, json, fitz, cv2, numpy as np
ap = argparse.ArgumentParser()
ap.add_argument('pdf'); ap.add_argument('pagina', type=int); ap.add_argument('clip'); ap.add_argument('imagem'); ap.add_argument('prefixo')
ap.add_argument('--k', type=float, required=True); ap.add_argument('--ky', type=float, default=0)
ap.add_argument('--ancora', required=True); ap.add_argument('--tiles', default='3x2')
a = ap.parse_args()
ptx, pty, pxx, pxy = [float(v) for v in a.ancora.split(',')]
kx = a.k; ky = a.ky or a.k
im = cv2.imread(a.imagem, cv2.IMREAD_UNCHANGED)
if im.shape[2] == 4:
    al = im[:, :, 3:4] / 255.0; im = (im[:, :, :3] * al + 255 * (1 - al)).astype(np.uint8)
clip = fitz.Rect(*[float(v) for v in a.clip.split(',')])
pg = fitz.open(a.pdf)[a.pagina - 1]
pix = pg.get_pixmap(matrix=fitz.Matrix(kx, ky), clip=clip, colorspace=fitz.csGRAY)
P = np.frombuffer(pix.samples, np.uint8).reshape(pix.h, pix.w)
X0 = int(round(pxx + (clip.x0 - ptx) * kx)); Y0 = int(round(pxy + (clip.y0 - pty) * ky))
ov = (im * 0.55 + 255 * 0.45).astype(np.uint8)
ys, xs = np.nonzero(P < 110); xs2, ys2 = xs + X0, ys + Y0
ok = (xs2 >= 0) & (xs2 < im.shape[1]) & (ys2 >= 0) & (ys2 < im.shape[0])
ov[ys2[ok], xs2[ok]] = (0, 0, 220)
cv2.imwrite(a.prefixo + '_overlay_alta.jpg', ov, [cv2.IMWRITE_JPEG_QUALITY, 85])
json.dump(dict(kx=kx, ky=ky, X0=X0, Y0=Y0, clip=list(clip), ancora=[ptx, pty, pxx, pxy]), open(a.prefixo + '_pt2px.json', 'w'))
yy, xx = ys2[ok], xs2[ok]
bx0, bx1, by0, by1 = np.percentile(xx, 1), np.percentile(xx, 99), np.percentile(yy, 1), np.percentile(yy, 99)
nc, nl = [int(v) for v in a.tiles.split('x')]
tw, th = (bx1 - bx0) / nc, (by1 - by0) / nl
for j in range(nl):
    for i in range(nc):
        x0, y0 = int(bx0 + i * tw - 120), int(by0 + j * th - 120)
        c = ov[max(0, y0):int(y0 + th + 240), max(0, x0):int(x0 + tw + 240)]
        f = 1500 / max(c.shape[:2])
        cv2.imwrite(f'{a.prefixo}_zona_{j}{i}.jpg', cv2.resize(c, None, fx=f, fy=f), [cv2.IMWRITE_JPEG_QUALITY, 85])
