"""Orquestrador ponta a ponta da skill (sem parada manual). Mede o tempo de cada etapa.

Uso: python roda_pipeline.py <empreendimento.json>
O JSON do empreendimento descreve entradas e parametros por pavimento (ver skill/exemplos/cachoeira-spot.json).
Saida: tudo em <saida>/ e <saida>/03_CONFERENCIA/tempos_etapas.csv.
A ultima etapa gera o pacote de publicacao com trava de QC; a carga no SpotSys/360 e feita fora daqui.
"""
import sys, json, os, subprocess, time, csv

E = json.load(open(sys.argv[1], encoding='utf-8'))
PY = sys.executable; S = os.path.dirname(os.path.abspath(__file__)); T = E['trabalho']
os.makedirs(T, exist_ok=True); os.makedirs(E['registro'], exist_ok=True)
for sub in ('sem_texto', 'celulas'): os.makedirs(os.path.join(T, sub), exist_ok=True)
tempos = []


def etapa(nome, args, item=''):
    t0 = time.perf_counter()
    r = subprocess.run([PY, '-I', os.path.join(S, args[0])] + [str(a) for a in args[1:]], capture_output=True, text=True)
    dt = time.perf_counter() - t0
    ok = r.returncode == 0
    tempos.append(dict(etapa=nome, item=item, segundos=round(dt, 1), ok=ok, saida=(r.stdout.strip().splitlines() or [''])[-1][:300]))
    print(f"[{'OK' if ok else 'ERRO'}] {nome} {item} {dt:.1f}s")
    if not ok:
        print(r.stderr[-2000:]); raise SystemExit(f'falhou: {nome} {item}')

t_total = time.perf_counter()
paginas = ','.join(str(p['pagina_pdf']) for p in E['pavimentos'] if not p.get('mesma_pagina_de'))
rot = os.path.join(T, 'rotulos_aprovado.json'); conf = os.path.join(E['diagnostico'], 'conferencia_spotsys_x_pdf_aprovado.csv')
os.makedirs(E['diagnostico'], exist_ok=True)
etapa('1 rotulos e areas do aprovado x SpotSys', ['extrai_rotulos_pdf.py', E['pdf_aprovado'], paginas, E['spotsys_csv'], rot, conf])
if E.get('quadro_areas'):
    etapa('2 quadro de areas x SpotSys', ['compara_areas.py', E['quadro_areas']['xlsx'], E['quadro_areas']['aba'], E['spotsys_csv'],
                                          os.path.join(E['diagnostico'], 'comparativo_areas_spotsys_x_aprovado.csv')])
cfg_rec = dict(empreendimento=E['empreendimento'], revisao=E['revisao'], saida=E['saida'], pavimentos=[], duplex=E.get('duplex', []))
for p in E['pavimentos']:
    st = os.path.join(T, 'sem_texto', p['id'] + '.png')
    etapa('3 remocao de texto', ['remove_texto.py', p['humanizada'], st, st.replace('.png', '_debug.png'), '--fundo-min', p.get('fundo_min', 100)] + (['--caixas-manuais', p['caixas_manuais']] if p.get('caixas_manuais') else []), p['id'])
    cel = os.path.join(T, 'celulas', p['id'] + '.json')
    a = ['celulas_pdf.py', E['pdf_aprovado'], p['pagina_pdf'], rot, cel, cel.replace('.json', '_debug.png')]
    if p.get('janela'): a += ['--janela', p['janela']]
    if p.get('esc'): a += ['--esc', p['esc']]
    if E.get('correcoes_rotulos'): a += ['--correcoes', E['correcoes_rotulos']]
    etapa('4 celulas das unidades (aprovado)', a, p['id'])
    reg = os.path.join(E['registro'], p['id'])
    a5 = ['registra_pdf_imagem.py', E['pdf_aprovado'], cel, st, reg, '--escala', p.get('escala', 100)]
    if p.get('registro_de'): a5 += ['--herdar', os.path.join(E['registro'], p['registro_de'] + '_transform.json')]
    etapa('5 registro aprovado x humanizada', a5, p['id'])
    cfg_rec['pavimentos'].append(dict(id=p['id'], imagem=st, celulas=cel, registro=reg + '_transform.json'))
cfg_p = os.path.join(T, f"config_recortes_{E['revisao']}.json"); json.dump(cfg_rec, open(cfg_p, 'w', encoding='utf-8'), indent=1)
etapa('6 recortes por unidade + plantas gerais', ['gera_recortes.py', cfg_p])
for d in sorted(os.listdir(os.path.join(E['saida'], '02_UNIDADES'))):
    etapa('7 folha de contato', ['folha_contato.py', os.path.join(E['saida'], '02_UNIDADES', d), os.path.join(E['saida'], '03_CONFERENCIA', f'folha_contato_{d}.jpg')], d)
etapa('8 relatorio de QC', ['relatorio_qc.py', cfg_p, E['spotsys_csv'], conf, E.get('revisao_visual', ''), E['registro'], os.path.join(T, 'sem_texto')])
etapa('9 trava QC + pacote (aguarda validacao humana) + pins 360', ['gera_pacote_publicacao.py', cfg_p, E['spotsys_csv']] + (['--aceitar-ressalva'] if E.get('aceitar_ressalva') else []) + (['--validacao', E['validacao_humana']] if E.get('validacao_humana') else []))
tempos.append(dict(etapa='TOTAL automatizado', item='', segundos=round(time.perf_counter() - t_total, 1), ok=True, saida=''))
with open(os.path.join(E['saida'], '03_CONFERENCIA', 'tempos_etapas.csv'), 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.DictWriter(f, fieldnames=list(tempos[0])); w.writeheader(); w.writerows(tempos)
print(f"TOTAL {tempos[-1]['segundos']} s")
