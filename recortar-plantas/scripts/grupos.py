"""Acha grupos de letras (texto preto) num recorte. uso: grupos.py img [limiar] -> lista bbox"""
import sys, numpy as np, cv2
from PIL import Image
def grupos(rgb, lim=62, f=1.0):
    g = rgb.mean(2); sat = rgb.max(2).astype(int) - rgb.min(2)
    band = ((g < lim) & (sat < 22)).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(band, 8)
    L = [i for i in range(1, n) if 3 * f <= st[i][3] <= 20 * f and st[i][2] <= 18 * f and st[i][4] >= 6 * f * f and st[i][4] < 0.62 * st[i][2] * st[i][3]]
    # componentes que parecem letra: altura parecida, agrupadas por proximidade
    boxes = [list(st[i][:4]) for i in L]
    gruposL = []
    usados = set()
    for i, b in enumerate(boxes):
        if i in usados: continue
        G = [i]; usados.add(i); x0, y0, x1, y1 = b[0], b[1], b[0] + b[2], b[1] + b[3]; mud = True
        while mud:
            mud = False
            for j, c in enumerate(boxes):
                if j in usados: continue
                h = max(c[3], y1 - y0) if len(G) == 1 else (y1 - y0)
                if c[0] < x1 + 1.0 * c[3] and c[0] + c[2] > x0 - 1.0 * c[3] and c[1] < y1 + 0.6 * c[3] and c[1] + c[3] > y0 - 0.6 * c[3]:
                    G.append(j); usados.add(j); x0, y0, x1, y1 = min(x0, c[0]), min(y0, c[1]), max(x1, c[0] + c[2]), max(y1, c[1] + c[3]); mud = True
        if len(G) >= 1: gruposL.append((x0, y0, x1, y1, len(G)))
    return gruposL
if __name__ == '__main__':
    im = np.array(Image.open(sys.argv[1]).convert('RGB')).astype(int)
    f = float(sys.argv[2]) if len(sys.argv) > 2 else 1
    for gpo in grupos(im, f=f): print(gpo)
