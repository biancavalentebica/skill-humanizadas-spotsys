"""Gera os configs da skill recortar-plantas (Bianca Valente) e os pins do 360 a partir da MESMA geometria que desenhou a
planta do pavimento (mascara de ambientes `<prefixo>.npz` com `ids` + `<prefixo>.json` com os nomes, no quadro da imagem).
O recorte em si e SEMPRE feito pela skill da Bianca:
  py ~/.claude/skills/recortar-plantas/scripts/recortar.py configs/<pav>.json --folha <rascunho>/folha_<pav>.png

Regras de contorno (aprovadas pela Rachel no Lagoa Spot, 22/10/2026):
- unidade = ambiente principal + WC(s) dela (o WC e da unidade para a qual a porta dele abre: soleira entre os dois; sem
  soleira legivel, a de mais contato) + garden (so as unidades com garden no SpotSys; grama limitada pelo gradil);
- entre duas unidades o contorno passa no MEIO da parede; no corredor e na fachada vai ate a FACE EXTERNA da parede, com a
  parede e a soleira da porta de entrada inteiras (o vao da porta e achado por geometria: a parede do corredor fechada em
  linha reta sobre o vao; nunca por cor, granito/asfalto/porcelanato se confundem);
- fora do predio (asfalto, grama comum) nada entra; o que e transparente na planta a skill corta sozinha.

Uso: py config_recorte_bianca.py <recorte.json>
recorte.json (caminhos relativos a pasta do empreendimento, onde o comando e rodado):
{
 "empreendimento": "Lagoa Spot",            # nome da pasta de saida: "<empreendimento> - <codigo>.png"
 "m_px": 0.004022,                          # metros por pixel da planta
 "spotsys_csv": "00_entradas/spotsys/spotsys_lagoa_2026-10-16.csv",   # export com a coluna id
 "regex_unidade": "ALOJ (\\d+)",            # nome do ambiente principal -> codigo (grupo 1)
 "regex_wc": "^WC",                         # nome dos sanitarios privativos
 "digitos": 2,                              # codigo com zeros a esquerda no nome do arquivo
 "configs": "configs", "unidades": "Plantas unidades",
 "pins": "04_saida/<entrega>/04_PUBLICACAO/pins_360_AGUARDANDO_VALIDACAO.json",
 "pavimentos": [{"id": "terreo", "pasta": "Térreo", "andar": "1", "planta": "<planta COM 'UNIDADE NN'>.png",
                 "ambientes": "03_trabalho/<...>/TER_hib_amb"}]
}
Saidas: configs/<id>.json (saida = Plantas unidades/<pasta>/), pins_360 (vertices 0-1 sobre a planta do pavimento, que tem de
ser exatamente a imagem que sobe no SpotSys) e, no terminal, a contagem por pavimento x SpotSys (C8)."""
import sys, os, json, csv, re
import numpy as np, cv2
from PIL import Image
from scipy import ndimage as ndi
Image.MAX_IMAGE_PIXELS = None
C = json.load(open(sys.argv[1], encoding='utf-8'))
M_PX = C['m_px']; DIG = C.get('digitos', 2)
spot = {r['code']: r for r in csv.DictReader(open(C['spotsys_csv'], encoding='utf-8'))}
RX_UN, RX_WC = re.compile(C.get('regex_unidade', r'ALOJ (\d+)')), re.compile(C.get('regex_wc', r'^WC'))
px = lambda m: max(int(round(m / M_PX)), 1)                     # metros -> pixels
k_ = lambda n: np.ones((n, n), np.uint8)
os.makedirs(C['configs'], exist_ok=True)
pins, erros = [], 0
for pv in C['pavimentos']:
    COM = np.array(Image.open(pv['planta']).convert('RGBA')); H, W = COM.shape[:2]; f = W / 2000.0
    ids = np.load(pv['ambientes'] + '.npz')['ids']
    amb = {int(k): v['nome'] for k, v in json.load(open(pv['ambientes'] + '.json', encoding='utf8'))['ambientes'].items()}
    assert ids.shape == (H, W), 'mascara de ambientes e planta em quadros diferentes'
    alojs = {int(RX_UN.match(v).group(1)): k for k, v in amb.items() if v and RX_UN.match(v)}
    wcs = [k for k, v in amb.items() if v and RX_WC.match(v)]
    c3 = COM[..., :3].astype(np.int16); lm = c3.mean(axis=2); sat = c3.max(axis=2) - c3.min(axis=2)
    verde = (c3[..., 1] > c3[..., 0] + 15) & (c3[..., 1] > c3[..., 2] + 15) & (COM[..., 3] > 0)
    # predio = ambientes + paredes pretas junto deles, fechados; asfalto/grama em volta ficam fora (face externa)
    preto = (lm < 50) & (sat < 20) & (COM[..., 3] > 0) & cv2.dilate((ids > 0).astype(np.uint8), k_(px(0.5))).astype(bool)
    pred = ndi.binary_fill_holes(cv2.morphologyEx(((ids > 0) | preto).astype(np.uint8), cv2.MORPH_CLOSE, k_(px(0.25))) > 0)
    pred &= (COM[..., 3] > 0) & ~verde
    nr = pred & (ids == 0)                                       # parede, esquadria, soleira
    # WC -> unidade da porta: o piso do WC so encosta direto no piso de uma unidade pelo vao da porta (no resto ha parede);
    # sem contato direto (vao com soleira marcada como parede), vale a unidade com mais piso a ate 0,30 m
    dono = {}
    for w in wcs:
        d1 = cv2.dilate((ids == w).astype(np.uint8), k_(7)).astype(bool)
        sc = {cod: int((d1 & (ids == a)).sum()) for cod, a in alojs.items()}
        cod = max(sc, key=sc.get)
        if sc[cod] < 20:
            dw = cv2.dilate((ids == w).astype(np.uint8), k_(px(0.3))).astype(bool)
            ct = {c: int((dw & (ids == a)).sum()) for c, a in alojs.items()}; cod = max(ct, key=ct.get)
            print('  WC', pv['id'], w, 'sem vao direto -> unidade de mais contato', cod, '(conferir na folha)')
        dono.setdefault(cod, []).append(w)
    # gardens: grama separada pelo gradil, encostada na unidade (so quem tem garden no SpotSys)
    gard = {}
    tem_garden = {cod for cod in alojs if float(spot.get(str(cod), {}).get('garden_total_area') or 0) > 0}
    if tem_garden:
        vg = cv2.morphologyEx((verde & ~pred).astype(np.uint8), cv2.MORPH_OPEN, k_(5))
        n, l, s, _ = cv2.connectedComponentsWithStats(vg, 4)
        for i in range(1, n):
            if s[i, 4] * M_PX ** 2 < 0.3: continue
            m = l == i
            d = cv2.dilate(m.astype(np.uint8), k_(px(0.65))).astype(bool)
            viz = {cod: int((d & (ids == a)).sum()) for cod, a in alojs.items() if cod in tem_garden}
            if not viz or max(viz.values()) < 5000: continue
            if s[i, 4] * M_PX ** 2 > 40:
                # gramado comum emendado ao garden (gradil fino nao separou): para cada unidade com garden encostada, o garden
                # e a faixa de grama logo depois da fachada dela, ate o primeiro corte (gradil) e no maximo 3 m
                for cod, v in viz.items():
                    if v < 5000 or cod in gard: continue
                    a_ = cv2.dilate((ids == alojs[cod]).astype(np.uint8), k_(9)).astype(bool)
                    ys, xs = np.nonzero(a_); bx0, bx1, by0, by1 = xs.min(), xs.max(), ys.min(), ys.max()
                    lados = {'b': m[by1:min(by1 + px(0.6), H), bx0:bx1].sum(), 't': m[max(by0 - px(0.6), 0):by0, bx0:bx1].sum(),
                             'r': m[by0:by1, bx1:min(bx1 + px(0.6), W)].sum(), 'l': m[by0:by1, max(bx0 - px(0.6), 0):bx0].sum()}
                    lado = max(lados, key=lados.get); mg = np.zeros((H, W), bool)
                    for t in (range(bx0, bx1 + 1) if lado in 'bt' else range(by0, by1 + 1)):
                        lin = m[:, t] if lado in 'bt' else m[t, :]
                        ini = by1 if lado == 'b' else by0 if lado == 't' else bx1 if lado == 'r' else bx0
                        passo = 1 if lado in 'br' else -1
                        rng = np.nonzero(lin[ini:] if passo == 1 else lin[:ini + 1][::-1])[0]
                        if not len(rng): continue
                        a0 = rng[0]; a1 = a0
                        while a1 + 1 < len(rng) and rng[a1 + 1] == rng[a1] + 1: a1 += 1
                        p0, p1 = rng[a0], rng[a1]
                        if (p1 - p0) * M_PX > 3.0: continue
                        if passo == 1: q0, q1 = ini + p0, ini + p1
                        else: q0, q1 = ini - p1, ini - p0
                        if lado in 'bt': mg[q0:q1 + 1, t] = True
                        else: mg[t, q0:q1 + 1] = True
                    gard[cod] = mg
                continue
            cod = max(viz, key=viz.get); gard[cod] = gard.get(cod, np.zeros((H, W), bool)) | m
    # contorno: meio da parede entre unidades; parede e vao de entrada inteiros do lado do corredor/fachada
    privado = np.isin(ids, list(alojs.values()) + wcs)
    _, (iy, ix) = ndi.distance_transform_edt(~privado, return_indices=True)
    mais_perto = ids[iy, ix]; dist = ndi.distance_transform_edt(~privado)
    mais_perto[(ids > 0) & ~privado] = 0
    nr8 = nr.astype(np.uint8); L = px(1.2) | 1
    vao = ((cv2.morphologyEx(nr8, cv2.MORPH_CLOSE, np.ones((1, L), np.uint8)) | cv2.morphologyEx(nr8, cv2.MORPH_CLOSE, np.ones((L, 1), np.uint8))) > 0) & ~nr & ~privado
    unidades = {}
    for cod in sorted(alojs):
        meus = [alojs[cod]] + dono.get(cod, [])
        core = np.isin(ids, meus)
        un = core | (nr & np.isin(mais_perto, meus) & (dist <= px(0.25)))
        un |= vao & cv2.dilate(core.astype(np.uint8), k_(2 * px(0.28) + 1)).astype(bool)
        ga = gard.get(cod)
        if ga is not None:
            un |= cv2.dilate(ga.astype(np.uint8), k_(25)).astype(bool) & ~(ids > 0) & (COM[..., 3] > 0)
            un |= cv2.morphologyEx(un.astype(np.uint8), cv2.MORPH_CLOSE, k_(41)).astype(bool) & (ids == 0)
        un = cv2.morphologyEx(un.astype(np.uint8), cv2.MORPH_CLOSE, k_(41)).astype(bool) & (np.isin(ids, meus) | (ids == 0) | (un & vao))
        n2, l2, s2, _ = cv2.connectedComponentsWithStats(un.astype(np.uint8), 8); un = ndi.binary_fill_holes(l2 == 1 + int(np.argmax(s2[1:, 4])))
        cs, _ = cv2.findContours(un.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        c = cv2.approxPolyDP(max(cs, key=cv2.contourArea), 4, True)[:, 0, :].astype(float)
        chave = str(cod).zfill(DIG)
        unidades[chave] = {'poligonos': [{'pts': [[round(x / f, 2), round(y / f, 2)] for x, y in c]}]}
        mo = cv2.moments(un.astype(np.uint8), True); s_ = spot.get(str(cod), {})
        if not s_.get('id'): print('  ERRO: unidade', cod, 'sem id no export do SpotSys'); erros += 1
        pins.append(dict(szi_unit_id=int(s_['id']) if s_.get('id') else None, codigo=str(cod), andar=pv['andar'],
                         planta=os.path.basename(pv['planta']), largura_px=W, altura_px=H, pin_type='polygon',
                         polygon_vertices=[dict(x=round(x / W, 5), y=round(y / H, 5)) for x, y in c],
                         x=round(mo['m10'] / mo['m00'] / W, 5), y=round(mo['m01'] / mo['m00'] / H, 5)))
    feitos = sorted(alojs); esperado = sorted(int(c) for c, r in spot.items() if r.get('floor') == str(pv['andar']) and c.isdigit())
    ok = feitos == esperado; erros += 0 if ok else 1
    print(pv['id'], 'unidades', feitos, '| SpotSys', esperado, '| C8', 'OK' if ok else 'DIFERENTE')
    cfg = {'planta': os.path.abspath(pv['planta']), 'saida': os.path.abspath(os.path.join(C['unidades'], pv.get('pasta', pv['id']))),
           'nome': C['empreendimento'] + ' - {id}.png', 'apagar': [], 'unidades': unidades}
    json.dump(cfg, open(os.path.join(C['configs'], pv['id'] + '.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
os.makedirs(os.path.dirname(os.path.abspath(C['pins'])), exist_ok=True)
json.dump(pins, open(C['pins'], 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print('pins', len(pins), '| erros', erros)
sys.exit(1 if erros else 0)
