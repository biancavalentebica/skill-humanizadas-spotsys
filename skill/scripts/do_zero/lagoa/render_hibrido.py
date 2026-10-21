"""Lagoa Spot: humanizada DO ZERO, padrao grafico da humanizada de lancamento (referencia), geometria:
- paredes, esquadrias, portas e loucas do EXECUTIVO R10 (DWG, retas e limpas) onde o layout nao mudou;
- PDF LEGAL (rev. 27/11/2024) nas zonas em que o projeto mudou (ZONAS_LEGAL: Administracao/Rouparia/WC PNE no terreo;
  Aloj 12/13 + WC PNE no 2o pav.) e na area externa (acesso social, plataforma, jardins, muros, gradis, lixo).
Representacao (igual ao lancamento): parede preta com filete branco interno; vao de janela/porta com peitoril/soleira de
granito e vidro azul-acinzentado em perfil fino; porta de abrir = folha fina com puxador + arco fino; box = vidro em
linha fina; escada = degraus em degrade com bocel fino (sem seta/eixo); moveis e loucas do layout do lancamento, sempre
dentro do ambiente, encostados nas paredes, fora do giro das portas.
Uso: py render_hibrido.py <P> <lancamento.png> <saida.png>"""
import sys, json, re, numpy as np, cv2
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
sys.path.insert(0, '../do_zero'); import kit_lagoa as kit; import tira_rotulos
DZ = '../do_zero/'
P, lanc_p, sai = sys.argv[1:4]
M_PX = 0.004022375816200381
ZONAS_LEGAL = {'TER': [(2205, 1085, 3290, 2420)], '02P': [(1790, 395, 5025, 1415), (4830, 1330, 5270, 1452)]}[P]
LA = np.array(Image.open(lanc_p).convert('RGBA')); LK = np.array(Image.open(kit.LANC).convert('RGB'))
H, W = LA.shape[:2]
PONTA = {'TER': (6122, 1960, 6888, 2810), '02P': (5712, 1180, 6478, 2030)}[P]
zona = np.zeros((H, W), bool)
for x0, y0, x1, y1 in ZONAS_LEGAL: zona[y0:y1, x0:x1] = True
A0 = np.load(DZ + P + '_amb.npz'); J0 = json.load(open(DZ + P + '_amb.json', encoding='utf8'))
AL = np.load(P + '_legal_amb.npz'); JL = json.load(open(P + '_legal_amb.json', encoding='utf8'))
Z = np.load(f'legal_{P}_masks.npz'); camada = lambda k: (Z[k] > 15) if k in Z.files else np.zeros((H, W), bool)
# ---- geometria hibrida ------------------------------------------------------------------------------------------
par = (A0['paredes'] & ~zona) | (AL['parede_so'] & zona)
# na borda da zona as duas fontes se encontram: une executivo e Legal numa faixa de 40 px para a parede nao abrir
_borda = cv2.dilate(zona.astype(np.uint8), np.ones((41, 41), np.uint8)).astype(bool) & ~cv2.erode(zona.astype(np.uint8), np.ones((41, 41), np.uint8)).astype(bool)
par |= (A0['paredes'] | AL['parede_so']) & _borda & cv2.dilate(A0['paredes'].astype(np.uint8), np.ones((15, 15), np.uint8)).astype(bool)
# ajustes pontuais conferidos no lancamento x Legal (02P: parede entre os WCs das unidades 13 e 14 vai ate o fundo;
# traco solto do shaft entre eles sai)
PAREDE_ADD = {'TER': [], '02P': [(5010, 1370, 5056, 1430)]}[P]
PAREDE_DEL = {'TER': [], '02P': [(5058, 1325, 5260, 1360)]}[P]
for x0, y0, x1, y1 in PAREDE_ADD: par[y0:y1, x0:x1] = True
if P == 'TER':   # WC PNE (Legal): paredes retas, vao de 0,75 m embaixo a esquerda
    par[1762:2215, 2690:3290] = False
    par[1762:1792, 2690:3262] = True; par[1762:2208, 2690:2742] = True; par[1762:2208, 3233:3262] = True
    par[2160:2208, 2690:3262] = True; par[2160:2208, 2742:2930] = False
for x0, y0, x1, y1 in PAREDE_DEL: par[y0:y1, x0:x1] = False
# so paredes de verdade: tira tracos finos (diagonais de hachura/shaft do CAD) com abertura de 9 px (~3,6 cm)
par = cv2.morphologyEx(par.astype(np.uint8), cv2.MORPH_OPEN, np.ones((15, 15), np.uint8)) > 0
if P != 'TER':   # pavimento tipo: sem pilares/projecao do terreo fora da lamina (o lancamento nao mostra)
    from scipy import ndimage as _ndi
    _env = cv2.morphologyEx(((A0['ids'] > 0) | A0['paredes']).astype(np.uint8), cv2.MORPH_CLOSE, np.ones((61, 61), np.uint8)) > 0
    _env = _ndi.binary_fill_holes(cv2.morphologyEx(_env.astype(np.uint8), cv2.MORPH_OPEN, np.ones((61, 61), np.uint8)) > 0)
    par &= cv2.dilate(_env.astype(np.uint8), np.ones((15, 15), np.uint8)).astype(bool)
vid = (A0['vidro'] & ~zona) | (AL['vidro'] & zona)
sol = (A0['soleira'] & ~zona) | (AL['soleira'] & zona)
if P == 'TER': vid[1762:2160, 2742:3233] = False; sol[2160:2208, 2742:2930] = True; sol[1762:2160, 2742:3233] = False; sol[2160:2208, 2505:2668] = True; par[2160:2208, 2505:2668] = False
for pt in J0['portas']:
    if 'CORTAFOGO' not in pt['nome']: continue
    # soleira so na espessura da parede (o bloco da porta corta-fogo marcava o vao inteiro como soleira)
    x0, y0, x1, y1 = pt['caixa']
    lin_p = par[y0:y1, max(x0 - 6, 0)] | par[y0:y1, min(x1 + 6, W - 1)]
    col_p = par[max(y0 - 6, 0), x0:x1] | par[min(y1 + 6, H - 1), x0:x1]
    if lin_p.any() and lin_p.sum() < (y1 - y0) * 0.6: sol[y0:y1, x0:x1] &= lin_p[:, None]
    elif col_p.any() and col_p.sum() < (x1 - x0) * 0.6: sol[y0:y1, x0:x1] &= col_p[None, :]
    vid[y0:y1, x0:x1] = False                     # sem vidro/traco do bloco dentro do vao da porta
for pt in J0['portas']:
    if int(round(pt['rot'])) % 90 == 0: continue
    x0, y0, x1, y1 = pt['caixa']; a_, b_, c_, d_ = max(x0 - 90, 0), max(y0 - 90, 0), min(x1 + 90, W), min(y1 + 90, H)
    _p = par[b_:d_, a_:c_].astype(np.uint8); _v = cv2.dilate((sol | vid)[b_:d_, a_:c_].astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    # preenche so os entalhes em 'V' (fecho convexo de cada pedaco de parede, limitado a 12 px da parede): face reta
    _n6, _l6 = cv2.connectedComponents(_p, connectivity=8); _f = np.zeros(_p.shape, bool)
    for _i in range(1, _n6):
        _pts = np.column_stack(np.nonzero(_l6 == _i)[::-1]).astype(np.int32)
        if len(_pts) < 30: continue
        _h = np.zeros(_p.shape, np.uint8); cv2.fillConvexPoly(_h, cv2.convexHull(_pts), 1); _f |= _h.astype(bool)
    _f &= cv2.dilate(_p, np.ones((25, 25), np.uint8)).astype(bool) & ~_v
    par[b_:d_, a_:c_] |= _f
muro = AL['muro'].copy() if P == 'TER' else np.zeros((H, W), bool)   # pavimento tipo: sem muros (o Legal traz a projecao do terreo)
# muro so fora do predio: pedacos colados na fachada / dentro dos ambientes vem de esquadria do Legal, nao sao muro
_pred = cv2.dilate((A0['ids'] > 0 | par).astype(np.uint8) if False else ((A0['ids'] > 0) | par).astype(np.uint8), np.ones((41, 41), np.uint8)).astype(bool)
_n, _l, _s, _ = cv2.connectedComponentsWithStats(muro.astype(np.uint8), 8)
for _i in range(1, _n):
    _m = _l == _i
    if _pred[_m].mean() > 0.5 and max(_s[_i, 2], _s[_i, 3]) < 900: muro[_m] = False
# ambientes: flood com a barreira hibrida, nomes pelo Legal (zonas) ou executivo (resto)
barr = par | cv2.dilate(vid.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool) | sol | (A0['barreira'] & ~zona)   # barreira do executivo fecha frestas de canto
n, lab = cv2.connectedComponents((~barr).astype(np.uint8), connectivity=4)
st = np.bincount(lab.ravel())
ids = np.zeros((H, W), np.int32); amb = {}
idsL, idsE = AL['ids'], A0['ids']
nomeL = {int(k): v['nome'] for k, v in JL['ambientes'].items() if v.get('nome')}
nomeE = {int(k): v['nome'] for k, v in J0['ambientes'].items()}
COD = {'TER': {'01': '11'}, '02P': {'11': '22'}}[P]
for k in range(1, n):
    if st[k] < 2000: continue
    m = lab == k
    if m[0].any() or m[-1].any() or m[:, 0].any() or m[:, -1].any(): continue
    def maj(I, N):
        v = I[m]; v = v[v > 0]
        if len(v) < 0.5 * m.sum(): return None
        c = np.bincount(v).argmax(); return N.get(int(c)) if (v == c).mean() > 0.4 else None
    nm = (maj(idsL, nomeL) or 'COMUM') if m[zona].mean() > 0.5 else (maj(idsE, nomeE) or maj(idsL, nomeL))
    if nm is None: continue
    mm = re.match(r'ALOJ (\d+)', nm)
    if mm and m[zona].mean() <= 0.5: nm = 'ALOJ %02d' % int(COD.get(mm.group(1), mm.group(1)))
    if P == 'TER' and m[2000, 2400]: nm = 'ROUPARIA'          # rouparia (Legal): piso de servico, nao alojamento
    ids[m] = k; amb[k] = nm
# frestas (soleiras) e cantos sem nome -> ambiente vizinho
for _ in range(70):
    z_ = (ids == 0) & ~par & cv2.dilate((ids > 0).astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool) & (sol | (lab > 0) & (st[lab] < 2000) | (A0['ids'] > 0) & (A0['barreira'] | (lab > 0) & (st[lab] < 60000)))
    if not z_.any(): break
    d_ = cv2.dilate(ids.astype(np.float32), np.ones((3, 3), np.uint8)).astype(np.int32); ids[z_] = d_[z_]
# nichos/frestas sem nome dentro da lamina (shaft raso, sobra da soleira da corta-fogo) -> ambiente mais proximo
from scipy import ndimage as ndi
_h = (ids == 0) & ~par
_n, _l, _s, _ = cv2.connectedComponentsWithStats(_h.astype(np.uint8), 4)
_ok = np.zeros(_n, bool)
for _i in range(1, _n):
    x_, y_, w_, h_, a_ = _s[_i]
    _ok[_i] = a_ < 60000 and x_ > 0 and y_ > 0 and x_ + w_ < W and y_ + h_ < H
_h = _ok[_l] & _h
if _h.any():
    _wcid = [k for k, v in amb.items() if re.match(r'WC|PNE', v)]
    _src = (ids == 0) | np.isin(ids, _wcid)
    _, (iy, ix) = ndi.distance_transform_edt(_src, return_indices=True)
    ids[_h] = ids[iy[_h], ix[_h]]
def m_nome(rx): return np.isin(ids, [k for k, v in amb.items() if re.match(rx, v)])
alojs, wcs = m_nome(r'ALOJ'), m_nome(r'WC|PNE')
elev = m_nome(r'ELEVADOR')
esc_int = np.isin(idsL, [k for k, v in nomeL.items() if v == 'ESCADA']) & (ids > 0) & ~par
comum = (ids > 0) & ~alojs & ~wcs & ~elev & ~esc_int
alojs &= ~esc_int
interno = ids > 0
img = np.full((H, W, 3), 255, np.uint8); alfa = np.zeros((H, W), np.uint8)
def tile(f, hw): h, w = f.shape[:2]; return np.tile(f, (hw[0] // h + 2, hw[1] // w + 2, 1))[:hw[0], :hw[1]]
# ---- area externa (Legal) -------------------------------------------------------------------------------------------
esc_ac = (AL['ids'] > 0) & np.isin(AL['ids'], [k for k, v in nomeL.items() if v == 'ESCADA_ACESSO']) if P == 'TER' else np.zeros((H, W), bool)
if P == 'TER':
    lote = cv2.morphologyEx((LA[..., 3] > 0).astype(np.uint8), cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8)) > 0
    pred = cv2.dilate((interno | par | vid | sol).astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    ext = lote & ~pred & ~muro
    simb = cv2.dilate(camada('cor_0_00_0_72_0_00_txt').astype(np.uint8), np.ones((61, 61), np.uint8)).astype(bool)
    _lr, _, _ = tira_rotulos.tira(LA[..., :3], LA[..., 3]); _fl = _lr.astype(np.int16)
    vg = cv2.morphologyEx(((_fl[..., 1] > _fl[..., 0] + 15) & (_fl[..., 1] > _fl[..., 2] + 15)).astype(np.uint8), cv2.MORPH_CLOSE, np.ones((81, 81), np.uint8)) > 0
    # grama do lancamento so onde o Legal tem jardim (simbolos verdes); onde o Legal tem vaga, e piso
    _nv, _lv = cv2.connectedComponents((ext & vg).astype(np.uint8), connectivity=8)
    _ok = np.ones(_nv, bool); _ok[0] = False
    for _px, _py in ((1800, 850),): _ok[_lv[_py, _px]] = False      # frente da Unidade 11: no Legal e estacionamento
    _ok[0] = False
    gram = cv2.morphologyEx((ext & ((simb & ~(_lv == _lv[850, 1800]) if _lv[850, 1800] else simb) | _ok[_lv])).astype(np.uint8), cv2.MORPH_OPEN, np.ones((15, 15), np.uint8)) > 0
    _n, _l, _s, _ = cv2.connectedComponentsWithStats((ext & ~gram).astype(np.uint8), 4)
    for i in range(1, _n):
        if _s[i, 4] > 250000: continue
        m = _l == i; an = cv2.dilate(m.astype(np.uint8), np.ones((7, 7), np.uint8)).astype(bool) & ~m & ext
        if an.any() and gram[an].mean() > 0.6: gram |= m
    GR = tile(LK[4300:4650, 600:3600], (H, W)); PX = tile(cv2.GaussianBlur(LK[300:700, 5100:5900], (0, 0), 1.0), (H, W))
    img[ext] = PX[ext]; img[gram] = GR[gram]; alfa[ext] = 255
    lixo = np.zeros((H, W), bool); lixo[70:480, 1420:1840] = True; lixo &= ext
    img[lixo] = tile(kit.porcelanato(), (H, W))[lixo]          # abrigo de lixo em piso claro, como no lancamento
    grad = cv2.morphologyEx(camada('preto_0_72').astype(np.uint8), cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8)) > 0
    grad &= ext
    _n, _l, _s, _ = cv2.connectedComponentsWithStats(grad.astype(np.uint8), 8)
    grad = np.isin(_l, [i for i in range(1, _n) if max(_s[i, 2], _s[i, 3]) > 250])
else:
    ext = np.zeros((H, W), bool); grad = ext.copy()
# ---- pisos -------------------------------------------------------------------------------------------------------
MAD = kit.assoalho(H, W)
POR = tile(kit.porcelanato(), (H, W)); WCP = tile(cv2.resize(kit.porcelanato(), None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA), (H, W))
img[alojs] = MAD[alojs]; img[comum] = POR[comum]; img[wcs] = WCP[wcs]; alfa[interno | par | vid | sol] = 255
img[elev] = LA[..., :3][elev]
som = np.roll(np.roll(cv2.GaussianBlur(par.astype(np.float32), (0, 0), 7), 6, 0), 6, 1) * 0.30
pis = (alojs | comum | wcs) & ~par
img[pis] = (img[pis] * (1 - som[pis, None])).astype(np.uint8)
# ---- escadas: degrade + bocel fino nas linhas de degrau (sem seta, sem eixo) ---------------------------------------
def caixa(M):
    # escada sempre retangular (o contorno do Legal tem hachura diagonal): caixa da mancha, sem parede
    out = np.zeros((H, W), bool); n_, l_, s_, _ = cv2.connectedComponentsWithStats(M.astype(np.uint8), 8)
    for i_ in range(1, n_):
        x, y, w, h, a = s_[i_]
        if a > 3000: out[y:y + h, x:x + w] = True
    return out & ~par
def degraus(EM, lin_src):
    hl = cv2.morphologyEx((lin_src & cv2.dilate(EM.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool)).astype(np.uint8),
                          cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (80, 1)))
    ys = np.nonzero((hl > 0).any(axis=1) & EM.any(axis=1))[0]
    lin = []
    for y in ys:                               # uma linha por degrau (agrupa linhas vizinhas do CAD)
        if not lin or y - lin[-1] > 12: lin.append(y)
    if len(lin) < 3: return lin
    # degraus iguais: passo = mediana dos intervalos coerentes (>= 0,20 m), do primeiro ao ultimo degrau
    d = np.diff(lin); d = d[d >= 50]; passo = float(np.median(d)) if len(d) else 70.0
    k = max(int(round((lin[-1] - lin[0]) / passo)), 1)
    return [int(round(lin[0] + i * (lin[-1] - lin[0]) / k)) for i in range(k + 1)]
def escada(EM, lin_src, clara=False):
    # lancamento: escada interna em degrade cinza com linhas finas de degrau; escada externa em piso claro com linhas finas
    if not EM.any(): return
    lin = degraus(EM, lin_src); ys, xs = np.nonzero(EM)
    y0, y1 = (lin[0], lin[-1]) if lin else (ys.min(), ys.max())
    yy = np.arange(H)[:, None]
    if clara:
        img[EM] = POR[EM]
    else:
        t = np.clip((ys - ys.min()) / max(ys.max() - ys.min(), 1), 0, 1).astype(np.float32)
        img[ys, xs] = np.clip((100 + 52 * t)[:, None] * np.array([1.0, 0.975, 0.97], np.float32), 0, 255).astype(np.uint8)
    for y in lin:
        row = EM[y]; xs_ = np.nonzero(row)[0]
        cor = (95, 92, 92) if clara else (62, 58, 58)
        img[y:y + 2][EM[y:y + 2]] = cor
    alfa[EM] = 255
esc_int = caixa(esc_int); comum &= ~esc_int; alojs &= ~esc_int
escada(esc_int, A0['escada'] | camada('preto_0_24'))
if P == 'TER': esc_ac = caixa(esc_ac); escada(esc_ac, camada('preto_0_24'), clara=True)
# plataforma elevatoria
plat = np.zeros((H, W), bool)
if P == 'TER':
    n_, l_, s_, _ = cv2.connectedComponentsWithStats(camada('preto_0_72').astype(np.uint8), 8)
    for i in range(1, n_):
        x, y, w, h, a = s_[i]
        if 200 < w < 500 and 200 < h < 500 and abs(w - h) < 80:
            plat[y:y + h, x:x + w] = True
            # plataforma como no lancamento: piso claro com guarda em gradil azul-acinzentado
            img[y:y + h, x:x + w] = POR[y:y + h, x:x + w]
            cv2.rectangle(img, (x, y), (x + w, y + h), (88, 107, 119), 10); cv2.rectangle(img, (x - 5, y - 5), (x + w + 5, y + h + 5), (44, 54, 60), 1)
    alfa[plat] = 255
    # corrimaos da escada de acesso
    if esc_ac.any():
        ys, xs = np.nonzero(esc_ac)
        for xx in (xs.min() + 10, xs.max() - 10):   # corrimao: barra cinza-azulada como no lancamento
            cv2.rectangle(img, (xx - 9, ys.min()), (xx + 9, ys.max()), (88, 107, 119), -1)
            cv2.rectangle(img, (xx - 9, ys.min()), (xx + 9, ys.max()), (44, 54, 60), 2)
# ---- objetos --------------------------------------------------------------------------------------------------------
parD = cv2.dilate(par.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
giro = np.zeros((H, W), bool)          # giro das portas: proibido para moveis (preenchido na secao de portas)
def cola(sp, a, x0, y0, k90=0, sombra=True, clip=None):
    s, al = np.rot90(sp, k90), np.rot90(a, k90).astype(np.float32); h, w = al.shape; x0, y0 = int(round(x0)), int(round(y0))
    xa, ya = max(x0, 0), max(y0, 0); xb, yb = min(x0 + w, W), min(y0 + h, H)
    if xb <= xa or yb <= ya: return
    al = al[ya - y0:yb - y0, xa - x0:xb - x0]; s = s[ya - y0:yb - y0, xa - x0:xb - x0]
    if clip is not None: al = al * clip[ya:yb, xa:xb]
    al = al[..., None]
    if sombra:
        sm = np.zeros_like(al[..., 0]); g_ = cv2.GaussianBlur(al[..., 0], (0, 0), 5); sm[5:, 5:] = g_[:-5, :-5]   # sombra deslocada, sem dar a volta
        sm = sm[..., None] * 0.35
        img[ya:yb, xa:xb] = (img[ya:yb, xa:xb] * (1 - sm)).astype(np.uint8)
    img[ya:yb, xa:xb] = (s * al + img[ya:yb, xa:xb] * (1 - al)).astype(np.uint8)
# portas de abrir: dobradica, folha, giro (antes dos moveis, para o giro ficar livre)
portas = []; LARG = {}
def peso(k): nm = amb.get(int(k), ''); return 3 if nm.startswith(('WC', 'PNE')) else 2 if nm.startswith('ALOJ') else 1 if k else 0
for pt in J0['portas']:
    x0, y0, x1, y1 = pt['caixa']
    if pt['tipo'] != 'abrir' or re.search(r'BASCULANTE', pt['nome']): continue
    if zona[(y0 + y1) // 2, (x0 + x1) // 2]: continue
    hz = pt['horiz'] if int(round(pt['rot'])) % 90 == 0 else None
    if 'CORTAFOGO' in pt['nome']:
        # porta corta-fogo da escada (executivo): vao = soleira dentro da caixa do bloco
        sb = sol[y0:y1, x0:x1]; yy_, xx_ = np.nonzero(sb)
        if not len(xx_): continue
        a_, b_, c_, d_ = x0 + xx_.min(), y0 + yy_.min(), x0 + xx_.max(), y0 + yy_.max()
        hz = (c_ - a_) >= (d_ - b_); x0, y0, x1, y1 = int(a_), int(b_), int(c_), int(d_)
    _mw = re.search(r'(\d{2,3}) ?x ?\d{2,3}', pt['nome'])
    LARG[(x0, y0, x1, y1, hz)] = (int(_mw.group(1)) / 100.0 / M_PX) if _mw else None   # folha com a largura do executivo
    portas.append((x0, y0, x1, y1, hz))
for (x0, y0, x1, y1) in [tuple(int(v) for v in b) for b in []]: pass
# portas do Legal nas zonas: pelos arcos (dobradica conhecida)
arcosL = json.load(open(f'{P}_legal_arcos.json'))
LUM = LA[..., :3].astype(np.float32).mean(axis=2)
# so o traco do arco/folha (cinza bem escuro e fino); piso de madeira escura nao conta
_linha = (LUM < 85) & ((LUM - cv2.blur(LUM, (9, 9))) < -25)
ESCURO = cv2.dilate(_linha.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
_LB = LA[..., :3].astype(np.int16)
FOLHA = cv2.dilate(((_LB[..., 2] - _LB[..., 0] > 8) & (LUM > 50) & (LUM < 135)).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0   # folha azul-acinzentada do lancamento
def porta_exec(x0, y0, x1, y1, horiz, Lfix=None):
    """lado da dobradica e da abertura lidos na humanizada de lancamento (arco + folha), que segue o executivo"""
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    if horiz is None:      # porta na diagonal: eixo do vao pela soleira dentro da caixa
        yy_, xx_ = np.nonzero(sol[y0:y1, x0:x1])
        if len(xx_) > 50:
            _m = np.array([xx_.mean() + x0, yy_.mean() + y0]); _cv = np.cov(np.vstack([xx_, yy_])); _w, _vv = np.linalg.eigh(_cv); _ax = _vv[:, 1]
            _hl = np.hypot(x1 - x0, y1 - y0) * 0.36
            segs = [(tuple(_m - _ax * _hl), tuple(_m + _ax * _hl))]
        else:
            segs = [((x0, y0), (x1, y1)), ((x0, y1), (x1, y0))]
        esp = 52.0
    elif horiz: segs = [((x0 + 4, cy), (x1 - 4, cy))]; esp = y1 - y0
    else: segs = [((cx, y0 + 4), (cx, y1 - 4))]; esp = x1 - x0
    best = None
    for pa, pb in segs:
        pa, pb = np.array(pa, float), np.array(pb, float); L = float(np.hypot(*(pb - pa)))
        # a caixa do executivo inclui os batentes: a folha e menor que o vao (diagonal: caixa inclui a parede)
        Ls = [Lfix] if Lfix else ([L * f for f in (0.5, 0.56, 0.62, 0.68, 0.74)] if horiz is None else [L * f for f in (0.74, 0.8, 0.86, 0.92, 1.0)])
        Lv = L
        e0 = (pb - pa) / max(np.hypot(*(pb - pa)), 1); nn = np.array([-e0[1], e0[0]])
        for L in Ls:
          for h0, e in ((pa, e0), (pb, -e0)):
            h0 = (pa + pb) / 2 - e * L / 2                 # folha centrada no vao (batentes iguais dos dois lados)
            for n in (nn, -nn):
                _c = (pa + pb) / 2; _q1 = _c + n * (esp / 2 + 45); _q0 = _c - n * (esp / 2 + 45)
                _p1 = peso(ids[int(np.clip(_q1[1], 0, H - 1)), int(np.clip(_q1[0], 0, W - 1))]); _p0 = peso(ids[int(np.clip(_q0[1], 0, H - 1)), int(np.clip(_q0[0], 0, W - 1))])
                if _p1 < _p0: continue                     # abre para o lado do alojamento/WC, nunca para a circulacao
                h = h0 + n * esp / 2
                ang = np.radians(np.arange(8, 84, 3))
                pts = h[None] + L * (np.cos(ang)[:, None] * n[None] + np.sin(ang)[:, None] * e[None])
                fol = h[None] + np.linspace(0.15, 0.9, 20)[:, None] * L * n[None]
                ok = lambda q, M=ESCURO: np.mean([M[int(np.clip(y, 0, H - 1)), int(np.clip(x, 0, W - 1))] for x, y in q])
                sc = ok(pts) + 0.5 * ok(fol) + 1.0 * ok(fol, FOLHA)
                if best is None or sc > best[0]: best = (sc, h, n, e, L)
    sc, h, n, e, L = best
    if sc < 0.25 or L < 100: return None
    return (float(h[0]), float(h[1]), float(n[0]), float(n[1]), float(e[0]), float(e[1]), float(L))
for x0, y0, x1, y1, horiz in list(portas):
    r_ = porta_exec(x0, y0, x1, y1, horiz, LARG.get((x0, y0, x1, y1, horiz)))
    if r_ is not None:
        portas[portas.index((x0, y0, x1, y1, horiz))] = r_; continue
    print('  porta sem arco no lancamento', x0, y0, x1, y1, horiz)
    if horiz is None: portas.remove((x0, y0, x1, y1, horiz)); continue
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    if horiz: L = x1 - x0 - 8; nx, ny, ex, ey, esp = 0, 1, 1, 0, y1 - y0
    else: L = y1 - y0 - 8; nx, ny, ex, ey, esp = 1, 0, 0, 1, x1 - x0
    L = LARG.get((x0, y0, x1, y1, horiz)) or L
    d_ = esp / 2 + 40
    ka = ids[int(np.clip(cy + ny * d_, 0, H - 1)), int(np.clip(cx + nx * d_, 0, W - 1))]; kb = ids[int(np.clip(cy - ny * d_, 0, H - 1)), int(np.clip(cx - nx * d_, 0, W - 1))]
    if peso(kb) > peso(ka): nx, ny = -nx, -ny
    def dp(sg):
        px0, py0 = cx + ex * sg * L / 2 + nx * (esp / 2 + 25), cy + ey * sg * L / 2 + ny * (esp / 2 + 25)
        for t_ in range(0, 400, 4):
            xx, yy = int(px0 + ex * sg * t_), int(py0 + ey * sg * t_)
            if not (0 <= xx < W and 0 <= yy < H) or par[yy, xx]: return t_
        return 400
    sg = -1 if dp(-1) <= dp(1) else 1
    hx, hy = cx + ex * sg * L / 2 + nx * esp / 2, cy + ey * sg * L / 2 + ny * esp / 2
    portas[portas.index((x0, y0, x1, y1, horiz))] = (hx, hy, nx, ny, -ex * sg, -ey * sg, L)
for a in arcosL:
    p0, p1, p2, p3, c = [np.array(q) for q in a]
    if not zona[int(c[1]), int(c[0])]: continue
    L = float(np.hypot(*(p0 - c)))
    na = lambda q: par[max(int(q[1]) - 15, 0):int(q[1]) + 15, max(int(q[0]) - 15, 0):int(q[0]) + 15].sum()
    ab, fe = (p0, p3) if na(p0) < na(p3) else (p3, p0)
    nv = (ab - c) / L; ev = (fe - c) / L
    portas.append((c[0], c[1], nv[0], nv[1], ev[0], ev[1], L))
# sem porta sobreposta: duas portas com o mesmo vao (folhas perto uma da outra) -> fica uma
_unicas = []
for q in portas:
    mq = (q[0] + q[2] * q[6] / 2 + q[4] * q[6] / 2, q[1] + q[3] * q[6] / 2 + q[5] * q[6] / 2)
    if any(np.hypot(mq[0] - m2[0], mq[1] - m2[1]) < 0.6 * min(q[6], q2[6]) for q2, m2 in _unicas): continue
    _unicas.append((q, mq))
portas = [q for q, _ in _unicas]
for k, nm in amb.items():   # todo WC tem porta: se faltou (zonas do Legal), poe no vao da soleira, abrindo para dentro
    if not re.match(r'WC|PNE', nm): continue
    sala = ids == k; ys_, xs_ = np.nonzero(sala)
    if any(xs_.min() - 40 <= q[0] + q[2] * q[6] / 2 + q[4] * q[6] / 2 <= xs_.max() + 40 and ys_.min() - 40 <= q[1] + q[3] * q[6] / 2 + q[5] * q[6] / 2 <= ys_.max() + 40 for q in portas): continue
    viz = sol & cv2.dilate(sala.astype(np.uint8), np.ones((15, 15), np.uint8)).astype(bool)
    n_, l_, s_, _ = cv2.connectedComponentsWithStats(viz.astype(np.uint8), 8)
    if n_ < 2: print('  WC SEM PORTA E SEM VAO', nm); continue
    i_ = 1 + int(np.argmax(s_[1:, 4])); x, y, w, h, _a = s_[i_]
    hz = w >= h; Lv = (w if hz else h); L = Lv * 0.86
    cx, cy = x + w / 2, y + h / 2
    # normal para dentro do WC
    nx, ny = (0, 1) if hz else (1, 0)
    if not sala[int(np.clip(cy + ny * (h / 2 + 25), 0, H - 1)), int(np.clip(cx + nx * (w / 2 + 25), 0, W - 1))]: nx, ny = -nx, -ny
    esp = h if hz else w; best = None
    for sg in (-1, 1):
        ex, ey = (1, 0) if hz else (0, 1)
        hx_, hy_ = cx - sg * ex * L / 2 + nx * esp / 2, cy - sg * ey * L / 2 + ny * esp / 2
        sec = np.zeros((H, W), np.uint8); a0 = np.degrees(np.arctan2(ny, nx)); a1 = np.degrees(np.arctan2(sg * ey, sg * ex)); d = ((a1 - a0 + 180) % 360) - 180
        cv2.ellipse(sec, (int(hx_), int(hy_)), (int(L), int(L)), 0, a0, a0 + d, 1, -1)
        livre_ = (sec.astype(bool) & sala).sum()
        if best is None or livre_ > best[0]: best = (livre_, (hx_, hy_, nx, ny, sg * ex, sg * ey, L))
    portas.append(best[1]); print('  porta do WC posta no vao da soleira', nm)
if P == 'TER':   # porta do PNE: uma so, dobradica no batente direito, abre para fora (Legal)
    portas = [q for q in portas if not (2700 <= q[0] + q[2] * q[6] / 2 <= 2990 and 1990 <= q[1] + q[3] * q[6] / 2 <= 2420)]
    portas.append((2930.0, 2208.0, 0.0, 1.0, -1.0, 0.0, 188.0))
_g = np.zeros((H, W), np.uint8)
for hx, hy, nx, ny, ex, ey, L in portas:
    a0 = np.degrees(np.arctan2(ny, nx)); a1 = np.degrees(np.arctan2(ey, ex)); d = ((a1 - a0 + 180) % 360) - 180
    cv2.ellipse(_g, (int(round(hx)), int(round(hy))), (int(L), int(L)), 0, a0, a0 + d, 1, -1)   # setor de 90 graus do giro
giro = (_g > 0) & interno & ~wcs
PQ = np.zeros((H, W), np.uint8)
for hx, hy, nx, ny, ex, ey, L in portas:
    q = np.array([[hx, hy], [hx + nx * L, hy + ny * L], [hx + nx * L + ex * L, hy + ny * L + ey * L], [hx + ex * L, hy + ey * L]], np.int32)
    cv2.fillPoly(PQ, [q], 1)
PQ = PQ > 0                                    # vao da porta: nenhum movel/bancada passa da soleira
# loucas (executivo fora das zonas; Legal->executivo pela caixa do WC dentro das zonas)
T = np.array(json.load(open(DZ + P + '_reg.json'))['exec_para_lanc'], np.float32)
ins = json.load(open(DZ + P + '_inserts.json', encoding='utf8'))
def cxl(c):
    p0 = T @ np.array([c[0], c[1], 1.0]); p1 = T @ np.array([c[2], c[3], 1.0]); return (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2
def sprite(x0, y0, x1, y1, tol=10):
    sp = LK[y0:y1, x0:x1].astype(np.float32); f0 = np.median(np.concatenate([sp[0], sp[-1], sp[:, 0], sp[:, -1]]), axis=0)
    a = np.clip(cv2.dilate(cv2.GaussianBlur((np.abs(sp - f0).max(axis=2) > tol).astype(np.float32), (0, 0), 1.2), np.ones((3, 3), np.uint8)) * 1.2, 0, 1)
    return sp.astype(np.uint8), a
VASO = sprite(5076, 2017, 5168, 2173); LAV = sprite(4789, 2038, 4963, 2174); _lf = LAV[0].astype(np.int16); _lu = _lf.mean(axis=2)
_wd = (_lf[..., 0] - _lf[..., 2] > 20) & (_lu > 70) & (_lu < 205)
LAV = (LAV[0], ((_wd.mean(axis=0) < 0.5)[None, :] & (_wd.mean(axis=1) < 0.5)[:, None]).astype(np.float32))   # bancada inteira, sem a madeira da borda do recorte
DUCHA = sprite(5282, 2084, 5368, 2160)   # chuveiro do lancamento: misturador + ducha, base na parede (embaixo)
DUCHA_A = DUCHA[1]
from scipy import ndimage as _nd
_va = _nd.binary_fill_holes(cv2.morphologyEx((VASO[1] > 0.3).astype(np.uint8), cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8)) > 0)

pecas = []
for e in ins:
    mt = re.search(r'Bacia|Lavat|Ducha|Assento', e['nome'])
    if mt: x, y = cxl(e['caixa']); pecas.append((mt.group(0), x, y, e['rot'], int(idsE[int(y), int(x)])))
def caixa(m): ys, xs = np.nonzero(m); return xs.min(), ys.min(), xs.max(), ys.max()
def encosta(al_, bx_, by_, sala, maxd=60):
    """encosta o objeto na parede preta mais proxima e depois na parede lateral (eixo perpendicular), sem giro/vao de porta"""
    hh_, ww_ = al_.shape; ruim = (giro | PQ) & sala
    def anda(bx_, by_, dirs):
        best = None
        for dx_, dy_ in dirs:
            for t_ in range(0, maxd + 1):
                xx_, yy_ = bx_ + dx_ * t_, by_ + dy_ * t_
                if xx_ < 0 or yy_ < 0 or xx_ + ww_ > W or yy_ + hh_ > H: break
                if (al_ & par[yy_:yy_ + hh_, xx_:xx_ + ww_]).sum() > 3:
                    if t_ > 1 and (best is None or t_ < best[0]):
                        nx_, ny_ = bx_ + dx_ * (t_ - 1), by_ + dy_ * (t_ - 1)
                        if not (al_ & ruim[ny_:ny_ + hh_, nx_:nx_ + ww_]).any(): best = (t_, dx_, dy_, nx_, ny_)
                    break
        return best
    b1 = anda(bx_, by_, ((0, -1), (0, 1), (-1, 0), (1, 0)))
    if b1 is None: return bx_, by_
    bx_, by_ = b1[3], b1[4]
    b2 = anda(bx_, by_, ((-1, 0), (1, 0)) if b1[2] else ((0, -1), (0, 1)))
    if b2 is not None and b2[0] <= 40: bx_, by_ = b2[3], b2[4]
    return bx_, by_
def assenta(al_, X, Y, sala, raio, livre_extra=None):
    """posicao (x0,y0) mais perto de (X,Y) com o objeto 100% dentro da sala, fora da parede e do giro"""
    h, w = al_.shape
    sala_t = cv2.dilate(sala.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool)      # tolera encostar na face da parede
    nucleo = cv2.erode(par.astype(np.uint8), np.ones((7, 7), np.uint8)).astype(bool)
    proib = ~sala_t | nucleo | (giro & ~sala_t) | (giro & ~cv2.erode(sala.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool) & False)
    proib = proib | (giro & sala) | (PQ & sala & ~wcs)
    best = None
    for dy in range(-raio, raio + 1, 3):
        for dx in range(-raio, raio + 1, 3):
            x0, y0 = int(X - w / 2 + dx), int(Y - h / 2 + dy)
            if x0 < 0 or y0 < 0 or x0 + w > W or y0 + h > H: continue
            inv = (al_ & proib[y0:y0 + h, x0:x0 + w]).sum()
            c = inv * 50 + abs(dx) + abs(dy)
            inv = inv if inv > 0.03 * al_.sum() else 0
            if best is None or c < best[0]: best = (c, x0, y0, inv)
    return best
n_l = 0
for k, nm in amb.items():
    if not re.match(r'WC|PNE', nm): continue
    if P == 'TER' and nm == 'PNE':
        sala = ids == k
        _vf = (VASO[0], cv2.GaussianBlur(_va.astype(np.float32), (0, 0), 1.0))
        for sp_, k90, cx_, cy_ in ((_vf, 2, 2810, 1792), (LAV, 1, 3233, 1885)):
            al2 = np.rot90(sp_[1], k90) > 0.5; hh_, ww_ = al2.shape
            x0_, y0_ = (int(cx_ - ww_ / 2), int(cy_) + 2) if sp_ is _vf else (int(cx_ - ww_), int(cy_ - hh_ / 2))
            cola(sp_[0], sp_[1], x0_, y0_, k90); n_l += 1
        continue
    sala = ids == k
    # nucleo do WC: maior pedaco depois de abrir 15 px (frestas herdadas do vizinho nao contam para o box)
    _n2, _l2, _s2, _ = cv2.connectedComponentsWithStats(cv2.morphologyEx(sala.astype(np.uint8), cv2.MORPH_OPEN, np.ones((15, 15), np.uint8)), 4)
    if _n2 > 1: sala = _l2 == 1 + int(np.argmax(_s2[1:, 4]))
    xa, ya, xb, yb = caixa(sala)
    ov = np.bincount(idsE[sala].ravel(), minlength=idsE.max() + 1); ov[0] = 0; k0 = int(ov.argmax())
    if ov[k0] < 0.3 * sala.sum(): print('  WC sem correspondente no executivo', nm, xa, ya, xb, yb); continue
    na_zona = sala[zona].sum() > 0.5 * sala.sum()
    a_ = caixa(idsE == k0)
    sx = (xb - xa) / max(a_[2] - a_[0], 1); sy = (yb - ya) / max(a_[3] - a_[1], 1)
    f = (lambda x, y: (xa + (x - a_[0]) * sx, ya + (y - a_[1]) * sy)) if na_zona else (lambda x, y: (x, y))
    meus = [p for p in pecas if p[4] == k0]; ass = [p for p in meus if p[0] == 'Assento']
    if not meus: print('  WC sem pecas', nm, xa, ya, xb, yb, 'exec', nomeE.get(k0))
    vasos = [f(p[1], p[2]) for p in meus if p[0] == 'Bacia']
    # box: vidro em linha fina separando a area do chuveiro (canto mais longe da porta e do vaso), como no lancamento
    sol_ = sol & cv2.dilate(sala.astype(np.uint8), np.ones((25, 25), np.uint8)).astype(bool)
    dy_, dx_ = np.nonzero(sol_); porta = (dx_.mean(), dy_.mean()) if len(dx_) else ((xa + xb) / 2, (ya + yb) / 2)
    # box igual ao lancamento: UMA linha de vidro reta atravessando o WC, a ~0,85 m da parede do fundo do chuveiro
    best = None
    for lado_ in ('t', 'b', 'l', 'r'):
        prof = (yb - ya) if lado_ in 'lr' else (xb - xa)        # largura do WC no sentido da linha
        comp = (xb - xa) if lado_ in 'lr' else (yb - ya)        # comprimento no sentido do chuveiro
        bw = int(min(0.85 / M_PX, comp * 0.45))
        if bw < 120: continue
        tira = np.zeros((H, W), bool)
        if lado_ == 't': tira[ya:ya + bw, xa:xb] = True
        elif lado_ == 'b': tira[yb - bw:yb, xa:xb] = True
        elif lado_ == 'l': tira[ya:yb, xa:xa + bw] = True
        else: tira[ya:yb, xb - bw:xb] = True
        tira &= sala
        if tira.sum() < 0.45 * bw * prof: continue
        if (tira & (_g > 0)).sum() > 0.05 * tira.sum(): continue          # o box nunca fica no giro da porta
        ty, tx = np.nonzero(tira); cc = (tx.mean(), ty.mean())
        dmin = min([np.hypot(cc[0] - porta[0], cc[1] - porta[1])] + [np.hypot(cc[0] - v[0], cc[1] - v[1]) for v in (vasos if not na_zona else [])])
        if best is None or dmin > best[0]: best = (dmin, lado_, bw, tira)
    box = np.zeros((H, W), bool); bx = by = bw = 0
    if best is not None:
        _, lado_, bw, box = best
        # a linha de vidro: borda interna da tira, de parede a parede
        ln = np.zeros((H, W), bool)
        if lado_ == 't': ln[ya + bw - 3:ya + bw + 3, xa:xb] = True
        elif lado_ == 'b': ln[yb - bw - 3:yb - bw + 3, xa:xb] = True
        elif lado_ == 'l': ln[ya:yb, xa + bw - 3:xa + bw + 3] = True
        else: ln[ya:yb, xb - bw - 3:xb - bw + 3] = True
        ln &= sala & ~par
        img[ln] = (100, 126, 142)
        ty, tx = np.nonzero(box); bx, by = tx.min(), ty.min(); bwx, bwy = tx.max() - bx, ty.max() - by
        # chuveiro na parede do fundo do box, no meio
        dh, dw = DUCHA[1].shape
        # chuveiro do lancamento (misturador + ducha) inteiro, com a base encostada na parede do fundo do box
        # como no lancamento: chuveiro na mesma parede do vaso (ao lado dele, do outro lado do vidro)
        vy = np.mean([v[1] for v in vasos]) if vasos else (ya + yb) / 2; vx = np.mean([v[0] for v in vasos]) if vasos else (xa + xb) / 2
        if lado_ in 'lr': pw_ = 'b' if abs(vy - yb) < abs(vy - ya) else 't'
        else: pw_ = 'r' if abs(vx - xb) < abs(vx - xa) else 'l'
        kd = {'b': 0, 't': 2, 'l': 3, 'r': 1}[pw_]
        dsp = (DUCHA[0], DUCHA_A); hh2, ww2 = np.rot90(DUCHA_A, kd).shape
        if pw_ == 'b': q = (bx + bwx / 2 - ww2 / 2, by + bwy - hh2)
        elif pw_ == 't': q = (bx + bwx / 2 - ww2 / 2, by)
        elif pw_ == 'l': q = (bx, by + bwy / 2 - hh2 / 2)
        else: q = (bx + bwx - ww2, by + bwy / 2 - hh2 / 2)
        cola(dsp[0], dsp[1], q[0], q[1], k90=kd, sombra=False)
    livre = sala & ~box
    for t, x, y, rot, _ in meus:
        X, Y = f(x, y)
        if t == 'Bacia':
            cs = min(ass, key=lambda s_: np.hypot(s_[1] - x, s_[2] - y)) if ass else None
            if cs is None: continue
            d = np.array([x - cs[1], y - cs[2]]); k90 = (0 if d[1] > 0 else 2) if abs(d[1]) >= abs(d[0]) else (1 if d[0] > 0 else 3); s_, a2 = VASO
        elif t == 'Lavat':
            if not sala[int(Y), int(X)] and not na_zona: continue
            k90 = {180: 0, 0: 2, 90: 1, 270: 3}.get(int(round(rot)) % 360, 0); s_, a2 = LAV
        else: continue
        al_ = np.rot90(a2, k90) > 0.5
        b = assenta(al_, X, Y, livre & ~(_g > 0), 130 if na_zona else 40)      # vaso/cuba nunca no giro da porta
        if b is None or b[3] > 0: continue
        cola(s_, a2, b[1], b[2], k90, clip=sala.astype(np.float32)); n_l += 1
# moveis dos alojamentos (lancamento): posicao do lancamento fora das zonas; ajustados dentro das zonas
O = json.load(open(P + '_objetos.json', encoding='utf8')); S = np.load(P + '_objetos.npz')
n_o = n_x = 0
for o in O:
    if not o['ambiente'].startswith('ALOJ') or o['px'] < 1500: continue
    cx_, cy_ = o['x'] + o['w'] / 2, o['y'] + o['h'] / 2
    kk = int(ids[int(cy_), int(cx_)])
    if not amb.get(kk, '').startswith('ALOJ'):
        # objeto caiu fora de alojamento (zona mudou): procura o alojamento mais proximo do mesmo executivo
        continue
    sp = S[o['id']].copy()
    # tira filetes de 1-4 px do recorte (viravam linha de sombra atravessando o ambiente)
    _ab = cv2.morphologyEx((sp[..., 3] > 128).astype(np.uint8), cv2.MORPH_OPEN, np.ones((7, 7), np.uint8))
    sp[..., 3] = (sp[..., 3] * cv2.dilate(_ab, np.ones((3, 3), np.uint8))).astype(np.uint8)
    # tira do recorte o que nao e movel: folha de porta azul-acinzentada, puxador, arco e filete de parede do lancamento
    _c = sp[..., :3].astype(np.int16); _lm = _c.mean(axis=2)
    _azul = (_c[..., 2] - _c[..., 0] > 8) & (_lm > 50) & (_lm < 140) & (sp[..., 3] > 128)
    _n3, _l3, _s3, _ = cv2.connectedComponentsWithStats(_azul.astype(np.uint8), 8)
    _rm = np.zeros(_azul.shape, bool)
    for _i in range(1, _n3):
        if min(_s3[_i, 2], _s3[_i, 3]) < 18 and max(_s3[_i, 2], _s3[_i, 3]) > 80: _rm |= _l3 == _i
    if _rm.any():
        _rm = cv2.dilate(_rm.astype(np.uint8), np.ones((31, 31), np.uint8)).astype(bool) & (_azul | (_lm < 70))
        sp[..., 3][_rm] = 0
    _pb = ((_lm < 40) | (_lm > 240)) & (sp[..., 3] > 128)              # filete preto/branco de parede no recorte
    _n3, _l3, _s3, _ = cv2.connectedComponentsWithStats(_pb.astype(np.uint8), 8)
    for _i in range(1, _n3):
        if min(_s3[_i, 2], _s3[_i, 3]) < 14 and max(_s3[_i, 2], _s3[_i, 3]) > 120: sp[..., 3][_l3 == _i] = 0
    _bd = np.zeros(_lm.shape, bool); _bd[:5] = _bd[-5:] = True; _bd[:, :5] = _bd[:, -5:] = True
    _sat = _c.max(axis=2) - _c.min(axis=2)
    if min(o['w'], o['h']) > 80: sp[..., 3][_bd & (_sat < 12) & ((_lm > 238) | (_lm < 32))] = 0   # filete de parede do lancamento na borda do recorte
    _lin = ((_lm < 80) | (_lm > 225)) & (_sat < 22) & (sp[..., 3] > 128)
    _n7, _l7, _s7, _ = cv2.connectedComponentsWithStats(_lin.astype(np.uint8), 8); _hh, _ww = _lin.shape
    for _i in range(1, _n7):
        x_, y_, w_, h_, a_ = _s7[_i]
        perto = (y_ < 30 or y_ + h_ > _hh - 30) if w_ > h_ else (x_ < 30 or x_ + w_ > _ww - 30)
        if perto and min(w_, h_) <= 10 and max(w_, h_) > 0.5 * (_ww if w_ > h_ else _hh):
            sp[..., 3][cv2.dilate((_l7 == _i).astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)] = 0   # filete de parede do lancamento
    al_ = sp[..., 3] > 128; sala = ids == kk
    if al_.sum() < 800: continue                                     # sobrou so folha/arco: nao era movel
    b = assenta(al_, cx_, cy_, sala, 120 if zona[int(cy_), int(cx_)] else 30)
    if b is None or b[3] > 0:
        n_x += 1
        if b is not None:
            x0, y0 = b[1], b[2]; hh_, ww_ = al_.shape
            sala_t = cv2.dilate(sala.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool)
            print('  descartado', o['id'], amb[kk], 'fora', int((al_ & ~sala_t[y0:y0+hh_, x0:x0+ww_]).sum()), 'giro', int((al_ & (giro & sala)[y0:y0+hh_, x0:x0+ww_]).sum()), 'area', int(al_.sum()))
        continue
    bx_, by_ = b[1], b[2]; hh_, ww_ = al_.shape
    bx_, by_ = encosta(al_, bx_, by_, sala, 150 if zona[int(cy_), int(cx_)] else 60)
    cola(sp[..., :3], sp[..., 3] / 255.0, bx_, by_, clip=sala.astype(np.float32)); n_o += 1
# bancadas de lavatorio fora do WC (no alojamento, junto da porta do WC): na posicao do executivo, rente a parede
for t, x, y, rot, k0 in pecas:
    if t != 'Lavat' or zona[int(y), int(x)]: continue
    kk = int(ids[int(y), int(x)])
    if not amb.get(kk, '').startswith('ALOJ'): continue
    # se ja tem bancada desenhada ali (objeto do lancamento), fica a do lancamento
    _r = img[max(int(y) - 40, 0):int(y) + 40, max(int(x) - 40, 0):int(x) + 40].astype(np.int16)
    _bc = (np.abs(_r[..., 0] - _r[..., 2]) < 14) & (_r.mean(axis=2) < 125) & (_r.mean(axis=2) > 40)
    _sl = (ids == kk)[max(int(y) - 40, 0):int(y) + 40, max(int(x) - 40, 0):int(x) + 40]
    if _bc.mean() > 0.3 or ((_r.mean(axis=2) > 225) & _sl).mean() > 0.12: continue   # ja tem bancada ou cuba ali (no alojamento)
    k90 = {180: 0, 0: 2, 90: 1, 270: 3}.get(int(round(rot)) % 360, 0); s_, a2 = LAV
    al_ = np.rot90(a2, k90) > 0.5; sala = ids == kk
    b = assenta(al_, x, y, sala, 60)
    if b is None or b[3] > 0: print('  lavatorio fora do WC nao coube', amb[kk]); continue
    # encosta na parede de tras (lado oposto a cuba): anda ate tocar a parede
    bx_, by_ = encosta(al_, b[1], b[2], sala)
    cola(s_, a2, bx_, by_, k90, clip=sala.astype(np.float32)); n_l += 1
if P == 'TER':
    adm = np.zeros((H, W), bool); adm[1120:1700, 2235:3200] = True; adm &= comum
    if adm.any():
        def sombra_ret(x0, y0, x1, y1, r=8):
            m = np.zeros((H, W), np.float32); cv2.rectangle(m, (x0 + 8, y0 + 8), (x1 + 8, y1 + 8), 1, -1)
            m = cv2.GaussianBlur(m, (0, 0), 7) * 0.35; img[:] = (img * (1 - m[..., None])).astype(np.uint8)
        # mesa de trabalho 0,76 x 1,53 m (Legal), tampo cinza como as bancadas do lancamento
        sombra_ret(2360, 1130, 2550, 1510); cv2.rectangle(img, (2360, 1130), (2550, 1510), (132, 128, 124), -1)
        cv2.rectangle(img, (2360, 1130), (2550, 1510), (96, 92, 88), 3)
        cv2.rectangle(img, (2400, 1250), (2490, 1320), (60, 62, 68), -1)            # notebook
        cv2.circle(img, (2300, 1320), 40, (55, 57, 64), -1); cv2.circle(img, (2300, 1320), 40, (35, 36, 42), 3)   # cadeira
        for (cx_, cy_) in ((2650, 1230), (2650, 1420)):                              # poltronas de atendimento
            sombra_ret(cx_ - 60, cy_ - 60, cx_ + 60, cy_ + 60)
            cv2.rectangle(img, (cx_ - 60, cy_ - 60), (cx_ + 60, cy_ + 60), (98, 108, 132), -1)
            cv2.rectangle(img, (cx_ + 30, cy_ - 60), (cx_ + 60, cy_ + 60), (74, 82, 104), -1)
            cv2.rectangle(img, (cx_ - 60, cy_ - 60), (cx_ + 60, cy_ + 60), (60, 66, 86), 3)
        # guarda-volumes individuais (bancada com portas a cada 30 cm)
        gv = np.zeros((H, W), bool); gv[1575:1680, 2245:3185] = True; gv &= comum
        img[gv] = (150, 132, 112)
        for xg in range(2245, 3185, 75): cv2.line(img, (xg, 1578), (xg, 1677), (110, 96, 82), 2)
        cv2.rectangle(img, (2245, 1575), (3185, 1680), (90, 80, 70), 3)
# ---- paredes, esquadrias e portas no padrao do lancamento -----------------------------------------------------------
# soleira rente a porta: so no vao da folha (largura do executivo); o que passar do perimetro da porta vira parede
_ns, _ls, _ss, _ = cv2.connectedComponentsWithStats(sol.astype(np.uint8), 8)
for hx, hy, nx, ny, ex, ey, L in portas:
    q = np.array([[hx - nx * 3, hy - ny * 3], [hx + ex * L - nx * 3, hy + ey * L - ny * 3], [hx + ex * L - nx * 90, hy + ey * L - ny * 90], [hx - nx * 90, hy - ny * 90]], np.int32)
    rq = np.zeros((H, W), np.uint8); cv2.fillPoly(rq, [q], 1); rq = rq > 0
    ii = np.unique(_ls[rq & sol]); ii = ii[ii > 0]
    if not len(ii): continue
    comp = np.isin(_ls, ii)
    xs_, ys_ = np.nonzero(comp)[1], np.nonzero(comp)[0]
    if comp.sum() > 4 * rq.sum(): continue                       # soleira gigante (erro de leitura): nao mexe
    extra = comp & ~cv2.dilate(rq.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    par |= extra; sol &= ~extra; vid &= ~extra
if P == 'TER':
    _n4, _l4, _s4, _ = cv2.connectedComponentsWithStats(par.astype(np.uint8), 8)
    _int = cv2.dilate((ids > 0).astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool)
    _ext = np.zeros((H, W), bool)
    for _i in range(1, _n4):
        _m = _l4 == _i
        if not (_m & _int).any(): _ext |= _m
    par &= ~_ext; img[_ext] = PX[_ext]; muro |= _ext
    # acesso como no lancamento: so o muro de divisa do lote (trechos longos); pedacos curtos/duplicados viram piso
    _n5, _l5, _s5, _ = cv2.connectedComponentsWithStats(muro.astype(np.uint8), 8)
    for _i in range(1, _n5):
        if max(_s5[_i, 2], _s5[_i, 3]) < 1500:
            _m = _l5 == _i; muro[_m] = False
            _ar = cv2.dilate(_m.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool) & ~_m
            _src = GR if gram[_ar].mean() > 0.5 else PX
            img[_m] = _src[_m]; alfa[_m] = 255
p8 = par.astype(np.uint8)
e2 = cv2.erode(p8, np.ones((7, 7), np.uint8)) > 0; e6 = cv2.erode(p8, np.ones((21, 21), np.uint8)) > 0   # perfil do lancamento: contorno 3 px, branco 7 px, nucleo preto
img[par] = (12, 12, 13); img[e2 & ~e6] = (244, 244, 244); img[e6] = (12, 12, 13); alfa[par] = 255
# area externa no padrao do lancamento: muro de divisa = faixa de concreto clara com contorno fino;
# gradil = barra azul-acinzentada fina com contorno, sem linhas soltas no jardim
if P == 'TER' and muro.any():
    grad = grad | muro; muro = np.zeros((H, W), bool)          # acesso: muro e gradil viram um gradil so, como no lancamento
    grad = cv2.morphologyEx(grad.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((25, 25), np.uint8)) > 0
if muro.any():
    img[muro] = (196, 196, 192)
    _mb = muro & ~cv2.erode(muro.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool); img[_mb] = (120, 120, 118); alfa[muro] = 255
if grad.any():
    _n, _l, _s, _ = cv2.connectedComponentsWithStats(grad.astype(np.uint8), 8)
    _gr = cv2.dilate(gram.astype(np.uint8), np.ones((25, 25), np.uint8)).astype(bool) if P == 'TER' else np.zeros((H, W), bool)
    for _i in range(1, _n):
        _m = _l == _i; _an = cv2.dilate(_m.astype(np.uint8), np.ones((31, 31), np.uint8)).astype(bool) & ~_m
        if P == 'TER' and gram[_an].mean() > 0.55: grad[_m] = False      # linha solta no meio do jardim
    if P == 'TER': grad &= ~(cv2.blur(gram.astype(np.float32), (41, 41)) > 0.8)   # linha solta no meio do jardim
    try:
        from skimage.morphology import skeletonize; sk = skeletonize(grad)
    except Exception: sk = grad
    g2 = cv2.dilate(sk.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool)
    img[cv2.dilate(g2.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)] = (44, 54, 60); img[g2] = (88, 107, 119)
    alfa[g2] = 255
# soleiras/peitoris: faixa reta entre os dois batentes (ate na diagonal), granito recortado do proprio lancamento
GRAN0 = LK[2195:2225, 6150:6320]          # soleira do lancamento (terreo, ponta da circulacao), textura 2D
GRANT = tile(GRAN0, (H, W)); GRANV = tile(np.ascontiguousarray(np.rot90(GRAN0)), (H, W))
vao0 = (vid | sol) & ~par
n_, l_, s_, _ = cv2.connectedComponentsWithStats(vao0.astype(np.uint8), 8)
vao = np.zeros((H, W), bool)
for i_ in range(1, n_):
    x, y, w, h, a = s_[i_]
    if a < 30: continue
    if not (interno[max(y - 10, 0):y + h + 10, max(x - 10, 0):x + w + 10]).any():   # sem soleira/vidro solto na area externa
        if P == 'TER':
            _m = l_ == i_; _ar = cv2.dilate(_m.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool) & ~_m
            _src = GR if gram[_ar].mean() > 0.5 else PX
            img[_m] = _src[_m]; alfa[_m] = 255
        continue
    x0_, y0_, x1_, y1_ = max(x - 30, 0), max(y - 30, 0), min(x + w + 30, W), min(y + h + 30, H)
    m = l_[y0_:y1_, x0_:x1_] == i_
    jamb = par[y0_:y1_, x0_:x1_] & cv2.dilate(m.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    pts = np.column_stack(np.nonzero(jamb)[::-1]).astype(np.int32)
    faixa = m.copy()
    if len(pts) > 10:
        hull = np.zeros(m.shape, np.uint8); cv2.fillConvexPoly(hull, cv2.convexHull(pts), 1)
        hull = hull.astype(bool) & ~par[y0_:y1_, x0_:x1_]
        if 0.3 * m.sum() < hull.sum() < 1.6 * m.sum() + 2000: faixa = hull
    (_, _), (rw, rh), ang = cv2.minAreaRect(np.column_stack(np.nonzero(faixa)[::-1]).astype(np.float32))
    if rw < rh: ang += 90                                       # angulo do lado comprido
    ang = ((ang + 90) % 180) - 90
    sub = img[y0_:y1_, x0_:x1_]
    if abs(ang) < 8: tex = GRANT[y0_:y1_, x0_:x1_]
    elif abs(abs(ang) - 90) < 8: tex = GRANV[y0_:y1_, x0_:x1_]
    else:
        big = tile(GRAN0, (m.shape[0] * 2 + 60, m.shape[1] * 2 + 60))
        Mr = cv2.getRotationMatrix2D((big.shape[1] / 2, big.shape[0] / 2), -ang, 1.0)
        rot = cv2.warpAffine(big, Mr, (big.shape[1], big.shape[0]), flags=cv2.INTER_LINEAR)
        oy, ox = (big.shape[0] - m.shape[0]) // 2, (big.shape[1] - m.shape[1]) // 2
        tex = rot[oy:oy + m.shape[0], ox:ox + m.shape[1]]
    # o que sobrou da mancha antiga fora da faixa volta a ser piso do ambiente vizinho
    sub[faixa] = tex[faixa]
    vao[y0_:y1_, x0_:x1_] |= faixa
alfa[vao] = 255
# vidro: faixa azul-acinzentada com contorno escuro no eixo da esquadria
n_, l_, s_, _ = cv2.connectedComponentsWithStats(vid.astype(np.uint8), 8)
for i in range(1, n_):
    x, y, w, h, a = s_[i]
    if a < 40: continue
    if not (interno[max(y - 10, 0):y + h + 10, max(x - 10, 0):x + w + 10]).any(): continue   # vidro so em esquadria do predio
    if w >= h:
        yc = y + h // 2; cv2.rectangle(img, (x, yc - 4), (x + w, yc + 4), (88, 107, 119), -1); cv2.rectangle(img, (x, yc - 4), (x + w, yc + 4), (44, 54, 60), 1)
    else:
        xc = x + w // 2; cv2.rectangle(img, (xc - 4, y), (xc + 4, y + h), (88, 107, 119), -1); cv2.rectangle(img, (xc - 4, y), (xc + 4, y + h), (44, 54, 60), 1)
# porta no padrao do lancamento: folha azul-acinzentada com contorno preto, puxador em "U" na ponta, arco fino
def P_(a, b, t, u=0.0):   # ponto na folha: t ao longo da folha (0 = dobradica), u para o lado
    return (int(round(a[0] + t * b[0] + u * b[2])), int(round(a[1] + t * b[1] + u * b[3])))
for hx, hy, nx, ny, ex, ey, L in portas:
    if PONTA[0] - 40 <= hx <= PONTA[2] and PONTA[1] <= hy <= PONTA[3]: continue      # trecho da ponta: porta do lancamento
    a0 = np.degrees(np.arctan2(ny, nx)); a1 = np.degrees(np.arctan2(ey, ex)); d = ((a1 - a0 + 180) % 360) - 180
    cv2.ellipse(img, (int(round(hx)), int(round(hy))), (int(L), int(L)), 0, a0, a0 + d, (24, 24, 26), 2, cv2.LINE_AA)
    # folha com 9 px (~3,5 cm) encostada do lado do batente (lado oposto ao arco)
    base = (hx - ex * 5, hy - ey * 5); v = (nx, ny, ex, ey)
    q = np.array([P_(base, v, 0, -4.5), P_(base, v, L, -4.5), P_(base, v, L, 4.5), P_(base, v, 0, 4.5)], np.int32)
    cv2.fillPoly(img, [q], (92, 96, 116)); cv2.polylines(img, [q], True, (22, 22, 26), 2, cv2.LINE_AA)
    # puxador em U dos dois lados da folha, perto da ponta
    for sgn in (-1, 1):
        u = [P_(base, v, L * 0.80, sgn * 13), P_(base, v, L * 0.92, sgn * 13), P_(base, v, L * 0.92, sgn * 4.5)]
        cv2.polylines(img, [np.array(u, np.int32)], False, (22, 22, 26), 6, cv2.LINE_AA)
        cv2.polylines(img, [np.array(u, np.int32)], False, (92, 96, 116), 2, cv2.LINE_AA)
if False:   # porta do elevador vem do lancamento (fora das zonas): 0,80 m no meio da face voltada para a circulacao, na espessura da parede
    ys_, xs_ = np.nonzero(elev); cxe = int(xs_.mean()); yb = ys_.max() + 1
    t_ = 0
    while yb + t_ < H and par[yb + t_, cxe]: t_ += 1
    x0, x1, y0, y1 = cxe - 100, cxe + 100, yb, yb + max(t_, 30)
    img[y0:y1, x0:x1] = GRANT[y0:y1, x0:x1]; alfa[y0:y1, x0:x1] = 255
    cv2.rectangle(img, (x0, y0), (x1 - 1, y1 - 1), (40, 42, 48), 2)
    xm = (x0 + x1) // 2; yq = (y0 + y1) // 2
    for a_, b_, yy in ((x0 + 4, xm + 6, yq - 13), (xm - 6, x1 - 4, yq + 1)):     # duas folhas de inox de correr
        cv2.rectangle(img, (a_, yy), (b_, yy + 12), (176, 180, 186), -1); cv2.rectangle(img, (a_, yy), (b_, yy + 12), (40, 42, 48), 2)
# ponta da circulacao (portas em diagonal): o executivo R10 = lancamento neste trecho (mesma geometria); reproduz a
# representacao do lancamento tal qual (paredes, soleiras, portas, bancadas), mantendo o piso da circulacao desenhado aqui
x0, y0, x1, y1 = PONTA
_L = LA[y0:y1, x0:x1, :3].astype(np.int16); _lm = _L.mean(axis=2); _st = _L.max(axis=2) - _L.min(axis=2)
_circ = np.isin(ids[y0:y1, x0:x1], [k for k, v in amb.items() if v == 'CIRCULACAO'])
_m = LA[y0:y1, x0:x1, 3] > 0                 # trecho inteiro do lancamento (sem misturar soleira/parede do desenho por baixo)
_w = np.ones(_m.shape, np.float32); _e = 12
for i_ in range(_e):
    f_ = (i_ + 1) / (_e + 1); _w[i_, :] = np.minimum(_w[i_, :], f_); _w[-1 - i_, :] = np.minimum(_w[-1 - i_, :], f_); _w[:, i_] = np.minimum(_w[:, i_], f_); _w[:, -1 - i_] = np.minimum(_w[:, -1 - i_], f_)
_a = (_m * _w)[..., None]
img[y0:y1, x0:x1] = (LA[y0:y1, x0:x1, :3] * _a + img[y0:y1, x0:x1] * (1 - _a)).astype(np.uint8)
# fora das zonas que mudaram no projeto o executivo R10 = lancamento (paredes, portas, soleiras, loucas, box, chuveiro):
# usa a representacao do lancamento tal qual, sem os rotulos; redesenho so nas zonas (Legal) e na area externa
_lr, _, _ = tira_rotulos.tira(LA[..., :3], LA[..., 3])
# a limpeza de rotulos so vale dentro das caixas azuis do lancamento; no resto fica o lancamento original
_lb = (np.abs(LA[..., :3].astype(np.int16) - np.array([57, 66, 94])).sum(axis=2) < 40) & (LA[..., 3] > 200)
_lbd = cv2.dilate(_lb.astype(np.uint8), np.ones((25, 25), np.uint8)).astype(bool)
_lr = np.where(_lbd[..., None], _lr[..., :3], LA[..., :3])
_pred = cv2.dilate(((A0['ids'] > 0) | A0['paredes'] | A0['vidro'] | A0['soleira']).astype(np.uint8), np.ones((31 if P != 'TER' else 5, 31 if P != 'TER' else 5), np.uint8)).astype(bool)
_pred &= LA[..., 3] > 0
ZDES = {'TER': [(2205, 1085, 3290, 2420)], '02P': [(1790, 395, 5025, 1392)]}[P]   # onde o desenho e meu (o resto = lancamento)
_zz = np.zeros((H, W), np.uint8)
for a_, b_, c_, d_ in ZDES: _zz[b_:d_, a_:c_] = 1
_zd = cv2.dilate(_zz, np.ones((5, 5), np.uint8))
_wz = cv2.GaussianBlur((1 - _zd).astype(np.float32), (0, 0), 2)
_a = (_pred * _wz)[..., None]
img[:] = (_lr[..., :3] * _a + img * (1 - _a)).astype(np.uint8); alfa[_pred] = 255
if P == 'TER':   # furos transparentes dentro do lote viram piso externo (eram os contornos brancos nos gradis)
    _gap = lote & (alfa < 250) & ~cv2.dilate(_pred.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    img[_gap & gram] = GR[_gap & gram]; img[_gap & ~gram] = PX[_gap & ~gram]; alfa[_gap] = 255
if P == 'TER':   # area externa: sem linha branca solta (vira o piso externo)
    _ee = ext & ~_pred & ~plat & ~esc_ac & ~grad & ~lixo
    _f = img.astype(np.int16); _wh = _ee & (_f.mean(axis=2) > 225) & ((_f.max(axis=2) - _f.min(axis=2)) < 14)
    _wh = cv2.dilate(_wh.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool) & _ee
    img[_wh & gram] = GR[_wh & gram]; img[_wh & ~gram] = PX[_wh & ~gram]
if P != 'TER':   # pavimento tipo: nada fora do contorno da fachada do lancamento (a janela ja e a parede)
    # acima da fachada (janela) nao vai nada: corta por coluna no primeiro pixel opaco do lancamento que nao e rotulo
    _okp = (LA[..., 3] > 250) & ~_lbd
    _top = np.where(_okp.any(axis=0), _okp.argmax(axis=0), H)
    _cx = np.arange(H)[:, None] < _top[None, :]
    img[_cx] = 255; alfa[_cx] = 0
    _fora = LA[..., 3] < 250; img[_fora] = LA[..., :3][_fora]; alfa[_fora] = LA[..., 3][_fora]   # borda/sombra da fachada = lancamento
Image.fromarray(np.dstack([img, alfa])).save(sai)
np.savez_compressed(P + '_hib_amb.npz', ids=ids); json.dump(dict(ambientes={str(k): dict(nome=v) for k, v in amb.items()}), open(P + '_hib_amb.json', 'w', encoding='utf8'), ensure_ascii=False)
print(P, 'ambientes', len(amb), 'loucas', n_l, 'moveis', n_o, 'descartados', n_x, 'portas', len(portas))
