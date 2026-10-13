"""Planta humanizada do PAVIMENTO a partir do DWG do projeto aprovado (Projeto Basico/Legal, export ArchiCAD/Revit).

Por que: o PDF legal so tem contornos; a imagem do lancamento nao tem o desenho novo. O DWG aprovado tem paredes,
escadas, portas, louças, marcenaria e mobiliario na geometria aprovada -> render direto, sem colagem e sem IA.
Nao precisa de Revit: o DWG vira DXF no AutoCAD (accoreconsole) ou no ODA File Converter (gratuito).

Estilo (paleta da humanizada de lancamento): piso porcelanato claro, paredes cinza escuro, camas brancas,
armarios/mesas em madeira, bancadas em granito escuro, louças brancas, sofas cinza, sombra suave.
Sem textos, cotas ou areas.

Uso: python gera_humanizada_dwg.py <pavimento.dxf> <saida.png> [--cm-px 0.6]
"""
import re, argparse, json, os
import ezdxf, numpy as np, cv2, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from ezdxf import bbox
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
from ezdxf.addons.drawing.config import Configuration, ColorPolicy, BackgroundPolicy, LineweightPolicy

ap = argparse.ArgumentParser()
ap.add_argument('dxf'); ap.add_argument('saida')
ap.add_argument('--cm-px', type=float, default=0.6)
ap.add_argument('--estilo', default='', help='pasta com texturas recortadas da humanizada de lancamento (porcelanato, deck, grama, agua, externo, cama)')
ap.add_argument('--cm-px-estilo', type=float, default=0.98, help='cm/px da humanizada de lancamento de onde vieram as texturas')
ap.add_argument('--pdf-aprovado', default='', help='PDF aprovado (Autodoc): le rotulos como PISCINA para posicionar elementos que o DWG nao tem')
ap.add_argument('--hidro-gardens', action='store_true', help='coloca hidromassagem nos gardens/terracos como no lancamento (ambientacao)')
ap.add_argument('--vazios', action='store_true', help='mezanino: area sem zona = vazio do pe-direito duplo, desenhado com X')
ap.add_argument('--hidro-lancamento', default='', help='humanizada de lancamento SEM texto do pavimento: banheiras na mesma posicao do lancamento')
ap.add_argument('--ocr-lancamento', default='', help='OCR do lancamento (ocr_windows.ps1) para levar posicoes do lancamento para a planta nova')
ap.add_argument('--transform', default='', help='transform.json do registro DWG x PDF (registra_pdf_imagem.py) para levar posicoes do PDF ao quadro')
a = ap.parse_args()

d = ezdxf.readfile(a.dxf); m = d.modelspace()
IGNORA = re.compile(r'^(Demolido|1-ANOT|2-INST(?!.*HIDR)|3-ANOT|4-ANOT|0-MOD M.SCARAS|0-MOD _ FORRO|0-MOD _ LAJES|0-MOD _ TERRENO|0_Caneta|Defpoints)', re.I)
# categoria por nome do bloco (ordem importa) -> (preenchimento BGR, contorno BGR)
CAT = [
    ('parede',    r'^Parede(?! Cortina)',                    None),
    ('lavat',     r'Balc.o Multi-Lavat',                     ((58, 58, 60), (30, 30, 30))),
    ('box',       r'Cabine de Chuveiro',                     ((236, 238, 240), (205, 205, 208))),
    ('ignorar2',  r'Kit Chuveiro|^Lavat.rio 27',             None),
    ('cortina',   r'^Parede Cortina|Janela|Esquadria|Porta-Janela', ((214, 200, 180), (150, 130, 110))),
    ('cama',      r'Cama',                                   ((242, 243, 245), (150, 150, 150))),
    ('armario',   r'Guarda-Roupa|Arm.rio Alto|Estante',     ((88, 140, 192), (50, 90, 130))),
    ('bancada',   r'Arm.rio Baixo|Bancada|Balc.o',          ((58, 58, 60), (30, 30, 30))),
    ('mesa',      r'Mesa',                                   ((96, 150, 200), (55, 95, 135))),
    ('sofa',      r'Sof.',                                   ((160, 160, 158), (100, 100, 100))),
    ('cadeira',   r'Cadeira|Poltrona|Puff|Espregui|Banqueta',                  ((232, 235, 238), (140, 140, 140))),
    ('loucas',    r'Vaso|Bacia|Cuba|Lavat|Chuveiro|Cabine|Pia|Tanque', ((252, 252, 252), (130, 130, 130))),
    ('cooktop',   r'Cooktop|Fog.o|Forno',                    ((35, 35, 35), (20, 20, 20))),
    ('tv',        r'^TV',                                    ((50, 50, 50), (30, 30, 30))),
    ('escada',    r'^Escada',                                ((205, 205, 205), (120, 120, 120))),
    ('guarda',    r'Guarda-?[Cc]orpo|Corrim',                ((175, 175, 175), (110, 110, 110))),
    ('porta',     r'^Porta(?!-Janela)',                      ((235, 235, 235), (140, 140, 140))),
    ('ignorar',   r'Ar Condicionado|Split|S.mbolo|Marcador|Malha|Viga|Laje|Pilar|Grelha', None),
]
# sem textos/etiquetas (P03, J07, numeros de degrau...) dentro dos blocos
zona_blocos = {e.dxf.name for e in m.query('INSERT') if 'ZONA' in e.dxf.layer.upper()}   # rotulos das zonas sao lidos depois
for blk in d.blocks:   # portas e marcadores do ArchiCAD fora: no lancamento a porta e so o vao na parede
    for e in list(blk):
        if e.dxftype() == 'INSERT' and re.search(r'Marcador|Portas Archicad|Janelas? Archicad.*Marc', e.dxf.layer + ' ' + e.dxf.name, re.I):
            blk.delete_entity(e)
for blk in d.blocks:
    if blk.name in zona_blocos: continue
    for e in list(blk):
        if e.dxftype() in ('TEXT', 'MTEXT', 'ATTDEF', 'DIMENSION'): blk.delete_entity(e)
for e in m.query('INSERT'):
    for at in list(e.attribs): e.delete_attrib(at.dxf.tag)
grupos = {c[0]: [] for c in CAT}; grupos['outros'] = []
for e in m:
    if IGNORA.match(e.dxf.layer): continue
    if e.dxftype() != 'INSERT':
        if e.dxftype() in ('LINE', 'LWPOLYLINE', 'ARC', 'CIRCLE', 'HATCH', 'POLYLINE', 'ELLIPSE', 'SPLINE'): grupos['outros'].append(e)
        continue
    nome = re.sub(r'\[\d+\]', '', e.dxf.name)
    if 'MARCENARIA' in e.dxf.layer.upper() and nome.startswith('Laje'):   # tampo com cadeiras = mesa de madeira (lancamento)
        grupos['mesa'].append(e); continue
    for k, rx, _ in CAT:
        if re.search(rx, nome): grupos[k].append(e); break
    else:
        lay = e.dxf.layer.upper()
        grupos['parede' if 'PAREDE' in lay else 'escada' if 'ESCADA' in lay else 'guarda' if 'GUARDA' in lay else
               'cortina' if 'FACHADA' in lay else 'outros'].append(e)

b = bbox.extents(grupos['parede']); pad = 800
X0, Y0, X1, Y1 = b.extmin.x - pad, b.extmin.y - pad, b.extmax.x + pad, b.extmax.y + pad
s = 1.0 / (a.cm_px * 10)  # px por mm
W, H = int((X1 - X0) * s), int((Y1 - Y0) * s)

SS = 2   # supersample
def render(ents, lw=0.18):
    """mascara (uint8 255 = tinta) das entidades, preto no branco, no quadro fixo."""
    W2, H2 = W * SS, H * SS
    fig = plt.figure(figsize=(W2 / 100, H2 / 100), dpi=100); ax = fig.add_axes([0, 0, 1, 1]); ax.set_axis_off()
    cfg = Configuration(color_policy=ColorPolicy.BLACK, background_policy=BackgroundPolicy.WHITE,
                        lineweight_policy=LineweightPolicy.ABSOLUTE, min_lineweight=lw * SS)
    fe = Frontend(RenderContext(d), MatplotlibBackend(ax), config=cfg)
    fe.draw_entities(ents)
    ax.set_xlim(X0, X1); ax.set_ylim(Y0, Y1); fig.set_size_inches(W2 / 100, H2 / 100); ax.set_position([0, 0, 1, 1])
    fig.canvas.draw(); img = np.asarray(fig.canvas.buffer_rgba())[:, :, :3]; plt.close(fig)
    tinta = 255 - cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    tinta = cv2.dilate(tinta, np.ones((SS, SS), np.uint8))
    return cv2.resize(tinta, (W, H), interpolation=cv2.INTER_AREA)

def preenche(lin):
    """silhueta: contornos externos preenchidos (cada bloco vira uma mancha solida)."""
    k = cv2.morphologyEx((lin > 25).astype(np.uint8), cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    cs, _ = cv2.findContours(k, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    out = np.zeros_like(k); cv2.drawContours(out, cs, -1, 1, -1); return out > 0

px = lambda cm: max(1, int(round(cm / a.cm_px)))
paredes = render(grupos['parede'], 0.25) > 100
# predio: maior mancha das paredes fechada (vaos de janela/porta ate ~3 m), com os furos preenchidos
fach = (render(grupos['cortina'] + grupos['guarda']) > 40) if (grupos['cortina'] or grupos['guarda']) else np.zeros((H, W), bool)
kf = px(700); env = cv2.copyMakeBorder((paredes | fach).astype(np.uint8), kf, kf, kf, kf, cv2.BORDER_CONSTANT, value=0)
env = cv2.morphologyEx(env, cv2.MORPH_CLOSE, np.ones((kf, kf), np.uint8))[kf:-kf, kf:-kf].copy()
cs, _ = cv2.findContours(env, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
predio = np.zeros((H, W), np.uint8); cv2.drawContours(predio, [max(cs, key=cv2.contourArea)], -1, 1, -1)
predio = predio > 0
print('predio frac', round(predio.mean(), 3))

# --- zonas do projeto aprovado (texto escrito em cada zona define o piso) ---------------------------------
from matplotlib.path import Path as MPath
def para_img(x, y): return (x - X0) * s, (Y1 - y) * s
def classe(txt):
    t = txt.upper()
    if 'GARDEN' in t or 'TERRA' in t or 'DECK' in t: return 'deck'
    if 'JARDIM' in t or 'FLOREIRA' in t or 'PAISAG' in t: return 'grama'
    if 'PISCINA' in t: return 'agua'
    if 'SACADA' in t or 'LAZER ABERTO' in t or 'COBERTA ABERTA' in t or 'VAGA' in t or 'IMPERME' in t: return 'externo'
    if re.search(r'T.CNICA|\bA\.T\.?|LIXO|MEDIDOR|DEP.SITO|SEGREGADOR', t): return 'cimentado'
    return 'porcelanato'
polys = [e for e in d.modelspace().query('LWPOLYLINE') if 'ZONA' in e.dxf.layer.upper() and len(e) >= 3]
rot = []
for e in d.modelspace().query('INSERT'):
    if 'ZONA' not in e.dxf.layer.upper(): continue
    ts = [t for t in e.virtual_entities() if t.dxftype() in ('MTEXT', 'TEXT')]
    if ts:
        txt = ' '.join((t.plain_text() if t.dxftype() == 'MTEXT' else t.dxf.text).replace('^', ' ') for t in ts)
        rot.append((txt, ts[0].dxf.insert.x, ts[0].dxf.insert.y))
zonas = []
for e in polys:
    pts = [(p[0], p[1]) for p in e.get_points('xy')]
    path = MPath(pts); dentro = [r for r in rot if path.contains_point((r[1], r[2]))]
    if not dentro: continue
    area = abs(sum(pts[k][0] * pts[k - 1][1] - pts[k - 1][0] * pts[k][1] for k in range(len(pts)))) / 2
    zonas.append(dict(texto=dentro[0][0], classe=classe(dentro[0][0]), area=area,
                      img=np.array([para_img(x, y) for x, y in pts], np.int32)))
zonas.sort(key=lambda z: -z['area'])   # grandes primeiro, pequenas (sacadas, gardens) por cima
print('zonas:', {c: sum(z['classe'] == c for z in zonas) for c in set(z['classe'] for z in zonas)})

# piscina e outros elementos que so o PDF aprovado escreve
extras = []
if a.pdf_aprovado and a.transform:
    import fitz
    T = json.load(open(a.transform, encoding='utf-8')); A = np.array(T['A_pdfpx_para_img'] + [[0, 0, 1]])
    pg = fitz.open(a.pdf_aprovado)[T['pagina'] - 1]
    for rotulo in ('PISCINA',):
        for r in pg.search_for(rotulo):
            z = 4; clip = fitz.Rect(r.x0 - 120, r.y0 - 120, r.x1 + 120, r.y1 + 220)
            pix = pg.get_pixmap(matrix=fitz.Matrix(z, z), clip=clip)
            g = cv2.cvtColor(np.frombuffer(pix.samples, np.uint8).reshape(pix.h, pix.w, pix.n)[:, :, :3], cv2.COLOR_RGB2GRAY)
            tinta = (g < 150).astype(np.uint8)
            semente = (int(((r.x0 + r.x1) / 2 - clip.x0) * z), int((r.y0 - 10 - clip.y0) * z))
            ff = tinta.copy(); msk = np.zeros((pix.h + 2, pix.w + 2), np.uint8)
            cv2.floodFill(ff, msk, semente, 2)
            reg = (ff == 2).astype(np.uint8)
            reg = cv2.morphologyEx(reg, cv2.MORPH_CLOSE, np.ones((25, 25), np.uint8))   # fecha o rotulo e o simbolo
            cs, _ = cv2.findContours(reg, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if not cs: continue
            c = max(cs, key=cv2.contourArea)[:, 0, :].astype(float)
            ptpdf = c / z + [clip.x0, clip.y0]
            pdfpx = (ptpdf - [T['clip_pt'][0], T['clip_pt'][1]]) * T['esc']
            im = (A @ np.c_[pdfpx, np.ones(len(pdfpx))].T).T[:, :2]
            # preferir o limite das paredes do DWG (a borda da piscina esta desenhada nele); o traco do PDF tem vaos
            cpt = np.array([[((r.x0 + r.x1) / 2 - T['clip_pt'][0]) * T['esc'], ((r.y0 + r.y1) / 2 - T['clip_pt'][1]) * T['esc'], 1]])
            sx, sy = (A @ cpt.T).T[0, :2].astype(int)
            barreira = cv2.dilate((paredes | fach).astype(np.uint8), np.ones((3, 3), np.uint8))
            if 0 <= sx < W and 0 <= sy < H and not barreira[sy, sx]:
                ff2 = barreira.copy(); m2 = np.zeros((H + 2, W + 2), np.uint8); cv2.floodFill(ff2, m2, (int(sx), int(sy)), 2)
                reg2 = ff2 == 2; area_m2 = reg2.sum() * (a.cm_px / 100) ** 2
                print('piscina pelas paredes do DWG:', round(area_m2, 1), 'm2')
                if 5 < area_m2 < 80:
                    cs2, _ = cv2.findContours(reg2.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
                    im = max(cs2, key=cv2.contourArea)[:, 0, :].astype(float)
            extras.append(dict(texto=rotulo, classe='agua', img=im.astype(np.int32)))
            print('extra do PDF aprovado:', rotulo, round(cv2.contourArea(c.astype(np.float32)) / z / z * (2.54 / 72 * 100) ** 2 / 1e4, 1), 'm2')

def textura(nome, cor):
    f_ = os.path.join(a.estilo, nome + '.png') if a.estilo else ''
    if f_ and os.path.exists(f_):
        t = cv2.imread(f_)
        f = a.cm_px_estilo / a.cm_px
        t = cv2.resize(t, (max(2, int(t.shape[1] * f)), max(2, int(t.shape[0] * f))), interpolation=cv2.INTER_CUBIC)
        t = np.vstack([np.hstack([t, t[:, ::-1]]), np.hstack([t[::-1], t[::-1, ::-1]])])   # espelhado: sem emenda
        return np.tile(t, (H // t.shape[0] + 1, W // t.shape[1] + 1, 1))[:H, :W]
    return np.full((H, W, 3), cor, np.uint8)
def piso_liso(nome, cor, modulo_cm, rejunte=0.93):
    f_ = os.path.join(a.estilo, nome + '.png') if a.estilo else ''
    if f_ and os.path.exists(f_):
        cor = np.median(cv2.imread(f_).reshape(-1, 3), axis=0)
    base = np.empty((H, W, 3), np.float32); base[:] = cor
    rn = cv2.GaussianBlur(np.random.default_rng(7).normal(0, 2.2, (H, W)).astype(np.float32), (0, 0), 3)
    base += rn[..., None]
    p_ = px(modulo_cm); g = np.zeros((H, W), bool); g[::p_, :] = True; g[:, ::p_] = True
    base[g] *= rejunte
    return np.clip(base, 0, 255).astype(np.uint8)
def textura_obj(nome):
    f_ = os.path.join(a.estilo, 'objetos', nome + '.png') if a.estilo else ''
    if not (f_ and os.path.exists(f_)): return None
    t = cv2.imread(f_); f = a.cm_px_estilo / a.cm_px
    t = cv2.resize(t, (max(2, int(t.shape[1] * f)), max(2, int(t.shape[0] * f))), interpolation=cv2.INTER_CUBIC)
    t = np.vstack([np.hstack([t, t[:, ::-1]]), np.hstack([t[::-1], t[::-1, ::-1]])])
    return np.tile(t, (H // t.shape[0] + 1, W // t.shape[1] + 1, 1))[:H, :W]
def textura_natural(nome, cor):
    f_ = os.path.join(a.estilo, nome + '.png') if a.estilo else ''
    if not (f_ and os.path.exists(f_)): return np.full((H, W, 3), cor, np.uint8)
    t = cv2.imread(f_); f = a.cm_px_estilo / a.cm_px
    t = cv2.resize(t, (max(2, int(t.shape[1] * f)), max(2, int(t.shape[0] * f))), interpolation=cv2.INTER_CUBIC)
    th, tw = t.shape[:2]; out = np.empty((H, W, 3), np.uint8)
    for r_, y in enumerate(range(0, H, th)):
        linha = np.tile(np.roll(t, (r_ * tw // 3) % tw, axis=1), (1, W // tw + 2, 1))[:, :W]
        out[y:y + th] = linha[:min(th, H - y)]
    return out
TEX = {k: textura(k, c) for k, c in [('porcelanato', (218, 220, 221)), ('deck', (90, 130, 170)), ('grama', (70, 120, 60)),
                                       ('agua', (190, 180, 150)), ('externo', (205, 207, 208))]}
TEX['grama'] = textura_natural('grama', (70, 120, 60))
def piso_pecas(pasta, periodo_px_lanc=117.5):
    import glob
    fs = sorted(glob.glob(os.path.join(pasta, '*.png')))
    if not fs: return None
    pcs = [cv2.imread(f) for f in fs]
    suav = [float(cv2.GaussianBlur(cv2.cvtColor(q, cv2.COLOR_BGR2GRAY).astype(np.float32), (0, 0), 12).std()) for q in pcs]
    pcs = [q for q, v in sorted(zip(pcs, suav), key=lambda t: t[1])][:3]   # as 3 mais uniformes
    def _alisa(q):   # tira o resto de sombra (variacao lenta), mantem veio e rejunte
        f_ = q.astype(np.float32); lz = cv2.GaussianBlur(f_, (0, 0), 9)
        return np.clip(f_ - lz + lz.reshape(-1, 3).mean(0), 0, 255).astype(np.uint8)
    pcs = [_alisa(q) for q in pcs]
    T = max(8, int(round(periodo_px_lanc * a.cm_px_estilo / a.cm_px)))
    pcs = [cv2.resize(q, (T, T), interpolation=cv2.INTER_AREA) for q in pcs]
    rg = np.random.default_rng(3); out = np.empty((H + T, W + T, 3), np.uint8)
    for yy in range(0, H + 1, T):
        for xx in range(0, W + 1, T):
            q = pcs[rg.integers(len(pcs))]
            if rg.random() < 0.5: q = q[:, ::-1]
            if rg.random() < 0.5: q = q[::-1]
            out[yy:yy + T, xx:xx + T] = q
    return out[:H, :W]
_pp = piso_pecas(os.path.join(a.estilo, 'porcelanato_pecas')) if a.estilo else None
TEX['porcelanato'] = _pp if _pp is not None else piso_liso('porcelanato', (218, 220, 221), 90)
TEX['externo'] = piso_liso('externo', (210, 212, 213), 60)
TEX['cimentado'] = piso_liso('', (196, 198, 199), 400, 1.0)

# --- composicao ---------------------------------------------------------------------------------------
img = np.full((H, W, 3), 255, np.uint8)
img[predio] = TEX['porcelanato'][predio]
zid = np.zeros((H, W), np.int32)
for k, z in enumerate(zonas + extras, 1):
    m_ = np.zeros((H, W), np.uint8); cv2.fillPoly(m_, [z['img']], 1); m_ = m_ > 0
    img[m_] = TEX[z['classe']][m_]
    if z['classe'] == 'deck': zid[m_] = k
    else: zid[m_] = 0
# muros entre unidades: divisa entre dois gardens/terracos diferentes (projeto aprovado: "MURO ENTRE UNID.")
muro = np.zeros((H, W), bool); kk = np.ones((px(6) * 2 + 1,) * 2, np.uint8)
for k in np.unique(zid[zid > 0]):
    mk = (zid == k).astype(np.uint8)
    viz = (cv2.dilate(mk, kk) > 0) & (zid > 0) & (zid != k)
    muro |= cv2.dilate(viz.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
muro &= ~paredes
rng = np.random.default_rng(1)
ruido = cv2.GaussianBlur(rng.normal(0, 3.0, (H, W)).astype(np.float32), (0, 0), 2)

sombra = np.zeros((H, W), np.float32)
camadas = []
for k, rx, cor in CAT:
    if cor is None or k == 'parede' or not grupos[k]: continue
    lin = render(grupos[k])
    if k in ('bancada', 'lavat', 'mesa', 'armario'):   # tampos: retangulo de cada contorno (bloco as vezes vem aberto)
        kk_ = cv2.morphologyEx((lin > 25).astype(np.uint8), cv2.MORPH_CLOSE, np.ones((px(6), px(6)), np.uint8))
        cs_, _ = cv2.findContours(kk_, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        sil = np.zeros((H, W), np.uint8)
        for c_ in cs_:
            if cv2.contourArea(cv2.convexHull(c_)) < px(15) ** 2: continue
            cv2.fillPoly(sil, [np.int32(cv2.boxPoints(cv2.minAreaRect(c_)))], 1)
        sil = sil > 0
    else:
        sil = preenche(lin) if k not in ('escada', 'guarda', 'porta', 'cortina', 'box') else (lin > 40)
    camadas.append((k, lin, sil, cor))
    if k in ('armario', 'bancada', 'mesa', 'cadeira', 'tv'):   # cama/sofa/loucas: o sprite do lancamento ja tem sombra
        sombra += sil.astype(np.float32)
sh = cv2.GaussianBlur(np.roll(np.roll(np.clip(sombra, 0, 1) + (paredes | muro).astype(np.float32), px(4), 0), px(4), 1), (0, 0), px(5))
img = (img.astype(np.float32) * (1 - 0.28 * np.clip(sh, 0, 1)[..., None])).astype(np.uint8)

# --- objetos do lancamento (sprites) na posicao e orientacao de cada bloco do DWG ---------------------------
OBJ = os.path.join(a.estilo, 'objetos') if a.estilo else ''
def carrega(n):
    for f_ in (os.path.join(OBJ, n + '.png'), os.path.join(a.estilo, n + '.png') if a.estilo else ''):
        if f_ and os.path.exists(f_):
            x_ = cv2.imread(f_, cv2.IMREAD_UNCHANGED)
            if x_.ndim == 3 and x_.shape[2] == 4:
                _alfa_png[id(x_[:, :, :3])] = None
                x3 = np.ascontiguousarray(x_[:, :, :3]); _alfa_fix[id(x3)] = (x_[:, :, 3] / 255.0).astype(np.float32); return x3
            return x_
    return None
_alfa_png = {}; _alfa_fix = {}
SPRITE = [  # (regex do bloco, sprite, orientacao, corpo (x0,x1,y0,y1), tamanho)
    (r'Cama', 'cama', 'detalhe_embaixo', (0.15, 0.845, 0.02, 0.945), 'dwg'),
    (r'Sof.', 'sofa', 'detalhe_embaixo', (0.0, 1.0, 0.0, 1.0), 'dwg'),
    (r'Poltrona', 'poltrona', 'detalhe_embaixo', (0.0, 1.0, 0.0, 1.0), 'dwg'),
    (r'Espregui', 'espreguicadeira', 'detalhe_embaixo', (0.0, 1.0, 0.0, 1.0), 'dwg'),
    (r'Mesa.*Redonda|Mesa de Jantar Redonda', 'mesa_redonda', 'livre', (0.0, 1.0, 0.0, 1.0), 'dwg'),
    (r'^Vaso Sanit.rio(?! Acess)', 'vaso_sanitario', 'detalhe_embaixo', (0.0, 1.0, 0.0, 1.0), 'lancamento'),
    (r'Guarda-Roupa', 'armario_cabides', 'detalhe_embaixo', (0.0, 1.0, 0.0, 1.0), 'lancamento'),   # arara: medida do lancamento
    (r'Balc.o Multi-Lavat', 'cuba_redonda', 'livre', (0.0, 1.0, 0.0, 1.0), 'lancamento'),
    (r'Cooktop', 'cooktop', 'livre', (0.0, 1.0, 0.0, 1.0), 'lancamento'),
]
sprites = {r[1]: carrega(r[1]) for r in SPRITE}
ESC_L = a.cm_px_estilo / a.cm_px   # px do lancamento -> px do quadro
coberto = np.zeros((H, W), bool)

_alfa = {}
def alfa(sprite):
    """mascara do objeto: tira o piso do lancamento que veio junto no recorte (cor da borda do recorte)."""
    k = id(sprite)
    if k in _alfa_fix: return _alfa_fix[k]
    if k not in _alfa:
        b = np.concatenate([sprite[0], sprite[-1], sprite[:, 0], sprite[:, -1]]).astype(np.float32)
        fundo = np.median(b, axis=0)
        dif = np.abs(sprite.astype(np.float32) - fundo).max(axis=2)
        # fundo = piso do lancamento ligado a borda do recorte (tolerancia 28): fica transparente
        perto = (dif <= 36).astype(np.uint8)
        hs_, ws_ = perto.shape; fl = perto.copy(); mk_ = np.zeros((hs_ + 2, ws_ + 2), np.uint8)
        for (xx, yy) in [(x_, 0) for x_ in range(0, ws_, 4)] + [(x_, hs_ - 1) for x_ in range(0, ws_, 4)] + [(0, y_) for y_ in range(0, hs_, 4)] + [(ws_ - 1, y_) for y_ in range(0, hs_, 4)]:
            if fl[yy, xx] == 1: cv2.floodFill(fl, mk_, (xx, yy), 2)
        a_ = (fl != 2).astype(np.float32)
        a_ = cv2.morphologyEx(a_, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        _alfa[k] = cv2.GaussianBlur(a_, (5, 5), 0)
    return _alfa[k]

# comodos: paredes com os vaos de porta fechados -> o objeto nao atravessa parede
_fech = cv2.morphologyEx(paredes.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((px(110), px(110)), np.uint8))
_nc, comodo = cv2.connectedComponents((_fech == 0).astype(np.uint8), connectivity=4)

def cola(sprite, dst3, recorte=None, alfa_sprite=None):
    """dst3 = pontos no quadro para (0,0), (w,0), (w,h) do sprite. recorte = mascara onde pode pintar."""
    hs, ws = sprite.shape[:2]
    Af = cv2.getAffineTransform(np.float32([[0, 0], [ws - 1, 0], [ws - 1, hs - 1]]), np.float32(dst3))
    warp = cv2.warpAffine(sprite, Af, (W, H), flags=cv2.INTER_AREA)
    al = cv2.warpAffine(alfa(sprite) if alfa_sprite is None else alfa_sprite, Af, (W, H), flags=cv2.INTER_LINEAR)
    if recorte is not None: al = al * recorte
    al = np.clip(al, 0, 1)[..., None]
    sel = al[..., 0] > 0.02
    img[sel] = (warp[sel] * al[sel] + img[sel] * (1 - al[sel])).astype(np.uint8)
    return al[..., 0] > 0.5

todos = [e for g in grupos.values() for e in g if e.dxftype() == 'INSERT']
for e in todos:
    nome = re.sub(r'\[\d+\]', '', e.dxf.name)
    regra = next((r for r in SPRITE if re.search(r[0], nome)), None)
    if regra is None or sprites[regra[1]] is None: continue
    ents = [x for x in d.blocks[e.dxf.name] if x.dxftype() in ('LINE', 'LWPOLYLINE', 'POLYLINE', 'ARC', 'CIRCLE', 'ELLIPSE')]
    bl = bbox.extents(ents)
    if not bl.has_data: continue
    x0, y0, x1, y1 = bl.extmin.x, bl.extmin.y, bl.extmax.x, bl.extmax.y
    pts = []
    for x in ents:
        if x.dxftype() == 'LINE': pts += [(x.dxf.start.x, x.dxf.start.y), (x.dxf.end.x, x.dxf.end.y)]
        elif x.dxftype() == 'LWPOLYLINE': pts += [(p[0], p[1]) for p in x.get_points('xy')]
    pts = np.array(pts) if pts else np.zeros((1, 2))
    spr0 = sprites[regra[1]]; fx0_, fx1_, fy0_, fy1_ = regra[3]
    paisagem = (fx1_ - fx0_) * spr0.shape[1] > (fy1_ - fy0_) * spr0.shape[0]   # corpo do sprite mais largo que alto
    longo_x = (x1 - x0) >= (y1 - y0)                                            # bloco mais comprido em x
    if regra[2] == 'livre':
        loc = [(x0, y1), (x1, y1), (x1, y0)]
    else:
        # largura do sprite vai no eixo comprido do bloco se o sprite for paisagem, senao no eixo curto
        largura_em_x = longo_x if paisagem else not longo_x
        if largura_em_x:   # u ao longo de x; base do sprite (detalhe) no lado y com mais pontos
            det_alto = (pts[:, 1] > y0 + 0.75 * (y1 - y0)).sum() >= (pts[:, 1] < y0 + 0.25 * (y1 - y0)).sum()
            loc = [(x0, y0), (x1, y0), (x1, y1)] if det_alto else [(x1, y1), (x0, y1), (x0, y0)]
        else:              # u ao longo de y; base do sprite no lado x com mais pontos
            det_dir = (pts[:, 0] > x0 + 0.75 * (x1 - x0)).sum() >= (pts[:, 0] < x0 + 0.25 * (x1 - x0)).sum()
            loc = [(x0, y1), (x0, y0), (x1, y0)] if det_dir else [(x1, y0), (x1, y1), (x0, y1)]
    M = e.matrix44()
    dst = [np.array(para_img(M.transform((qx, qy, 0)).x, M.transform((qx, qy, 0)).y)) for qx, qy in loc]
    spr = sprites[regra[1]]
    fx0, fx1, fy0, fy1 = regra[3]
    p0, p1, p2 = dst; u = p1 - p0; v = p2 - p1
    wd, hd = np.linalg.norm(u), np.linalg.norm(v)
    if wd < 1 or hd < 1: continue
    u, v = u / wd, v / hd
    wf, hf = wd / (fx1 - fx0), hd / (fy1 - fy0)       # sprite inteiro, com o corpo na medida do DWG
    if u[0] * v[1] - u[1] * v[0] < 0:   # bloco espelhado no DWG: desespelha (logo e textos do lancamento legiveis)
        p0 = p0 + u * wd; u = -u
    tl = p0 - u * fx0 * wf - v * fy0 * hf
    if regra[4] == 'lancamento':                       # medida do objeto no lancamento (sem esticar)
        wl_, hl_ = spr.shape[1] * ESC_L, spr.shape[0] * ESC_L
        if regra[2] == 'livre':                        # centrado no bloco, lado comprido do sprite no lado comprido do bloco
            c0 = p0 + u * wd / 2 + v * hd / 2
            if (wl_ >= hl_) != (wd >= hd): u, v = v, -u
            tl = c0 - u * wl_ / 2 - v * hl_ / 2
        else:                                          # base (caixa acoplada, fundo da arara) encostada no mesmo lado
            base_ = p0 + u * wd / 2 + v * hd
            tl = base_ - u * wl_ / 2 - v * hl_
        wf, hf = wl_, hl_
    dst = [tl, tl + u * wf, tl + u * wf + v * hf]
    cc = (dst[0] + dst[2]) / 2
    cx_, cy_ = int(np.clip(cc[0], 0, W - 1)), int(np.clip(cc[1], 0, H - 1))
    lab_c = comodo[cy_, cx_]
    rec = None
    if lab_c > 0:
        rec = cv2.dilate((comodo == lab_c).astype(np.uint8), np.ones((px(14), px(14)), np.uint8)).astype(np.float32)
        rec[paredes] = 0
    alfa_mod = None
    if regra[1] == 'cama':   # criado-mudo que bate na parede ou sai do comodo fica de fora
        hs_, ws_ = spr.shape[:2]
        Af_ = cv2.getAffineTransform(np.float32([[0, 0], [ws_ - 1, 0], [ws_ - 1, hs_ - 1]]), np.float32(dst))
        alfa_mod = alfa(spr).copy()
        for (ax0, ax1, ay0, ay1) in ((0.0, 0.16, 0.70, 0.95), (0.83, 1.0, 0.70, 0.95)):
            reg_ = np.zeros((hs_, ws_), np.uint8); reg_[int(ay0 * hs_):int(ay1 * hs_), int(ax0 * ws_):int(ax1 * ws_)] = 1
            mreg = cv2.warpAffine(reg_, Af_, (W, H), flags=cv2.INTER_NEAREST) > 0
            n_ = max(1, int(mreg.sum()))
            vao = (_fech > 0) & ~paredes
            fora = ((mreg & paredes).sum() / n_ > 0.02 or (rec is not None and (mreg & (rec == 0)).sum() / n_ > 0.05)
                    or (mreg & vao).sum() / n_ > 0.02 or (mreg & fach).sum() / n_ > 0.02 or (mreg & ((comodo != lab_c) & (comodo > 0))).sum() / n_ > 0.02)
            if fora: alfa_mod[reg_ > 0] = 0
    coberto |= cola(spr, dst, rec, alfa_mod)

# --- cuba da cozinha no tampo, no lado oposto ao cooktop (como no lancamento)
cuba = carrega('cuba_cozinha')
cooks = []
for e in grupos.get('cooktop', []):
    if e.dxftype() == 'INSERT':
        bb_ = bbox.extents([e])
        if bb_.has_data: cooks.append(np.array(para_img(bb_.center.x, bb_.center.y)))
if cuba is not None:
    for e in grupos['bancada']:
        if not re.search(r'Arm.rio Baixo', e.dxf.name): continue
        bb_ = bbox.extents([e])
        if not bb_.has_data: continue
        (ax, ay), (bx, by) = para_img(bb_.extmin.x, bb_.extmax.y), para_img(bb_.extmax.x, bb_.extmin.y)
        w_, h_ = bx - ax, by - ay
        if max(w_, h_) < px(120): continue
        if w_ >= h_: e1, e2, larg = np.array([ax, (ay + by) / 2]), np.array([bx, (ay + by) / 2]), h_
        else: e1, e2, larg = np.array([(ax + bx) / 2, ay]), np.array([(ax + bx) / 2, by]), w_
        perto = min(cooks, key=lambda c: min(np.linalg.norm(c - e1), np.linalg.norm(c - e2))) if cooks else e1
        fim = e1 if np.linalg.norm(perto - e1) > np.linalg.norm(perto - e2) else e2
        dirv = (e2 - e1) / np.linalg.norm(e2 - e1); dentro = dirv if fim is e1 else -dirv
        c_ = fim + dentro * px(35)
        wl_, hl_ = cuba.shape[1] * ESC_L, cuba.shape[0] * ESC_L; nrm = np.array([-dirv[1], dirv[0]])
        tl_ = c_ - dirv * wl_ / 2 - nrm * hl_ / 2
        coberto |= cola(cuba, [tl_, tl_ + dirv * wl_, tl_ + dirv * wl_ + nrm * hl_])

if a.hidro_lancamento and a.ocr_lancamento:
    L_ = cv2.imread(a.hidro_lancamento, cv2.IMREAD_UNCHANGED)
    if L_.shape[2] == 4:
        al_ = L_[:, :, 3:] / 255.0; L_ = (L_[:, :, :3] * al_ + 255 * (1 - al_)).astype(np.uint8)
    # posicao das unidades: OCR do lancamento x rotulos das zonas do DWG -> escala + deslocamento
    oc = {}
    for ln in json.load(open(a.ocr_lancamento, encoding='utf-8-sig')):
        ws_ = ln['palavras'] if isinstance(ln['palavras'], list) else [ln['palavras']]
        mm = re.search(r'\b(\d{3})\b', ' '.join(w['t'] for w in ws_))
        if mm: oc.setdefault(mm.group(1), (np.mean([w['x'] + w['w'] / 2 for w in ws_]), np.mean([w['y'] + w['h'] / 2 for w in ws_])))
    nv = {}
    for txt, xw, yw in rot:
        mm = re.match(r'\s*(\d{3})\b', txt)
        if mm and not re.search('GARDEN|SACADA|TERRA', txt, re.I): nv.setdefault(mm.group(1), para_img(xw, yw))
    ks = [k for k in oc if k in nv]
    if len(ks) >= 3:
        A_ = np.array([oc[k] for k in ks]); B_ = np.array([nv[k] for k in ks])
        sc = float(np.sum((A_ - A_.mean(0)) * (B_ - B_.mean(0))) / np.sum((A_ - A_.mean(0)) ** 2)); tq = B_.mean(0) - sc * A_.mean(0)
        gl = cv2.cvtColor(L_, cv2.COLOR_BGR2GRAY)
        # banheiras do lancamento pela cor da agua (exclui a piscina, que e muito maior); cada uma recortada inteira
        Lf_ = L_.astype(int)
        agua = (Lf_[:, :, 1] > Lf_[:, :, 2] + 6) & (Lf_[:, :, 0] > Lf_[:, :, 2] + 4) & (Lf_[:, :, 2] > 120)
        agua = cv2.morphologyEx(agua.astype(np.uint8), cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
        agua = cv2.morphologyEx(agua, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
        na, la, sa, _ = cv2.connectedComponentsWithStats(agua, 8)
        achados = []
        for i_ in range(1, na):
            x_, y_, w_, h_, ar_ = sa[i_]
            if not (2500 < ar_ < 40000) or max(w_, h_) > 260: continue
            comp = (la == i_).astype(np.uint8)
            hull = cv2.convexHull(cv2.findContours(comp, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0][0])
            m_ = np.zeros_like(comp); cv2.fillPoly(m_, [hull], 1); m_ = cv2.dilate(m_, np.ones((13, 13), np.uint8))   # borda branca da banheira
            ys_, xs_ = np.where(m_ > 0); X0_, Y0_, X1_, Y1_ = xs_.min(), ys_.min(), xs_.max() + 1, ys_.max() + 1
            tpl = np.ascontiguousarray(L_[Y0_:Y1_, X0_:X1_])
            _alfa_fix[id(tpl)] = cv2.GaussianBlur(m_[Y0_:Y1_, X0_:X1_].astype(np.float32), (3, 3), 0)
            achados.append(((X0_ + X1_) / 2, (Y0_ + Y1_) / 2, tpl, 1.0))
        deck_ = cv2.dilate((zid > 0).astype(np.uint8), np.ones((px(20), px(20)), np.uint8)).astype(np.float32)
        deck_[paredes | muro] = 0
        # terracos do lancamento: madeira do deck, separados pelos muros
        Lf = L_.astype(int); bb, gg, rr = Lf[:, :, 0], Lf[:, :, 1], Lf[:, :, 2]
        madeira = ((rr - bb) > 30) & (rr > gg) & (gg > bb) & (rr > 70) & (rr < 215)
        madeira = cv2.morphologyEx(madeira.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
        nL, labL, stL, _ = cv2.connectedComponentsWithStats(madeira, 4)
        zdeck = [z for z in zonas if z['classe'] == 'deck']
        n_h = 0
        for cx, cy, tpl, sc_ in achados:
            hs_, ws_ = tpl.shape[:2]
            tx0, ty0, tx1, ty1 = cx - ws_ / 2, cy - hs_ / 2, cx + ws_ / 2, cy + hs_ / 2
            # terraco do lancamento que mais envolve a banheira
            win = labL[int(max(0, ty0 - 15)):int(ty1 + 15), int(max(0, tx0 - 15)):int(tx1 + 15)]
            ids, cnt = np.unique(win[win > 0], return_counts=True)
            if not len(ids): continue
            lx, ly, lw, lh = stL[ids[np.argmax(cnt)], :4]
            # terraco novo correspondente: o que contem (ou fica mais perto de) a posicao levada pela escala geral
            c_ = np.array([cx, cy]) * sc + tq
            # unidade do terraco: numero do lancamento dentro da faixa do terraco (eixo comprido), o mais proximo
            longo_h = lw >= lh
            cand_ = [(k_, q_) for k_, q_ in oc.items() if (lx <= q_[0] <= lx + lw if longo_h else ly <= q_[1] <= ly + lh)]
            cod = min(cand_, key=lambda t: np.hypot(t[1][0] - cx, t[1][1] - cy))[0] if cand_ else None
            zc = [z for z in zdeck if cod and z['texto'].strip().startswith(cod)]
            z_ = (zc or zdeck)
            z_ = max(z_, key=lambda z: cv2.pointPolygonTest(z['img'].astype(np.int32).reshape(-1, 1, 2), (float(c_[0]), float(c_[1])), True))
            zx, zy, zw, zh = cv2.boundingRect(z_['img'].astype(np.int32))
            wl_, hl_ = ws_ * ESC_L, hs_ * ESC_L
            dl, dr = (tx0 - lx) * ESC_L, (lx + lw - tx1) * ESC_L
            dt, db = (ty0 - ly) * ESC_L, (ly + lh - ty1) * ESC_L
            nx = zx + max(0, dl) if dl <= dr else zx + zw - max(0, dr) - wl_
            ny = zy + max(0, dt) if dt <= db else zy + zh - max(0, db) - hl_
            nx = float(np.clip(nx, zx, zx + zw - wl_)); ny = float(np.clip(ny, zy, zy + zh - hl_))
            mz = np.zeros((H, W), np.uint8); cv2.fillPoly(mz, [z_['img'].astype(np.int32)], 1)
            rec_ = cv2.dilate(mz, np.ones((px(8), px(8)), np.uint8)).astype(np.float32); rec_[paredes | muro] = 0
            tl_ = np.array([nx, ny])
            coberto |= cola(tpl, [tl_, tl_ + [wl_, 0], tl_ + [wl_, hl_]], rec_); n_h += 1
        print('banheiras na posicao do lancamento:', n_h, 'de', len(achados), '| escala lancamento->planta', round(sc, 3))
# --- decoracao dos gardens/terracos como no lancamento (nao consta no projeto aprovado: so ambientacao) -----------
decor = []
hidro, palm, polt = carrega('hidro_redonda'), carrega('palmeira'), carrega('poltrona')
livre_ext = ~(paredes | muro | coberto)
for k, z in enumerate(zonas, 1):
    if z['classe'] != 'deck': continue
    mz = np.zeros((H, W), np.uint8); cv2.fillPoly(mz, [z['img']], 1)
    mz = (mz > 0) & livre_ext
    dist = cv2.distanceTransform(mz.astype(np.uint8), cv2.DIST_L2, 5)
    tam = lambda spr: int(round(max(spr.shape[:2]) * a.cm_px_estilo / 2)) if spr is not None else 0   # raio em cm no lancamento
    itens = ([('hidro', hidro, (tam(hidro),))] if a.hidro_gardens and not a.hidro_lancamento and hidro is not None else []) + [('palmeira', palm, (tam(palm),))] + [('poltrona', polt, (tam(polt),))] * 2
    for nome_, spr, raios in itens:
        if spr is None: continue
        cabe = [r for r in raios if dist.max() >= px(r) + px(5)]
        if not cabe: continue
        r_ = px(cabe[0])
        yy, xx = np.unravel_index(np.argmax(dist), dist.shape)
        cola(spr, [(xx - r_, yy - r_), (xx + r_, yy - r_), (xx + r_, yy + r_)])
        cv2.circle(dist, (int(xx), int(yy)), r_ + px(40), 0, -1)
        dist = cv2.distanceTransform((dist > 0).astype(np.uint8), cv2.DIST_L2, 5)
        decor.append(nome_)
print('decoracao gardens:', {n: decor.count(n) for n in set(decor)})

# --- piscina: borda de pedra -------------------------------------------------------------------------------
for z in extras:
    if z['classe'] == 'agua':
        cv2.polylines(img, [z['img']], True, (214, 222, 226), px(18))

TEXOBJ = {'lavat': textura_obj('granito'), 'bancada': textura_obj('granito'), 'armario': textura_obj('madeira'), 'mesa': textura_obj('madeira')}

for k, lin, sil, (fill, edge) in camadas:
    sil = sil & ~coberto; lin = np.where(coberto, 0, lin)
    if k in ('escada', 'guarda', 'porta', 'cortina', 'box'):
        img[sil] = edge
        continue
    if k in TEXOBJ and TEXOBJ[k] is not None:
        img[sil] = TEXOBJ[k][sil]
    else:
        img[sil] = fill
    if k not in ('bancada', 'lavat', 'mesa'): img[lin > 70] = edge   # tampo de granito sem o traco interno do bloco
img[muro] = (118, 118, 120)
if a.vazios:
    com_zona = np.zeros((H, W), np.uint8)
    for z in zonas: cv2.fillPoly(com_zona, [z['img']], 1)
    vaz = (predio & (com_zona == 0) & ~paredes).astype(np.uint8)
    vaz = cv2.morphologyEx(vaz, cv2.MORPH_OPEN, np.ones((px(40), px(40)), np.uint8))
    n_, lab_, st_, _ = cv2.connectedComponentsWithStats(vaz, 4)
    for i_ in range(1, n_):
        if st_[i_, 4] * (a.cm_px / 100) ** 2 < 1.5: continue
        mk = lab_ == i_
        img[mk] = (img[mk].astype(np.float32) * 0.55 + 255 * 0.45).astype(np.uint8)   # vazio: piso de baixo, esmaecido
        x_, y_, w_, h_ = st_[i_, :4]
        xis = np.zeros((H, W), np.uint8)
        cv2.line(xis, (int(x_), int(y_)), (int(x_ + w_), int(y_ + h_)), 1, max(2, px(2.5)))
        cv2.line(xis, (int(x_ + w_), int(y_)), (int(x_), int(y_ + h_)), 1, max(2, px(2.5)))
        cv2.rectangle(xis, (int(x_), int(y_)), (int(x_ + w_), int(y_ + h_)), 1, max(2, px(2.5)))
        img[(xis > 0) & mk] = (95, 95, 97)
img[paredes] = (66, 66, 68)
ok_ = cv2.imwrite(a.saida, img)
if not ok_: raise SystemExit("ERRO: nao consegui gravar " + a.saida + " (arquivo aberto em outro programa?)")
json.dump(dict(dxf=a.dxf, X0=X0, Y1=Y1, px_por_mm=s, largura=W, altura=H), open(a.saida[:-4] + '_quadro.json', 'w'))
cv2.imwrite(a.saida[:-4] + '_paredes_qc.png', cv2.cvtColor(np.where(paredes, 0, 255).astype(np.uint8), cv2.COLOR_GRAY2BGR))   # so para a conferencia com o R06
print(a.saida, W, H, {k: len(v) for k, v in grupos.items()})
