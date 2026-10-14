"""Painel de conferencia: recorte final em volta de cada item de 'apagar', ampliado."""
import sys, json, numpy as np
from PIL import Image
sys.path.insert(0, __import__('os').path.dirname(__file__))
from plantas import carregar, mascara_unidade, ler_config
c = ler_config(sys.argv[1]); saida = sys.argv[2]
_, alpha = carregar(c['planta']); FH, FW = alpha.shape; f = FW/2000
dono = {}
for k, un in c['unidades'].items():
    m = mascara_unidade(un, c.get('angulo', 0), 2000, round(FH/f), (FH, FW), f); m[alpha == 0] = 0
    ys, xs = np.where(m > 0); dono[k] = (m, xs.min(), ys.min())
tiles = []
for it in c['apagar']:
    cx, cy = it['centro']; X, Y = int(cx*f), int(cy*f)
    ks = [k for k, (m, _, _) in dono.items() if m[Y, X]]
    if not ks: print('fora de unidade:', it.get('obs')); continue
    m, x0, y0 = dono[ks[0]]; im = Image.open(c['saida'] + '/' + c['nome'].format(id=ks[0]))
    R = int(45*f)
    tiles.append(im.crop((X-x0-R, Y-y0-int(R*.5), X-x0+R, Y-y0+int(R*.4))).resize((280, 126), Image.NEAREST))
sh = Image.new('RGB', (6*284, ((len(tiles)+5)//6)*130), 'gray')
for i, t in enumerate(tiles): sh.paste(t, ((i%6)*284, (i//6)*130))
sh.save(saida); print(len(tiles))
