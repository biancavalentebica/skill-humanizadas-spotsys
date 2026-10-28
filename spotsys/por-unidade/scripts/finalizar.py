# -*- coding: utf-8 -*-
"""Passo final por empreendimento: le out/<id>_ver.json. Se ok -> registra e renomeia a pasta OK -> SUBIDO.

Uso: python -I finalizar.py <id> [--falha "motivo"]   (--falha so registra, nao renomeia)
     python -I finalizar.py --soltar                   (remove a trava no fim da execucao)
"""
import json, os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comum import *

if sys.argv[1] == '--soltar':
    if os.path.exists(LOCK):
        os.remove(LOCK)
    print('trava removida')
    sys.exit(0)

bid = int(sys.argv[1])
falha = sys.argv[3] if len(sys.argv) > 3 and sys.argv[2] == '--falha' else None
plano = ler_json(os.path.join(OUT, 'plano.json'))
r = next(x for x in plano['empreendimentos'] if x.get('id') == bid)
ver = None
if not falha:
    vj = os.path.join(OUT, f'{bid}_ver.json')
    ver = ler_json(vj) if os.path.exists(vj) else None
    if not ver:
        falha = 'conferencia final nao encontrada'
    elif not ver.get('ok'):
        falha = 'conferencia final com problemas: ' + '; '.join(ver.get('problemas', [])[:20])

slug = re.sub(r'[^a-z0-9]+', '-', norm(r['nome'])).strip('-')
regs = [f for f in os.listdir(os.path.join(PROJ, 'registro')) if f.startswith(f'{bid}-')]
reg_path = os.path.join(PROJ, 'registro', regs[0] if regs else f'{bid}-{slug}.md')
novo = not os.path.exists(reg_path)
hoje = time.strftime('%Y-%m-%d %H:%M')

linhas = []
if novo:
    linhas += [f"# {r['nome']} (id {bid})", '', f'360: `spotsys.seazone.dev/lancamentos/empreendimentos-360/{bid}`', '']
linhas += ['', f"## {hoje} — Plantas Baixas, fluxo automatico (pasta \"{r['pasta']}\")", '']
if falha:
    linhas += [f'- **NAO CONCLUIDO:** {falha}', '- Pasta **nao** renomeada; precisa de olho humano antes de rodar de novo.']
else:
    linhas += [
        f"- **Unidades que receberam planta nova ({len(r['unidades_novas'])}):** {' '.join(r['unidades_novas'])}",
        f"- **Trocadas (planta anterior removida pelo x antes de subir) ({len(r['remover'])}):** {' '.join(r['remover']) or '-'}",
        f"- **Area desatualizada desmarcada ({len(r['area'])}):** {' '.join(r['area']) or '-'}",
        f"- **Mantidas (tinham planta, sem arquivo novo):** {' '.join(r['manter']) or '-'}",
        f"- **Continuam sem planta (sem arquivo):** {' '.join(r['sem_planta_depois']) or '-'}",
        f"- **Mezaninos fora:** {r['mezaninos']}",
        f"- **Depois:** {ver['imagens']} imagens, {ver['com_planta']} de {ver['unidades']} unidades com planta",
        f"- **Origem:** upload local, `{os.path.join(RAIZ_PLANTAS, r['pasta'], SUB_UNIDADES)}`",
        '- **Validacao:** API (1 planta por unidade, nao e a antiga, bytes = arquivo local, area desmarcada, '
        'unidades sem arquivo intactas); conteudo visual nao conferido. As plantas removidas continuam no storage.',
    ]
open(reg_path, 'a', encoding='utf-8').write('\n'.join(linhas) + '\n')

if falha:
    if not plano.get('teste'):
        marcar_avisado(r['pasta'], 'FALHOU: ' + falha[:1500])
    print(f'FALHOU {r["pasta"]}: {falha}')
    print('registro:', reg_path)
    sys.exit(1)

origem = os.path.join(RAIZ_PLANTAS, r['pasta'])
m = RE_OK.match(r['pasta'])
destino_nome = (m.group(1).strip() if m else r['pasta']) + ' SUBIDO'
destino = os.path.join(RAIZ_PLANTAS, destino_nome)
if plano.get('teste'):
    print('TESTE: nao renomeio.')
elif os.path.exists(destino):
    destino = destino + ' ' + time.strftime('%Y%m%d-%H%M')
    os.rename(origem, destino)
else:
    os.rename(origem, destino)
print(f"CONCLUIDO {r['nome']} (id {bid}): {len(r['unidades_novas'])} unidades com planta nova, "
      f"{len(r['remover'])} trocadas, {len(r['area'])} areas desmarcadas. Pasta -> {os.path.basename(destino)}")
print('registro:', reg_path)
