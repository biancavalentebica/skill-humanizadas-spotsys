"""Recorte ampliado com regua em px da imagem de origem. Uso: py regua.py img x0 y0 x1 y1 saida fator [passo]"""
import sys, cv2
a = cv2.imread(sys.argv[1], -1)
if a.shape[2] == 4:
    al = a[:, :, 3:4] / 255.0; a = (a[:, :, :3] * al + 255 * (1 - al)).astype('uint8')
x0, y0, x1, y1 = [int(v) for v in sys.argv[2:6]]; f = float(sys.argv[7]); p = int(sys.argv[8]) if len(sys.argv) > 8 else 10
c = cv2.resize(a[y0:y1, x0:x1], None, fx=f, fy=f, interpolation=cv2.INTER_NEAREST)
for x in range(0, x1 - x0, p):
    cv2.line(c, (int(x * f), 0), (int(x * f), 12 if x % (5 * p) == 0 else 5), (255, 0, 0), 1)
    if x % (5 * p) == 0: cv2.putText(c, str(x0 + x), (int(x * f) + 2, 22), 0, 0.38, (255, 0, 0), 1)
for y in range(0, y1 - y0, p):
    cv2.line(c, (0, int(y * f)), (12 if y % (5 * p) == 0 else 5, int(y * f)), (255, 0, 0), 1)
    if y % (5 * p) == 0: cv2.putText(c, str(y0 + y), (14, int(y * f) + 4), 0, 0.38, (255, 0, 0), 1)
cv2.imwrite(sys.argv[6], c)
