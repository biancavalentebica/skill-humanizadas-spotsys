"""Ajuda a escrever o config de um pavimento com as caixas de 'apagar' geradas pelo OCR.

Uso (num script do pavimento, ex.: configs/s_03A.py):
    import sys; sys.path.insert(0, r'<pasta da skill>/scripts')
    from config_helper import *
    u = {'201 A': [R(15, 200, 142, 465)], ...}           # contornos (frame de trabalho)
    salvar(planta='.../SANTINHOSPOT-...-03P-BLA-000-R00.png', ocr='ocr_03P.json',
           cfg='configs/03P-BLA.json', saida='.../Plantas unidades',
           empreendimento='Santinho Spot', uns=u, laje=(20, 238, 2000, 657))
Para mezanino: sufixo=' - Mezanino'.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from auto_apagar import gerar

R = lambda x0, y0, x1, y1: [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]


def corta(uns, x0, y0, x1, y1):
    """Limita os poligonos a caixa da laje (evita pegar rosa dos ventos, jardim externo etc.)."""
    return {k: [[[min(max(x, x0), x1), min(max(y, y0), y1)] for x, y in p] for p in v] for k, v in uns.items()}


def salvar(planta, ocr, cfg, saida, empreendimento, uns, sufixo='', extra=(), laje=None, limiar_escuro=62):
    if laje:
        uns = corta(uns, *laje)
    ap = gerar(ocr) + list(extra)
    # alem da caixa exata, apaga o bloco de letras inteiro (rotulo S./T./Garden) ou a linha (m2)
    ap += [{"frame": "o", "centro": it["centro"], "bloco": True if it["obs"].startswith("rotulo") else "linha",
            "obs": "bloco " + it["obs"]} for it in ap if "centro" in it and "largura" in it]
    c = {"planta": planta, "saida": saida, "nome": empreendimento + " - {id}.png", "angulo": 0,
         "ampliar_ia": False, "limiar_escuro": limiar_escuro,
         "unidades": {k + sufixo: {"poligonos": [{"frame": "o", "pts": p} for p in v]} for k, v in uns.items()},
         "apagar": ap}
    os.makedirs(os.path.dirname(os.path.abspath(cfg)), exist_ok=True)
    json.dump(c, open(cfg, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(os.path.basename(cfg), len(uns), 'unidades', len(ap), 'textos')
