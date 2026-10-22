"""Lagoa Spot: gera os configs da skill recortar-plantas (Bianca Valente) e os pins do 360 a partir da MESMA geometria
que desenhou a planta (<P>_hib_amb.npz, no quadro da imagem do pavimento). O recorte em si e feito pela skill:
  python ~/.claude/skills/recortar-plantas/scripts/recortar.py configs/<pav>.json --folha ...

Contorno da unidade (padrao da skill): alojamento + WC dela (o da porta: soleira entre os dois) + garden (grama limitada
pelo gradil, so as unidades com garden no SpotSys), com o contorno no MEIO das paredes entre ambientes (cada pixel de
parede fica com o ambiente mais perto) e ate a face externa na fachada (fora do lote/predio a transparencia corta sozinha).
Coordenadas no frame de trabalho da skill (planta reduzida para 2000 px de largura).
Uso: py config_bianca.py <planta_TER.png> <planta_02P.png> <spotsys.csv> <pasta_configs> <saida_pins.json>"""
import sys, os, json, csv, re
import numpy as np, cv2
from PIL import Image
from scipy import ndimage as ndi
Image.MAX_IMAGE_PIXELS = None
M_PX = 0.004022375816200381
PL = {'TER': sys.argv[1], '02P': sys.argv[2]}
spot = {r['code']: r for r in csv.DictReader(open(sys.argv[3], encoding='utf-8'))}
CFG, PINS = sys.argv[4], sys.argv[5]
AQUI = os.path.dirname(os.path.abspath(__file__))
PAV = {'TER': ('terreo', '1'), '02P': ('pav02', '2')}
k_ = lambda n: np.ones((n, n), np.uint8)
os.makedirs(CFG, exist_ok=True)
pins = []
for P, (nome, andar) in PAV.items():
    COM = np.array(Image.open(PL[P]).convert('RGBA')); H, W = COM.shape[:2]; f = W / 2000.0
    ids = np.load(os.path.join(AQUI, f'{P}_hib_amb.npz'))['ids']
    amb = {int(k): v['nome'] for k, v in json.load(open(os.path.join(AQUI, f'{P}_hib_amb.json'), encoding='utf8'))['ambientes'].items()}
    alojs = {int(re.match(r'ALOJ (\d+)', v).group(1)): k for k, v in amb.items() if re.match(r'ALOJ \d+', v)}
    wcs = [k for k, v in amb.items() if re.match(r'WC', v)]
    c3 = COM[..., :3].astype(np.int16)
    verde = (c3[..., 1] > c3[..., 0] + 15) & (c3[..., 1] > c3[..., 2] + 15) & (COM[..., 3] > 0)
    # predio = ambientes + paredes pretas (fachada inclusa) fechados; o asfalto/grama em volta fica fora (face externa)
    lm0 = c3.mean(axis=2); sat0 = c3.max(axis=2) - c3.min(axis=2)
    preto = (lm0 < 50) & (sat0 < 20) & (COM[..., 3] > 0)
    preto = preto & cv2.dilate(((ids > 0)).astype(np.uint8), k_(121)).astype(bool)        # so parede junto dos ambientes
    pred = ndi.binary_fill_holes(cv2.morphologyEx(((ids > 0) | preto).astype(np.uint8), cv2.MORPH_CLOSE, k_(61)) > 0)
    pred &= (COM[..., 3] > 0) & ~verde
    nr = pred & (ids == 0)                                   # parede, esquadria, soleira
    # WC -> unidade da porta (soleira de granito entre os dois); sem soleira legivel: a de mais contato
    lm = c3.mean(axis=2); sat = c3.max(axis=2) - c3.min(axis=2)
    soleira = (lm > 120) & (lm < 232) & (sat < 40) & ~((c3[..., 2] - c3[..., 0]) > 12)
    dono = {}
    for w in wcs:
        dw = cv2.dilate((ids == w).astype(np.uint8), k_(71)).astype(bool)
        sc = {cod: int((dw & cv2.dilate((ids == a).astype(np.uint8), k_(71)).astype(bool) & nr & soleira).sum()) for cod, a in alojs.items()}
        cod = max(sc, key=sc.get)
        if sc[cod] < 300:
            ct = {c: int((dw & (ids == a)).sum()) for c, a in alojs.items()}; cod = max(ct, key=ct.get)
            print('  WC', P, w, 'pelo contato ->', cod)
        dono.setdefault(cod, []).append(w)
    # gardens (terreo): grama separada pelo gradil, encostada na unidade
    gard = {}
    if P == 'TER':
        vg = cv2.morphologyEx((verde & ~pred).astype(np.uint8), cv2.MORPH_OPEN, k_(5))
        n, l, s, _ = cv2.connectedComponentsWithStats(vg, 4)
        for i in range(1, n):
            if s[i, 4] < 20000: continue
            m = l == i
            if s[i, 4] * M_PX ** 2 > 40:      # gramado comum emendado: o garden da 08 e o trecho acima do gradil de baixo
                a8 = cv2.dilate((ids == alojs[8]).astype(np.uint8), k_(9)).astype(bool)
                xs8 = np.nonzero(a8.any(axis=0))[0]; m8 = np.zeros((H, W), bool); yf = np.nonzero(a8.any(axis=1))[0].max()
                for x in range(xs8.min(), xs8.max() + 1):
                    col = m[:, x]; ys = np.nonzero(col[yf:])[0]
                    if not len(ys): continue
                    y0 = yf + ys[0]; y1 = y0
                    while y1 + 1 < H and col[y1 + 1]: y1 += 1
                    if (y1 - y0) * M_PX < 3.0: m8[y0:y1 + 1, x] = True
                m = m8
            d = cv2.dilate(m.astype(np.uint8), k_(161)).astype(bool)
            viz = {cod: int((d & (ids == a)).sum()) for cod, a in alojs.items()}
            cod = max(viz, key=viz.get)
            if viz[cod] < 5000 or float(spot.get(str(cod), {}).get('garden_total_area') or 0) <= 0: continue
            gard[cod] = gard.get(cod, np.zeros((H, W), bool)) | m
    # contorno pelo meio das paredes: cada pixel de parede vai para o ambiente mais perto
    # so entre unidades a parede e dividida ao meio; parede (e soleira da porta de entrada) entre unidade e area comum
    # fica inteira com a unidade, ate a face do corredor (senao a porta de entrada sai cortada no meio da soleira)
    privado = np.isin(ids, list(alojs.values()) + wcs)
    _, (iy, ix) = ndi.distance_transform_edt(~privado, return_indices=True)
    mais_perto = ids[iy, ix]; dist = ndi.distance_transform_edt(~privado)
    mais_perto[(ids > 0) & ~privado] = 0
    # vao da porta de entrada (soleira + faixa de piso no vao): a parede do corredor fechada em linha reta sobre o vao.
    # Geometria, nao cor (granito, asfalto e porcelanato se confundem)
    nr8 = nr.astype(np.uint8)
    vao = ((cv2.morphologyEx(nr8, cv2.MORPH_CLOSE, np.ones((1, 301), np.uint8)) | cv2.morphologyEx(nr8, cv2.MORPH_CLOSE, np.ones((301, 1), np.uint8))) > 0) & ~nr & ~privado
    unidades = {}
    for cod in sorted(alojs):
        meus = [alojs[cod]] + dono.get(cod, [])
        core = np.isin(ids, meus)
        un = core | (nr & np.isin(mais_perto, meus) & (dist <= 62))
        un |= vao & cv2.dilate(core.astype(np.uint8), k_(2 * 70 + 1)).astype(bool)
        ga = gard.get(cod)
        if ga is not None:
            un |= cv2.dilate(ga.astype(np.uint8), k_(25)).astype(bool) & ~(ids > 0) & (COM[..., 3] > 0)
            un |= cv2.morphologyEx(un.astype(np.uint8), cv2.MORPH_CLOSE, k_(41)).astype(bool) & (ids == 0)
        un = cv2.morphologyEx(un.astype(np.uint8), cv2.MORPH_CLOSE, k_(41)).astype(bool) & (np.isin(ids, meus) | (ids == 0) | (un & vao))
        n2, l2, s2, _ = cv2.connectedComponentsWithStats(un.astype(np.uint8), 8); un = ndi.binary_fill_holes(l2 == 1 + int(np.argmax(s2[1:, 4])))
        cs, _ = cv2.findContours(un.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        c = cv2.approxPolyDP(max(cs, key=cv2.contourArea), 4, True)[:, 0, :].astype(float)
        unidades[f'{cod:02d}'] = {'poligonos': [{'pts': [[round(x / f, 2), round(y / f, 2)] for x, y in c]}]}
        mo = cv2.moments(un.astype(np.uint8), True); s_ = spot[str(cod)]
        pins.append(dict(szi_unit_id=int(s_['id']), codigo=str(cod), andar=andar, planta=os.path.basename(PL[P]),
                         largura_px=W, altura_px=H, pin_type='polygon',
                         polygon_vertices=[dict(x=round(x / W, 5), y=round(y / H, 5)) for x, y in c],
                         x=round(mo['m10'] / mo['m00'] / W, 5), y=round(mo['m01'] / mo['m00'] / H, 5)))
    esperado = sorted(int(c) for c, r in spot.items() if r['floor'] == andar)
    print(P, 'unidades', sorted(int(k) for k in unidades), 'SpotSys', esperado, 'OK' if sorted(int(k) for k in unidades) == esperado else 'DIFERENTE')
    cfg = {'planta': os.path.abspath(PL[P]), 'saida': os.path.abspath(os.path.join(CFG, '..', 'Plantas unidades')),
           'nome': 'Lagoa Spot - {id}.png', 'apagar': [], 'unidades': unidades}
    json.dump(cfg, open(os.path.join(CFG, nome + '.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
json.dump(pins, open(PINS, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print('pins', len(pins))
