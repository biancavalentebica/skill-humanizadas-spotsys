"""Ajusta a entrada do terreo do Batel Spot a prancha aprovada R04 (Autodoc 2.1.c.a): acesso de veiculos com vaga
de embarque e desembarque (asfalto da avenida) e E.T. de 4,00 m2 como um unico ambiente em L. A escada de pedestres
fica como na humanizada (decisao da Rachel, 15/10/2026).

Geometria: lida da prancha rasterizada no referencial da TER-001 (05_qc/TERREO_pt2px_TER001.json; ver
03_trabalho/entrada/lift_grade.png e zlarga_s.jpg). Texturas: recortadas da propria humanizada (asfalto da avenida,
piso da recepcao, paredes). Sem IA e sem fonte externa.

Uso: py redesenha_entrada_terreo.py <entrada.png> <saida.png> [--dy 0] [--dx 0]
  TER-001 (com texto): dx=0 dy=0.  TER-000 (com estudo solar): dx=-2 dy=997.
"""
import argparse, json
import numpy as np, cv2
from PIL import Image
Image.MAX_IMAGE_PIXELS = None

ap = argparse.ArgumentParser()
ap.add_argument('entrada'); ap.add_argument('saida')
ap.add_argument('--dx', type=int, default=0); ap.add_argument('--dy', type=int, default=0)
a = ap.parse_args()
DX, DY = a.dx, a.dy
src = np.array(Image.open(a.entrada).convert('RGB'))
im = src.astype(np.float32)
H, W = im.shape[:2]
rng = np.random.default_rng(7)

def R(x0, y0, x1, y1):
    return slice(y0 + DY, y1 + DY), slice(x0 + DX, x1 + DX)

def ladrilha(pat, w, h):
    """Preenche w x h espelhando o recorte (sem emendas duras)."""
    t = np.concatenate([pat, pat[:, ::-1]], 1); t = np.concatenate([t, t[::-1]], 0)
    ny, nx = h // t.shape[0] + 1, w // t.shape[1] + 1
    return np.tile(t, (ny, nx, 1))[:h, :w]

def grao(pat, w, h, base=None, var=5.0, escala=60):
    """Superficie continua: cor media (ou base) + grao fino do recorte + variacao suave. Evita o espelhamento visivel."""
    g = pat - cv2.GaussianBlur(pat, (0, 0), 4)
    g = ladrilha(g, w, h)
    m = pat.reshape(-1, 3).mean(0) if base is None else np.asarray(base, np.float32)
    lf = cv2.GaussianBlur(rng.standard_normal((h, w)).astype(np.float32), (0, 0), escala)
    lf = lf / (lf.std() + 1e-6) * var
    return m + g + lf[..., None]

def mascara(shape_wh, desenha, pena=1.2):
    w, h = shape_wh
    m = np.zeros((h, w), np.uint8); desenha(m)
    m = m.astype(np.float32) / 255
    return cv2.GaussianBlur(m, (0, 0), pena) if pena else m

def compoe(x0, y0, img, m):
    """Mistura img (h,w,3) sobre im no canto (x0,y0) do referencial TER-001, com mascara m (0..1)."""
    h, w = m.shape
    sl = R(x0, y0, x0 + w, y0 + h)
    im[sl] = im[sl] * (1 - m[..., None]) + img * m[..., None]

def sombra(x0, y0, w, h, desenha, off=(10, 14), sig=12, forca=0.35):
    m = mascara((w, h), desenha, 0)
    m = np.roll(np.roll(m, off[1], 0), off[0], 1)
    m = cv2.GaussianBlur(m, (0, 0), sig) * forca
    sl = R(x0, y0, x0 + w, y0 + h)
    im[sl] *= (1 - m[..., None])

def parede(x0, y0, x1, y1, branco=7):
    """Parede no estilo da humanizada: faixa branca com miolo grafite."""
    w, h = x1 - x0, y1 - y0
    cor = np.full((h, w, 3), 252, np.float32)
    if w > h: cor[branco:h - branco, :] = 44
    else: cor[:, branco:w - branco] = 44
    m = np.ones((h, w), np.float32)
    compoe(x0, y0, cor, m)

def ret(c, x0, y0, x1, y1, v=255):
    cv2.rectangle(c, (x0, y0), (x1 - 1, y1 - 1), v, -1)

# ---------------------------------------------------------------- texturas (sempre do original, sem deslocamento DX/DY)
def recorte(x0, y0, x1, y1):
    return src[y0 + DY:y1 + DY, x0 + DX:x1 + DX].astype(np.float32)


# ---------------------------------------------------------------- zona da entrada (referencial TER-001)
# Decisao da Rachel (15/10): o acesso de pedestres fica como na humanizada (escada original); entra so a vaga de
# embarque e desembarque com o acesso de veiculos pela avenida, em asfalto recortado da propria avenida.
X0, Y0, X1, Y1 = 1380, 4200, 3905, 6000
w, h = X1 - X0, Y1 - Y0
orig = recorte(X0, Y0, X1, Y1)
asfalto = recorte(470, 4800, 840, 6200)             # Av. Visc. de Guarapuava, entre as faixas, sem marcas

# 1) acesso de veiculos (faixa entre as linhas da prancha, y 5165..5850) + area da vaga ate a divisa (y 5985)
def quilting(fonte, w, h, B=112, O=28, cand=80):
    """Monta w x h com blocos reais da fonte (Efros-Freeman): cada bloco e escolhido pela menor diferenca na
    sobreposicao e costurado pelo caminho de menor erro. So pixels reais, sem media nem ruido sintetico."""
    H_, W_ = fonte.shape[:2]; P = B - O
    nx, ny = (w - O) // P + 1, (h - O) // P + 1
    out = np.zeros((ny * P + O, nx * P + O, 3), np.float32)
    def corte(err):                      # caminho de menor erro de cima a baixo (err: h x o) -> mascara 0/1 (1 = bloco novo)
        hh, oo = err.shape; E = err.copy()
        for i in range(1, hh):
            l = np.r_[np.inf, E[i - 1, :-1]]; r = np.r_[E[i - 1, 1:], np.inf]
            E[i] += np.minimum(np.minimum(l, E[i - 1]), r)
        m = np.zeros((hh, oo), np.float32); j = int(np.argmin(E[-1]))
        for i in range(hh - 1, -1, -1):
            m[i, j:] = 1
            if i:
                js = [k for k in (j - 1, j, j + 1) if 0 <= k < oo]; j = js[int(np.argmin([E[i - 1, k] for k in js]))]
        return m
    for by in range(ny):
        for bx in range(nx):
            y0, x0 = by * P, bx * P
            alvo = out[y0:y0 + B, x0:x0 + B]
            best, berr = None, np.inf
            for _ in range(cand):
                sy, sx = rng.integers(0, H_ - B), rng.integers(0, W_ - B)
                blk = fonte[sy:sy + B, sx:sx + B]
                e = 0.0
                if bx: e += ((blk[:, :O] - alvo[:, :O]) ** 2).sum()
                if by: e += ((blk[:O] - alvo[:O]) ** 2).sum()
                if e < berr: best, berr = blk, e
            m = np.ones((B, B), np.float32)
            if bx: m[:, :O] = np.minimum(m[:, :O], corte(((best[:, :O] - alvo[:, :O]) ** 2).sum(2)))
            if by: m[:O, :] = np.minimum(m[:O, :], corte(((best[:O] - alvo[:O]) ** 2).sum(2).T).T)
            m = cv2.GaussianBlur(m, (0, 0), 1.0) if (bx or by) else m
            out[y0:y0 + B, x0:x0 + B] = alvo * (1 - m[..., None]) + best * m[..., None]
    return out[:h, :w]

# Rachel (15/10): toda a area entre a calcada, o passeio, o muro da direita e a divisa do fundo e pavimentada, sem jardim.
def m_acesso(c):
    ret(c, 1390 - X0, 5006 - Y0, 2200 - X0, 5986 - Y0)                          # abaixo do passeio (sem muro)
    ret(c, 2200 - X0, 5042 - Y0, 3880 - X0, 5986 - Y0)                          # abaixo do muro do jardim
ma = mascara((w, h), m_acesso, 1.0)
AX0, AY0 = 1390, 5000
pav = np.zeros((h, w, 3), np.float32)
pav[AY0 - Y0:, AX0 - X0:] = quilting(asfalto, X1 - AX0, Y1 - AY0)
compoe(X0, Y0, pav, ma)
# meio-fio: a guia real da avenida (faixa clara entre o asfalto e a calcada, x 963..993), girada quando horizontal
guia = recorte(963, 4400, 993, 6200)                                             # 30 px de largura, vertical
def meiofio(x0, y0, x1, y1):
    if (x1 - x0) > (y1 - y0):                                                    # horizontal
        g = np.rot90(guia).copy()                                                # 30 x 1800
        reps = (x1 - x0) // g.shape[1] + 1
        g = np.concatenate([g] * reps, 1)[:, :x1 - x0]
        g = cv2.resize(g, (x1 - x0, y1 - y0), interpolation=cv2.INTER_AREA)
    else:
        reps = (y1 - y0) // guia.shape[0] + 1
        g = np.concatenate([guia] * reps, 0)[:y1 - y0]
        g = cv2.resize(g, (x1 - x0, y1 - y0), interpolation=cv2.INTER_AREA)
    compoe(x0, y0, g, mascara((x1 - x0, y1 - y0), lambda c: ret(c, 0, 0, x1 - x0, y1 - y0), 0.8))
# borda do passeio (onde nao ha muro): meio-fio real; sombra curta do muro e do meio-fio sobre o asfalto
sombra(1390, 5000, 2490, 80, lambda c: (ret(c, 0, 0, 810, 22), ret(c, 810, 0, 2490, 42)), off=(0, 9), sig=7, forca=0.30)
meiofio(1390, 4996, 2200, 5020)
# ponta do muro do jardim, que antes encontrava o muro vertical (retirado): fecha com a face branca
compoe(2186, 5004, np.full((36, 10, 3), 250, np.float32), np.ones((36, 10), np.float32))
# divisa a direita (linha dupla da prancha): o muro real do jardim (x 2186..2232), repetido na vertical
muro = recorte(2186, 5250, 2232, 5800)
mur = np.concatenate([muro, muro[::-1], muro], 0)[:5990 - 5030]
sombra(3857, 5030, 46, 960, lambda c: c.__setitem__(slice(None), 255), off=(10, 6), sig=8, forca=0.25)
compoe(3857, 5030, mur, mascara((46, 960), lambda c: ret(c, 0, 0, 46, 960), 0.8))
# 2) vaga: tracejado com a tinta real da faixa da avenida (x 424..440), sobre o asfalto
tinta = recorte(424, 4400, 440, 6200)                                            # 16 px de largura, vertical
def tracejado(x0, y0, x1, y1, esp=16, traco=70, vao=40):
    horiz = (y1 - y0) < (x1 - x0)
    L = (x1 - x0) if horiz else (y1 - y0)
    p, k = 0, 0
    while p < L:
        q = min(p + traco, L)
        t = tinta[k * 97 % 1500:k * 97 % 1500 + (q - p)]                           # trecho diferente da faixa a cada traco
        if horiz: t = np.rot90(t).copy(); bx0, by0 = x0 + p, y0
        else: bx0, by0 = x0, y0 + p
        hh, ww = t.shape[:2]
        compoe(bx0, by0, t, mascara((ww, hh), lambda c: ret(c, 0, 0, ww, hh), 0.7) * 0.95)
        p = q + vao; k += 1
VX0, VY0, VX1, VY1 = 2640, 5228, 3850, 5815
tracejado(VX0, VY0, VX1, VY0 + 16); tracejado(VX0, VY1 - 16, VX1, VY1)
tracejado(VX0, VY0, VX0 + 16, VY1); tracejado(VX1 - 16, VY0, VX1, VY1)

# 3) escada original: desce do muro do jardim direto no pavimento (entre os degraus aparece o asfalto)
ex0, ey0, ex1, ey1 = 3136, 5040, 3500, 5310
eo = recorte(ex0, ey0, ex1, ey1)
ehsv = cv2.cvtColor(eo.astype(np.uint8), cv2.COLOR_RGB2HSV)
me = ((ehsv[..., 2] < 80) & (ehsv[..., 1] < 90)).astype(np.uint8)
me = cv2.morphologyEx(me, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
me[:, :4] = 0; me[:, -10:] = 0                                                   # so a escada (x 3142..3490)
sombra(ex0, ey0, ex1 - ex0, ey1 - ey0, lambda c: c.__setitem__(slice(None), me * 255), off=(8, 10), sig=8, forca=0.35)
compoe(ex0, ey0, eo, cv2.GaussianBlur(me.astype(np.float32), (0, 0), 0.8))

# ---------------------------------------------------------------- E.T. em L (4,00 m2): um unico ambiente
def piso_por_linha(x0, y0, x1, y1, desenha):
    """Refaz o piso nas areas marcadas: em cada linha, interpola entre o piso a esquerda e a direita da mascara
    (a luz e as sombras diagonais da imagem continuam) e soma o grao fino do proprio piso."""
    reg = im[R(x0, y0, x1, y1)].copy()
    m = np.zeros(reg.shape[:2], np.uint8); desenha(m)
    pat = recorte(4960, 4760, 5120, 4900)
    g = ladrilha(pat - cv2.GaussianBlur(pat, (0, 0), 3), x1 - x0, y1 - y0)
    for j in range(reg.shape[0]):
        xs = np.nonzero(m[j])[0]
        if not len(xs): continue
        a_, b_ = xs[0] - 3, xs[-1] + 3
        ca, cb = reg[j, max(a_ - 4, 0):a_ + 1].mean(0), reg[j, b_:b_ + 5].mean(0)
        t = np.linspace(0, 1, b_ - a_ + 1)[:, None]
        reg[j, a_:b_ + 1] = ca * (1 - t) + cb * t + g[j, a_:b_ + 1] * 0.8
    im[R(x0, y0, x1, y1)] = reg

EX0, EY0_ = 5150, 4580
def m_et(c):
    ret(c, 5196 - EX0, 4622 - EY0_, 5262 - EX0, 4990 - EY0_)   # divisoria entre os dois comodos
    ret(c, 5196 - EX0, 4646 - EY0_, 5294 - EX0, 4714 - EY0_)   # dente da divisoria (porta do 2o comodo)
    ret(c, 5196 - EX0, 4690 - EY0_, 5314 - EX0, 4892 - EY0_)   # folha de porta + sombra do 2o comodo
piso_por_linha(EX0, EY0_, 5460, 5010, m_et)
# junta vertical do piso que passava sob a folha de porta
im[R(5304, 4714, 5306, 4990)] *= 0.93
# parede inferior: refaz o encontro onde a divisoria chegava
im[R(5190, 4984, 5320, 5040)] = np.repeat(recorte(5150, 4984, 5151, 5040), 130, 1)

def paredes(brancos, miolos, cor_miolo=46):
    """Paredes como conjunto: primeiro a uniao das faixas brancas, depois os miolos (os encontros ficam limpos)."""
    for (x0, y0, x1, y1) in brancos:
        im[R(x0, y0, x1, y1)] = 252
    for (x0, y0, x1, y1) in miolos:
        im[R(x0, y0, x1, y1)] = cor_miolo
    xs = [r[0] for r in brancos] + [r[2] for r in brancos]; ys = [r[1] for r in brancos] + [r[3] for r in brancos]
    x0, y0, x1, y1 = min(xs) - 4, min(ys) - 4, max(xs) + 4, max(ys) + 4
    im[R(x0, y0, x1, y1)] = cv2.GaussianBlur(im[R(x0, y0, x1, y1)], (0, 0), 0.7)
# quina do L na posicao do aprovado (x 5272): topo do braco esquerdo, trecho vertical, topo do braco direito
paredes(brancos=[(5200, 4594, 5297, 4622), (5247, 4594, 5297, 4706), (5247, 4656, 5466, 4707)],
        miolos=[(5266, 4603, 5281, 4690), (5266, 4675, 5466, 4690)])
im[R(5190, 4603, 5266, 4612)] = np.repeat(recorte(5180, 4603, 5181, 4612), 76, 1)                   # miolo fino do topo, como o existente

# ---------------------------------------------------------------- WC PCD da recepcao: nao existe mais (Rachel, 15/10)
# No aprovado R04 o trecho e circulacao da recepcao; fica so o shaft (VAZIO 0,59 m2) junto a fachada.
GX0, GY0, GP = 4189.0, 4558.0, 187.5                                             # grade do porcelanato (juntas)
cel = recorte(4189, 4371, 4377, 4559)                                            # uma placa limpa da recepcao (original)
jx = jy = 0                                                                      # a placa recortada ja comeca numa junta da grade
hp = cel / cv2.GaussianBlur(cel, (0, 0), 25)                                     # juntas e grao da placa real, sem o reflexo
WX0, WY0, WX1, WY1 = 4398, 4560, 4882, 4989
ys, xs = np.mgrid[WY0:WY1, WX0:WX1]
sx = (jx + np.floor((xs - GX0) % GP)).astype(int) % cel.shape[1]
sy = (jy + np.floor((ys - GY0) % GP)).astype(int) % cel.shape[0]
tex = hp[sy, sx]
# luz: a da recepcao logo abaixo do letreiro (por coluna), escurecendo de leve ate a fachada. A faixa escura a
# esquerda era sombra da parede do WC, que deixa de existir.
topo = cv2.GaussianBlur(recorte(WX0, 4528, WX1, 4553).mean(0)[None], (0, 0), sigmaX=30, sigmaY=0)[0]   # luz junto a junta
base = recorte(4189, 4371, 4377, 4559).reshape(-1, 3).mean(0)                      # tom medio de uma placa da recepcao
t = (np.arange(WY1 - WY0) / (WY1 - WY0))[:, None, None]
luz = topo[None] * (1 - np.minimum(t * 3, 1)) + base[None, None] * 0.98 * np.minimum(t * 3, 1)
luz = luz * (1 - 0.04 * t)
piso_wc = luz * tex
dy_ = (ys - WY0).astype(np.float32); dfa = (WY1 - ys).astype(np.float32); dfd = (WX1 - xs).astype(np.float32)
piso_wc *= (1 - 0.05 * np.exp(-dfa / 18) - 0.04 * np.exp(-dfd / 18))[..., None]   # contato com fachada e parede do E.T.
mw = np.zeros((WY1 - WY0, WX1 - WX0), np.uint8)
mw[:4902 - WY0, :] = 1                                                           # parede esquerda (acima do shaft) + interior
mw[:, 4453 - WX0:] = 1
mw[4902 - WY0:, :4416 - WX0] = 0                                                # nao invade o shaft
mw = cv2.GaussianBlur(mw.astype(np.float32), (0, 0), 1.2)
fb = np.minimum(np.minimum(np.arange(mw.shape[0])[:, None] / 6.0, np.arange(mw.shape[1])[None] / 18.0), 1)   # borda suave em cima e a esquerda
mw *= fb
im[R(WX0, WY0, WX1, WY1)] = im[R(WX0, WY0, WX1, WY1)] * (1 - mw[..., None]) + piso_wc * mw[..., None]
# shaft: o topo (parede horizontal) segue ate a quina; a parede vertical abaixo fica como estava
im[R(4416, 4900, 4456, 4936)] = np.repeat(recorte(4300, 4900, 4301, 4936), 40, 1)
im[R(4450, 4904, 4457, 4933)] = 250
# parede do E.T. (antiga parede direita do WC): fecha a ponta de cima, onde chegava a parede do WC
im[R(4879, 4594, 4885, 4624)] = 250

out = np.clip(im, 0, 255).astype(np.uint8)
Image.fromarray(out).save(a.saida, optimize=False)
json.dump(dict(entrada=a.entrada, dx=DX, dy=DY, referencia='BATELSPOT-PL-ARQ-DCT-GER-ASS-001-R04 (Autodoc 2.1.c.a)',
               itens=['escada de pedestres original mantida (chega ao acesso)',
                      'area toda pavimentada em asfalto real da avenida x1390-3880 y5006-5986 (sem jardim) + vaga x2640-3850 y5228-5815',
                      'WC PCD retirado: area volta a recepcao (piso na grade do porcelanato), shaft mantido', 'E.T. em L: divisoria removida (inpaint do piso), quina em x5272 (parede x5247-5297), topo do braco direito em y4654-4708']),
          open(a.saida.rsplit('.', 1)[0] + '_entrada_log.json', 'w'), indent=1, ensure_ascii=False)
print('ok', a.saida)
