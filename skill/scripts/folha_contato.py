"""Folha de contato para conferencia humana: todas as imagens de uma pasta em grade, com o nome da unidade
como legenda (a legenda existe SO na folha de conferencia; as imagens finais nao tem texto).
Uso: python folha_contato.py <pasta_png> <saida.jpg> [colunas]"""
import sys, glob, os, re, cv2, numpy as np
pasta, saida = sys.argv[1], sys.argv[2]; COLS = int(sys.argv[3]) if len(sys.argv) > 3 else 6
fs = sorted(glob.glob(os.path.join(pasta, '*.png')))
CEL = 420; tiles = []
for f in fs:
    im = cv2.imread(f, cv2.IMREAD_UNCHANGED)
    if im.shape[2] == 4:
        a = im[:, :, 3:] / 255.0
        chk = np.indices(im.shape[:2]).sum(0) // 12 % 2  # xadrez = transparente
        bg = np.where(chk[..., None] == 1, 235, 250)
        im = (im[:, :, :3] * a + bg * (1 - a)).astype(np.uint8)
    s = min((CEL - 10) / im.shape[1], (CEL - 50) / im.shape[0])
    im = cv2.resize(im, (int(im.shape[1] * s), int(im.shape[0] * s)), interpolation=cv2.INTER_AREA)
    t = np.full((CEL, CEL, 3), 255, np.uint8)
    t[5:5 + im.shape[0], (CEL - im.shape[1]) // 2:(CEL - im.shape[1]) // 2 + im.shape[1]] = im
    m = re.search(r'_(UN-[^_]+)_', os.path.basename(f)); nome = m.group(1) if m else os.path.basename(f)[:20]
    cv2.putText(t, nome, (10, CEL - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 200), 2)
    cv2.rectangle(t, (0, 0), (CEL - 1, CEL - 1), (180, 180, 180), 1)
    tiles.append(t)
rows = [np.hstack(tiles[i:i + COLS] + [np.full((CEL, CEL, 3), 255, np.uint8)] * (COLS - len(tiles[i:i + COLS]))) for i in range(0, len(tiles), COLS)]
cv2.imwrite(saida, np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 85]); print(saida, len(tiles))
