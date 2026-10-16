"""Mapa de ambientes do terreo R06 (um id por ambiente) e fronteiras entre ambientes, base das paredes.
Rodar direto mostra, por unidade, os trechos de fronteira com a circulacao (onde pode ficar a porta de acesso)."""
import sys, os
import cv2, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from r06_base import *


def ambientes():
    A = areas(); G = raster(((0.3647, 0.3647, 0.3647),))
    amb = []   # (nome, tipo, mascara)
    for a in A:
        labs = ' '.join(a['labs'])
        un = [s for s in a['labs'] if s.isdigit() and len(s) == 3]
        if a['tipo'] == 'outra': continue
        if a['tipo'] == 'computavel':
            if un: nome = un[0]; t = 'unidade'
            elif 'LOJA' in labs: nome = 'LOJA'; t = 'loja'
            elif 'ELEVADORES' in labs: nome = 'CIRC'; t = 'circ'
            elif 'TÉCNICA' in labs or 'TECNICA' in labs.upper(): nome = 'AT'; t = 'tecnica'
            elif 'PERMANENTE' in labs: nome = 'LIXO_P'; t = 'servico'
            elif 'SEGREGADOR' in labs: nome = 'SEGREG'; t = 'servico'
            else: nome = '?'; t = 'outro'
        elif a['tipo'] == 'garden' or 'GARDEN' in labs:
            nome = 'G' + (un[0] if un else '?'); t = 'garden'
        else:
            if 'VAGA PCD' in labs: nome = 'PCD'
            elif 'MEDIDORES' in labs: nome = 'MED'
            elif 'LIXO' in labs: nome = 'LIXO_T'
            elif 'ABERTA' in labs or not a['labs']: nome = 'COBERTA'
            else: nome = '?d'
            t = 'descoberta'
        amb.append([nome, t, mascara(a['pts']), a])
    # lojas numeradas da esquerda para a direita
    lj = sorted([x for x in amb if x[0] == 'LOJA'], key=lambda x: np.nonzero(x[2])[1].mean())
    for i, x in enumerate(lj): x[0] = 'LOJA 0%d' % (i + 1)
    # nucleo: escada e elevadores (hachura cinza) recortados da circulacao
    n, lab, st, _ = cv2.connectedComponentsWithStats(cv2.dilate(G.astype(np.uint8), np.ones((15, 15), np.uint8)))
    caixas = sorted([st[i] for i in range(1, n) if st[i, 4] > 20000], key=lambda s: -s[4])
    return amb, caixas


def mapa():
    amb, caixas = ambientes()
    ids = np.zeros((H, W), np.int32); nomes = {0: 'FORA'}; tipos = {0: 'fora'}
    ordem = sorted(range(len(amb)), key=lambda i: -amb[i][2].sum())   # grandes primeiro, pequenos por cima
    for k, i in enumerate(ordem, start=1):
        nome, t, m, _ = amb[i]
        ids[m] = k; nomes[k] = nome; tipos[k] = t
    return ids, nomes, tipos, caixas, amb


if __name__ == '__main__':
    ids, nomes, tipos, caixas, amb = mapa()
    print('ambientes:', sorted(set(nomes.values())))
    print('caixas cinza (x,y,w,h,area):', [list(c) for c in caixas])
    circ = [k for k, v in nomes.items() if v == 'CIRC'][0]
    for k, v in sorted(nomes.items(), key=lambda t: t[1]):
        if tipos[k] not in ('unidade', 'loja', 'tecnica', 'servico'): continue
        m = ids == k
        viz = cv2.dilate(m.astype(np.uint8), np.ones((11, 11), np.uint8)).astype(bool) & ~m
        f = viz & (ids == circ)
        ys, xs = np.nonzero(f)
        if len(xs) == 0: print(v, 'sem fronteira com a circulacao'); continue
        print(v, 'fronteira c/ circ: x %d-%d y %d-%d (%d px)' % (xs.min(), xs.max(), ys.min(), ys.max(), len(xs)))
    col = np.zeros((H, W, 3), np.uint8); rng = np.random.default_rng(1)
    for k in nomes:
        col[ids == k] = rng.integers(60, 255, 3) if k else 255
    for k, v in nomes.items():
        if k == 0: continue
        ys, xs = np.nonzero(ids == k)
        if len(xs): cv2.putText(col, v, (int(xs.mean()) - 40, int(ys.mean())), 0, 1.2, (0, 0, 0), 3)
    cv2.imwrite('03_trabalho/do_zero/mapa_ids.jpg', cv2.resize(col, None, fx=0.4, fy=0.4))
