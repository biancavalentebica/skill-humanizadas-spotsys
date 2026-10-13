"""Trava de QC + pacote de publicacao (SpotSys / 360).

So entram unidades com status APROVADO no qc_unidades.csv (opcionalmente tambem APROVADO_COM_RESSALVA,
se --aceitar-ressalva). Para cada uma:
  - copia a imagem individual para 04_PUBLICACAO/imagens_unidades
  - copia a(s) planta(s) do pavimento usada(s) como base dos pins
  - gera o pin poligonal no formato da tabela seazone360_floor_plan_pins:
      {szi_unit_id, codigo, planta (arquivo), pin_type: "polygon", polygon_vertices: [{x,y} 0-1], x, y (centroide)}
Saidas: manifesto_publicacao.csv, pins_360.json, BLOQUEADOS.csv (o que ficou fora e por que).
NAO escreve em nenhum sistema: a carga no SpotSys/360 e um passo autorizado a parte (API/tela do SpotSys).

VALIDACAO HUMANA OBRIGATORIA: a carga so pode usar o que uma pessoa validou.
  - Sem arquivo de validacao: o pacote sai como AGUARDANDO_VALIDACAO (pins_360_AGUARDANDO_VALIDACAO.json) e e gerada
    a planilha VALIDACAO_HUMANA.csv para preencher (uma linha por unidade aprovada no QC).
  - Com --validacao <VALIDACAO_HUMANA.csv preenchida>: so entram no pins_360.json/manifesto as unidades com
    validado = S e com validador e data preenchidos. Reprovadas vao para BLOQUEADOS.csv com o motivo escrito.

Uso: python gera_pacote_publicacao.py <config_recortes.json> <spotsys.csv> [--aceitar-ressalva] [--validacao arquivo.csv]
"""
import sys, json, csv, os, shutil

cfg = json.load(open(sys.argv[1], encoding='utf-8')); spot_p = sys.argv[2]
aceitar = '--aceitar-ressalva' in sys.argv
val_p = sys.argv[sys.argv.index('--validacao') + 1] if '--validacao' in sys.argv else ''
validacao = {}
if val_p and os.path.exists(val_p):
    for r in csv.DictReader(open(val_p, encoding='utf-8-sig')):
        validacao[r['unidade']] = r
SAIDA = cfg['saida']; CONF = os.path.join(SAIDA, '03_CONFERENCIA'); PUB = os.path.join(SAIDA, '04_PUBLICACAO')
if os.path.isdir(PUB):
    for raiz, _, arqs in os.walk(PUB):  # limpa arquivos (pasta pode estar aberta no Explorer)
        for f in arqs: os.remove(os.path.join(raiz, f))
os.makedirs(os.path.join(PUB, 'imagens_unidades'), exist_ok=True); os.makedirs(os.path.join(PUB, 'plantas_pavimento'), exist_ok=True)
spot = {r['code']: r for r in csv.DictReader(open(spot_p, encoding='utf-8'))}
qc = {r['unidade']: r for r in csv.DictReader(open(os.path.join(CONF, 'qc_unidades.csv'), encoding='utf-8-sig'))}
log = {r['unidade']: r for r in json.load(open(os.path.join(CONF, 'recortes_log.json'), encoding='utf-8')) if 'arquivo' in r}
ok_status = {'APROVADO'} | ({'APROVADO_COM_RESSALVA'} if aceitar else set())
geral = {p['imagem']: f"{cfg['empreendimento']}_{p['id']}_GERAL_HUM-SEM-TEXTO_{cfg['revisao']}.png" for p in cfg['pavimentos']}

manif, pins, bloq = [], [], []
for code, q in qc.items():
    if q['status'] not in ok_status:
        bloq.append(dict(unidade=code, status=q['status'], motivo=q.get('motivo', ''))); continue
    v = validacao.get(code)
    if validacao:
        if not v or v.get('validado', '').strip().upper() != 'S' or not v.get('validador', '').strip() or not v.get('data', '').strip():
            bloq.append(dict(unidade=code, status='NAO_VALIDADA', motivo=(v or {}).get('observacao', '') or 'sem validacao humana registrada')); continue
    r = log[code]; uid = spot[code]['unit_id']
    dst = os.path.join(PUB, 'imagens_unidades', os.path.basename(r['arquivo']))
    shutil.copy2(r['arquivo'], dst)
    niveis = [r] + ([r['nivel_superior']] if 'nivel_superior' in r else [])
    for nv in niveis:
        planta = geral[nv['imagem_pavimento']]
        src_planta = os.path.join(SAIDA, '01_PAVIMENTOS', planta)
        if not os.path.exists(os.path.join(PUB, 'plantas_pavimento', planta)):
            shutil.copy2(src_planta, os.path.join(PUB, 'plantas_pavimento', planta))
        V = nv['poligono_norm']
        pins.append(dict(szi_unit_id=int(uid), codigo=code, planta=planta, pin_type='polygon', polygon_vertices=V,
                         x=round(sum(v['x'] for v in V) / len(V), 5), y=round(sum(v['y'] for v in V) / len(V), 5),
                         origem='skill atualiza-humanizadas-spotsys ' + cfg['revisao']))
    manif.append(dict(szi_unit_id=uid, codigo=code, versao_projeto=spot[code]['project_version'],
                      imagem_unidade=os.path.relpath(dst, PUB), plantas=';'.join(geral[nv['imagem_pavimento']] for nv in niveis),
                      status_qc=q['status'], validado_por=(v or {}).get('validador', ''), data_validacao=(v or {}).get('data', ''),
                      acao_spotsys='substituir floor_plan da unidade; nao marcar is_outdated_area'))
estado = 'VALIDADO' if validacao else 'AGUARDANDO_VALIDACAO'
nome_pins = 'pins_360.json' if validacao else 'pins_360_AGUARDANDO_VALIDACAO.json'
json.dump(pins, open(os.path.join(PUB, nome_pins), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
if not validacao:  # planilha para a validacao humana
    with open(os.path.join(PUB, 'VALIDACAO_HUMANA.csv'), 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f); w.writerow(['unidade', 'imagem', 'status_qc', 'validado', 'validador', 'data', 'observacao'])
        for m_ in manif: w.writerow([m_['codigo'], m_['imagem_unidade'], m_['status_qc'], '', '', '', ''])
    open(os.path.join(PUB, 'LEIA-ME_NAO_CARREGAR.txt'), 'w', encoding='utf-8').write(chr(10).join([
        'Pacote AGUARDANDO VALIDACAO HUMANA. Nao carregar no SpotSys/360.',
        '1) Abra as imagens e as folhas de contato (03_CONFERENCIA).',
        '2) Preencha VALIDACAO_HUMANA.csv: validado = S ou N, validador, data, observacao.',
        '3) Rode de novo com --validacao VALIDACAO_HUMANA.csv (ou validacao_humana no JSON do empreendimento).',
        'So as unidades validadas entram em pins_360.json e no manifesto de carga.', '']))
for nome, rows in (('manifesto_publicacao.csv', manif), ('BLOQUEADOS.csv', bloq)):
    if rows:
        with open(os.path.join(PUB, nome), 'w', newline='', encoding='utf-8-sig') as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
print(json.dumps(dict(estado=estado, aprovadas_qc_no_pacote=len(manif), pins=len(pins), bloqueadas=len(bloq), aceitar_ressalva=aceitar)))
