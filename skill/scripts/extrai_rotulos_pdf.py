"""Extrai do PDF vetorial do projeto aprovado os pares (unidade, area) e a posicao dos rotulos.
Uso: python extrai_rotulos_pdf.py <aprovado.pdf> <paginas ex: 4,5,6,7,8,9> <spotsys.csv> <saida.json> <saida_check.csv>
Para cada unidade do SpotSys verifica se cada componente de area (coberta, descoberta, mezanino) aparece
no PDF ao lado do codigo da unidade. Nao interpreta: so registra encontrado/nao encontrado."""
import sys, re, json, csv, fitz
pdf, pages, spot, out_json, out_csv = sys.argv[1:6]
pages = [int(p) for p in pages.split(',')]
d = fitz.open(pdf)
pat = re.compile(r'(?:LOJA\s*0?(\d)|(\d{3}))\s*(?:Sacada|GARDEN|APTO)?\s*\n?\s*(\d{1,3},\d{2})\s*m', re.I)
found = []
for pg in pages:
    p = d[pg - 1]
    for b in p.get_text('blocks'):
        t = b[4]
        for m in pat.finditer(t):
            code = ('L' + m.group(1)) if m.group(1) else m.group(2)
            found.append(dict(page=pg, code=code, area=float(m.group(3).replace(',', '.')), bbox=[round(x, 1) for x in b[:4]]))
# rotulos de area descoberta/mezanino: le a caixa de texto logo apos 'NNN Sacada|GARDEN' ou 'MEZANINO NNN'
# e exige o padrao exato '<codigo> <tipo> <x,xx> m2' (evita confundir com cotas proximas)
for pg in pages:
    pgo = d[pg - 1]; ws = pgo.get_text('words')
    for i, w in enumerate(ws):
        t = w[4]; nxt = ws[i + 1][4].upper() if i + 1 < len(ws) else ''; prv = ws[i - 1][4].upper() if i else ''
        if not re.fullmatch(r'\d{3}', t) or not (nxt in ('SACADA', 'GARDEN') or prv in ('MEZANINO', 'GARDEN')): continue
        box = ' '.join(pgo.get_textbox(fitz.Rect(w[:4]) + (-70, -5, 80, 24)).split())
        m = re.search(r'(?:(?:MEZANINO|GARDEN)\s+)?' + t + r'\s*(Sacada|GARDEN)?\s+(\d{1,3},\d{2})\s*m', box, re.I)
        if m: found.append(dict(page=pg, code=t, tipo=(m.group(1) or prv).upper(), area=float(m.group(2).replace(',', '.')), bbox=[round(x, 1) for x in w[:4]], via='rotulo'))
json.dump(found, open(out_json, 'w', encoding='utf-8'), indent=1)
def f(v):
    try: return round(float(v), 2)
    except ValueError: return None
rows = []
for s in csv.DictReader(open(spot, encoding='utf-8')):
    c = s['code']; tot = f(s['total_area']); mez = f(s['mezzanine_total_area']); desc = f(s['garden_total_area']) or f(s['terrace_balcony_total_area'])
    vals = sorted({x['area'] for x in found if x['code'] == c})
    cob = round(tot - (desc or 0), 2) if not c.startswith('L') else tot
    exp = {'cob': cob, 'desc': desc, 'mez': mez}
    # soma das partes descobertas por pagina (pranchas repetem rotulos em plantas-chave)
    somas = {}
    for x in found:
        if x['code'] == c and x.get('tipo') in ('SACADA', 'GARDEN'):
            somas.setdefault(x['page'], {})[(x['area'], round(x['bbox'][0]), round(x['bbox'][1]))] = x['area']
    somas = [round(sum(v.values()), 2) for v in somas.values()]
    hits = {}
    for k, v in exp.items():
        if v is None: continue
        # coberta pode estar dividida em terreo + mezanino no PDF
        ok = v in vals or (k == 'cob' and mez and round(v - mez, 2) in vals) or (k == 'desc' and any(abs(sum(p) - v) < 0.015 for p in [(a, b) for a in vals for b in vals if a < b and a < v and b < v]) and False)
        if k == 'desc' and not ok and any(abs(sd - v) < 0.015 for sd in somas): ok = 'OK_SOMA_PARTES'
        hits[k] = ok if isinstance(ok, str) else ('OK' if ok else 'NAO_ENCONTRADO')
    st = 'OK' if hits and all(h.startswith('OK') for h in hits.values()) else 'VERIFICAR'
    rows.append(dict(code=c, valores_pdf=';'.join(map(str, vals)), esperado=json.dumps(exp), resultado=json.dumps(hits), status=st))
w = csv.DictWriter(open(out_csv, 'w', newline='', encoding='utf-8-sig'), fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
print('rotulos extraidos', len(found), '| unidades', len(rows), '| OK', sum(r['status'] == 'OK' for r in rows))
for r in rows:
    if r['status'] != 'OK': print(r)
