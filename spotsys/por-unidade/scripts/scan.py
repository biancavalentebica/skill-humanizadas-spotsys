# -*- coding: utf-8 -*-
"""Passo 1: procura pastas "... OK". Imprime NADA, OCUPADO ou PENDENTES e gera run/estado.js.

Uso: python -I scan.py            (normal)
     python -I scan.py --teste "Rosa Norte Spot"   (simula uma pasta OK, so leitura)
"""
import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comum import *

teste = sys.argv[2] if len(sys.argv) > 2 and sys.argv[1] == '--teste' else None

idade = lock_status()
if idade is not None and idade < LOCK_MAX_H and not teste:
    print(f'OCUPADO: outra execucao comecou ha {idade*60:.0f} min (trava {LOCK}). Nao faca nada.')
    sys.exit(0)

pend = [(teste, teste)] if teste else pastas_ok()
ja_avisadas = []
if not teste:
    av = avisados()
    ja_avisadas = [p for p, n in pend if p in av and av[p]['assinatura'] == assinatura(p)]
    pend = [(p, n) for p, n in pend if p not in ja_avisadas]
if not pend:
    extra = f' ({len(ja_avisadas)} pasta(s) OK ja avisada(s) como bloqueada(s), sem mudanca: {", ".join(ja_avisadas)})' if ja_avisadas else ''
    print('NADA: nenhuma pasta OK nova para subir.' + extra)
    sys.exit(0)

if not teste:
    open(LOCK, 'w').write(time.strftime('%Y-%m-%d %H:%M:%S'))

for f in os.listdir(RUN):
    os.remove(os.path.join(RUN, f))
lista = [{'pasta': p, 'alvo': n} for p, n in pend]
gravar_json(os.path.join(OUT, 'pendentes.json'), {'teste': bool(teste), 'pastas': lista})

js = open(os.path.join(AUTO, 'tpl_estado.js'), encoding='utf-8').read()
js = js.replace('__NOMES__', json.dumps(lista, ensure_ascii=True))
open(os.path.join(RUN, 'estado.js'), 'w', encoding='utf-8').write(js)

print('PENDENTES' + (' (TESTE, so leitura)' if teste else '') + ':')
for p, n in pend:
    print(f'  - {p}  ->  procurar no SpotSys: "{n}"')
print('Proximo: browser_run_code_unsafe filename=' + os.path.join(RUN, 'estado.js'))
print('Depois:  browser_evaluate () => JSON.stringify(window.__autoEstado)  filename=' + os.path.join(OUT, 'estado.json'))
