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
ap.add_argument('--transform', default='', help='transform.json do registro DWG x PDF (registra_pdf_imagem.py) para levar posicoes do PDF ao quadro')
a = ap.parse_args()

d = ezdxf.readfile(a.dxf); m = d.modelspace()
IGNORA = re.compile(r'^(Demolido|1-ANOT|2-INST|3-ANOT|4-ANOT|0-MOD M.SCARAS|0-MOD _ FORRO|0-MOD _ LAJES|0-MOD _ TERRENO|0_Caneta|Defpoints)', re.I)
# categoria por nome do bloco (ordem importa) -> (preenchimento BGR, contorno BGR)
CAT = [
    ('parede',    r'^Parede(?! Cortina)',                    None),
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
TEX = {k: textura(k, c) for k, c in [('porcelanato', (218, 220, 221)), ('deck', (90, 130, 170)), ('grama', (70, 120, 60)),
                                       ('agua', (190, 180, 150)), ('externo', (205, 207, 208))]}
TEX['porcelanato'] = piso_liso('porcelanato', (218, 220, 221), 90)
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
    sil = preenche(lin) if k not in ('escada', 'guarda', 'porta', 'cortina') else (lin > 40)
    camadas.append((k, lin, sil, cor))
    if k in ('cama', 'armario', 'bancada', 'mesa', 'sofa', 'cadeira', 'loucas', 'tv'):
        sombra += sil.astype(np.float32)
sh = cv2.GaussianBlur(np.roll(np.roll(np.clip(sombra, 0, 1) + (paredes | muro).astype(np.float32), px(4), 0), px(4), 1), (0, 0), px(5))
img = (img.astype(np.float32) * (1 - 0.28 * np.clip(sh, 0, 1)[..., None])).astype(np.uint8)

# --- objetos do lancamento (sprites) na posicao e orientacao de cada bloco do DWG ---------------------------
OBJ = os.path.join(a.estilo, 'objetos') if a.estilo else ''
def carrega(n):
    for f_ in (os.path.join(OBJ, n + '.png'), os.path.join(a.estilo, n + '.png') if a.estilo else ''):
        if f_ and os.path.exists(f_): return cv2.imread(f_)
    return None
SPRITE = [  # (regex do nome do bloco, sprite, orientacao: 'detalhe_embaixo' | 'livre')
    (r'Cama', 'cama', 'detalhe_embaixo'),
    (r'Sof.', 'sofa', 'detalhe_embaixo'),
    (r'Poltrona', 'poltrona', 'detalhe_embaixo'),
    (r'Espregui', 'espreguicadeira', 'detalhe_embaixo'),
    (r'Mesa.*Redonda|Mesa de Jantar Redonda', 'mesa_redonda', 'livre'),
    (r'^Vaso Sanit.rio(?! Acess)', 'vaso_sanitario', 'detalhe_embaixo'),
    (r'Guarda-Roupa', 'armario_cabides', 'detalhe_embaixo'),
]
sprites = {n: carrega(n) for _, n, _ in SPRITE}
coberto = np.zeros((H, W), bool)

def cola(sprite, dst3):
    """dst3 = pontos no quadro para (0,0), (w,0), (w,h) do sprite."""
    hs, ws = sprite.shape[:2]
    Af = cv2.getAffineTransform(np.float32([[0, 0], [ws - 1, 0], [ws - 1, hs - 1]]), np.float32(dst3))
    warp = cv2.warpAffine(sprite, Af, (W, H), flags=cv2.INTER_AREA)
    mk = cv2.warpAffine(np.full((hs, ws), 255, np.uint8), Af, (W, H)) > 128
    img[mk] = warp[mk]
    return mk

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
    if regra[2] == 'livre':
        loc = [(x0, y1), (x1, y1), (x1, y0)]
    elif (y1 - y0) >= (x1 - x0):   # lado com mais detalhe (travesseiros, encosto, caixa acoplada) = base do sprite
        cima = (pts[:, 1] > y0 + 0.75 * (y1 - y0)).sum() >= (pts[:, 1] < y0 + 0.25 * (y1 - y0)).sum()
        loc = [(x0, y0), (x1, y0), (x1, y1)] if cima else [(x1, y1), (x0, y1), (x0, y0)]
    else:
        dire = (pts[:, 0] > x0 + 0.75 * (x1 - x0)).sum() >= (pts[:, 0] < x0 + 0.25 * (x1 - x0)).sum()
        loc = [(x0, y1), (x0, y0), (x1, y0)] if dire else [(x1, y0), (x1, y1), (x0, y1)]
    M = e.matrix44()
    dst = [para_img(M.transform((qx, qy, 0)).x, M.transform((qx, qy, 0)).y) for qx, qy in loc]
    coberto |= cola(sprites[regra[1]], dst)

# --- decoracao dos gardens/terracos como no lancamento (nao consta no projeto aprovado: so ambientacao) -----------
decor = []
hidro, palm, polt = carrega('hidro_redonda'), carrega('palmeira'), carrega('poltrona')
livre_ext = ~(paredes | muro | coberto)
for k, z in enumerate(zonas, 1):
    if z['classe'] != 'deck': continue
    mz = np.zeros((H, W), np.uint8); cv2.fillPoly(mz, [z['img']], 1)
    mz = (mz > 0) & livre_ext
    dist = cv2.distanceTransform(mz.astype(np.uint8), cv2.DIST_L2, 5)
    itens = ([('hidro', hidro, (95, 80, 70))] if a.hidro_gardens and hidro is not None else []) + [('palmeira', palm, (45, 35))] + [('poltrona', polt, (40, 34))] * 2
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

TEXOBJ = {'bancada': textura_obj('granito'), 'armario': textura_obj('madeira'), 'mesa': textura_obj('madeira')}

for k, lin, sil, (fill, edge) in camadas:
    sil = sil & ~coberto; lin = np.where(coberto, 0, lin)
    if k in ('escada', 'guarda', 'porta', 'cortina'):
        img[sil] = edge
        continue
    if k in TEXOBJ and TEXOBJ[k] is not None:
        img[sil] = TEXOBJ[k][sil]
    else:
        img[sil] = fill
    img[lin > 70] = edge
img[muro] = (118, 118, 120)
img[paredes] = (66, 66, 68)
ok_ = cv2.imwrite(a.saida, img)
if not ok_: raise SystemExit("ERRO: nao consegui gravar " + a.saida + " (arquivo aberto em outro programa?)")
json.dump(dict(dxf=a.dxf, X0=X0, Y1=Y1, px_por_mm=s, largura=W, altura=H), open(a.saida[:-4] + '_quadro.json', 'w'))
cv2.imwrite(a.saida[:-4] + '_paredes_qc.png', cv2.cvtColor(np.where(paredes, 0, 255).astype(np.uint8), cv2.COLOR_GRAY2BGR))   # so para a conferencia com o R06
print(a.saida, W, H, {k: len(v) for k, v in grupos.items()})
