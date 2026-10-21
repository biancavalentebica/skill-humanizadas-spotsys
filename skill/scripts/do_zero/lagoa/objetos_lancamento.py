"""Le o layout do lancamento: objetos de cada alojamento e WC (cama, criados, tapete, bancada com cuba e cooktop,
estrutura metalica, planta, sofa, vaso, lavatorio, ducha) como sprites RGBA isolados, com posicao no quadro do
lancamento (= quadro do executivo registrado, 03_trabalho/do_zero/<P>_amb.npz) e o ambiente onde estao.
Separa objeto do piso pela cor do piso (madeira nos alojamentos, porcelanato claro nos WCs), tira tracos finos (arcos de
porta, juntas, filetes de parede) e rotulos.
Saida: <P>_objetos.npz (sprites) + <P>_objetos.json; folha de conferencia <P>_objetos.jpg
Uso: py objetos_lancamento.py <P> <lancamento.png>"""
import sys, json, re, numpy as np, cv2
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
DZ = '../do_zero/'
P, lanc_p = sys.argv[1:3]
A = np.load(DZ + P + '_amb.npz'); J = json.load(open(DZ + P + '_amb.json', encoding='utf8')); ids = A['ids']
L = np.array(Image.open(lanc_p).convert('RGB')); f = L.astype(np.int16); H, W = ids.shape
R, G, B = f[..., 0], f[..., 1], f[..., 2]; lum = f.mean(axis=2); sat = f.max(axis=2) - f.min(axis=2)
madeira = (R - B > 20) & (R - B < 85) & (lum > 85) & (lum < 200) & (G >= B - 2)
claro = (lum > 200) & (sat < 22)
nav = (np.abs(R - 57) < 6) & (np.abs(G - 66) < 6) & (np.abs(B - 94) < 6)
objs, sprites = [], {}
for k, v in J['ambientes'].items():
    nm = v['nome']
    if not re.match(r'ALOJ|WC|PNE', nm): continue
    piso = madeira if nm.startswith('ALOJ') else claro
    sala = ids == int(k); x0, y0, x1, y1 = v['caixa']; x0, y0 = max(x0 - 2, 0), max(y0 - 2, 0); x1, y1 = x1 + 3, y1 + 3
    s = sala[y0:y1, x0:x1]
    s_in = cv2.erode(s.astype(np.uint8), np.ones((7, 7), np.uint8)) > 0
    ob = s_in & ~piso[y0:y1, x0:x1] & ~nav[y0:y1, x0:x1]
    nuc = cv2.erode(ob.astype(np.uint8), np.ones((7, 7), np.uint8)); rec = nuc.copy()
    for _ in range(40):
        nv = cv2.dilate(rec, np.ones((3, 3), np.uint8)) & ob.astype(np.uint8)
        if (nv == rec).all(): break
        rec = nv
    perto = s & ~s_in
    rec = (cv2.dilate(rec, np.ones((9, 9), np.uint8)) > 0) & (rec.astype(bool) | (perto & ~piso[y0:y1, x0:x1]))
    rec = cv2.morphologyEx(rec.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)) & s.astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(rec, 8)
    for i in range(1, n):
        x, y, w, h, a = st[i]
        if a < (700 if nm.startswith('ALOJ') else 250): continue
        comp = lab == i
        lc = lum[y0:y1, x0:x1][comp]
        if min(w, h) <= 24 and max(w, h) >= 100: continue                       # folha de porta
        if min(w, h) <= 30 and ((lc < 60) | (lc > 230)).mean() > 0.5: continue  # filete de parede
        if a / (w * h) < 0.25: continue                                          # arco/traco solto
        m = comp[y:y + h, x:x + w]
        al = cv2.GaussianBlur(m.astype(np.float32), (0, 0), 0.7)
        rgba = np.dstack([L[y0 + y:y0 + y + h, x0 + x:x0 + x + w], (al * 255).astype(np.uint8)])
        key = f'o{len(objs)}'
        sprites[key] = rgba
        # distancia a cada parede do ambiente (para assentar no executivo): face mais proxima por lado
        objs.append(dict(id=key, ambiente=nm, amb_id=int(k), x=int(x0 + x), y=int(y0 + y), w=int(w), h=int(h), px=int(a)))
np.savez_compressed(P + '_objetos.npz', **sprites)
json.dump(objs, open(P + '_objetos.json', 'w', encoding='utf8'), indent=1, ensure_ascii=False)
viz = (L * 0.35 + 160).astype(np.uint8)
for o in objs:
    sp = sprites[o['id']]; a = sp[..., 3:4] / 255.0
    reg = viz[o['y']:o['y'] + o['h'], o['x']:o['x'] + o['w']]
    reg[:] = (sp[..., :3] * a + reg * (1 - a)).astype(np.uint8)
    cv2.rectangle(viz, (o['x'], o['y']), (o['x'] + o['w'], o['y'] + o['h']), (255, 0, 0), 3)
Image.fromarray(viz).resize((W // 4, H // 4)).save(P + '_objetos.jpg', quality=85)
print(P, len(objs), 'objetos')
