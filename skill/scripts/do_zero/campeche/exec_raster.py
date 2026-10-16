"""Rasteriza tracos/preenchimentos do executivo no quadro do legal (1 cm/px) com o registro exec2legal."""
import fitz, json, sys, os
import numpy as np, cv2
sys.path.insert(0, os.path.dirname(__file__))
from base import Z, W, H, CLIP
EX = '00_entradas/originais/executivo/CAMPECHESPOT-PE-ARQ-DCT-TER-XXX-012-R01.pdf'
q = json.load(open('03_trabalho/do_zero/exec2legal.json'))['q']
def M():
    s, th, tx, ty = q; c, sn = np.cos(th), np.sin(th)
    # pt exec -> pt legal -> px legal
    return np.array([[s * c * Z, -s * sn * Z, (tx - CLIP.x0) * Z], [s * sn * Z, s * c * Z, (ty - CLIP.y0) * Z]])
def rast(clip_ex=fitz.Rect(0, 0, 2700, 2384), k=4):
    """Renderiza o executivo (so tracos e preenchimentos, sem texto) a k px/pt e leva ao quadro do legal."""
    p = fitz.open(EX)[0]
    doc = fitz.open(); np_ = doc.new_page(width=p.rect.width, height=p.rect.height)
    np_.show_pdf_page(np_.rect, fitz.open(EX), 0)
    for b in np_.get_text('dict')['blocks']:
        for l in b.get('lines', []):
            for sp in l['spans']: np_.add_redact_annot(fitz.Rect(sp['bbox']))
    np_.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)
    pix = np_.get_pixmap(matrix=fitz.Matrix(k, k), clip=clip_ex)
    A = np.frombuffer(pix.samples, np.uint8).reshape(pix.h, pix.w, pix.n)[:, :, :3][:, :, ::-1].copy()
    T = M().copy(); T[:, :2] /= k
    T[:, 2] += T[:, :2] @ np.array([clip_ex.x0 * k, clip_ex.y0 * k])
    return cv2.warpAffine(A, T, (W, H), flags=cv2.INTER_AREA, borderValue=(255, 255, 255))
if __name__ == '__main__':
    R = rast()
    cv2.imwrite('03_trabalho/do_zero/exec_no_legal.png', R)
    from base import raster
    B = raster(); ov = R.copy(); ov[B] = (0, 0, 230)
    cv2.imwrite('03_trabalho/do_zero/exec_x_legal.jpg', cv2.resize(ov, None, fx=0.3, fy=0.3, interpolation=cv2.INTER_AREA))
    cv2.imwrite('03_trabalho/do_zero/exec_x_legal_core.jpg', ov[500:1700, 1300:2300])
