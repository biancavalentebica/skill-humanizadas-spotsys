# -*- coding: utf-8 -*-
"""Passo 2: cruza as pastas OK com o estado do SpotSys (out/estado.json) e gera os scripts em run/.

Regras (decididas pela Bianca em 09/10/2026):
- so pastas que terminam em OK; mezanino fica de fora
- troca a planta das unidades que tem arquivo novo: remove (x) a atual e sobe a da pasta
- unidade com planta e sem arquivo novo: mantem
- "X - Y" no nome = todos os andares de X a Y; se algum andar tiver arquivo proprio -> BLOQUEADO (perguntar)
- desmarca Area desatualizada nas unidades que recebem planta nova
Qualquer coisa fora do padrao -> BLOQUEADO (nao mexe naquele empreendimento e avisa a Bianca).
"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comum import *

pend = ler_json(os.path.join(OUT, 'pendentes.json'))
est = ler_json(os.path.join(OUT, 'estado.json'))
tpl_up = open(os.path.join(AUTO, 'tpl_upload.js'), encoding='utf-8').read()
tpl_rm = open(os.path.join(AUTO, 'tpl_remover.js'), encoding='utf-8').read()
tpl_ar = open(os.path.join(AUTO, 'tpl_area.js'), encoding='utf-8').read()
tpl_vf = open(os.path.join(AUTO, 'tpl_verificar.js'), encoding='utf-8').read()


def codigos(stem, todas=()):
    """Unidades de um nome 'Empreendimento - 201.png' / '- 201 - 501' / '- 101 102' / '- 101 A'.
    None + motivo se fora do padrao. 'todas' = codigos do SpotSys (aceita o texto exato, ex. 'LOJA 01')."""
    partes = [p.strip() for p in stem.split(' - ')]
    if len(partes) < 2:
        return None, 'nome sem " - <unidade>"'
    segs = partes[1:]
    if len(segs) == 1:
        s = segs[0]
        if s in todas:
            return [s], None
        if re.fullmatch(r'\d{1,4} [A-Za-z]', s):          # '101 A' -> '101A' (Santinho)
            return [s.replace(' ', '')], None
        toks = s.split()
        if toks and all(RE_COD.match(t) for t in toks):
            # zero a esquerda ('01' -> '1') quando so a versao sem zero existe no SpotSys (Trancoso/Lagoa, 09/10)
            toks = [t.lstrip('0') if t not in todas and t.isdigit() and t.lstrip('0') in todas else t for t in toks]
            # loja 'L1' -> 'L01' quando so a versao com zero existe no SpotSys (Ilha do Campeche II, 10/10)
            toks = [f'L{int(t[1:]):02d}' if t not in todas and re.fullmatch(r'L\d', t) and f'L{int(t[1:]):02d}' in todas else t for t in toks]
            return toks, None
        return None, 'unidade fora do padrao: "' + s + '"'
    if len(segs) == 2 and all(re.fullmatch(r'\d{3,4}', s) for s in segs):
        a, b = segs
        if a[-2:] != b[-2:]:
            return None, f'intervalo {a} - {b} com finais diferentes'
        fa, fb = int(a[:-2]), int(b[:-2])
        if fb <= fa:
            return None, f'intervalo {a} - {b} invertido'
        return [f'{p}{a[-2:]}' for p in range(fa, fb + 1)], None
    return None, 'nome fora do padrao (' + ' - '.join(segs) + ')'


IGN = os.path.join(OUT, 'ignorar.json')   # {pasta: [arquivos a pular]} decidido pela Bianca caso a caso
ignorar = ler_json(IGN) if os.path.exists(IGN) else {}
MAPA = os.path.join(OUT, 'mapa.json')     # {pasta: {codigo do arquivo: codigo no SpotSys}} decidido pela Bianca caso a caso
mapa = ler_json(MAPA) if os.path.exists(MAPA) else {}
plano ={'teste': pend['teste'], 'empreendimentos': []}
for item in pend['pastas']:
    pasta = item['pasta']
    e = est.get(pasta)
    reg = {'pasta': pasta, 'status': 'OK', 'motivos': []}
    plano['empreendimentos'].append(reg)
    if not e or 'erro' in e:
        reg.update(status='BLOQUEADO', motivos=[(e or {}).get('erro', 'sem leitura do SpotSys')])
        continue
    bid = e['id']
    reg.update(id=bid, nome=e['nome'])
    dir_un = os.path.join(RAIZ_PLANTAS, pasta, SUB_UNIDADES)
    if not os.path.isdir(dir_un):
        reg.update(status='BLOQUEADO', motivos=['pasta "Plantas unidades" nao existe'])
        continue
    code_by_id = {u['id']: u['code'] for u in e['units']}
    todas = {u['code'] for u in e['units']}
    outd = {u['code']: u['outdated'] for u in e['units']}
    plantas = {}
    for p in e['plantas']:
        plantas.setdefault(code_by_id.get(p['unit']), []).append(p['img'])

    itens, cobre, mezaninos, ignorados = [], {}, [], []
    for f in sorted(os.listdir(dir_un), key=chave):
        cam = os.path.join(dir_un, f)
        stem, ext = os.path.splitext(f)
        if not os.path.isfile(cam):
            continue
        if ext.lower() not in EXT_IMG:
            ignorados.append(f); continue
        if 'mezanino' in f.lower():
            mezaninos.append(f); continue
        if f in ignorar.get(pasta, []):
            ignorados.append(f); continue
        junta = os.path.join(RAIZ_PLANTAS, pasta, 'Plantas unidades com mezanino', f)
        if os.path.isfile(junta):   # 13/10: unidade com mezanino sobe a imagem pavimento + mezanino (nao desfazer)
            cam = junta
        cods, mot = codigos(stem, todas)
        if cods and pasta in mapa:
            cods = [mapa[pasta].get(c, c) for c in cods]
        if mot:
            reg['motivos'].append(f'{f}: {mot}'); continue
        faltam = [c for c in cods if c not in todas]
        if faltam:
            reg['motivos'].append(f'{f}: unidade(s) {" ".join(faltam)} nao existem no SpotSys'); continue
        tam = os.path.getsize(cam)
        if tam > MAX_BYTES:
            reg['motivos'].append(f'{f}: {tam/1e6:.1f} MB (acima de 10 MB, precisa converter)'); continue
        for c in cods:
            cobre.setdefault(c, []).append(f)
        itens.append({'f': cam, 'u': cods, 'bytes': tam})
    for c, fs in cobre.items():
        if len(fs) > 1:
            reg['motivos'].append(f'unidade {c} aparece em mais de um arquivo: {" | ".join(fs)}')
    if not itens and not reg['motivos']:
        reg['motivos'].append('nenhuma planta (sem mezanino) na pasta')
    if reg['motivos']:
        reg['status'] = 'BLOQUEADO'
        continue

    novas = sorted(cobre, key=chave)
    remover = [u for u in novas if plantas.get(u)]
    area = [u for u in novas if outd.get(u)]
    manter = {u: ids for u, ids in plantas.items() if u and u not in cobre}
    ant = {u: plantas.get(u, []) for u in novas}
    bytes_u = {u: it['bytes'] for it in itens for u in it['u']}
    reg.update(arquivos=len(itens), unidades_novas=novas, remover=remover, area=area,
               manter=sorted(manter, key=chave), sem_planta_depois=sorted(todas - set(novas) - set(manter), key=chave),
               mezaninos=len(mezaninos), ignorados=ignorados, scripts=[])

    pre = os.path.join(RUN, f'{bid}_')
    for k in range(0, len(remover), 20):          # blocos de 20 para nao estourar o tempo da chamada
        n = pre + f'1_remover_{k // 20:02d}.js'
        open(n, 'w', encoding='utf-8').write(
            tpl_rm.replace('__ID__', str(bid)).replace('__UNIDS__', json.dumps(remover[k:k + 20], ensure_ascii=True)))
        reg['scripts'].append(n)
    lote = [{'f': it['f'], 'u': it['u']} for it in itens]
    for k in range(0, len(lote), 8):
        n = pre + f'2_up_{k // 8:02d}.js'
        open(n, 'w', encoding='utf-8').write(
            tpl_up.replace('__ID__', str(bid)).replace('__ITENS__', json.dumps(lote[k:k + 8], ensure_ascii=True)))
        reg['scripts'].append(n)
    if area:
        open(pre + '3_area.js', 'w', encoding='utf-8').write(
            tpl_ar.replace('__ID__', str(bid)).replace('__UNIDS__', json.dumps(area, ensure_ascii=True)))
        reg['scripts'].append(pre + '3_area.js')
    open(pre + '4_verificar.js', 'w', encoding='utf-8').write(
        tpl_vf.replace('__ID__', str(bid)).replace('__NOVAS__', json.dumps(bytes_u))
        .replace('__ANT__', json.dumps(ant)).replace('__MANTER__', json.dumps(manter)))
    reg['scripts'].append(pre + '4_verificar.js')
    reg['ver_json'] = os.path.join(OUT, f'{bid}_ver.json')

gravar_json(os.path.join(OUT, 'plano.json'), plano)
if not plano['teste']:
    for r in plano['empreendimentos']:
        if r['status'] != 'OK':
            marcar_avisado(r['pasta'], 'BLOQUEADO: ' + ' | '.join(r['motivos'])[:1500])

for r in plano['empreendimentos']:
    if r['status'] != 'OK':
        print(f"BLOQUEADO  {r['pasta']}:")
        for m in r['motivos']:
            print('   -', m)
        continue
    print(f"OK  {r['pasta']}  ->  {r['nome']} (id {r['id']})")
    print(f"   arquivos: {r['arquivos']} | unidades que recebem planta: {len(r['unidades_novas'])} | "
          f"trocar (remover antes): {len(r['remover'])} | desmarcar area: {len(r['area'])} | "
          f"mantidas sem arquivo: {len(r['manter'])} | mezaninos fora: {r['mezaninos']}")
    if r['sem_planta_depois']:
        print('   continuam sem planta (sem arquivo):', ' '.join(r['sem_planta_depois']))
    if plano['teste']:
        print('   (TESTE: nao rode os scripts)')
    else:
        print('   rode NESTA ORDEM, um por vez, esperando o resultado:')
        for s in r['scripts']:
            print('     ', s)
        print('   depois: browser_evaluate () => JSON.stringify(window.__autoVer)  filename=' + r['ver_json'])
        print(f"   e por fim: python -I finalizar.py {r['id']}")
