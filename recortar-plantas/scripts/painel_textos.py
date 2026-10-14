"""Painel: cada item de 'apagar' ampliado 4x, com grade de 5 px (frame trabalho) e a caixa."""
import sys, json, cv2, numpy as np
sys.path.insert(0, __import__('os').path.dirname(__file__))
from plantas import *
cfg = ler_config(sys.argv[1]); saida = sys.argv[2]
rgb, _ = carregar(cfg['planta']); f = rgb.shape[1] / 2000
Z = 4; RX, RY = 60, 22; tiles = []
for it in cfg['apagar']:
    cx, cy = it['centro']; w = it.get('largura', cfg.get('largura_area', 56)); h = it.get('altura', cfg.get('altura_texto', 11))
    x0, y0 = cx - RX, cy - RY
    c = rgb[int(y0*f):int((cy+RY)*f), int(x0*f):int((cx+RX)*f)]
    c = cv2.resize(c, (2*RX*Z, 2*RY*Z), interpolation=cv2.INTER_NEAREST).copy()
    for gx in range(int(x0) - int(x0) % 5, int(cx+RX)+1, 5):
        X = int((gx-x0)*Z); cv2.line(c, (X, 0), (X, c.shape[0]), (255, 0, 0) if gx % 25 == 0 else (255, 200, 200), 1)
        if gx % 25 == 0: cv2.putText(c, str(gx), (X+2, 10), 0, 0.35, (255, 0, 0), 1)
    for gy in range(int(y0) - int(y0) % 5, int(cy+RY)+1, 5):
        Y = int((gy-y0)*Z); cv2.line(c, (0, Y), (c.shape[1], Y), (0, 0, 255) if gy % 25 == 0 else (200, 200, 255), 1)
        if gy % 25 == 0: cv2.putText(c, str(gy), (2, Y-2), 0, 0.35, (0, 0, 255), 1)
    cv2.rectangle(c, (int((cx-w/2-x0)*Z), int((cy-h/2-y0)*Z)), (int((cx+w/2-x0)*Z), int((cy+h/2-y0)*Z)), (255, 120, 0), 2)
    cv2.putText(c, it.get('obs', ''), (c.shape[1]-90, c.shape[0]-6), 0, 0.45, (0, 150, 0), 1)
    tiles.append(c)
cols = 3; Hh, Ww = tiles[0].shape[:2]; rows = (len(tiles)+cols-1)//cols
sh = np.full((rows*(Hh+6), cols*(Ww+6), 3), 128, np.uint8)
for i, t in enumerate(tiles): r, k = divmod(i, cols); sh[r*(Hh+6):r*(Hh+6)+Hh, k*(Ww+6):k*(Ww+6)+Ww] = t
cv2.imwrite(saida, cv2.cvtColor(sh, cv2.COLOR_RGB2BGR)); print(len(tiles), sh.shape)
