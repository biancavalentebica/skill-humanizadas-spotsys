"""Pegada de cada escada de unidade/loja do R06 (regiao fechada pelos tracos pretos que contem o rotulo ESCADA)."""
import cv2, numpy as np
from r06_base import raster, rotulos, H, W


def escadas(ids, nomes, tipos):
    B = raster(); out = {}
    for s, x, y in rotulos():
        if s != 'ESCADA': continue
        k = int(ids[int(y), int(x)]); nm = nomes.get(k)
        if tipos.get(k) not in ('unidade', 'loja'): continue
        M = ids == k
        ff = (~B & M).astype(np.uint8)
        ff = cv2.morphologyEx(ff, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        n, lab = cv2.connectedComponents(ff)
        c = lab[int(y), int(x)]
        if c == 0: continue
        e = lab == c
        if e.sum() > 0.5 * M.sum(): continue
        out[nm] = cv2.dilate(e.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    return out
