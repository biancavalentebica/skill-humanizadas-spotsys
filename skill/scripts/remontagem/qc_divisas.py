"""QC: distancia das divisas do R06 (contornos das areas) ate as paredes da imagem, em cm. Uso: py qc_divisas.py img [saida.json]"""
import sys, os, json, cv2, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from geo_terreo import px, poligonos
from remonta_lib import carrega
im = carrega(sys.argv[1]); g = im.mean(2)
parede = (g < 100).astype(np.uint8)
dt = cv2.distanceTransform(1 - parede, cv2.DIST_L2, 5)
d = []
for q in poligonos():
    if q['tipo'] == 'outra': continue
    P = [px(x, y) for x, y in q['pts']]
    for (x0, y0), (x1, y1) in zip(P, P[1:] + P[:1]):
        n = int(max(abs(x1 - x0), abs(y1 - y0)) // 3)
        for t in np.linspace(0, 1, max(n, 2)):
            u, v = int(x0 + t * (x1 - x0)), int(y0 + t * (y1 - y0))
            if 0 <= u < g.shape[1] and 0 <= v < g.shape[0]: d.append(dt[v, u])
d = np.array(d) * 1.535
r = dict(imagem=sys.argv[1], mediana_cm=round(float(np.median(d)), 1), p90_cm=round(float(np.percentile(d, 90)), 1), ate_15cm=round(float(np.mean(d <= 15)), 3))
print(json.dumps(r))
if len(sys.argv) > 2: json.dump(r, open(sys.argv[2], 'w'), indent=1)
