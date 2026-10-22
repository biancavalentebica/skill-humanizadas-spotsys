"""Lagoa Spot, humanizada DO ZERO pelo executivo R10: base do pavimento (sem mobiliario).
Predio: pisos por ambiente (madeira nos alojamentos, porcelanato 90x90 na circulacao/recepcao, porcelanato menor nos WC),
paredes no perfil do lancamento (contorno preto, filete branco, miolo preto) com sombra suave, vidros, portas (folha e arco
do executivo) com soleira de granito, loucas (vaso, ducha, lavatorio) recortadas do lancamento e giradas pela caixa do
executivo, escada e elevador. Area externa: a do lancamento (o executivo nao desenha estacionamento, gardens e gradis).
Uso: py gera_base.py <prefixo> <lancamento.png> <saida.png>"""
import sys, json, re, numpy as np, cv2
from PIL import Image; Image.MAX_IMAGE_PIXELS = None
import kit_lagoa as kit
pref, lanc_p, saida = sys.argv[1:4]
A = np.load(pref + '_amb.npz'); J = json.load(open(pref + '_amb.json', encoding='utf8'))
T = np.array(json.load(open(pref + '_reg.json'))['exec_para_lanc'], np.float32)
ids, par, vid, sol, porta = A['ids'], A['paredes'], A['vidro'], A['soleira'], A['porta_linhas']
esc, guarda = A['escada'], A['guarda']
LA = np.array(Image.open(lanc_p).convert('RGBA')); H, W = ids.shape
LK = np.array(Image.open(kit.LANC).convert('RGB'))     # kit sempre do terreo
img = LA[..., :3].copy(); alfa = LA[..., 3].copy()
import tira_rotulos
_pred = cv2.dilate((((A['ids'] > 0) | A['paredes'] | A['vidro'])).astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool)
img, alfa, LOG_ROT = tira_rotulos.tira(img, alfa, _pred)
print('rotulos do lancamento retirados', len(LOG_ROT), 'custos', [r.get('custo_emenda') for r in LOG_ROT])
amb = {int(k): v for k, v in J['ambientes'].items()}
def m_nome(rx): return np.isin(ids, [k for k, v in amb.items() if re.match(rx, v['nome'])])
alojs, wcs = m_nome(r'ALOJ'), m_nome(r'WC|PNE')
comum = m_nome(r'CIRC|RECEP|ESCADA|ESTAR|HALL'); elev = m_nome(r'ELEVADOR')
# escada: dentro do comum, onde ha linhas de degrau do executivo (fecho convexo dos tracos)
esc_area = np.zeros((H, W), bool)
ys, xs = np.nonzero(esc & comum)
if len(ys):
    n, lab, st, _ = cv2.connectedComponentsWithStats(cv2.dilate((esc & comum).astype(np.uint8), np.ones((41, 41), np.uint8)), 8)
    for i in range(1, n):
        if st[i, 4] > 20000:
            pts = np.column_stack(np.nonzero(lab == i)[::-1]); hull = cv2.convexHull(pts)
            t = np.zeros((H, W), np.uint8); cv2.fillPoly(t, [hull], 1); esc_area |= (t > 0) & comum
comum_piso = comum & ~esc_area
predio = (ids > 0) | par | vid | sol
rng = np.random.default_rng(7)

def tile(fonte, hw, roll_cols=0):
    h, w = fonte.shape[:2]; Hh, Ww = hw
    out = np.tile(fonte, (Hh // h + 2, Ww // w + 2, 1))
    if roll_cols:   # madeira: cada faixa de reguas com deslocamento vertical proprio (juntas desencontradas)
        for c0 in range(0, out.shape[1], roll_cols):
            out[:, c0:c0 + roll_cols] = np.roll(out[:, c0:c0 + roll_cols], int(rng.integers(0, h)), axis=0)
    return out[:Hh, :Ww]
def madeira_real(alvo):
    """Assoalho do proprio lancamento (mesma geometria do executivo). Onde ha movel, sombra ou texto, cada coluna
    continua com o trecho de regua real logo acima (ou abaixo): as reguas sao verticais, entao a continuacao e real."""
    f = LK.astype(np.int16); R, G, B = f[..., 0], f[..., 1], f[..., 2]; lum = f.mean(axis=2)
    ok = (R - B > 28) & (R - B < 75) & (lum > 105) & (lum < 175) & (G > B)
    ok = cv2.erode(ok.astype(np.uint8), np.ones((7, 7), np.uint8)) > 0
    out = LK.copy(); ys, xs = np.nonzero(alvo)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    for x in range(x0, x1):
        col_a = alvo[y0:y1, x]; col_ok = ok[y0:y1, x] & col_a
        if not col_a.any(): continue
        bons = np.nonzero(col_ok)[0]
        if not len(bons): continue
        y = 0; n = y1 - y0
        while y < n:
            if col_a[y] and not col_ok[y]:
                r = y
                while r < n and col_a[r] and not col_ok[r]: r += 1
                L = r - y
                # fonte: o mesmo comprimento logo acima, se for regua valida; senao logo abaixo; senao o trecho valido mais longo
                for s0 in (y - L, r, None):
                    if s0 is None:
                        s0 = bons[0]; src = np.arange(L) % max(1, len(bons)); out[y0 + y:y0 + r, x] = out[y0 + bons[src], x]; break
                    if s0 >= 0 and s0 + L <= n and col_ok[s0:s0 + L].all():
                        out[y0 + y:y0 + r, x] = out[y0 + s0:y0 + s0 + L, x]; break
                y = r
            else: y += 1
    return out
MAD = kit.assoalho(H, W)
_f = LA[..., :3].astype(np.int16); _m = ((_f[..., 0] - _f[..., 2] > 28) & (_f[..., 0] - _f[..., 2] < 75) & (_f.mean(2) > 105) & (_f.mean(2) < 185))
_alvo = LA[..., :3][_m & alojs].reshape(-1, 3).mean(0); _atual = MAD[alojs].reshape(-1, 3).mean(0)
MAD = np.clip(MAD.astype(np.float32) * (_alvo / _atual), 0, 255).astype(np.uint8)
print('madeira lancamento', _alvo.round(), 'antes', _atual.round())
POR = tile(kit.porcelanato(), (H, W))
p2 = cv2.resize(kit.porcelanato(), None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA); WCP = tile(p2, (H, W))
img[alojs] = MAD[alojs]; img[comum_piso] = POR[comum_piso]; img[wcs] = WCP[wcs]
# escada: degraus reais do lancamento (cinza) + tracos de degrau do executivo
if esc_area.any():
    img[esc_area] = LA[..., :3][esc_area]      # degraus reais do lancamento (mesma escada do executivo)
ELV = tile(LK[1750:1850, 3900:4000], (H, W)); img[elev] = ELV[elev]
SOL = tile(LK[1895:2040, 4965:5005], (H, W)); img[sol] = SOL[sol]
alfa[predio] = 255
# sombra suave das paredes sobre os pisos
som = cv2.GaussianBlur(par.astype(np.float32), (0, 0), 6)
som = np.roll(np.roll(som, 5, 0), 5, 1) * 0.28
piso = predio & ~par
img[piso] = (img[piso] * (1 - som[piso, None])).astype(np.uint8)
# paredes: contorno preto 2 px, filete branco 4 px, miolo preto
p8 = par.astype(np.uint8)
e2 = cv2.erode(p8, np.ones((5, 5), np.uint8)) > 0; e6 = cv2.erode(p8, np.ones((13, 13), np.uint8)) > 0
img[par] = (18, 18, 20); img[e2 & ~e6] = (245, 245, 245); img[e6] = (18, 18, 20)
# vidros: faixa clara com contorno grafite
v = cv2.dilate(vid.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
img[v] = (205, 212, 218); img[vid & ~(cv2.erode(v.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0)] = (70, 80, 92)
# portas: folha e arco do executivo
pl = cv2.dilate(porta.astype(np.uint8), np.ones((2, 2), np.uint8)) > 0
img[pl & ~par] = (35, 38, 48)
if guarda.any(): img[guarda] = (90, 90, 95)

def lado_alvo(cx, cy, nx, ny, d):
    """id do ambiente a distancia d do centro do vao, nos dois sentidos da normal."""
    a = ids[int(np.clip(cy + ny * d, 0, H - 1)), int(np.clip(cx + nx * d, 0, W - 1))]
    b = ids[int(np.clip(cy - ny * d, 0, H - 1)), int(np.clip(cx - nx * d, 0, W - 1))]
    return a, b
def peso(k):   # abre para dentro do alojamento / WC (nunca para a circulacao)
    nm = amb.get(int(k), {}).get('nome', '')
    return 3 if nm.startswith(('WC', 'PNE')) else 2 if nm.startswith('ALOJ') else 1 if k else 0
n_p = 0
for pt in J['portas']:
    if pt['tipo'] != 'abrir' or int(round(pt['rot'])) % 90 or re.search(r'BASCULANTE|CORTAFOGO', pt['nome']): continue
    x0, y0, x1, y1 = pt['caixa']; cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    if pt['horiz']: L = x1 - x0 - 8; nx, ny = 0, 1; ex, ey = 1, 0; esp = y1 - y0
    else: L = y1 - y0 - 8; nx, ny = 1, 0; ex, ey = 0, 1; esp = x1 - x0
    a, b = lado_alvo(cx, cy, nx, ny, esp / 2 + 40)
    if peso(b) > peso(a): nx, ny = -nx, -ny
    # dobradica: a ponta do vao mais perto de uma parede perpendicular dentro do ambiente
    def dist_parede(sg):
        px0, py0 = cx + ex * sg * L / 2 + nx * (esp / 2 + 25), cy + ey * sg * L / 2 + ny * (esp / 2 + 25)
        for t in range(0, 400, 4):
            xx, yy = int(px0 + ex * sg * t), int(py0 + ey * sg * t)
            if not (0 <= xx < W and 0 <= yy < H) or par[yy, xx]: return t
        return 400
    sg = -1 if dist_parede(-1) <= dist_parede(1) else 1
    hx, hy = cx + ex * sg * L / 2 + nx * esp / 2, cy + ey * sg * L / 2 + ny * esp / 2      # dobradica na face
    tx, ty = hx + nx * L, hy + ny * L                                                       # ponta da folha aberta
    e = 9   # folha ~3,5 cm
    q = np.array([[hx, hy], [tx, ty], [tx - ex * sg * e, ty - ey * sg * e], [hx - ex * sg * e, hy - ey * sg * e]], np.int32)
    cv2.fillPoly(img, [q], (62, 68, 84)); cv2.polylines(img, [q], True, (30, 32, 40), 1, cv2.LINE_AA)
    # arco: da ponta da folha ate a outra ponta do vao
    a0 = np.degrees(np.arctan2(ny, nx)); a1 = np.degrees(np.arctan2(-ey * sg, -ex * sg))
    if abs(((a1 - a0 + 180) % 360) - 180) > 0:
        d = ((a1 - a0 + 180) % 360) - 180
        cv2.ellipse(img, (int(round(hx)), int(round(hy))), (int(L), int(L)), 0, a0, a0 + d, (25, 25, 25), 2, cv2.LINE_AA)
    n_p += 1
print('portas desenhadas', n_p)

# loucas: recortes do lancamento (orientacao de referencia) girados pela caixa do executivo
ins = json.load(open(pref + '_inserts.json', encoding='utf8'))
def caixa_lanc(c):
    p0 = T @ np.array([c[0], c[1], 1.0]); p1 = T @ np.array([c[2], c[3], 1.0])
    return int(round(min(p0[0], p1[0]))), int(round(min(p0[1], p1[1]))), int(round(max(p0[0], p1[0]))), int(round(max(p0[1], p1[1])))
def sprite(x0, y0, x1, y1, fundo_tol=10):
    sp = LK[y0:y1, x0:x1].astype(np.float32)
    borda = np.concatenate([sp[0], sp[-1], sp[:, 0], sp[:, -1]]); f = np.median(borda, axis=0)
    d = np.abs(sp - f).max(axis=2); a = cv2.GaussianBlur((d > fundo_tol).astype(np.float32), (0, 0), 1.2)
    a = np.clip(cv2.dilate(a, np.ones((3, 3), np.uint8)) * 1.2, 0, 1)
    return sp.astype(np.uint8), a
VASO = sprite(5076, 2017, 5168, 2173)        # caixa do executivo no lancamento: tanque embaixo (assento em cima)
LAV = sprite(4789, 2038, 4963, 2174)          # lavatorio redondo na bancada, rot 180 no executivo
LAV = (LAV[0], np.ones(LAV[1].shape, np.float32))   # com o granito da bancada (recorte inteiro)
DUCHA = sprite(5292, 2046, 5333, 2118)
def cola(sp, a, x0, y0, k90=0, flip=False):
    s, al = sp, a
    if flip: s, al = s[:, ::-1], al[:, ::-1]
    s, al = np.rot90(s, k90), np.rot90(al, k90)
    h, w = al.shape; x1, y1 = min(x0 + w, W), min(y0 + h, H)
    if x0 < 0 or y0 < 0 or x1 <= x0 or y1 <= y0: return
    al = al[:y1 - y0, :x1 - x0, None]; s = s[:y1 - y0, :x1 - x0]
    img[y0:y1, x0:x1] = (s * al + img[y0:y1, x0:x1] * (1 - al)).astype(np.uint8)
bacias = [e for e in ins if re.search(r'Bacia', e['nome'])]; assentos = [e for e in ins if re.search(r'Assento', e['nome'])]
n_v = n_l = n_d = 0
for b in bacias:
    bx = caixa_lanc(b['caixa']); cb = np.array([(bx[0] + bx[2]) / 2, (bx[1] + bx[3]) / 2])
    near = min(assentos, key=lambda s: np.hypot(*(np.array([(caixa_lanc(s['caixa'])[0] + caixa_lanc(s['caixa'])[2]) / 2,
                                                         (caixa_lanc(s['caixa'])[1] + caixa_lanc(s['caixa'])[3]) / 2]) - cb)))
    sx = caixa_lanc(near['caixa']); cs = np.array([(sx[0] + sx[2]) / 2, (sx[1] + sx[3]) / 2])
    d = cb - cs   # do assento para o tanque
    k90 = 0 if abs(d[1]) >= abs(d[0]) and d[1] > 0 else 2 if abs(d[1]) >= abs(d[0]) else 1 if d[0] > 0 else 3
    # rot90 do numpy e anti-horario: tanque embaixo -> k=1 tanque a direita
    s, a = VASO; h, w = a.shape
    hh, ww = (h, w) if k90 % 2 == 0 else (w, h)
    cola(s, a, int(cb[0] - ww / 2), int(cb[1] - hh / 2), k90); n_v += 1
for e in ins:
    if re.search(r'Lavat', e['nome']):
        bx = caixa_lanc(e['caixa']); r = int(round(e['rot'])) % 360
        k90 = {180: 0, 0: 2, 90: 1, 270: 3}.get(r, 0)   # rot 180 = referencia (torneira para cima)
        s, a = LAV; h, w = a.shape; hh, ww = (h, w) if k90 % 2 == 0 else (w, h)
        cx, cy = (bx[0] + bx[2]) / 2, (bx[1] + bx[3]) / 2
        cola(s, a, int(cx - ww / 2), int(cy - hh / 2), k90); n_l += 1
    elif re.search(r'Ducha', e['nome']):
        bx = caixa_lanc(e['caixa']); s, a = DUCHA; h, w = a.shape
        cola(s, a, int((bx[0] + bx[2]) / 2 - w / 2), int((bx[1] + bx[3]) / 2 - h / 2)); n_d += 1
print('vasos', n_v, 'lavatorios', n_l, 'duchas', n_d)
out = np.dstack([img, alfa])
Image.fromarray(out).save(saida)
Image.fromarray(img).resize((W // 4, H // 4)).save(saida.replace('.png', '_previa.jpg'), quality=85)
