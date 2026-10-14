"""OCR dos rotulos: ocr.py planta.png saida.json  -> linhas com bbox no frame de trabalho (2000 px)."""
import sys, json, re, numpy as np, pytesseract
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
im = Image.open(sys.argv[1]).convert('RGBA'); bg = Image.new('RGB', im.size, 'white'); bg.paste(im, mask=im.split()[3])
W = im.width; f = W / 2000
# so pixels escuros e sem cor (texto preto) -> imagem binaria limpa
a = np.array(bg).astype(int); g = a.mean(2); sat = a.max(2) - a.min(2)
bw = np.where((g < 110) & (sat < 30), 0, 255).astype(np.uint8)
linhas = {}
TILE = 3000
for esc, psm in ((0.5, 11), (0.75, 11), (0.5, 12)):
  b = Image.fromarray(bw).resize((int(W * esc), int(im.height * esc)), Image.LANCZOS)
  for x0 in range(0, b.width, TILE - 300):
    t = b.crop((x0, 0, min(x0 + TILE, b.width), b.height))
    d = pytesseract.image_to_data(t, lang='por' if 'por' in pytesseract.get_languages() else 'eng', config=f'--psm {psm}', output_type=pytesseract.Output.DICT)
    for i, txt in enumerate(d['text']):
        txt = txt.strip()
        if not txt or float(d['conf'][i]) < 30: continue
        X = (d['left'][i] + x0) / esc / f; Y = d['top'][i] / esc / f; w = d['width'][i] / esc / f; h = d['height'][i] / esc / f
        key = (round(X), round(Y))
        if any(abs(k[0] - key[0]) < 4 and abs(k[1] - key[1]) < 4 for k in linhas): continue
        linhas[key] = dict(t=txt, x=round(X, 1), y=round(Y, 1), w=round(w, 1), h=round(h, 1))
json.dump(sorted(linhas.values(), key=lambda r: (r['y'], r['x'])), open(sys.argv[2], 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
print(len(linhas))
