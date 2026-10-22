"""Mobiliario dos alojamentos sobre a base do zero: em cada alojamento do executivo, os moveis reais do lancamento
(cama, criados-mudos, tapete, pufe, bancada, estrutura metalica, plantas) sao recortados do piso antigo e assentados
no assoalho novo com sombra nova. O arranjo do lancamento foi conferido com o interiores (Nidus, set/2022) por
tipologia antes de usar (ver 01_diagnostico/CONFERENCIA_INTERIORES_LAGOA.md).
Nao entram: tracos finos do lancamento (arcos de porta, juntas), loucas (vem do executivo) e o que encosta na parede.
Uso: py mobilia.py <prefixo> <lancamento.png> <base.png> <saida.png> [--pular ALOJ 01,...]"""
import sys, json, re, numpy as np, cv2
from PIL import Image; Image.MAX_IMAGE_PIXELS = None
pref, lanc_p, base_p, saida = sys.argv[1:5]
pular = sys.argv[sys.argv.index('--pular') + 1].split(',') if '--pular' in sys.argv else []
A = np.load(pref + '_amb.npz'); J = json.load(open(pref + '_amb.json', encoding='utf8'))
ids, par = A['ids'], A['paredes']
L = np.array(Image.open(lanc_p).convert('RGB')); B = np.array(Image.open(base_p).convert('RGBA'))
img = B[..., :3].copy(); H, W = ids.shape
f = L.astype(np.int16); R, G, Bc = f[..., 0], f[..., 1], f[..., 2]; lum = f.mean(axis=2)
madeira = (R - Bc > 20) & (R - Bc < 85) & (lum > 85) & (lum < 200) & (G >= Bc - 2)
claro = (lum > 205) & ((f.max(axis=2) - f.min(axis=2)) < 18)          # porcelanato da recepcao/circulacao
piso_comum = madeira | claro
log = []
for k, v in J['ambientes'].items():
    if not re.match(r'ALOJ|ESCADA|RECEP|CIRC', v['nome']) or v['nome'] in pular: continue
    sala = ids == int(k)
    x0, y0, x1, y1 = v['caixa']; x0, y0, x1, y1 = max(x0 - 2, 0), max(y0 - 2, 0), x1 + 3, y1 + 3
    s = sala[y0:y1, x0:x1]
    s_in = cv2.erode(s.astype(np.uint8), np.ones((9, 9), np.uint8)) > 0          # longe da parede
    PISO = madeira if v['nome'].startswith('ALOJ') else piso_comum
    obj = s_in & ~PISO[y0:y1, x0:x1]
    # tira tracos finos (arcos, juntas): reconstrucao geodesica a partir do nucleo grosso
    nucleo = cv2.erode(obj.astype(np.uint8), np.ones((9, 9), np.uint8))
    rec = nucleo.copy()
    for _ in range(60):
        nv = cv2.dilate(rec, np.ones((3, 3), np.uint8)) & obj.astype(np.uint8)
        if (nv == rec).all(): break
        rec = nv
    # objetos colados na parede (bancada, estrutura) perdem a borda pela erosao: recupera ate a face da parede
    perto = s & ~s_in
    rec = (cv2.dilate(rec, np.ones((11, 11), np.uint8)) > 0) & (rec.astype(bool) | (perto & ~PISO[y0:y1, x0:x1]))
    n, lab, st, _ = cv2.connectedComponentsWithStats(rec.astype(np.uint8), 8)
    keep = np.zeros_like(rec)
    for i in range(1, n):
        w_, h_ = st[i, 2], st[i, 3]
        if st[i, 4] < 1200: continue
        if min(w_, h_) <= 24 and max(w_, h_) >= 120: continue          # folha de porta do lancamento
        comp = lab == i
        lum_c = lum[y0:y1, x0:x1][comp]
        if min(w_, h_) <= 30 and ((lum_c < 60) | (lum_c > 225)).mean() > 0.5: continue   # parede/filete do lancamento
        keep |= lab == i
    a = cv2.GaussianBlur(keep.astype(np.float32), (0, 0), 0.8)
    som = cv2.GaussianBlur(np.roll(np.roll(keep.astype(np.float32), 6, 0), 6, 1), (0, 0), 7) * 0.33
    reg = img[y0:y1, x0:x1].astype(np.float32)
    reg[s] = reg[s] * (1 - som[s, None])
    reg = reg * (1 - a[..., None]) + L[y0:y1, x0:x1].astype(np.float32) * a[..., None]
    out = img[y0:y1, x0:x1].copy(); out[s] = reg[s].astype(np.uint8); img[y0:y1, x0:x1] = out
    log.append(dict(alojamento=v['nome'], objetos=int(n - 1), px=int(keep.sum())))
    print(v['nome'], 'componentes', n - 1, 'px', int(keep.sum()))
Image.fromarray(np.dstack([img, B[..., 3]])).save(saida)
Image.fromarray(img).resize((W // 4, H // 4)).save(saida.replace('.png', '_previa.jpg'), quality=85)
json.dump(log, open(saida.replace('.png', '_log.json'), 'w', encoding='utf8'), indent=1, ensure_ascii=False)
