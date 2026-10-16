"""Comparativo por pavimento: humanizada LANCADA | prancha APROVADA (PDF) | NOVA humanizada conforme aprovado.
Gera uma pagina JPG por pavimento e um PDF com todas.

Uso: py monta_comparativo.py <config.json> <pasta_saida>
"""
import json, os, sys
import cv2, fitz, numpy as np
from PIL import Image, ImageDraw, ImageFont

cfg = json.load(open(sys.argv[1], encoding='utf-8')); OUT = sys.argv[2]
os.makedirs(OUT, exist_ok=True)
F = 'C:/Windows/Fonts/'
f_tit = ImageFont.truetype(F + 'arialbd.ttf', 54); f_col = ImageFont.truetype(F + 'arialbd.ttf', 34)
f_txt = ImageFont.truetype(F + 'arial.ttf', 28); f_txtb = ImageFont.truetype(F + 'arialbd.ttf', 28)
f_pe = ImageFont.truetype(F + 'arial.ttf', 22)
W, PW, M = 4200, 1340, 40  # largura da pagina, largura de cada painel, margem
COR = dict(tinta=(30, 30, 35), cinza=(110, 110, 115), linha=(215, 215, 220), ok=(30, 130, 70), alerta=(200, 90, 0), muda=(225, 110, 0))
pdf = fitz.open(cfg['pdf_aprovado'])


def carrega(p):
    im = cv2.imread(p, cv2.IMREAD_UNCHANGED)
    if im.shape[2] == 4:
        a = im[:, :, 3:4] / 255.0; im = (im[:, :, :3] * a + 255 * (1 - a)).astype(np.uint8)
    return im


def ajusta(im, w, h):
    s = min(w / im.shape[1], h / im.shape[0])
    r = cv2.resize(im, (int(im.shape[1] * s), int(im.shape[0] * s)), interpolation=cv2.INTER_AREA)
    tela = np.full((h, w, 3), 255, np.uint8); y, x = (h - r.shape[0]) // 2, (w - r.shape[1]) // 2
    tela[y:y + r.shape[0], x:x + r.shape[1]] = r
    return tela, s, x, y


paginas = []
for pv in cfg['pavimentos']:
    PH = 900
    lanc = carrega(pv['lancada'])
    nova = carrega(pv['nova'])
    pg = pdf[pv['pagina'] - 1]
    pix = pg.get_pixmap(dpi=200, clip=fitz.Rect(*pv['clip_pt']))
    apr = np.frombuffer(pix.samples, np.uint8).reshape(pix.h, pix.w, pix.n)[:, :, :3][:, :, ::-1].copy()
    p1, *_ = ajusta(lanc, PW, PH); p2, *_ = ajusta(apr, PW, PH)
    nv = nova.copy()
    for (x0, y0, x1, y1) in pv.get('marcas', []):  # destaca o que mudou na nova
        cv2.rectangle(nv, (x0 - 110, y0 - 150), (x1 + 110, y1 + 70), COR['muda'][::-1], 22)
    p3, *_ = ajusta(nv, PW, PH)
    notas = pv['notas']
    det = None
    if pv.get('detalhe'):
        dimg = Image.open(pv['detalhe']).convert('RGB'); s_ = (W - 2 * M) / dimg.width
        det = dimg.resize((W - 2 * M, int(dimg.height * s_)))
    H = 120 + 60 + PH + 40 + 44 * len(notas) + 120 + ((det.height + 80) if det else 0)
    pag = Image.new('RGB', (W, H), 'white'); d = ImageDraw.Draw(pag)
    d.text((M, 30), f"{cfg['empreendimento']}  |  {pv['nome']}", font=f_tit, fill=COR['tinta'])
    st = pv['status']; cst = COR['ok'] if st.startswith('SEM') else COR['alerta']
    tw = d.textlength(st, font=f_col); d.rounded_rectangle((W - M - tw - 40, 34, W - M, 92), 12, outline=cst, width=4)
    d.text((W - M - tw - 20, 44), st, font=f_col, fill=cst)
    y = 130
    cols = [('1. HUMANIZADA LANÇADA', pv['rotulo_lancada']), ('2. PROJETO APROVADO (PDF)', pv['rotulo_aprovado']),
            ('3. NOVA HUMANIZADA (conforme aprovado)', pv['rotulo_nova'])]
    for i, (p, (t, sub)) in enumerate(zip((p1, p2, p3), cols)):
        x = M + i * (PW + 30)
        d.text((x, y), t, font=f_col, fill=COR['tinta']); d.text((x, y + 42), sub, font=f_pe, fill=COR['cinza'])
        pag.paste(Image.fromarray(p[:, :, ::-1]), (x, y + 80))
        d.rectangle((x - 1, y + 79, x + PW, y + 80 + PH), outline=COR['linha'], width=2)
    y = y + 80 + PH + 30
    for n in notas:
        neg = n.startswith('!')
        d.text((M, y), ('• ' + n.lstrip('!')), font=f_txtb if neg else f_txt, fill=COR['alerta'] if neg else COR['tinta']); y += 44
    if det:
        y += 20; d.text((M, y), pv.get('titulo_detalhe', 'Detalhe'), font=f_col, fill=COR['tinta']); y += 50
        pag.paste(det, (M, y)); y += det.height
    d.text((M, H - 60), cfg['rodape'], font=f_pe, fill=COR['cinza'])
    nome = os.path.join(OUT, f"{cfg['prefixo']}_{pv['id']}.jpg")
    pag.save(nome, quality=90); paginas.append(pag); print(nome)

paginas[0].save(os.path.join(OUT, f"{cfg['prefixo']}.pdf"), save_all=True, append_images=paginas[1:], resolution=150)
print(os.path.join(OUT, f"{cfg['prefixo']}.pdf"))
