"""Roda a Fase 1 (planta do PAVIMENTO compatibilizada) de ponta a ponta e mede o tempo de cada etapa.
Uso: python roda_compatibilizacao.py <config.json>
config: {"pdf":..., "pdf_sha256":..., "spotsys_csv":..., "paginas":"4,5,6,7,8,9", "saida":..., "trabalho":...,
         "pavimentos":[{"id":"PAV-01","celulas":...,"lancamento_com_texto":...,"lancamento_sem_texto":...,"escala":100}, ...]}
"""
import sys, os, json, time, hashlib, subprocess, csv
cfg = json.load(open(sys.argv[1], encoding='utf-8'))
PY = sys.executable; S = os.path.dirname(os.path.abspath(__file__))
os.makedirs(cfg['saida'], exist_ok=True); os.makedirs(cfg['trabalho'], exist_ok=True)
tempos = []
def etapa(nome, fn):
    t = time.perf_counter(); r = fn(); tempos.append((nome, round(time.perf_counter() - t, 1), r)); print(f'{nome}: {tempos[-1][1]} s  {r}')
def run(*args):
    subprocess.run(args, check=True, capture_output=True)

def autodoc():
    h = hashlib.sha256(open(cfg['pdf'], 'rb').read()).hexdigest()
    return 'PDF R06 conferido (sha256 igual ao baixado do Autodoc)' if h == cfg['pdf_sha256'] else 'ATENCAO: PDF diferente do registrado'
etapa('1. Projeto aprovado (Autodoc)', autodoc)

def comparacao():
    for p in cfg['pavimentos']:
        b = os.path.join(cfg['trabalho'], p['id'] + '_bin.png')
        run(PY, '-I', os.path.join(S, 'prepara_ocr.py'), p['lancamento_com_texto'], b)
        run('powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', os.path.join(S, 'ocr_windows.ps1'), b, os.path.join(cfg['trabalho'], p['id'] + '.json'), '2')
    return f"{len(cfg['pavimentos'])} pavimentos: numeracao do lancamento lida (OCR) para casar com o aprovado"
etapa('2. Comparacao lancamento x aprovado', comparacao)

res = {}
def geracao():
    for p in cfg['pavimentos']:
        out = os.path.join(cfg['saida'], p['id'] + '.png')
        run(PY, '-I', os.path.join(S, 'gera_planta_compatibilizada.py'), cfg['pdf'], p['celulas'], p['lancamento_sem_texto'], out,
            '--escala', str(p.get('escala', 100)), '--ocr', os.path.join(cfg['trabalho'], p['id'] + '.json'))
        res[p['id']] = json.load(open(out[:-4] + '_log.json', encoding='utf-8'))
    return f"{len(res)} plantas de pavimento"
etapa('3. Geracao por pavimento', geracao)

def conferencia():
    run(PY, '-I', os.path.join(S, 'extrai_rotulos_pdf.py'), cfg['pdf'], cfg['paginas'], cfg['spotsys_csv'],
        os.path.join(cfg['trabalho'], 'rotulos_aprovado.json'), os.path.join(cfg['saida'], 'conferencia_spotsys_x_aprovado.csv'))
    rows = list(csv.DictReader(open(os.path.join(cfg['saida'], 'conferencia_spotsys_x_aprovado.csv'), encoding='utf-8-sig')))
    return f'{len(rows)} linhas conferidas SpotSys x PDF aprovado'
etapa('4. Conferencia no SpotSys', conferencia)

def qc():
    linhas = []
    for k, L in res.items():
        linhas.append(dict(pavimento=k, divisa_parede_mediana_cm=L['qc']['divisa_parede_mediana_cm'], frac_divisas_ate_15cm=L['qc']['frac_divisas_ate_15cm'],
                           unidades=L['unidades'], encaixadas=L['ok'], sinalizadas=' '.join(L['sinalizadas']),
                           status='APROVADO_QC' if L['qc']['divisa_parede_mediana_cm'] <= 5 and L['qc']['frac_divisas_ate_15cm'] >= 0.8 else 'REPROVADO_QC'))
    with open(os.path.join(cfg['saida'], 'qc_pavimentos.csv'), 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=list(linhas[0]), delimiter=';'); w.writeheader(); w.writerows(linhas)
    return f"{sum(l['status'] == 'APROVADO_QC' for l in linhas)}/{len(linhas)} pavimentos aprovados no QC automatico"
etapa('5. QC automatico (trava)', qc)

with open(os.path.join(cfg['saida'], 'tempos_etapas.csv'), 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f, delimiter=';'); w.writerow(['etapa', 'segundos', 'resultado']); w.writerows(tempos)
    w.writerow(['TOTAL', round(sum(t[1] for t in tempos), 1), ''])
print('TOTAL', round(sum(t[1] for t in tempos), 1), 's')
