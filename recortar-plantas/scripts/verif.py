"""OCR nas imagens finais: aponta texto de area/sacada/terraco que sobrou. uso: verif.py pasta padrao"""
import sys, glob, os, re, numpy as np, pytesseract
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
RUIM = re.compile(r'(\d[,.]\d{2})|m[²2?]|^(S|T)\.|VRN|Garden|GARDEN', re.I)
for p in sorted(glob.glob(os.path.join(sys.argv[1], sys.argv[2]))):
    im = Image.open(p).convert('RGB'); a = np.array(im).astype(int)
    bw = np.where((a.mean(2) < 110) & (a.max(2) - a.min(2) < 30), 0, 255).astype(np.uint8)
    b = Image.fromarray(bw); b = b.resize((b.width // 2, b.height // 2), Image.LANCZOS)
    txt = pytesseract.image_to_string(b, config='--psm 11')
    ach = [t for t in txt.split() if RUIM.search(t)]
    if ach: print(os.path.basename(p), '->', ach)
print('fim')
