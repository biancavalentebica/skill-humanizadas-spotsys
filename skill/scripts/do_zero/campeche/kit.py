"""Kit de objetos e texturas REAIS da humanizada de lancamento do Campeche Spot (terreo, sem texto).
Lancamento a 0,476 cm/px; planta nova a 0,5 cm/px (fator 0,952). Unidade canonica: garden embaixo, porta em cima."""
import cv2, numpy as np
LS = cv2.imread('03_trabalho/lanc_sem_texto.png', cv2.IMREAD_UNCHANGED)
if LS.shape[2] == 4:
    a = LS[:, :, 3:4] / 255.0; LS = (LS[:, :, :3] * a + 255 * (1 - a)).astype(np.uint8)
K = 0.476 / 0.5


def rc(x0, y0, x1, y1, k=K):
    return cv2.resize(LS[y0:y1, x0:x1], None, fx=k, fy=k, interpolation=cv2.INTER_AREA)


BANHO = rc(4990, 3910, 5352, 4420)          # chuveiro, vaso e bancada com cuba + divisorias (canto do fundo, lado esquerdo)
COZINHA = rc(5528, 3925, 5700, 4305)         # copa: cuba + base escura (fundo, lado direito)
BANCADA = rc(5718, 4335, 5866, 5010)[:, ::-1].copy()   # bancada de madeira + 2 cadeiras (unidade 109, espelhada: parede a direita)
SOFA_ESC = rc(6452, 4420, 6650, 4905)        # sofa-cama + escada (junto a parede esquerda, perto do garden), unidade 110
PISO = rc(5866, 3965, 6060, 4400)            # porcelanato livre (unidade 109, entre copa e banheiro)
VIDRO = rc(4990, 5045, 5700, 5075)           # caixilho da fachada do garden
DECK = rc(5740, 5142, 6400, 5205)            # faixa limpa do deck (tabuas verticais): ladrilhada na vertical
MIOLO = rc(4957, 4500, 4973, 4900)            # parede (azul-escuro do lancamento)
CALCADA = rc(8300, 5560, 9300, 5880)          # calcada / area externa (cinza-lilas claro do lancamento)
GRAMA = rc(7790, 2700, 7950, 3300)           # gramado
ARBUSTO = rc(7960, 2690, 8400, 3300)         # massa de arbustos (canteiros)
DEGRAUS = rc(7040, 2420, 7330, 2700)         # escada do nucleo (degraus)
PER_DEGRAU = 60                              # periodo de 1 degrau no lancamento (px)
VASO = rc(4995, 4125, 5140, 4255)            # vaso sanitario (parede a esquerda)
LAVAT = rc(5150, 4300, 5345, 4400)           # bancada com cuba


def degraus_nucleo(H, W, ang=-57.4, k=K):
    """Degraus reais do nucleo do lancamento: faixa girada para os espelhos ficarem horizontais, repetida pelo periodo
    do degrau e girada de volta (espelhos na mesma direcao do lancamento)."""
    M = cv2.getRotationMatrix2D((250, 200), 57.4, 1.0)
    r = cv2.warpAffine(LS[2600:3000, 7200:7700], M, (500, 400))
    tira = r[120:120 + PER_DEGRAU, 150:300]
    tira = cv2.resize(tira, None, fx=k, fy=k, interpolation=cv2.INTER_AREA)
    L = int(np.hypot(H, W)) + 10
    big = np.tile(tira, (L // tira.shape[0] + 2, L // tira.shape[1] + 2, 1))[:L, :L]
    M2 = cv2.getRotationMatrix2D((L / 2, L / 2), ang, 1.0)
    big = cv2.warpAffine(big, M2, (L, L))
    y0, x0 = (L - H) // 2, (L - W) // 2
    return big[y0:y0 + H, x0:x0 + W]
RUA = rc(8000, 6100, 10500, 6650)             # rua do lancamento (granulado lilas)
PASSEIO = rc(3400, 5820, 7200, 6230)          # passeio do lancamento (lilas claro liso)


def _arbusto():
    """Copa de arbusto do lancamento: recorte central do macico, borda pela propria folhagem (escura) dentro de um disco."""
    f_ = 12000 / 1400; x0, y0 = int(890 * f_), int(230 * f_)
    sp = LS[y0 + 120:y0 + 520, x0 + 140:x0 + 540].copy()
    g = sp.astype(np.float32).mean(2)
    yy, xx = np.mgrid[0:400, 0:400]; r = np.hypot(xx - 200, yy - 200)
    disco = np.clip((195 - r) / 25, 0, 1)
    folha = np.clip((105 - cv2.GaussianBlur(g, (0, 0), 3)) / 25, 0, 1)
    return sp, (disco * np.maximum(folha, (r < 140))).astype(np.float32)
ARVORE, ARVORE_A = _arbusto()
