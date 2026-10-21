"""Escreve "Unidade NN" dentro do ambiente de cada unidade (regra da Rachel, 19/10/2026: sem caixa de rotulo, sem
area/hospedes; so o nome da unidade, dentro do ambiente). Numero = codigo do SpotSys (mapeado do numero do executivo).
Posicao: no alojamento, o retangulo do texto onde ha mais piso livre (madeira), o mais perto possivel do centro.
Fonte Segoe UI Semibold, cor azul dos rotulos do lancamento (57,66,94), halo claro suave.
Uso: py escreve_unidades.py <prefixo> <entrada.png> <saida.png>"""
import sys, json, re, numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter
Image.MAX_IMAGE_PIXELS = None
pref, ent, sai = sys.argv[1:4]
AMB = sys.argv[sys.argv.index('--amb') + 1] if '--amb' in sys.argv else pref
A = np.load(AMB + '_amb.npz'); J = json.load(open(AMB + '_amb.json', encoding='utf8')); ids = A['ids']
im = Image.open(ent).convert('RGBA'); rgb = np.array(im)[..., :3]; H, W = ids.shape
MAPA = {} if '--amb' in sys.argv else {'02P': {'11': '22'}}.get(pref, {})   # ambientes do Legal ja vem com o codigo SpotSys
fonte = ImageFont.truetype('C:/Windows/Fonts/seguisb.ttf', 76)   # padrao unico: Segoe UI Semibold 76 px, azul dos rotulos
f = rgb.astype(np.int16); R, G, B = f[..., 0], f[..., 1], f[..., 2]; lum = f.mean(axis=2)
livre = (R - B > 20) & (R - B < 85) & (lum > 85) & (lum < 200)         # assoalho
camada = Image.new('RGBA', im.size, (0, 0, 0, 0)); halo = Image.new('RGBA', im.size, (0, 0, 0, 0))
dc, dh = ImageDraw.Draw(camada), ImageDraw.Draw(halo); log = []
for k, v in J['ambientes'].items():
    mm = re.match(r'ALOJ (\d+)', v['nome'] or '')
    if not mm: continue
    num = MAPA.get(mm.group(1), mm.group(1)); txt = f'UNIDADE {int(num):02d}'
    x0, y0, x1, y1 = dc.textbbox((0, 0), txt, font=fonte); tw, th = x1 - x0, y1 - y0
    sala = ids == int(k); ok = (livre & sala).astype(np.float32)
    ys, xs = np.nonzero(sala); cx, cy = xs.mean(), ys.mean()
    # fracao de piso livre em cada janela do tamanho do texto (+ margem)
    pw, ph = tw + 40, th + 30
    I = cv2.integral(ok); S = cv2.integral(sala.astype(np.float32))
    best = None
    for yy in range(ys.min(), ys.max() - ph, 6):
        for xx in range(xs.min(), xs.max() - pw, 6):
            dentro = S[yy + ph, xx + pw] - S[yy, xx + pw] - S[yy + ph, xx] + S[yy, xx]
            if dentro < pw * ph * 0.999: continue
            fr = (I[yy + ph, xx + pw] - I[yy, xx + pw] - I[yy + ph, xx] + I[yy, xx]) / (pw * ph)
            d = np.hypot(xx + pw / 2 - cx, yy + ph / 2 - cy) / 1000
            c = (0 if fr >= 0.97 else 50 + (1 - fr) * 20) + d * 3
            if best is None or c < best[0]: best = (c, xx, yy, fr)
    if best is None: print('sem lugar', txt); continue
    _, xx, yy, fr = best
    px, py = xx + 20 - x0, yy + 15 - y0
    dc.text((px, py), txt, font=fonte, fill=(57, 66, 94, 255))
    log.append(dict(ambiente=v['nome'], texto=txt, x=int(xx), y=int(yy), piso_livre=round(float(fr), 3)))
    print(v['nome'], '->', txt, 'piso livre', round(float(fr), 2))
halo = halo.filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.GaussianBlur(4))
out = Image.alpha_composite(Image.alpha_composite(im, halo), camada)
out.save(sai); json.dump(log, open(sai.replace('.png', '_log.json'), 'w', encoding='utf8'), indent=1, ensure_ascii=False)
Image.alpha_composite(Image.new('RGBA', out.size, (255, 255, 255, 255)), out).convert('RGB').resize((W // 4, H // 4)).save(sai.replace('.png', '_previa.jpg'), quality=85)
