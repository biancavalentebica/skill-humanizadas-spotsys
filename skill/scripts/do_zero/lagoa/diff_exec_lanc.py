"""Onde as paredes do executivo (registrado) e as do lancamento discordam, com tolerancia. Saida: mapa e lista de zonas.
Uso: py diff_exec_lanc.py <prefixo> <lancamento.png>"""
import sys, json, numpy as np, cv2
from PIL import Image; Image.MAX_IMAGE_PIXELS = None
pref, lanc = sys.argv[1:3]
M = np.load(pref + '_masks.npz'); T = np.array(json.load(open(pref + '_reg.json'))['exec_para_lanc'], np.float32)
L = np.array(Image.open(lanc).convert('RGB')); H, W = L.shape[:2]
def wp(a): return cv2.warpAffine(a, T, (W, H), flags=cv2.INTER_NEAREST)
ph = wp(((M['parede_ext_hatch'] > 60) | (M['parede_int_hatch'] > 60)).astype(np.uint8))   # miolo das paredes (hatch)
lum = L.astype(np.int16).mean(axis=2); A = np.array(Image.open(lanc))[..., 3] if np.array(Image.open(lanc)).shape[2] == 4 else None
pl = ((lum < 110) & (np.abs(L[..., 0].astype(int) - L[..., 2]) < 25)).astype(np.uint8)   # paredes cinza-escuro do lancamento
pl = cv2.morphologyEx(pl, cv2.MORPH_OPEN, np.ones((7, 7), np.uint8))                     # so massas (tira tracos finos)
tol = np.ones((25, 25), np.uint8)   # 10 cm
so_exec = ph & (cv2.dilate(pl, tol) == 0)
so_lanc = pl & (cv2.dilate(ph, tol) == 0)
def zonas(mk, nome):
    k = cv2.morphologyEx(mk, cv2.MORPH_OPEN, np.ones((9, 9), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(cv2.dilate(k, np.ones((61, 61), np.uint8)), 8)
    return [dict(tipo=nome, caixa=[int(x), int(y), int(x + w), int(y + h)], px=int(k[y:y + h, x:x + w].sum()))
            for x, y, w, h, a in st[1:] if k[y:y + h, x:x + w].sum() > 800]
Z = zonas(so_exec, 'so_executivo') + zonas(so_lanc, 'so_lancamento')
ov = (L[..., :3] * 0.45 + 140).astype(np.uint8)
ov[ph > 0] = (90, 90, 90); ov[so_exec > 0] = (230, 0, 0); ov[so_lanc > 0] = (0, 90, 230)
for z in Z:
    x0, y0, x1, y1 = z['caixa']; cv2.rectangle(ov, (x0, y0), (x1, y1), (230, 0, 0) if z['tipo'] == 'so_executivo' else (0, 90, 230), 6)
Image.fromarray(ov).resize((W // 3, H // 3)).save(pref + '_diff_exec_lanc.jpg', quality=85)
json.dump(Z, open(pref + '_diff_zonas.json', 'w'), indent=1)
for z in Z: print(z)
