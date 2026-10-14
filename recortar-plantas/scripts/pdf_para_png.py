"""Converte planta em PDF para PNG grande (para recortar). uso: pdf_para_png.py arquivo.pdf [dpi=300]
Se o PDF tiver uma imagem embutida grande (render humanizado), extrai ela na resolucao original;
senao, rasteriza a pagina no dpi pedido. Salva ao lado do PDF com o mesmo nome + _p<pagina>.png."""
import sys, os, fitz
pdf = sys.argv[1]; dpi = int(sys.argv[2]) if len(sys.argv) > 2 else 300
d = fitz.open(pdf); base = os.path.splitext(pdf)[0]
for n, pg in enumerate(d, 1):
    imgs = sorted(((d.extract_image(i[0]), i[0]) for i in pg.get_images(full=True)), key=lambda t: -t[0]['width'] * t[0]['height'])
    if imgs and imgs[0][0]['width'] >= 4000:
        x = imgs[0][0]; out = f'{base}_p{n}_imagem.{x["ext"]}'
        open(out, 'wb').write(x['image']); print('imagem embutida', x['width'], 'x', x['height'], '->', out)
    out = f'{base}_p{n}.png'
    pg.get_pixmap(dpi=dpi, alpha=False).save(out); print('pagina rasterizada', dpi, 'dpi ->', out)
