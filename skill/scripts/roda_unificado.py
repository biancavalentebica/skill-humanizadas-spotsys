"""TESTE UNIFICADO das 3 skills de plantas humanizadas (14/10/2026), por pavimento:

  A. planta do pavimento SEM TEXTO a partir do DWG aprovado + acabamento do lancamento   (esta skill)
  B. cfg do recorte gerado do DWG (sementes, area comum, paredes de porta)               (esta skill)
  C. recorte por unidade                                                                 (Raquel: recortar_tipologias.py)
  D. texto + capacidade + solar no pavimento inteiro                                     (Raquel: texto_pavimento.py) [opcional]
  E. planta de tipologias + estudo solar                                                 (Arthur: pv.pecas)
  F. entrega com o nome padrao "GRUPO (unidades) - SEM COTA.png"                         (padrao Raquel)
Antes de tudo: conferencia de areas do arquivo base x PDF aprovado (esta skill, regra 4) ja gravada em 05_qc.

Uso: python roda_unificado.py <config.json>
config: {"saida", "dxf_dir", "pdf", "rotulos", "transform_dir", "spotsys_csv", "tipologias", "estilo",
         "raquel_scripts", "arthur_pipeline", "pavimentos": [{"id", "escala", "extra": [...], "texto": bool}]}
"""
import os, sys, json, time, csv, re, subprocess, shutil
cfg = json.load(open(sys.argv[1], encoding='utf-8'))
PY = sys.executable; S = os.path.dirname(os.path.abspath(__file__))
U = cfg['saida']; os.makedirs(U, exist_ok=True)
os.environ.setdefault('SZI_ASAP_FONT', os.path.join(cfg['raquel_scripts'], '..', 'assets', 'Asap-VariableFont_wdth,wght.ttf'))
tempos = []


def etapa(pav, nome, fn):
    t = time.perf_counter()
    try:
        r = fn(); ok = 'ok'
    except Exception as e:
        r = '%s: %s' % (type(e).__name__, str(e)[:300]); ok = 'ERRO'
    tempos.append(dict(pavimento=pav, etapa=nome, segundos=round(time.perf_counter() - t, 1), status=ok, resultado=str(r)[:200]))
    print('[%s] %s: %ss %s %s' % (pav, nome, tempos[-1]['segundos'], ok, str(r)[:160]), flush=True)
    return ok == 'ok'


def run(*args):
    p = subprocess.run(list(map(str, args)), capture_output=True, text=True, encoding='utf-8', errors='replace')
    if p.returncode != 0:
        raise RuntimeError((p.stderr or p.stdout)[-400:])
    return (p.stdout.strip().splitlines() or [''])[-1]


# tipologias (grupos do Projeto Legal) e areas oficiais (SpotSys)
TIP = json.load(open(cfg['tipologias'], encoding='utf-8'))['grupos']
grupo_de = {u: g for g in TIP for u in g['unidades']}
spot = {r['code']: r for r in csv.DictReader(open(cfg['spotsys_csv'], encoding='utf-8-sig'))}
f2 = lambda v: float(v) if v not in (None, '', 'None') else 0.0

for P in cfg['pavimentos']:
    pav = P['id']; dxf = os.path.join(cfg['dxf_dir'], pav + '.dxf')
    png = os.path.join(U, pav + '.png'); quadro = os.path.join(U, pav + '_quadro.json')
    cfgr = os.path.join(U, 'cfg_%s.json' % pav); out_rec = os.path.join(U, 'TIPOLOGIAS_' + pav)
    trf = os.path.join(cfg['transform_dir'], pav + '_transform.json')

    # A. planta (esta skill)
    if not etapa(pav, 'A planta do DWG aprovado', lambda: run(
            PY, '-I', os.path.join(S, 'gera_humanizada_dwg.py'), dxf, png, '--cm-px', '0.9', '--fundo-transparente',
            '--estilo', cfg['estilo'], '--pdf-aprovado', cfg['pdf'], '--transform', trf, *P.get('extra', []))):
        continue
    # B. cfg do recorte (esta skill)
    if not etapa(pav, 'B cfg do recorte (DWG)', lambda: run(
            PY, '-I', os.path.join(S, 'gera_cfg_recorte.py'), dxf, png, quadro, cfgr, out_rec,
            '--rotulos', cfg['rotulos'], '--transform', trf)):
        continue
    # C. recorte (Raquel)
    etapa(pav, 'C recorte por unidade (Raquel)', lambda: run(
        PY, '-I', os.path.join(cfg['raquel_scripts'], 'recortar_tipologias.py'), cfgr, '--preview'))

    # D. texto/capacidade/solar (Raquel) - dados do SpotSys + capacidade dos grupos do Projeto Legal
    if P.get('texto'):
        dados = os.path.join(U, 'dados_%s.csv' % pav)
        Z = json.load(open(cfgr[:-5] + '_zonas.json', encoding='utf-8'))['zonas']
        with open(dados, 'w', newline='', encoding='utf-8') as fh:
            w = csv.writer(fh, delimiter=';'); w.writerow(['unidade', 'area_m2', 'tipologia', 'capacidade', 'externo', 'externo_m2'])
            for cod in sorted(Z):
                r = spot.get(cod); g = grupo_de.get(cod)
                if not r: continue
                gar, ter = f2(r.get('garden_total_area')), f2(r.get('terrace_balcony_total_area'))
                ext, ext_m2 = ('G', gar) if gar else ('S', ter) if ter else ('', '')
                w.writerow([cod, '%.2f' % (f2(r['total_area']) - gar - ter), g['grupo'] if g else '', g['capacidade'] if g else '',
                            ext, ('%.2f' % ext_m2) if ext else ''])

        def texto():
            run(PY, '-I', os.path.join(cfg['raquel_scripts'], 'texto_pavimento.py'), 'preparar', cfgr, dados, '--pav', pav)
            return run(PY, '-I', os.path.join(cfg['raquel_scripts'], 'texto_pavimento.py'), 'gerar', cfgr, dados, '--pav', pav,
                       '--modos', 'texto,capacidade,solar')
        etapa(pav, 'D texto/capacidade/solar (Raquel)', texto)

    # E. planta de tipologias + estudo solar (Arthur)
    def pecas_arthur():
        sys.path.insert(0, cfg['arthur_pipeline'])
        from PIL import Image
        from shapely.geometry import Polygon
        from shapely.ops import transform as stransform
        from pv import pecas
        Zj = json.load(open(cfgr[:-5] + '_zonas.json', encoding='utf-8')); Q = Zj['quadro']

        class Tm:   # metros (DWG) -> pixel do quadro gerado
            escala = Q['px_por_mm'] * 1000
            def geom(self, g):
                return stransform(lambda x, y, z=None: ((x * 1000 - Q['X0']) * Q['px_por_mm'], (Q['Y1'] - y * 1000) * Q['px_por_mm']), g)
        areas = {}
        for cod, zs in Zj['zonas'].items():
            for z in zs:
                pg = Polygon([(x / 1000, y / 1000) for x, y in z['pts_mm']])
                k = cod if z['tipo'] in ('unidade', 'mezanino') else {'garden': 'G.', 'sacada': 'S.'}[z['tipo']] + cod
                if k in areas: pg = areas[k]['poly'].union(pg)
                areas[k] = dict(poly=pg, tipo='unidade' if k == cod else z['tipo'], area_m2=f2(spot.get(cod, {}).get('total_area')) or (z['area_m2'] or 0))
        tips = {}
        for g in TIP:
            tips.setdefault(g['grupo'], []).extend(g['unidades'])
        base = Image.open(png).convert('RGBA')
        pecas.planta_tipologias(base, Tm(), areas, tips, titulo='CACHOEIRA SPOT · %s · GRUPOS DO PROJETO LEGAL (letras a definir)' % pav).save(
            os.path.join(U, '%s_PLANTA_DE_TIPOLOGIAS.png' % pav))
        pecas.estudo_solar(base).save(os.path.join(U, '%s_ESTUDO_SOLAR.png' % pav))
        return '%d areas' % len(areas)
    etapa(pav, 'E planta de tipologias + estudo solar (Arthur)', pecas_arthur)

    # F. entrega com nome padrao (uma por grupo: primeira unidade do grupo presente no pavimento)
    def entrega():
        dst = os.path.join(U, 'ENTREGA'); os.makedirs(dst, exist_ok=True); n = 0
        feitos = set()
        for f in sorted(os.listdir(out_rec)) if os.path.isdir(out_rec) else []:
            cod = f[:-4]
            if not re.fullmatch(r'\d{3}|L\d', cod): continue
            g = grupo_de.get(cod)
            nome = 'GRUPO %s (%s) - SEM COTA.png' % (g['grupo'], ', '.join(g['unidades'])) if g else 'UNIDADE %s - SEM COTA.png' % cod
            if nome in feitos or os.path.exists(os.path.join(dst, nome)): continue
            feitos.add(nome); shutil.copyfile(os.path.join(out_rec, f), os.path.join(dst, nome)); n += 1
        return '%d pecas' % n
    etapa(pav, 'F entrega (nome padrao)', entrega)

with open(os.path.join(U, 'tempos_unificado.csv'), 'w', newline='', encoding='utf-8-sig') as fh:
    w = csv.DictWriter(fh, fieldnames=list(tempos[0]), delimiter=';'); w.writeheader(); w.writerows(tempos)
print('TOTAL', round(sum(t['segundos'] for t in tempos), 1), 's')
