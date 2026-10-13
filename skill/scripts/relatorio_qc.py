"""Relatorio de controle de qualidade por unidade. Todos os numeros sao calculados dos arquivos.

Entradas: export SpotSys (csv), conferencia SpotSys x PDF (csv), log de recortes (json), registros (json),
logs de remocao de texto (json), revisao visual (json), config dos recortes.
Saidas: qc_unidades.csv e QC_RELATORIO.md na pasta 03_CONFERENCIA.

Criterios automaticos (por unidade):
  C1 identificacao  : codigo existe no SpotSys, tem celula no aprovado e arquivo gerado com o codigo no nome
  C2 area           : SpotSys = rotulos do PDF aprovado (coberta, descoberta, mezanino) -> conferencia_spotsys_x_pdf
  C3 sem_texto      : reverificacao de texto residual do pavimento = 0 linhas
  C4 distorcao      : anisotropia do registro do pavimento em [0,98; 1,02]
  C5 aderencia      : chamfer mediano das divisas do aprovado ate paredes da imagem <= 15 cm
  C6 correspondencia: pixels do recorte identicos a planta geral do pavimento (recorte nao altera imagem)
  C7 resolucao      : maior lado do recorte >= 400 px
Status: APROVADO (C1-C7 ok e sem observacao visual) | APROVADO_COM_RESSALVA (C2..C5 com ressalva ou
observacao visual 'RESSALVA') | PENDENTE (C1/C6 falha, observacao visual 'PENDENTE' ou arquivo ausente).

Uso: python relatorio_qc.py <config_recortes.json> <spotsys.csv> <conferencia_pdf.csv> <revisao_visual.json> <dir_registro> <dir_sem_texto_json>
"""
import sys, json, csv, os, glob
import cv2, numpy as np

cfg_p, spot_p, conf_p, rev_p, reg_dir, st_dir = sys.argv[1:7]
cfg = json.load(open(cfg_p, encoding='utf-8')); OUT = os.path.join(cfg['saida'], '03_CONFERENCIA')
spot = {r['code']: r for r in csv.DictReader(open(spot_p, encoding='utf-8'))}
conf = {r['code']: r for r in csv.DictReader(open(conf_p, encoding='utf-8-sig'))}
rev = json.load(open(rev_p, encoding='utf-8')) if rev_p and os.path.exists(rev_p) else {'observacoes': {}}
rev.setdefault('observacoes', {})
log = json.load(open(os.path.join(OUT, 'recortes_log.json'), encoding='utf-8'))
pav_img = {p['id']: p['imagem'] for p in cfg['pavimentos']}
pav_reg = {p['id']: json.load(open(p['registro'], encoding='utf-8')) for p in cfg['pavimentos']}
pav_rem = {}
for p in cfg['pavimentos']:
    j = p['imagem'].rsplit('.', 1)[0] + '_remocao.json'
    pav_rem[p['id']] = json.load(open(j, encoding='utf-8')) if os.path.exists(j) else None
cache = {}

def img(p):
    if p not in cache: cache[p] = cv2.imread(p, cv2.IMREAD_UNCHANGED)
    return cache[p]

def confere_pixels(arq, pav, origem=None):
    """C6: confere que os pixels opacos do recorte sao identicos aos da planta geral na posicao registrada
    (sem posicao registrada: localiza por matchTemplate)."""
    c = cv2.imread(arq, cv2.IMREAD_UNCHANGED); g = img(pav_img[pav])
    if c is None or g is None: return False, 'arquivo ausente'
    m = c[:, :, 3] > 250
    tpl = c[:, :, :3]
    if origem:
        x, y = origem
    else:
        res = cv2.matchTemplate(g[:, :, :3], tpl, cv2.TM_SQDIFF, mask=np.dstack([m.astype(np.uint8)] * 3))
        _, _, (x, y), _ = cv2.minMaxLoc(res)
    reg = g[y:y + c.shape[0], x:x + c.shape[1], :3]
    if reg.shape[:2] != tpl.shape[:2]: return False, 'fora da planta' 
    dif = np.abs(reg.astype(int) - tpl.astype(int))[m].max() if m.any() else 0
    return bool(dif == 0), f'dif_max={int(dif)}'

linhas = []
gerados = {r['unidade']: r for r in log if 'arquivo' in r}
for code in sorted(spot, key=lambda c: (c.startswith('L'), c)):
    s = spot[code]; r = gerados.get(code)
    L = dict(unidade=code, pavimento_spotsys=s['floor'], versao_spotsys=s['project_version'],
             area_total_spotsys=s['total_area'], arquivo=os.path.relpath(r['arquivo'], cfg['saida']) if r else '')
    obs = []
    if not r:
        L.update(status='PENDENTE', motivo='nao processada: humanizada do pavimento nao disponivel no ambiente (arquivo > 10 MB no Drive)')
        linhas.append(L); continue
    dup = {d['id']: [d['inferior'], d['superior']] for d in cfg.get('duplex', [])}
    pids = dup.get(r['pavimento'], [r['pavimento']])
    c1 = code in r['arquivo'] and os.path.exists(r['arquivo'])
    c2 = conf.get(code, {}).get('status', 'SEM_DADO')
    if c2 != 'OK' and code in rev.get('area_conferida_manual', {}):
        c2 = 'OK_MANUAL'; obs.append('area conferida manualmente: ' + rev['area_conferida_manual'][code])
    def sem_texto(p):
        T = pav_rem[p] or {}
        if T.get('texto_residual_linhas', 1) == 0: return True
        ok = rev.get('residuo_nao_texto', {}).get(p, [])  # caixas conferidas visualmente como nao-texto
        return all(list(b) in ok for b in T.get('caixas_residuais', [None]))
    c3 = all(sem_texto(p) for p in pids)
    anis = [pav_reg[p]['anisotropia'] for p in pids]; cham = [pav_reg[p]['chamfer_mediana_cm'] for p in pids]
    c4 = all(0.98 <= v <= 1.02 for v in anis); c5 = all(v <= 15 for v in cham)
    # C6 nos niveis individuais (o combinado duplex e montagem lado a lado)
    arqs = [r['arquivo']] if r['pavimento'] not in dup else sorted(glob.glob(os.path.join(cfg['saida'], '02_UNIDADES', r['pavimento'], 'niveis', f'*_UN-{code}_*.png')))
    def origem_de(p):
        if r['pavimento'] in dup and p == dup[r['pavimento']][1]: return (r.get('nivel_superior') or {}).get('origem_px')
        return r.get('origem_px')
    c6s = []
    for a_ in arqs:
        p_ = next((p for p in pids if f'_{p}_' in os.path.basename(a_)), pids[0])
        c6s.append(confere_pixels(a_, p_, origem_de(p_)))
    c6 = all(v for v, _ in c6s)
    c7 = max(r['largura_px'], r['altura_px']) >= 400
    L.update(C1_identificacao=c1, C2_area_spotsys_x_aprovado=c2, C3_sem_texto=c3, C4_anisotropia=';'.join(map(str, anis)),
             C4_ok=c4, C5_chamfer_mediana_cm=';'.join(map(str, cham)), C5_ok=c5, C6_pixels_identicos=c6,
             C6_detalhe=';'.join(d for _, d in c6s), C7_resolucao_px=f"{r['largura_px']}x{r['altura_px']}", C7_ok=c7)
    status = 'APROVADO'
    if not (c1 and c6): status = 'PENDENTE'; obs.append('falha de identificacao/correspondencia')
    if c2 not in ('OK', 'OK_MANUAL'):
        status = 'PENDENTE' if c2 == 'DIVERGENTE' else ('APROVADO_COM_RESSALVA' if status == 'APROVADO' else status)
        obs.append(f'area SpotSys x aprovado: {c2} (conferencia manual registrada no diagnostico)')
    if not c3: status = 'PENDENTE'; obs.append('texto residual')
    if not c4 or not c5:
        if status == 'APROVADO': status = 'APROVADO_COM_RESSALVA'
        obs.append(f'registro do pavimento: anisotropia {anis}, chamfer {cham} cm')
    if not c7:
        if status == 'APROVADO': status = 'APROVADO_COM_RESSALVA'
        obs.append('resolucao abaixo de 400 px no maior lado')
    for p in pids:
        o = rev.get('observacoes_pavimento', {}).get(p)
        if o and o['status'] == 'RESSALVA' and status == 'APROVADO': status = 'APROVADO_COM_RESSALVA'
        if o: obs.append(f'{p}: ' + o['motivo'])
    o = rev['observacoes'].get(code)
    if o:
        if o['status'] == 'PENDENTE': status = 'PENDENTE'
        elif status == 'APROVADO': status = 'APROVADO_COM_RESSALVA'
        obs.append('visual: ' + o['motivo'])
    L.update(status=status, motivo=' | '.join(obs))
    linhas.append(L)

campos = list(dict.fromkeys(k for l in linhas for k in l))
with open(os.path.join(OUT, 'qc_unidades.csv'), 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.DictWriter(f, fieldnames=campos); w.writeheader(); w.writerows(linhas)
tot = len(linhas); proc = sum(1 for l in linhas if l['arquivo']); confd = sum(1 for l in linhas if 'C1_identificacao' in l)
cont = {k: sum(1 for l in linhas if l['status'] == k) for k in ('APROVADO', 'APROVADO_COM_RESSALVA', 'PENDENTE')}
md = [f"# Relatorio de controle de qualidade - {cfg['empreendimento']} {cfg['revisao']}", '',
      'Gerado por `skill/scripts/relatorio_qc.py` a partir dos arquivos processados (nenhum numero estimado).', '',
      '| Indicador | Total |', '|---|---|',
      f'| Unidades identificadas (SpotSys, ativas) | {tot} |', f'| Unidades processadas (imagem gerada) | {proc} |',
      f'| Unidades conferidas (C1-C7 executados) | {confd} |', f"| Aprovadas | {cont['APROVADO']} |",
      f"| Aprovadas com ressalva | {cont['APROVADO_COM_RESSALVA']} |", f"| Pendentes | {cont['PENDENTE']} |", '',
      '## Pavimentos', '', '| Pavimento | Anisotropia | Chamfer mediano (cm) | Divisas ate 15 cm | Texto residual (linhas) | Pixels alterados pela remocao de texto |', '|---|---|---|---|---|---|']
for p in cfg['pavimentos']:
    R = pav_reg[p['id']]; T = pav_rem[p['id']] or {}
    md.append(f"| {p['id']} | {R['anisotropia']} | {R['chamfer_mediana_cm']} | {R['frac_divisas_ate_15cm']:.0%} | {T.get('texto_residual_linhas')} | {T.get('pct_alterado')}% |")
md += ['', '## Pendencias e ressalvas', '', '| Unidade | Status | Motivo |', '|---|---|---|']
for l in linhas:
    if l['status'] != 'APROVADO':
        md.append(f"| {l['unidade']} | {l['status']} | {l['motivo']} |")
md += ['', 'Detalhe por unidade: `qc_unidades.csv`. Evidencias visuais: `folha_contato_*.jpg` (esta pasta) e `05_qc/registro/*_overlay.jpg`.']
open(os.path.join(OUT, 'QC_RELATORIO.md'), 'w', encoding='utf-8').write('\n'.join(md))
print(json.dumps(dict(identificadas=tot, processadas=proc, conferidas=confd, **cont)))
