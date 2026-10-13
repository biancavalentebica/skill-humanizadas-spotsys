"""Prepara a humanizada (com texto) para o OCR do Windows: so os pixels escuros (texto), ampliada 2x."""
import sys, cv2, numpy as np
im = cv2.imread(sys.argv[1], cv2.IMREAD_UNCHANGED)
if im.shape[2] == 4:
    a = im[:, :, 3:] / 255.; im = (im[:, :, :3] * a + 255 * (1 - a)).astype(np.uint8)
g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
cv2.imwrite(sys.argv[2], cv2.resize(np.where(g < 60, 0, 255).astype(np.uint8), None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC))
