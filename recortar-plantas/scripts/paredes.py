"""Acha centros de paredes (frame trabalho). uso: paredes.py planta v y0 y1 [x0 x1]  |  h x0 x1 [y0 y1]"""
import sys, numpy as np
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
im = Image.open(sys.argv[1]).convert('L'); f = im.width / 2000; a = np.array(im).astype(float)
modo = sys.argv[2]; v = [float(x) for x in sys.argv[3:]]; lim = 0.8
def grupos(idx):
    g = []
    for x in idx:
        if g and x - g[-1][-1] < 3: g[-1].append(x)
        else: g.append([x])
    return [(round((s[0] + s[-1]) / 2), round(s[-1] - s[0] + 1, 1)) for s in g]
if modo == 'v':
    y0, y1 = v[:2]; x0, x1 = (v[2:] or [0, 2000])
    band = a[int(y0*f):int(y1*f), int(x0*f):int(x1*f)]; prof = (band < 70).mean(0)
    print(grupos(np.where(prof > lim)[0] / f + x0))
else:
    x0, x1 = v[:2]; y0, y1 = (v[2:] or [0, a.shape[0]/f])
    band = a[int(y0*f):int(y1*f), int(x0*f):int(x1*f)]; prof = (band < 70).mean(1)
    print(grupos(np.where(prof > lim)[0] / f + y0))
