"""Motor de desenho da humanizada do zero: pisos, paredes (perfil real), vidros, portas, escadas do R06 e objetos
do kit colocados no referencial de cada unidade (u = a partir do vidro do garden, v = a partir da parede da escada)."""
import cv2, numpy as np
import kit
OCUPADO = None   # mascara (H, W) dos objetos ja colocados; criada pelo gerador


def poe(img, sp, x, y, a_extra=None):
    """Cola o sprite com o canto superior esquerdo em (x, y) da imagem, usando a mascara."""
    h, w = sp.img.shape[:2]; x, y = int(round(x)), int(round(y))
    y0, x0 = max(0, y), max(0, x); y1, x1 = min(img.shape[0], y + h), min(img.shape[1], x + w)
    if y1 <= y0 or x1 <= x0: return
    s = sp.img[y0 - y:y1 - y, x0 - x:x1 - x].astype(np.float32); a = sp.alfa[y0 - y:y1 - y, x0 - x:x1 - x, None]
    if a_extra is not None: a = a * a_extra
    reg = img[y0:y1, x0:x1].astype(np.float32)
    img[y0:y1, x0:x1] = (s * a + reg * (1 - a)).astype(np.uint8)


def orienta(sp, dc, dr):
    """Gira/espelha o sprite para que +coluna aponte para dc e +linha para dr (vetores da imagem, eixo x/y)."""
    im, al = sp.img, sp.alfa
    if dc[0] == 0:
        im, al = im.swapaxes(0, 1), al.swapaxes(0, 1); dc, dr = dr, dc
    if dc[0] < 0: im, al = im[:, ::-1], al[:, ::-1]
    if dr[1] < 0: im, al = im[::-1], al[::-1]
    return kit.Sprite(np.ascontiguousarray(im), np.ascontiguousarray(al))


class Quadro:
    """Referencial local de uma unidade. O = canto (vidro do garden x parede da escada), eu/ev = eixos da imagem."""
    def __init__(self, O, eu, ev):
        self.O = np.array(O, float); self.eu = np.array(eu, float); self.ev = np.array(ev, float)

    def p(self, u, v): return self.O + u * self.eu + v * self.ev

    def caixa(self, u0, v0, u1, v1):
        a, b = self.p(u0, v0), self.p(u1, v1)
        return min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])

    def eixo(self, nome):
        return {'+u': self.eu, '-u': -self.eu, '+v': self.ev, '-v': -self.ev}[nome]

    def objeto(self, img, sp, u0, v0, col, lin, ocupa=True):
        """Sprite com +coluna ao longo de `col` e +linha ao longo de `lin` ('+u','-u','+v','-v'); (u0, v0) = canto
        mais proximo da origem da caixa ocupada no referencial local."""
        dc, dr = self.eixo(col).astype(int), self.eixo(lin).astype(int)
        o = orienta(sp, tuple(dc), tuple(dr))
        h, w = sp.img.shape[:2]
        du = {'+u': w, '-u': w, '+v': 0, '-v': 0}[col] + {'+u': h, '-u': h, '+v': 0, '-v': 0}[lin]
        dv = {'+v': w, '-v': w, '+u': 0, '-u': 0}[col] + {'+v': h, '-v': h, '+u': 0, '-u': 0}[lin]
        x0, y0, x1, y1 = self.caixa(u0, v0, u0 + du, v0 + dv)
        poe(img, o, x0, y0)
        if ocupa: OCUPADO[int(y0):int(y1), int(x0):int(x1)] |= o.alfa[:int(y1) - int(y0), :int(x1) - int(x0)] > 0.3
        return (u0, v0, u0 + du, v0 + dv)


# ---------------- paredes com o perfil real do lancamento ----------------
def paredes(img, m, cor_borda=(57, 58, 57), filete=(245, 246, 245), trans=(150, 152, 150)):
    m = m.astype(np.uint8)
    din = cv2.distanceTransform(m, cv2.DIST_L2, 3); dout = cv2.distanceTransform(1 - m, cv2.DIST_L2, 3)
    ys, xs = np.nonzero(m); M = kit.MIOLO; fh, fw = M.shape[:2]
    img[ys, xs] = M[ys % fh, xs % fw]
    img[(m > 0) & (din <= 1.5)] = cor_borda
    a1 = (m == 0) & (dout <= 1.5); a2 = (m == 0) & (dout > 1.5) & (dout <= 3.4); a3 = (m == 0) & (dout > 3.4) & (dout <= 7)
    img[a1] = trans; img[a2] = filete
    img[a3] = (img[a3] * 0.86).astype(np.uint8)


def muro(img, m):
    """Muro baixo entre gardens (cinza claro com filete), como os divisores de garden do lancamento."""
    m = m.astype(np.uint8)
    din = cv2.distanceTransform(m, cv2.DIST_L2, 3)
    img[m > 0] = (214, 216, 216); img[(m > 0) & (din <= 1.5)] = (160, 162, 162)
    dout = cv2.distanceTransform(1 - m, cv2.DIST_L2, 3); a3 = (m == 0) & (dout <= 6)
    img[a3] = (img[a3] * 0.88).astype(np.uint8)


def vidro(img, x0, y0, x1, y1):
    """Caixilho do garden (recorte real) ao longo de um trecho horizontal ou vertical."""
    V = kit.VIDRO
    if abs(x1 - x0) >= abs(y1 - y0):
        L = int(abs(x1 - x0)); t = np.tile(V, (1, L // V.shape[1] + 2, 1))[:, :L]
        y = int(round(y0 - V.shape[0] / 2)); img[y:y + V.shape[0], int(min(x0, x1)):int(min(x0, x1)) + L] = t
    else:
        L = int(abs(y1 - y0)); Vt = np.rot90(V); t = np.tile(Vt, (L // Vt.shape[0] + 2, 1, 1))[:L]
        x = int(round(x0 - Vt.shape[1] / 2)); img[int(min(y0, y1)):int(min(y0, y1)) + L, x:x + Vt.shape[1]] = t


def porta(img, paredes_m, x0, y0, x1, y1, esp=24):
    """Abre o vao na parede (mascara) e cola a porta do lancamento no vao (trecho horizontal ou vertical)."""
    P = kit.PORTA
    if abs(x1 - x0) >= abs(y1 - y0):
        L = int(abs(x1 - x0)); xa = int(min(x0, x1)); yc = int(round(y0))
        paredes_m[yc - esp // 2:yc + esp // 2 + 1, xa:xa + L] = False
        sp = cv2.resize(P.img, (L, P.img.shape[0]), interpolation=cv2.INTER_AREA)
        return ('h', xa, yc - sp.shape[0] // 2, sp)
    L = int(abs(y1 - y0)); ya = int(min(y0, y1)); xc = int(round(x0))
    paredes_m[ya:ya + L, xc - esp // 2:xc + esp // 2 + 1] = False
    sp = cv2.resize(np.rot90(P.img).copy(), (P.img.shape[0], L), interpolation=cv2.INTER_AREA)
    return ('v', xc - sp.shape[1] // 2, ya, sp)


# ---------------- escada (pegada do R06, degraus reais do lancamento) ----------------
def escada(img, mask, eixo_lance, sentido_canto, degrau_cm=27):
    """Desenha a escada em Γ do R06. eixo_lance: 'y' se o lance longo corre na vertical, 'x' se na horizontal.
    sentido_canto: canto do leque (lado do garden x parede) como (sx, sy) = -1/+1 da bbox (ex.: (-1,-1) = topo-esquerda)."""
    ys, xs = np.nonzero(mask); x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    D = kit.DEGRAU   # degrau com o comprimento na horizontal
    sub = img[y0:y1, x0:x1]; m = mask[y0:y1, x0:x1]
    h, w = m.shape
    # largura do lance longo = largura da pegada longe do canto
    if eixo_lance == 'y':
        linha = m[h // 2]; larg = int(linha.sum())
        tread = cv2.resize(D, (larg, degrau_cm), interpolation=cv2.INTER_CUBIC)
        lance = np.tile(tread, (h // degrau_cm + 2, 1, 1))[:h]
        xa = 0 if sentido_canto[0] < 0 else w - larg
        fill = np.zeros_like(sub); fill[:, xa:xa + larg] = lance
        # barra (lance curto, junto ao garden): degraus verticais
        ycanto = 0 if sentido_canto[1] < 0 else h
        col = m[(5 if sentido_canto[1] < 0 else h - 6)]; barra_w = int(col.sum())
        hb = int(m[:, (w - 6 if sentido_canto[0] < 0 else 5)].sum()) if barra_w > larg + 20 else 0
        if hb:
            tv = cv2.resize(np.rot90(D).copy(), (degrau_cm, hb), interpolation=cv2.INTER_CUBIC)
            barra = np.tile(tv, (1, w // degrau_cm + 2, 1))[:, :w]
            yb = 0 if sentido_canto[1] < 0 else h - hb
            fill[yb:yb + hb] = np.where(np.arange(w)[None, :, None] >= 0, barra, 0)
            lq = cv2.resize(kit.LEQUE, (larg, hb), interpolation=cv2.INTER_CUBIC)
            if sentido_canto[0] > 0: lq = lq[:, ::-1]
            if sentido_canto[1] > 0: lq = lq[::-1]
            fill[yb:yb + hb, xa:xa + larg] = lq
    else:
        linha = m[:, w // 2]; larg = int(linha.sum())
        tread = cv2.resize(np.rot90(D).copy(), (degrau_cm, larg), interpolation=cv2.INTER_CUBIC)
        lance = np.tile(tread, (1, w // degrau_cm + 2, 1))[:, :w]
        ya = 0 if sentido_canto[1] < 0 else h - larg
        fill = np.zeros_like(sub); fill[ya:ya + larg] = lance
        hb = int(m[:, (5 if sentido_canto[0] < 0 else w - 6)].sum())
        wb = int(m[(h - 6 if sentido_canto[1] < 0 else 5)].sum()) if hb > larg + 20 else 0
        if wb:
            th = cv2.resize(D, (wb, degrau_cm), interpolation=cv2.INTER_CUBIC)
            barra = np.tile(th, (h // degrau_cm + 2, 1, 1))[:h]
            xb = 0 if sentido_canto[0] < 0 else w - wb
            fill[:, xb:xb + wb] = barra
            lq = cv2.resize(np.rot90(kit.LEQUE).copy(), (wb, larg), interpolation=cv2.INTER_CUBIC)
            if sentido_canto[0] > 0: lq = lq[:, ::-1]
            if sentido_canto[1] > 0: lq = lq[::-1]
            fill[ya:ya + larg, xb:xb + wb] = lq
    sub[m] = fill[m]
    # contorno escuro da pegada (como o guarda-corpo/espelho do lancamento)
    cs, _ = cv2.findContours(m.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    cv2.drawContours(sub, cs, -1, (70, 72, 72), 2)
