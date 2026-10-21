"""Ambientes do executivo no quadro da humanizada de lancamento: paredes, vidros, portas (com soleira) e cada espaco
livre rotulado pelo texto do executivo que cai dentro dele (ALOJ 02, WC, CIRCULACAO...). O que nao tem texto e externo.
Saida <prefixo>_amb.npz (ids, paredes, vidro, porta_linhas, soleira, loucas_linhas, escada_linhas) e <prefixo>_amb.json.
Uso: py ambientes.py <prefixo> <lancamento.png>"""
import sys, json, re, numpy as np, cv2
from PIL import Image; Image.MAX_IMAGE_PIXELS = None
pref, lanc = sys.argv[1:3]
M = np.load(pref + '_masks.npz'); T = np.array(json.load(open(pref + '_reg.json'))['exec_para_lanc'], np.float32)
W, H = Image.open(lanc).size
def wp(a, thr=60):
    return cv2.warpAffine((a > thr).astype(np.uint8), T, (W, H), flags=cv2.INTER_NEAREST) > 0
def tem(k): return k in M.files
par = wp(M['parede_ext']) | wp(M['parede_int'])
for k in ('parede_ext_hatch', 'parede_int_hatch'):
    if tem(k): par |= wp(M[k])
# contorno de parede -> parede cheia (furos menores que 40 cm2 dentro da massa)
par = cv2.morphologyEx(par.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)) > 0
inv = (~par).astype(np.uint8); n, lab, st, _ = cv2.connectedComponentsWithStats(inv, 4)
for i in range(1, n):
    if st[i, 4] < 2500: par[lab == i] = True
vid = wp(M['vidro']) if tem('vidro') else np.zeros((H, W), bool)
porta = wp(M['porta']) if tem('porta') else np.zeros((H, W), bool)
louc = wp(M['loucas'], 40) if tem('loucas') else np.zeros((H, W), bool)
esc = wp(M['escada'], 40) if tem('escada') else np.zeros((H, W), bool)
guarda = wp(M['guarda']) if tem('guarda') else np.zeros((H, W), bool)
# vaos: o DXF do Revit nao corta a parede na porta (a hachura passa pelo vao) -> a caixa de cada bloco de porta
# abre a parede. Porta de abrir/corta-fogo/basculante = soleira de granito; porta-janela de correr = vidro.
ins = json.load(open(pref + '_inserts.json', encoding='utf8'))
sol = np.zeros((H, W), bool); portas = []
for e in ins:
    if e['layer'] != 'A-DOOR': continue
    x0, y0, x1, y1 = e['caixa']
    p0 = T @ np.array([x0, y0, 1.0]); p1 = T @ np.array([x1, y1, 1.0])
    a0, b0 = int(round(min(p0[0], p1[0]))), int(round(min(p0[1], p1[1]))); a1, b1 = int(round(max(p0[0], p1[0]))), int(round(max(p0[1], p1[1])))
    a0, b0 = max(a0, 0), max(b0, 0)
    horiz = (a1 - a0) >= (b1 - b0)
    # so a faixa da parede: na espessura, a caixa toda; no comprimento, tira 2 px de cada lado (batente)
    reg = np.zeros((b1 - b0, a1 - a0), bool)
    if horiz: reg[:, 2:-2] = True
    else: reg[2:-2, :] = True
    tipo = 'correr' if re.search(r'PJN|CORRER', e['nome']) else 'abrir'
    if tipo == 'abrir' and int(round(e['rot'])) % 90:
        # porta em diagonal: o vao ja existe; a soleira e o fecho das paredes dentro da caixa (fecha o vao, nao invade o piso)
        pc = par[b0:b1, a0:a1].astype(np.uint8)
        fch = cv2.morphologyEx(pc, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (181, 181))) > 0
        reg = fch
    par[b0:b1, a0:a1] &= ~reg
    if tipo == 'correr': vid[b0:b1, a0:a1] |= reg
    else: sol[b0:b1, a0:a1] |= reg
    portas.append(dict(nome=e['nome'][:70], tipo=tipo, caixa=[a0, b0, a1, b1], horiz=bool(horiz), rot=e['rot']))
# esquadria: as linhas do caixilho vem em pares (face interna e externa); a faixa entre elas e esquadria, nao passagem
vid = cv2.morphologyEx(vid.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((31, 31), np.uint8)) > 0
barreira = par | cv2.dilate(vid.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool) | sol | guarda
# frestas da envoltoria (encontro de parede com caixilho no DXF): fecho de 25 cm so para separar dentro/fora
_env = cv2.morphologyEx((par | vid).astype(np.uint8), cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (61, 61))) > 0
barreira |= _env & (cv2.morphologyEx((par | vid).astype(np.uint8), cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (61, 61))) > 0)
livre = (~barreira).astype(np.uint8)
n, lab = cv2.connectedComponents(livre, connectivity=4)
# textos do executivo -> quadro
tx = json.load(open(pref + '_textos.json', encoding='utf8'))
NOMES = r'^(ALOJ\.?|WC|PNE|CIRCULA|ESTAR|RECEP|ELEVADOR|ESCADA|HALL|CIRC)'
pontos = []
for t in tx:
    p = T @ np.array([t['x'], t['y'], 1.0]); pontos.append((t['t'], int(p[0]), int(p[1])))
amb = {}
for t, x, y in pontos:
    if not (0 <= x < W and 0 <= y < H): continue
    k = int(lab[y, x])
    if k == 0:   # texto em cima de linha: procura o espaco livre mais proximo
        ys, xs = np.nonzero(lab[max(y - 30, 0):y + 30, max(x - 30, 0):x + 30])
        if not len(ys): continue
        k = int(lab[max(y - 30, 0) + ys[0], max(x - 30, 0) + xs[0]])
    amb.setdefault(k, []).append(t)
def nome(ts):
    s = ' '.join(ts).upper()
    num = [t for t in ts if re.fullmatch(r'\d{2}', t.strip())]
    area = [t for t in ts if 'm' in t and ',' in t]
    if 'ALOJ' in s: return 'ALOJ ' + (num[0] if num else '?'), area
    for chave in ('PNE', 'WC', 'ELEVADOR', 'ESCADA', 'RECEP', 'CIRC', 'HALL'):
        if chave in s: return {'RECEP': 'RECEPCAO', 'CIRC': 'CIRCULACAO', 'HALL': 'CIRCULACAO'}.get(chave, chave), area
    return s, area
# espacos fechados sem texto (ex.: WC do Aloj 12 no 2o pav.): WC se tiver vaso do executivo dentro
_n2, _lab2, _st2, _ = cv2.connectedComponentsWithStats(livre, connectivity=4)
for e in ins:
    if not re.search(r'Bacia', e['nome']): continue
    x0, y0, x1, y1 = e['caixa']; c = T @ np.array([(x0 + x1) / 2, (y0 + y1) / 2, 1.0])
    k = int(lab[int(c[1]), int(c[0])])
    if k and k not in amb:
        ys_, xs_ = np.nonzero(lab == k)
        if len(ys_) * 0.004022 ** 2 < 6 and xs_.min() > 0 and ys_.min() > 0: amb[k] = ['WC', '(sem texto no executivo)']
ids = np.zeros((H, W), np.int32); info = {}
for k, ts in amb.items():
    nm, area = nome(ts); ids[lab == k] = k
    ys, xs = np.nonzero(lab == k)
    info[k] = dict(nome=nm, textos=ts, area_texto=area, px=int(len(ys)), m2=round(len(ys) * 0.004022 ** 2, 2),
                   caixa=[int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())])
np.savez_compressed(pref + '_amb.npz', barreira=barreira, ids=ids, paredes=par, vidro=vid, porta_linhas=porta, soleira=sol, loucas=louc, escada=esc, guarda=guarda)
json.dump(dict(ambientes={str(k): v for k, v in info.items()}, portas=portas), open(pref + '_amb.json', 'w', encoding='utf8'), indent=1, ensure_ascii=False)
for k, v in sorted(info.items(), key=lambda kv: kv[1]['nome']): print(v['nome'], v['m2'], v['area_texto'], v['textos'][:3])
# conferencia visual
rng = np.random.default_rng(1); cor = rng.integers(60, 255, (ids.max() + 1, 3)).astype(np.uint8); cor[0] = 255
viz = cor[ids]; viz[par] = 0; viz[sol] = (255, 0, 0); viz[vid] = (0, 120, 255)
for k, v in info.items():
    x0, y0, x1, y1 = v['caixa']; cv2.putText(viz, v['nome'], ((x0 + x1) // 2 - 80, (y0 + y1) // 2), 0, 1.6, (0, 0, 0), 4)
Image.fromarray(viz).resize((W // 3, H // 3)).save(pref + '_amb.jpg', quality=85)
