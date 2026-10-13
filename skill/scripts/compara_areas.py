"""Compara quadro de areas aprovado (xlsx) x export SpotSys (csv). Uso:
python compara_areas.py <areas.xlsx> <aba> <spotsys.csv> <saida.csv>
Colunas esperadas na aba (Cachoeira/Planilha1): A=pavimento B=unidade C/D=R00 cob/desc E/F=R03 cob/desc O=observacao."""
import sys, csv, openpyxl, re
xlsx, aba, spot, out = sys.argv[1:5]
ws = openpyxl.load_workbook(xlsx, data_only=True)[aba]
def num(v):
    try: return round(float(v), 2)
    except (TypeError, ValueError): return None
apr = {}
for r in ws.iter_rows(min_row=1, values_only=True):
    if not r[1]: continue
    code = str(r[1]).strip().upper().replace('LOJA 0', 'L').replace('.0', '')
    if not re.fullmatch(r'L\d|\d{3}', code): continue
    apr[code] = dict(pav=r[0], r00c=num(r[2]), r00d=num(r[3]), r03c=num(r[4]), r03d=num(r[5]), obs=r[14] if len(r) > 14 else '')
rows = []
for s in csv.DictReader(open(spot, encoding='utf-8')):
    c = s['code']; a = apr.get(c)
    tot = num(s['total_area']); desc = num(s['garden_total_area']) or num(s['terrace_balcony_total_area']) or 0.0
    if not a:
        rows.append(dict(code=c, status='SEM_REF_APROVADO')); continue
    r03d = a['r03d'] or 0.0
    cob_spot = round(tot - desc, 2) if not c.startswith('L') else tot
    d_cob = round(cob_spot - a['r03c'], 2) if a['r03c'] is not None else None
    d_desc = round(desc - r03d, 2) if not c.startswith('L') else None
    st = 'OK' if (d_cob is not None and abs(d_cob) <= 0.01 and (d_desc is None or abs(d_desc) <= 0.01)) else 'DIVERGENTE'
    lay = round(a['r03c'] - a['r00c'], 2) if a['r00c'] is not None else None
    rows.append(dict(code=c, pavimento=s['floor'], spotsys_total=tot, spotsys_desc=desc, spotsys_cob=cob_spot,
        aprov_r03_cob=a['r03c'], aprov_r03_desc=r03d, dif_cob=d_cob, dif_desc=d_desc, status=st,
        r00_cob=a['r00c'], delta_cob_r00_r03=lay, obs_quadro=a['obs'], is_outdated_area=s['is_outdated_area'], n_imgs=s['n_imgs']))
missing = sorted(set(apr) - {r['code'] for r in rows})
keys = list(dict.fromkeys(k for r in rows for k in r))
w = csv.DictWriter(open(out, 'w', newline='', encoding='utf-8-sig'), fieldnames=keys); w.writeheader(); w.writerows(rows)
n = len(rows); div = [r for r in rows if r['status'] != 'OK']
print(f'unidades SpotSys={n} aprovadas no quadro={len(apr)} OK={n-len(div)} divergentes={len(div)} so_no_quadro={missing}')
for r in div: print(r)
