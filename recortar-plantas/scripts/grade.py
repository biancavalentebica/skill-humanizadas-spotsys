"""Gera imagens com grade de coordenadas para medir paredes/rotulos e conferir o config.

Exemplos:
  # visao geral da planta original com grade a cada 50 px (frame de trabalho)
  python grade.py PLANTA.png --saida geral.png
  # zoom num trecho, grade a cada 10 px, ampliado 2x
  python grade.py PLANTA.png --regiao 900 680 1480 1000 --zoom 2 --passo 10 --saida z.png
  # mesmo trecho na planta girada (ala inclinada alinhada)
  python grade.py PLANTA.png --angulo -19.3 --regiao 340 100 880 560 --zoom 2 --passo 10 --saida zr.png
  # sobrepor contornos e caixas de apagar do config (conferencia)
  python grade.py PLANTA.png --config planta.json --saida conferencia.png [--angulo X]
"""
import argparse, sys, os, numpy as np, cv2
sys.path.insert(0, os.path.dirname(__file__))
from plantas import *

ap = argparse.ArgumentParser()
ap.add_argument('planta')
ap.add_argument('--saida', required=True)
ap.add_argument('--angulo', type=float, default=None, help='desenha no frame girado')
ap.add_argument('--regiao', type=float, nargs=4, default=None, help='x0 y0 x1 y1 no frame escolhido')
ap.add_argument('--zoom', type=float, default=1)
ap.add_argument('--passo', type=int, default=50)
ap.add_argument('--config', default=None)
a = ap.parse_args()

rgb, _ = carregar(a.planta)
img, f = trabalho(rgb)
Ht, Wt = img.shape[:2]
cfg = ler_config(a.config) if a.config else None
ang_cfg = cfg.get('angulo', 0) if cfg else 0
if a.angulo is not None:
    img, M = girar(img, a.angulo)
else:
    M = None

if cfg:
    cores = [(230, 0, 0), (0, 150, 0), (0, 0, 230), (190, 0, 190), (0, 140, 140)]
    for i, (k, un) in enumerate(sorted(cfg['unidades'].items())):
        cor = cores[i % len(cores)]
        m = mascara_unidade(un, ang_cfg, Wt, Ht, (Ht, Wt), 1.0)
        if M is not None:
            m = cv2.warpAffine(m, M, (img.shape[1], img.shape[0]), flags=cv2.INTER_NEAREST)
        cs = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]
        cv2.drawContours(img, cs, -1, cor, 2)
        if cs:
            x, y, w, h = cv2.boundingRect(max(cs, key=cv2.contourArea))
            cv2.putText(img, k, (x + 4, y + 16), cv2.FONT_HERSHEY_SIMPLEX, 0.5, cor, 1)
    for ap_ in cfg.get('apagar', []):
        cx, cy = ap_['centro']
        w = ap_.get('largura', cfg.get('largura_area', 56)); h = cfg.get('altura_texto', 11)
        if ap_.get('vertical'): w, h = h, w
        box = np.array([[cx - w / 2, cy - h / 2], [cx + w / 2, cy - h / 2], [cx + w / 2, cy + h / 2], [cx - w / 2, cy + h / 2]])
        fr = ap_.get('frame', 'o')
        if fr == 'r' and M is None:
            box = r2o(box, ang_cfg, Wt, Ht)
        elif fr == 'o' and M is not None:
            box = box @ M[:, :2].T + M[:, 2]
        cv2.polylines(img, [np.round(box).astype(np.int32)], True, (255, 120, 0), 1)

x0, y0, x1, y1 = [int(v) for v in (a.regiao or (0, 0, img.shape[1], img.shape[0]))]
x0, y0 = max(x0, 0), max(y0, 0); x1, y1 = min(x1, img.shape[1]), min(y1, img.shape[0])
c = img[y0:y1, x0:x1]
z = a.zoom
c = cv2.resize(c, (int(c.shape[1] * z), int(c.shape[0] * z)), interpolation=cv2.INTER_LANCZOS4 if z > 1 else cv2.INTER_AREA)
for x in range(x0 - x0 % a.passo, x1, a.passo):
    X = int((x - x0) * z); forte = x % (a.passo * 5) == 0
    cv2.line(c, (X, 0), (X, c.shape[0]), (255, 0, 0) if forte else (255, 205, 205), 1)
    if forte: cv2.putText(c, str(x), (X + 2, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 0), 1)
for y in range(y0 - y0 % a.passo, y1, a.passo):
    Y = int((y - y0) * z); forte = y % (a.passo * 5) == 0
    cv2.line(c, (0, Y), (c.shape[1], Y), (0, 0, 255) if forte else (205, 205, 255), 1)
    if forte: cv2.putText(c, str(y), (2, Y + 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
cv2.imwrite(a.saida, cv2.cvtColor(c, cv2.COLOR_RGB2BGR))
print('ok', a.saida, c.shape[1], 'x', c.shape[0], '| planta original', rgb.shape[1], 'x', rgb.shape[0])
