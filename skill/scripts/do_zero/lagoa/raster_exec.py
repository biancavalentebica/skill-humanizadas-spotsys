"""Lagoa Spot, do zero: rasteriza o executivo R10 (DXF exportado do Revit) por camada, na escala da humanizada de
lancamento (0,4022 cm/px), para que texturas e objetos recortados do lancamento entrem 1:1.

Saida: <prefixo>_masks.npz (uma mascara uint8 por grupo de camada), <prefixo>_quadro.json (origem e escala, para
converter mm do DXF em px) e <prefixo>_textos.json (MTEXT de A-AREA-IDEN com posicao em px).
Uso: py raster_exec.py <pavimento.dxf> <prefixo>
"""
import sys, json, re
import ezdxf, numpy as np, cv2, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from ezdxf import bbox
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
from ezdxf.addons.drawing.config import Configuration, ColorPolicy, BackgroundPolicy, LineweightPolicy

CM_PX = 0.4022375816200381          # m_por_px_humanizada do registro do terreo (05_qc/TER_registro.json) x 100
dxf, pref = sys.argv[1:3]
d = ezdxf.readfile(dxf); m = d.modelspace()
GRUPOS = {
    'parede_ext': ['A-WALL'], 'parede_int': ['I-WALL'], 'porta': ['A-DOOR'], 'vidro': ['A-GLAZ', 'A-GLAZ-CURT', 'A-GLAZ-CWMG'],
    'loucas': ['P-SANR-FIXT'], 'escada': ['S-STRS', 'S-STRS-MBND'], 'piso': ['A-FLOR'], 'piso_padrao': ['A-FLOR-PATT'],
    'guarda': ['Bala\xfastres', 'Balaústres'], 'area': ['A-AREA'], 'detalhe': ['A-DETL'],
}
def lay(e): return e.dxf.layer
todas = [e for e in m if e.dxftype() not in ('MTEXT', 'TEXT', 'DIMENSION')]
b = bbox.extents(todas); pad = 600
X0, Y0, X1, Y1 = b.extmin.x - pad, b.extmin.y - pad, b.extmax.x + pad, b.extmax.y + pad
s = 1.0 / (CM_PX * 10)            # px por mm
W, H = int((X1 - X0) * s), int((Y1 - Y0) * s)
SS = 2

def render(ents, lw=0.13):
    W2, H2 = W * SS, H * SS
    fig = plt.figure(figsize=(W2 / 100, H2 / 100), dpi=100); ax = fig.add_axes([0, 0, 1, 1]); ax.set_axis_off()
    cfg = Configuration(color_policy=ColorPolicy.BLACK, background_policy=BackgroundPolicy.WHITE,
                        lineweight_policy=LineweightPolicy.ABSOLUTE, min_lineweight=lw * SS)
    Frontend(RenderContext(d), MatplotlibBackend(ax), config=cfg).draw_entities(ents)
    ax.set_xlim(X0, X1); ax.set_ylim(Y0, Y1); fig.set_size_inches(W2 / 100, H2 / 100); ax.set_position([0, 0, 1, 1])
    fig.canvas.draw(); img = np.asarray(fig.canvas.buffer_rgba())[:, :, :3]; plt.close(fig)
    tinta = 255 - cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    return cv2.resize(tinta, (W, H), interpolation=cv2.INTER_AREA)

out = {}
for g, camadas in GRUPOS.items():
    ents = [e for e in todas if lay(e) in camadas]
    if not ents: continue
    out[g] = render(ents)
    # hatches separados (cheios) das linhas, para paredes e pisos
    hs = [e for e in ents if e.dxftype() == 'HATCH']
    if hs and g in ('parede_ext', 'parede_int', 'piso', 'escada'):
        out[g + '_hatch'] = render(hs)
    print(g, len(ents), 'px tinta', int((out[g] > 60).sum()))
np.savez_compressed(pref + '_masks.npz', **out)
json.dump(dict(X0=X0, Y0=Y0, X1=X1, Y1=Y1, px_por_mm=s, cm_px=CM_PX, W=W, H=H), open(pref + '_quadro.json', 'w'), indent=1)

def para_px(x, y): return (x - X0) * s, (Y1 - y) * s
txt = []
for e in m.query('MTEXT TEXT'):
    t = e.plain_text() if e.dxftype() == 'MTEXT' else e.dxf.text
    p = e.dxf.insert; u, v = para_px(p.x, p.y)
    txt.append(dict(t=re.sub(r'\s+', ' ', t).strip(), x=round(u, 1), y=round(v, 1), layer=lay(e)))
json.dump(txt, open(pref + '_textos.json', 'w', encoding='utf8'), indent=1, ensure_ascii=False)
# inserts (portas, loucas, esquadrias): nome, posicao, rotacao, escala -> para colocar objetos do lancamento
ins = []
for e in m.query('INSERT'):
    p = e.dxf.insert; u, v = para_px(p.x, p.y)
    bb = bbox.extents([e])
    a0 = para_px(bb.extmin.x, bb.extmax.y); a1 = para_px(bb.extmax.x, bb.extmin.y)
    ins.append(dict(nome=e.dxf.name, layer=lay(e), x=round(u, 1), y=round(v, 1), rot=round(e.dxf.rotation, 2),
                    sx=e.dxf.xscale, sy=e.dxf.yscale, caixa=[round(a0[0]), round(a0[1]), round(a1[0]), round(a1[1])]))
json.dump(ins, open(pref + '_inserts.json', 'w', encoding='utf8'), indent=1, ensure_ascii=False)
print('quadro', W, H)
