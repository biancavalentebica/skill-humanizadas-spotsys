"""Leva as mascaras do executivo (quadro do legal, 1 cm/px) ao quadro da planta nova (girado, 0,5 cm/px, recortado)."""
import sys, os, json
import numpy as np, cv2
sys.path.insert(0, os.path.dirname(__file__))
from mapa import gira
q = json.load(open('03_trabalho/do_zero/t1_quadro.json'))
E = np.load('03_trabalho/do_zero/exec_masks.npz')
def rot(m, interp=cv2.INTER_LINEAR, borda=0):
    g, _ = gira(m, interp, borda); return g[q['Y0']:, q['X0']:]
out = {}
out['parede'] = rot((E['alvenaria'] | E['estrutura'] | E['cinza50']).astype(np.float32)) > 0.5
out['parede_fina'] = rot(E['cinza36'].astype(np.float32)) > 0.5
out['jardim'] = rot(E['jardim'].astype(np.float32)) > 0.5
out['pilar'] = rot(E['estrutura'].astype(np.float32)) > 0.5
R = cv2.imread('03_trabalho/do_zero/exec_no_legal.png')
out['exec_rgb_gray'] = rot(R.mean(2).astype(np.float32), borda=255)
np.savez_compressed('03_trabalho/do_zero/exec_rot.npz', **{k: v for k, v in out.items()})
print({k: v.shape for k, v in out.items()})
