"""Mascaras do executivo no quadro do legal (1 cm/px): preenchimentos por cor (paredes) e tracos do nucleo."""
import fitz, json, sys, os
import numpy as np, cv2
sys.path.insert(0, os.path.dirname(__file__))
from base import Z, W, H, CLIP
from exec_raster import EX, M
def mascara_fill(cores, tol=0.02, opac_min=0.9, xmax=2700):
    p = fitz.open(EX)[0]; T = M(); m = np.zeros((H, W), np.uint8)
    for d in p.get_drawings():
        if d['type'] not in ('f', 'fs') or fitz.Rect(d['rect']).x1 > xmax: continue
        f = d['fill']; 
        if (d.get('fill_opacity') or 1) < opac_min or not any(all(abs(a - b) < tol for a, b in zip(f, c)) for c in cores): continue
        polys = []; cur = []
        for it in d['items']:
            if it[0] == 'l':
                if not cur: cur.append((it[1].x, it[1].y))
                cur.append((it[2].x, it[2].y))
            elif it[0] == 're':
                r = it[1]; polys.append([(r.x0, r.y0), (r.x1, r.y0), (r.x1, r.y1), (r.x0, r.y1)])
            elif it[0] == 'qu':
                q = it[1]; polys.append([(q.ul.x, q.ul.y), (q.ur.x, q.ur.y), (q.lr.x, q.lr.y), (q.ll.x, q.ll.y)])
            elif it[0] == 'c':
                if not cur: cur.append((it[1].x, it[1].y))
                cur.append((it[4].x, it[4].y))
        if cur: polys.append(cur)
        for pl in polys:
            a = np.array(pl, np.float64); xy = (T[:, :2] @ a.T).T + T[:, 2]
            cv2.fillPoly(m, [np.round(xy * 8).astype(np.int32)], 1, shift=3)
    return m.astype(bool)
def mascara_tracos(rect_pt, cor_max=0.6, larg=2):
    """Tracos (escuros) do executivo dentro de um retangulo (pt do executivo) -> mascara no quadro do legal."""
    p = fitz.open(EX)[0]; T = M(); m = np.zeros((H, W), np.uint8)
    for d in p.get_drawings():
        c = d.get('color')
        if d['type'] != 's' or not c or max(c) > cor_max or not fitz.Rect(d['rect']).intersects(rect_pt): continue
        for it in d['items']:
            if it[0] == 'l':
                a = np.array([[it[1].x, it[1].y], [it[2].x, it[2].y]]); xy = (T[:, :2] @ a.T).T + T[:, 2]
                cv2.line(m, tuple(np.round(xy[0]).astype(int)), tuple(np.round(xy[1]).astype(int)), 1, larg)
    return m.astype(bool)
if __name__ == '__main__':
    out = {}
    for nm, cores in {'alvenaria': [(0.82, 0.67, 0.53), (0.73, 0.5, 0.3)], 'estrutura': [(0.0, 0.0, 0.0)], 'cinza36': [(0.36, 0.36, 0.36)],
                      'cinza50': [(0.5, 0.5, 0.5)], 'cinza54': [(0.54, 0.54, 0.54)], 'cinza68': [(0.68, 0.68, 0.68)], 'cinza75': [(0.75, 0.75, 0.75)], 'jardim': [(0.6, 0.655, 0.373)]}.items():
        m = mascara_fill(cores, opac_min=0.2 if nm == 'jardim' else 0.9); out[nm] = m; print(nm, m.sum())
        cv2.imwrite(f'03_trabalho/do_zero/em_{nm}.jpg', cv2.resize((~m * 255).astype(np.uint8), None, fx=0.25, fy=0.25, interpolation=cv2.INTER_AREA))
    np.savez_compressed('03_trabalho/do_zero/exec_masks.npz', **out)
