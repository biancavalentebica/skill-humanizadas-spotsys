"""Textos da humanizada com as letras da PROPRIA imagem de lancamento (mesma fonte, tamanho e antialias).

Cada rotulo do lancamento (texto conhecido) e separado em glifos pela diferenca entre a imagem com texto e a
versao sem texto (alfa = escurecimento do texto sobre o fundo). Um texto novo e escrito juntando esses glifos
na mesma linha de base, escolhendo para cada letra o exemplar mais limpo (fundo liso, largura tipica).
"""
import json
import cv2, numpy as np

ORIG = '00_entradas/originais/humanizada_lancamento_2024/1 - terreo.png'
SEM = '03_trabalho/lancamento_sem_texto/PAV-01.png'
BOXES = '03_trabalho/conforme_R06/terreo/rotulos_lanc_boxes.json'
TEXTOS = {0: 'Garden', 1: 'Garden', 2: 'Garden', 3: 'Garden', 4: 'Garden', 5: 'Garden', 6: '11,32m²', 7: 'Garden', 8: '11,55m²',
          9: 'Garden', 10: '9,60m²', 11: '10,16m²', 12: '10,39m²', 13: '10,63m²', 14: '10,86m²', 15: '11,09m²', 16: 'UN107',
          17: 'UN114', 18: 'UN113', 19: 'UN112', 20: 'UN109', 21: 'UN108', 22: '22,21m²', 23: 'Garden', 24: 'UN115',
          25: '15,42m²', 26: '15,42m²', 27: '15,42m²', 28: 'UN111', 29: 'UN110', 30: '15,42m²', 31: '15,43m²', 32: '47,28m²',
          33: '22,57m²', 34: '21,03m²', 35: '21,03m²', 36: 'UN106', 37: '17,60m²', 38: 'Garden', 39: '11,28m²', 40: '17,70m²',
          41: 'UN105', 42: 'Lixeiras', 43: 'Garden', 44: '9,89m²', 45: 'Medidores', 46: 'PNE', 47: '17,60m²', 48: 'UN104',
          49: 'Garden', 50: 'PNE', 51: 'PNE', 52: 'Recepção', 53: '11,48m²', 54: 'UN101', 55: '22,16m²', 56: 'Loja01',
          57: '21,89m²', 58: 'Loja02', 59: '22,33m²', 60: 'Loja03', 61: '15,42m²', 62: '15,26m²', 63: 'UN102', 64: 'UN103',
          65: '21,14m²', 66: 'Garden', 67: 'Garden', 68: 'Garden', 69: '5,00m²', 70: '4,90m²', 71: '9,42m²'}
DESCE = set(',jpçg')


def _plano(caminho):
    im = cv2.imread(caminho, cv2.IMREAD_UNCHANGED)
    al = im[:, :, 3:4] / 255.0
    return (im[:, :, :3] * al + 255 * (1 - al)).astype(np.float32)


def _runs(A, n_alvo):
    m = cv2.morphologyEx((A > 0.45).astype(np.uint8), cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, 8)
    cs = sorted([[st[i, 0], st[i, 0] + st[i, 2]] for i in range(1, n) if st[i, 4] >= 4], key=lambda r: r[0])
    out = []
    for c in cs:  # junta pingo, til e cedilha ao glifo de baixo
        if out:
            a0, a1 = out[-1]; ov = min(a1, c[1]) - max(a0, c[0])
            if ov >= 0.5 * min(a1 - a0, c[1] - c[0]): out[-1] = [min(a0, c[0]), max(a1, c[1])]; continue
        out.append(c)
    runs = [(int(a), int(b)) for a, b in out]
    while 0 < len(runs) < n_alvo:  # letras coladas: corta o mais largo no vale de tinta
        k = max(range(len(runs)), key=lambda q: runs[q][1] - runs[q][0]); j0, j1 = runs[k]
        prof = (A[:, j0:j1] > 0.4).sum(0)[3:-3]
        if len(prof) == 0: break
        c = j0 + 3 + int(np.argmin(prof)); runs = runs[:k] + [(j0, c), (c, j1)] + runs[k + 1:]
    return runs, m


class Fonte:
    def __init__(self):
        a = _plano(ORIG).mean(2); b = _plano(SEM).mean(2)
        self.boxes = [tuple(v) for v in json.load(open(BOXES))]
        cand = {}; gaps = []; espacos = []
        for i, txt in TEXTOS.items():
            x, y, w, h = self.boxes[i]
            A = np.clip(1 - (a[y:y + h, x:x + w] + 1) / (b[y:y + h, x:x + w] + 1), 0, 1)
            runs, m = _runs(A, len(txt))
            if len(runs) != len(txt): continue
            A = A * cv2.dilate(m, np.ones((3, 3), np.uint8))           # tira o ruido do fundo
            ruido = float(b[y:y + h, x:x + w].std())
            fundos = [np.nonzero(A[:, j0:j1].max(1) > 0.3)[0] for j0, j1 in runs]
            bases = [f[-1] for f, c in zip(fundos, txt) if len(f) and c not in DESCE and c != '²']
            if not bases: continue
            base = int(np.median(bases))
            for k, (c, (j0, j1)) in enumerate(zip(txt, runs)):
                f = fundos[k]
                if not len(f): continue
                t0, t1 = max(0, f[0] - 1), min(h, f[-1] + 2)
                cand.setdefault(c, []).append(dict(a=A[t0:t1, max(0, j0 - 1):j1 + 1], off=t0 - base, ruido=ruido))
            gaps += [runs[k + 1][0] - runs[k][1] for k in range(len(runs) - 1)]
            if txt.startswith('UN'): espacos.append(runs[2][0] - runs[1][1])
            if txt.startswith('Loja'): espacos.append(runs[4][0] - runs[3][1])
            if txt.endswith('m²'): espacos.append(runs[-2][0] - runs[-3][1])
        self.glifos = {}
        for c, lst in cand.items():
            ws = np.array([g['a'].shape[1] for g in lst]); md = np.median(ws)
            boa = [g for g in lst if abs(g['a'].shape[1] - md) <= 1] or lst
            self.glifos[c] = min(boa, key=lambda g: g['ruido'])
        self.gap = max(1, int(np.median(gaps)) - 2)
        self.esp = int(np.median(espacos))

    def render(self, texto):
        itens = []; x = 0
        for c in texto:
            if c == ' ': x += self.esp - self.gap; continue
            g = self.glifos[c]; itens.append((x, g)); x += g['a'].shape[1] + self.gap
        top = min(g['off'] for _, g in itens); bot = max(g['off'] + g['a'].shape[0] for _, g in itens)
        A = np.zeros((bot - top, x), np.float32)
        for xx, g in itens:
            r = g['off'] - top; h, w = g['a'].shape
            A[r:r + h, xx:xx + w] = np.maximum(A[r:r + h, xx:xx + w], g['a'])
        return A, -top  # alfa e linha de base

    def escreve(self, canvas, texto, cx, base_y, cor=(0, 0, 0)):
        A, b = self.render(texto); h, w = A.shape
        x0, y0 = int(round(cx - w / 2)), int(round(base_y - b))
        reg = canvas[y0:y0 + h, x0:x0 + w].astype(np.float32)
        al = A[:reg.shape[0], :reg.shape[1], None]
        canvas[y0:y0 + h, x0:x0 + w] = (reg * (1 - al) + np.array(cor, np.float32) * al).astype(np.uint8)

    def rotulo(self, canvas, linha1, linha2, cx, cy, entre=31):
        """Duas linhas centradas em (cx, cy), como nos rotulos do lancamento."""
        if linha2:
            self.escreve(canvas, linha1, cx, cy - 4); self.escreve(canvas, linha2, cx, cy - 4 + entre)
        else:
            self.escreve(canvas, linha1, cx, cy + 10)
