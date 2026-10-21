"""Sobreposicao em ALTA resolucao: prancha aprovada (linhas + textos, em vermelho) sobre a humanizada em tamanho cheio,
usando o registro de sobrepoe_aprovado.py. Corta em mosaico para inspecao zona a zona (o QC por chamfer nao ve
ambientes, equipamentos e acessos que mudaram; essa leitura e visual).

Uso: py overlay_alta.py <registro.json> <render_cheio.png> <largura_render_do_registro> <x0,y0,x1,y1 pt> <saida_prefixo> --pdf <aprovado.pdf> [--tiles 3x2]
"""
import argparse, json
import fitz, cv2, numpy as np

ap = argparse.ArgumentParser()
ap.add_argument('registro'); ap.add_argument('render'); ap.add_argument('larg_reg', type=float)
ap.add_argument('clip'); ap.add_argument('prefixo'); ap.add_argument('--tiles', default='3x2')
ap.add_argument('--pdf', required=True, help='PDF aprovado (Autodoc 2.1.c.a) do mesmo registro')
a = ap.parse_args()
T = json.load(open(a.registro))
(sx, _, tx), (_, sy, ty) = T['A']; fat = T['fator_reducao']; cx, cy = T['clip_pt'][:2]; zoom = 2.0
im = cv2.imread(a.render, cv2.IMREAD_UNCHANGED)
if im.shape[2] == 4:
    al = im[:, :, 3:4] / 255.0; im = (im[:, :, :3] * al + 255 * (1 - al)).astype(np.uint8)
R = im.shape[1] / a.larg_reg
kx, ky = R * sx * zoom / fat, R * sy * zoom / fat
clip = fitz.Rect(*[float(v) for v in a.clip.split(',')])
X0 = int(round(R * (((clip.x0 - cx) * zoom) * sx + tx) / fat)); Y0 = int(round(R * (((clip.y0 - cy) * zoom) * sy + ty) / fat))
pg = fitz.open(a.pdf)[T['pagina'] - 1]
pix = pg.get_pixmap(matrix=fitz.Matrix(kx, ky), clip=clip, colorspace=fitz.csGRAY)
P = np.frombuffer(pix.samples, np.uint8).reshape(pix.h, pix.w)
ov = (im * 0.55 + 255 * 0.45).astype(np.uint8)
ys, xs = np.nonzero(P < 110); xs2, ys2 = xs + X0, ys + Y0
ok = (xs2 >= 0) & (xs2 < im.shape[1]) & (ys2 >= 0) & (ys2 < im.shape[0])
ov[ys2[ok], xs2[ok]] = (0, 0, 220)
cv2.imwrite(a.prefixo + '_overlay_alta.jpg', ov, [cv2.IMWRITE_JPEG_QUALITY, 85])
json.dump(dict(kx=kx, ky=ky, X0=X0, Y0=Y0, clip=list(clip)), open(a.prefixo + '_pt2px.json', 'w'))
# mosaico sobre a area do predio
yy, xx = ys2[ok], xs2[ok]
bx0, bx1, by0, by1 = np.percentile(xx, 1), np.percentile(xx, 99), np.percentile(yy, 1), np.percentile(yy, 99)
nc, nl = [int(v) for v in a.tiles.split('x')]
tw, th = (bx1 - bx0) / nc, (by1 - by0) / nl
for j in range(nl):
    for i in range(nc):
        x0, y0 = int(bx0 + i * tw - 150), int(by0 + j * th - 150)
        c = ov[max(0, y0):int(y0 + th + 300), max(0, x0):int(x0 + tw + 300)]
        f = 1500 / max(c.shape[:2])
        cv2.imwrite(f'{a.prefixo}_zona_{j}{i}.jpg', cv2.resize(c, None, fx=f, fy=f), [cv2.IMWRITE_JPEG_QUALITY, 85])
print(a.prefixo, kx, ky, X0, Y0)
