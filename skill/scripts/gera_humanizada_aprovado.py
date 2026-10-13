"""FASE 1: gera a planta humanizada do pavimento NA GEOMETRIA DO PROJETO APROVADO (Autodoc).

O projeto legal aprovado traz o contorno de cada unidade e area (sem paredes internas nem mobiliario).
A planta gerada combina:
  - geometria e proporcao do APROVADO: o quadro de saida e o proprio sistema de coordenadas da prancha
    (escala fixa em cm/px); as divisas do aprovado viram paredes onde a humanizada de referencia nao tem parede;
  - interiores (banheiro, cozinha, mobiliario, piso) da humanizada de referencia (ex.: humanizada 2026 sem texto),
    reamostrada para a geometria do aprovado pela transformacao registrada (corrige escala e desproporcao);
  - unidades marcadas como divergentes: interior removido (piso neutro + paredes do aprovado) e sinalizadas.

Uso: python gera_humanizada_aprovado.py <aprovado.pdf> <celulas.json> <registro_transform.json> <humanizada_ref.png>
                                        <saida.png> [--divergentes 505,506,507] [--cm-px 0.9]
Saidas: <saida>.png (RGBA), <saida>_paredes_aprovado.png (debug: vermelho = parede desenhada pelo aprovado),
        <saida>_log.json
"""
import sys, json, argparse
import fitz, cv2, numpy as np

ap = argparse.ArgumentParser()
for k in ('pdf', 'celulas', 'registro', 'referencia', 'saida'): ap.add_argument(k)
ap.add_argument('--divergentes', default='')
ap.add_argument('--cm-px', type=float, default=0.9, help='resolucao da saida em cm reais por pixel')
ap.add_argument('--escala', type=float, default=100)
ap.add_argument('--parede-cm', type=float, default=14, help='espessura das divisas desenhadas pelo aprovado')
ap.add_argument('--vao-max-cm', type=float, default=120, help='trechos sem parede ate este comprimento sao vaos (portas) e ficam abertos')
a = ap.parse_args()

C = json.load(open(a.celulas, encoding='utf-8')); R = json.load(open(a.registro, encoding='utf-8'))
clip = fitz.Rect(*C['clip_pt']); esc_cel = C['esc']
CM_POR_PT = 2.54 / 72 * a.escala
ESC = CM_POR_PT / a.cm_px                      # px de saida por pt da prancha
W, H = int(clip.width * ESC), int(clip.height * ESC)
cmpx = a.cm_px
px = lambda cm: max(1, int(round(cm / cmpx)))

# 1) classes de area a partir da prancha aprovada (manchas coloridas)
pg = fitz.open(a.pdf)[C['pagina'] - 1]
pix = pg.get_pixmap(matrix=fitz.Matrix(ESC, ESC), clip=clip)
pim = np.frombuffer(pix.samples, np.uint8).reshape(pix.h, pix.w, pix.n)[:, :, :3][:, :, ::-1].astype(int)
pim = cv2.resize(pim.astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST).astype(int)
b, g, r = pim[:, :, 0], pim[:, :, 1], pim[:, :, 2]
mx, mn = np.maximum(np.maximum(b, g), r), np.minimum(np.minimum(b, g), r)
area = ((mx > 150) & (mx - mn > 12) & (mn > 60)) | ((abs(b - 240) <= 4) & (abs(g - 240) <= 4) & (abs(r - 240) <= 4))
area = cv2.morphologyEx(area.astype(np.uint8), cv2.MORPH_OPEN, np.ones((px(30), px(30)), np.uint8))  # tira cotas e tracejados
area = cv2.morphologyEx(area, cv2.MORPH_CLOSE, np.ones((px(20), px(20)), np.uint8))
nf, lf, sf, _ = cv2.connectedComponentsWithStats(area, 8)
predio = (lf == 1 + int(np.argmax(sf[1:, 4]))).astype(np.uint8) if nf > 1 else area
cs_p, _ = cv2.findContours(predio, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
predio = np.zeros_like(predio); cv2.drawContours(predio, cs_p, -1, 1, -1)   # inclui nucleo (escada/elevadores) e vazios

# 2) humanizada de referencia reamostrada para a geometria do aprovado
ref = cv2.imread(a.referencia, cv2.IMREAD_UNCHANGED)
if ref.shape[2] == 3: ref = np.dstack([ref, np.full(ref.shape[:2], 255, np.uint8)])
A = np.vstack([np.array(R['A_pdfpx_para_img']), [0, 0, 1]])          # pdf px (esc_cel) -> imagem ref
S = np.diag([esc_cel / ESC, esc_cel / ESC, 1.0])                        # saida -> pdf px (esc_cel)
M = (A @ S)[:2].astype(np.float32)                                      # saida -> imagem ref
base = cv2.warpAffine(ref, M, (W, H), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255, 0))

# 3) poligonos das unidades no quadro de saida
def poly_px(poly):
    return np.array([[(x - clip.x0) * ESC, (y - clip.y0) * ESC] for x, y in poly], np.int32)
unid = {}
for code, cel in C['celulas'].items():
    m = np.zeros((H, W), np.uint8)
    for poly in cel.get('poligonos_pt', []):
        cv2.fillPoly(m, [poly_px(poly)], 255)
    if m.any(): unid[code] = m

# 4) unidades divergentes: interior removido, piso neutro
divergentes = [c.strip() for c in a.divergentes.split(',') if c.strip()]
cinza_piso = np.array([226, 229, 232, 255], np.uint8)
creme = (abs(g - 232) < 15) & (abs(r - 254) < 15) & (abs(b - 200) < 20)          # garden no aprovado
div_union = np.zeros((H, W), bool)
for code in divergentes:
    if code in unid: div_union |= unid[code] > 0
# textura de deck: maior quadrado de garden fora das unidades divergentes
textura = None
cand = (creme & ~cv2.dilate(div_union.astype(np.uint8), np.ones((px(40),) * 2, np.uint8)).astype(bool) & (base[:, :, 3] > 0)).astype(np.uint8)
if cand.any():
    dt = cv2.distanceTransform(cand, cv2.DIST_L2, 5); _, rmax, _, (cx, cy) = cv2.minMaxLoc(dt)
    k = int(rmax * 1.3)
    if k > 20: textura = base[cy - k // 2:cy + k // 2, cx - k // 2:cx + k // 2].copy()
for code in divergentes:
    if code in unid:
        m = cv2.erode(unid[code], np.ones((3, 3), np.uint8)) > 0
        base[m] = cinza_piso
        mg = m & (cv2.morphologyEx(creme.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((px(60), px(60)), np.uint8)) > 0)
        if textura is not None and mg.any():
            th, tw = textura.shape[:2]
            tile = np.tile(textura, (H // th + 1, W // tw + 1, 1))[:H, :W]
            base[mg] = tile[mg]

# 5) paredes do aprovado: so DIVISAS (unidade x unidade e unidade x area comum); bordas externas
#    (fachada, guarda-corpo de sacada/garden) nao viram parede
linhas = np.zeros((H, W), np.uint8)
t = px(a.parede_cm)
todas = np.zeros((H, W), np.uint8)
for m in unid.values(): todas |= m
comum = ((predio > 0) & (todas == 0)).astype(np.uint8) * 255
for code, m in unid.items():
    cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    borda = np.zeros((H, W), np.uint8); cv2.drawContours(borda, cs, -1, 255, t)
    outros = (todas > 0) & (m == 0) | (comum > 0)
    viz = cv2.dilate(outros.astype(np.uint8), np.ones((t * 2 + 1,) * 2, np.uint8)) > 0
    linhas[(borda > 0) & viz] = 255
gb = cv2.cvtColor(base[:, :, :3], cv2.COLOR_BGR2GRAY)
parede_ref = ((gb < 60) & (base[:, :, 3] > 0)).astype(np.uint8)
coberto = cv2.dilate(parede_ref, np.ones((px(16) * 2 + 1,) * 2, np.uint8)) > 0
falta = ((linhas > 0) & ~coberto).astype(np.uint8)
# vaos curtos (portas) ficam abertos; trechos longos sem parede recebem parede do aprovado
n, lab, st, _ = cv2.connectedComponentsWithStats(falta, 8)
desenhar = np.zeros((H, W), bool)
div_masks = [unid[c] > 0 for c in divergentes if c in unid]
div_any = np.any(div_masks, axis=0) if div_masks else np.zeros((H, W), bool)
div_borda = cv2.dilate(div_any.astype(np.uint8), np.ones((t * 2 + 1,) * 2, np.uint8)) > 0
for i in range(1, n):
    comp = lab == i
    comprimento_cm = max(st[i, 2], st[i, 3]) * cmpx
    if comprimento_cm > a.vao_max_cm or (comp & div_borda).any():
        desenhar |= comp
base[desenhar] = (34, 34, 34, 255)

# 6) recorte ao predio (fora do predio: transparente)
fora = cv2.dilate(predio, np.ones((px(150), px(150)), np.uint8)) == 0
base[fora] = (255, 255, 255, 0)
cv2.imwrite(a.saida, base)

dbg = base[:, :, :3].copy(); dbg[desenhar] = (0, 0, 255)
for code in divergentes:
    if code in unid:
        cs, _ = cv2.findContours(unid[code], cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        cv2.drawContours(dbg, cs, -1, (0, 140, 255), 4)
cv2.imwrite(a.saida.rsplit('.', 1)[0] + '_paredes_aprovado.png', dbg)
log = dict(pagina=C['pagina'], referencia=a.referencia, cm_por_px=cmpx, largura=W, altura=H,
           anisotropia_corrigida=R.get('anisotropia'), unidades=len(unid), divergentes_sem_interior=divergentes,
           metros_de_parede_desenhados_pelo_aprovado=round(float(desenhar.sum()) * cmpx / max(1, t) / 100, 1))
json.dump(log, open(a.saida.rsplit('.', 1)[0] + '_log.json', 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print(json.dumps(log, ensure_ascii=False))
