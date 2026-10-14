"""Confere se cada imagem ainda mostra o proprio numero (OCR). uso: tem_numero.py pasta"""
import sys, glob, os, re, numpy as np, pytesseract
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
falta = []
for p in sorted(glob.glob(os.path.join(sys.argv[1], '*.png'))):
    num = re.search(r' - (\d{3})', os.path.basename(p)).group(1)
    im = Image.open(p).convert('RGB'); a = np.array(im).astype(int)
    bw = np.where((a.mean(2) < 110) & (a.max(2) - a.min(2) < 30), 0, 255).astype(np.uint8)
    ok = False
    for esc in (0.5, 0.35, 0.75):
        b = Image.fromarray(bw); b = b.resize((max(1, int(b.width * esc)), max(1, int(b.height * esc))), Image.LANCZOS)
        if num in re.sub(r'\s', '', pytesseract.image_to_string(b, config='--psm 11')): ok = True; break
    if not ok: falta.append(os.path.basename(p))
print('SEM NUMERO:', falta)
