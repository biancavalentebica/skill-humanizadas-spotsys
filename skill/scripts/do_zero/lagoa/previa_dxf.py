"""Prévia do DXF do executivo (linhas pretas, textos) para leitura: py previa_dxf.py <dxf> <png> [larg_px]"""
import sys, ezdxf, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
from ezdxf.addons.drawing.config import Configuration, ColorPolicy, BackgroundPolicy
doc = ezdxf.readfile(sys.argv[1]); msp = doc.modelspace()
larg = int(sys.argv[3]) if len(sys.argv) > 3 else 6000
fig = plt.figure(); ax = fig.add_axes([0, 0, 1, 1])
cfg = Configuration(color_policy=ColorPolicy.BLACK, background_policy=BackgroundPolicy.WHITE)
Frontend(RenderContext(doc), MatplotlibBackend(ax), config=cfg).draw_layout(msp)
x0, x1 = ax.get_xlim(); y0, y1 = ax.get_ylim()
fig.set_size_inches(larg / 100, larg / 100 * (y1 - y0) / (x1 - x0))
fig.savefig(sys.argv[2], dpi=100, facecolor='white')
print(x0, x1, y0, y1)
