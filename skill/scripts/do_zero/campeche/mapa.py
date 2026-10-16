"""Ambientes do legal R00 (prancha 03) por preenchimento entre os tracos pretos, semeados nos rotulos.
Saida no referencial da planta nova: girado +45 graus (como a humanizada de lancamento), 0,5 cm/px."""
import re, sys, os
import cv2, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from base import raster, rotulos, W, H, px, Z, CLIP

ESC = 2.0          # px por cm na planta nova (0,5 cm/px)
ANG = -45.0


def nome_de(s):
    u = s.upper()
    m = re.match(r'(STUDIO|VARANDA)\s+(\d{3})', u)
    if m: return ('U' if m.group(1) == 'STUDIO' else 'G') + m.group(2)
    if u.startswith('LOJA'): return 'LOJA ' + u.split()[-1]
    for k, v in (('WC 1', 'WC1'), ('WC 2', 'WC2'), ('WC - PCD', 'WC_HALL'), ('ÁREA COMUM', 'CIRC'), ('DEP. TEMP', 'LIXO'),
                 ('MEDIDORES', 'MED'), ('JARDIM', 'JARDIM'), ('CANTEIRO', 'CANTEIRO'), ('ESCADAS E ELEV', 'NUCLEO')):
        if u.startswith(k): return v
    return None


def ambientes():
    B = raster()
    Bc = cv2.dilate(B.astype(np.uint8), np.ones((5, 5), np.uint8))
    n, lab = cv2.connectedComponents((1 - Bc).astype(np.uint8), connectivity=4)
    ids = np.zeros((H, W), np.int32); nomes = {0: 'FORA'}; usados = {}
    for s, x, y, d in rotulos():
        nm = nome_de(s)
        if not nm: continue
        k = lab[int(y), int(x)]
        if k == 0 or k in usados: continue
        if (lab == k).sum() > 2_000_000: continue
        if nm == 'G102' and 'G102' in nomes.values(): nm = 'G101'    # prancha escreve VARANDA 102 duas vezes (a de 9,28 e da 101)
        i = len(nomes); nomes[i] = nm; usados[k] = i
        ids[lab == k] = i
    # devolve a espessura das linhas a cada ambiente vizinho (as paredes nascem na fronteira)
    for _ in range(4):
        z = ids == 0
        dil = cv2.dilate(ids.astype(np.float32), np.ones((3, 3), np.uint8)).astype(np.int32)
        ids[z] = dil[z]
    return ids, nomes, B


def gira(img, interp=cv2.INTER_NEAREST, borda=0):
    """Do quadro do legal (1 cm/px) para o quadro novo (girado +ANG, ESC px/cm)."""
    c = (W / 2, H / 2)
    M = cv2.getRotationMatrix2D(c, ANG, ESC)
    cos, sin = abs(M[0, 0]), abs(M[0, 1])
    nW, nH = int(H * sin + W * cos), int(H * cos + W * sin)
    M[0, 2] += nW / 2 - c[0]; M[1, 2] += nH / 2 - c[1]
    return cv2.warpAffine(img, M, (nW, nH), flags=interp, borderValue=borda), M


if __name__ == '__main__':
    ids, nomes, B = ambientes()
    print(len(nomes), sorted(nomes.values()))
    G, M = gira(ids.astype(np.float32)); G = G.astype(np.int32)
    np.save('03_trabalho/do_zero/ids_rot.npy', G); np.save('03_trabalho/do_zero/M.npy', M)
    import json; json.dump({str(k): v for k, v in nomes.items()}, open('03_trabalho/do_zero/nomes.json', 'w'))
    col = np.full((*G.shape, 3), 255, np.uint8); rng = np.random.default_rng(2)
    for k, v in nomes.items():
        if k == 0: continue
        m = G == k; col[m] = rng.integers(60, 230, 3)
        ys, xs = np.nonzero(m)
        if len(xs): cv2.putText(col, v, (int(xs.mean()) - 60, int(ys.mean())), 0, 1.6, (0, 0, 0), 4)
    print(G.shape)
    cv2.imwrite('03_trabalho/do_zero/mapa_rot.jpg', cv2.resize(col, None, fx=0.18, fy=0.18, interpolation=cv2.INTER_AREA))
