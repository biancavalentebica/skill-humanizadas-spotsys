"""Renderiza um pavimento (DXF do modelo Revit) no estilo 'desenho tecnico humanizado' da humanizada de lancamento."""
import sys, re, ezdxf, numpy as np, cv2, matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
from ezdxf.addons.drawing.config import Configuration, ColorPolicy, BackgroundPolicy, LineweightPolicy, HatchPolicy
dxf, saida, s = sys.argv[1], sys.argv[2], float(sys.argv[3])
d = ezdxf.readfile(dxf); m = d.modelspace()
# categoria -> (preenchimento, contorno)
CAT = [
 (r'cama|CAMA', ((246,245,242),(150,150,150))),
 (r'SOF|Sof', ((140,140,142),(90,90,90))),
 (r'Tapete', ((205,188,152),(170,150,120))),
 (r'CADEIRA|PUFF|MESA LATERAL', ((238,236,232),(140,140,140))),
 (r'Respaldo|Cooktok|Cooktop', ((48,48,50),(30,30,30))),
 (r'TV', ((60,60,60),(40,40,40))),
 (r'Bacia|Cuba|Chuveiro|Torneira', ((255,255,255),(120,120,125))),
 (r'CHAPA HORIZONTAL', ((170,170,170),(120,120,120))),
 (r'MLR|PCI|L7', ((185,187,190),(120,122,125))),
 (r'Chapa|Mesa-bancada|ARARA|Suporte|VASSOUREIRO', ((196,150,98),(140,100,60))),
 (r'Porta|Elevador', ((235,235,235),(110,110,110))),
 (r'janela|Janela|PJ |Mullion', ((175,200,220),(90,120,150))),
 (r'Guarda-corpo', ((150,150,150),(110,110,110))),
 (r'Lance', ((200,200,200),(110,110,110))),
]
LAYER = {'A-WALL':(28,28,28),'A-WALL-PATT':(28,28,28),'I-WALL':(40,40,40),'A-GENM':(120,120,120),'A-FLOR':(200,198,194)}
HIDE = {'Q-CASE','E-ELEC-EQPM_x','I-FURN-HDLN_x','C-PRKG','Q-SPCQ_x'}
for L in d.layers:
    if L.dxf.name in HIDE: L.off()
    L.rgb = LAYER.get(L.dxf.name, (110,110,110))
def cat(nome):
    for rx, c in CAT:
        if re.search(rx, nome): return c
feito = {}
def pinta(bname, c):
    if bname in feito or bname not in d.blocks: return
    feito[bname] = c
    for e in d.blocks[bname]:
        if e.dxftype() == 'INSERT':
            pinta(e.dxf.name, cat(e.dxf.name) or c); continue
        if c is None:
            e.dxf.color = 256; e.dxf.discard('true_color'); continue
        e.rgb = c[0] if e.dxftype() in ('HATCH','SOLID') else c[1]
for e in m:
    if e.dxftype() == 'INSERT': pinta(e.dxf.name, cat(e.dxf.name))
    else:
        e.dxf.color = 256; e.dxf.discard('true_color')
ext = d.header['$EXTMIN'], d.header['$EXTMAX']
w = ext[1][0]-ext[0][0]; h = ext[1][1]-ext[0][1]
fig = plt.figure(figsize=(w*s/100, h*s/100), dpi=100); ax = fig.add_axes([0,0,1,1]); ax.set_axis_off()
cfg = Configuration(color_policy=ColorPolicy.COLOR, background_policy=BackgroundPolicy.WHITE, lineweight_policy=LineweightPolicy.ABSOLUTE, min_lineweight=0.3)
import matplotlib.patches as mp
wl = [e for e in m.query('LINE[layer=="A-WALL"]')]
xs_ = [p for e in wl for p in (e.dxf.start.x, e.dxf.end.x)]; ys_ = [p for e in wl for p in (e.dxf.start.y, e.dxf.end.y)]
ax.add_patch(mp.Rectangle((min(xs_), min(ys_)), max(xs_)-min(xs_), max(ys_)-min(ys_), color=(226/255,224/255,221/255), zorder=-100))
Frontend(RenderContext(d), MatplotlibBackend(ax), config=cfg).draw_layout(m, finalize=True)
ax.set_xlim(ext[0][0], ext[1][0]); ax.set_ylim(ext[0][1], ext[1][1]); fig.set_size_inches(w*s/100, h*s/100); ax.set_position([0,0,1,1])
fig.savefig(saida, dpi=100, facecolor='white')
print('ok')
