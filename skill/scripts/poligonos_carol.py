"""Adaptador (fase 2): poligonos da segmentacao da skill da Carol (seazone-tech/skill-atualizar-humanizada, planta.py)
-> recorte por unidade na humanizada + pins do 360, no referencial do registro ja validado (sobrepoe_aprovado.py).

Le SO as saidas da Carol (saida/trabalho/pagNN.json + pagNN-rotulos.npz); nao importa nem copia o codigo dela.
Cadeia de coordenadas:  px do raster da Carol --(x0 + u/K, K = res/pt_m)--> pt do PDF aprovado
                        --(registro: ((x - cx)*zoom*sx + tx) / fator_reducao * largura_img/largura_img_registro)--> px da imagem.
O PDF usado pela Carol tem que manter as coordenadas da pagina original (recorte por redacao, nao por show_pdf_page).

Regras de anexo (SpotSys/aprovado mandam): sanitario orfao descartado se a unidade sozinha ja = A.COMP (3%); se o SpotSys tem
garden/terraco e o recorte nao tem anexo externo, entra o anexo livre vizinho de area mais proxima (0,6-1,6x). Tudo vai para o log.
Por unidade: mascara da unidade + anexos com o mesmo numero (sanitario, terraco/garden, jardineira), dilatada ate a face
externa das paredes (--folga-m) e fechada; contorno simplificado (--tol-m); recorte RGBA com fundo transparente.

Uso: py poligonos_carol.py <config.json>
config: {"empreendimento": "BATEL-SPOT", "rotulo": "TESTE", "saida": "...", "carol_trabalho": ".../saida/trabalho",
         "spotsys_csv": "...", "zoom_registro": 2.0,
         "pavimentos": [{"id": "TERREO", "pagina_carol": 1, "andares": [1], "imagem": "...png",
                         "registro": "05_qc/TERREO_registro.json"}]}
Saidas: 02_UNIDADES/<PAV>/<EMP>_<PAV>_UN-<codigo>_<rotulo>.png, 03_CONFERENCIA/<PAV>_poligonos.jpg (contornos sobre a planta),
        03_CONFERENCIA/recortes_carol_log.csv, 04_PUBLICACAO/pins_360_<rotulo>.json (polygon_vertices 0-1 por szi_unit_id).
NAO publica nada. A trava de validacao humana (etapa 7 e 9 da SKILL.md) continua valendo.
"""
import sys, os, json, csv
import numpy as np, cv2
from PIL import Image
Image.MAX_IMAGE_PIXELS = None

cfg = json.load(open(sys.argv[1], encoding='utf-8'))
FOLGA_M = cfg.get('folga_m', 0.15); TOL_M = cfg.get('tol_m', 0.02); ZOOM = cfg.get('zoom_registro', 2.0)
EMP, ROT, OUT = cfg['empreendimento'], cfg.get('rotulo', 'TESTE'), cfg['saida']
spot = {r['code']: r for r in csv.DictReader(open(cfg['spotsys_csv'], encoding='utf-8'))}
ANEXOS = ('sanitario', 'terraco', 'jardineira', 'jardim')


def grava(caminho, arr):  # cv2.imwrite falha calado em caminho com acento
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    cv2.imencode(os.path.splitext(caminho)[1], arr)[1].tofile(caminho)


def le(caminho):
    return cv2.imdecode(np.fromfile(caminho, np.uint8), cv2.IMREAD_UNCHANGED)


log, pins, vistos = [], [], set()
for pv in cfg['pavimentos']:
    meta = json.load(open(os.path.join(cfg['carol_trabalho'], f"pag{pv['pagina_carol']:02d}.json"), encoding='utf-8'))
    lab = np.load(os.path.join(cfg['carol_trabalho'], f"pag{pv['pagina_carol']:02d}-rotulos.npz"))['lab']
    K = meta['res'] / meta['pt_m']; RES = meta['res']
    R = json.load(open(pv['registro'], encoding='utf-8'))
    (sx, _, tx), (_, sy, ty) = R['A']; fat = R['fator_reducao']; cx, cy = R['clip_pt'][:2]
    im = le(pv['imagem'])
    if im.shape[2] == 3:
        im = np.dstack([im, np.full(im.shape[:2], 255, np.uint8)])
    H, W = im.shape[:2]
    larg_reg = Image.open(R['imagem']).size[0] if os.path.exists(R['imagem']) else pv['largura_registro']
    esc = W / larg_reg
    # px Carol -> px imagem (afim por eixo)
    ax, bx = esc * ZOOM * sx / (fat * K), esc * (ZOOM * sx * (meta['x0'] - cx) + tx) / fat
    ay, by = esc * ZOOM * sy / (fat * K), esc * (ZOOM * sy * (meta['y0'] - cy) + ty) / fat
    cm_px_img = 100 / (RES * ax)
    reg = meta['regioes']
    por_un = {}
    for n, r in reg.items():
        u = r.get('unidade')
        if u is None or 'id' not in r: continue
        if r['tipo'] == 'unidade' or r['tipo'] in ANEXOS:
            por_un.setdefault(str(u), []).append(r)
    # regras de anexo pela hierarquia (SpotSys = aprovado manda; a segmentacao so propoe)
    EXT = ('terraco', 'jardim', 'jardineira')
    ajustes, notas0 = {}, {}
    # 0) grama/jardineira vai para a unidade com a MAIOR divisa (unidade + terraco + sanitario dela), nao pelo rotulo mais proximo
    nomes = sorted(por_un); core = np.zeros(lab.shape, np.int32)
    for k, nn in enumerate(nomes, 1):
        core[np.isin(lab, [r['id'] for r in por_un[nn] if r['tipo'] in ('unidade', 'terraco', 'sanitario')])] = k
    pad = int(0.35 * RES)
    for r in [r for r in reg.values() if r['tipo'] in ('jardim', 'jardineira') and 'id' in r]:
        ys, xs = np.nonzero(lab == r['id'])
        if not len(xs): continue
        y0_, y1_, x0_, x1_ = max(ys.min() - pad, 0), ys.max() + pad + 1, max(xs.min() - pad, 0), xs.max() + pad + 1
        dil = cv2.dilate((lab[y0_:y1_, x0_:x1_] == r['id']).astype(np.uint8), np.ones((pad | 1,) * 2, np.uint8)) > 0
        cnt = np.bincount(core[y0_:y1_, x0_:x1_][dil], minlength=len(nomes) + 1); cnt[0] = 0
        novo = nomes[cnt.argmax() - 1] if cnt.max() >= 0.5 * RES else None
        velho = None if r.get('unidade') is None else str(r['unidade'])
        if novo != velho:
            if velho in por_un and r in por_un[velho]:
                por_un[velho].remove(r); notas0.setdefault(velho, []).append(f"{r['tipo']} {r['area_m2']} m2 retirado (divisa maior com {novo})")
            if novo:
                por_un[novo].append(r); notas0.setdefault(novo, []).append(f"{r['tipo']} {r['area_m2']} m2 anexado pela divisa")
            r['unidade'] = novo
    livres = [r for r in reg.values() if r['tipo'] in EXT and r.get('unidade') is None and 'id' in r]
    for nn, regs in por_un.items():
        s0 = spot.get(f"{pv['andares'][0]}{nn[-2:]}", {})
        if not s0: continue
        G = float(s0.get('garden_total_area') or 0) + float(s0.get('terrace_balcony_total_area') or 0)
        priv = float(s0['total_area']) - G
        a_u = sum(r['area_m2'] for r in regs if r['tipo'] == 'unidade')
        nota = list(notas0.get(nn, []))
        # 1) sanitario "orfao" (classificado so por vizinhanca) sobra quando a unidade sozinha ja tem a A. COMP.
        if priv and abs(a_u / priv - 1) <= 0.03:
            fora = [r for r in regs if r['tipo'] == 'sanitario' and r.get('orfao')]
            if fora:
                regs[:] = [r for r in regs if r not in fora]
                nota.append(f"sanitario orfao descartado ({', '.join(str(r['area_m2']) for r in fora)} m2; unidade {a_u:.2f} = A.COMP {priv:.2f})")
        # 2) SpotSys tem area externa e o recorte nao tem anexo externo: anexo livre vizinho com area mais proxima
        if G > 0 and not any(r['tipo'] in EXT for r in regs):
            mu = cv2.dilate(np.isin(lab, [r['id'] for r in regs if r['tipo'] == 'unidade']).astype(np.uint8),
                            np.ones((int(0.35 * RES) | 1,) * 2, np.uint8)) > 0
            cand = [r for r in livres if (mu & (lab == r['id'])).any()]
            cand = [r for r in cand if 0.6 <= r['area_m2'] / G <= 1.6]
            if cand:
                r = min(cand, key=lambda r: abs(r['area_m2'] - G)); regs.append(r); livres.remove(r)
                nota.append(f"anexo atribuido pelo SpotSys: {r['tipo']} {r['area_m2']} m2 (SpotSys {G} m2)")
        ext = sum(r['area_m2'] for r in regs if r['tipo'] in EXT)
        if G > 0 and ext:
            nota.append(f'anexo externo {ext:.2f} m2 / SpotSys {G} m2 = {ext / G:.2f}')
        ajustes[nn] = '; '.join(nota)
    conf = cv2.cvtColor(im[:, :, :3], cv2.COLOR_BGR2GRAY); conf = cv2.cvtColor((conf * 0.6 + 100).astype(np.uint8), cv2.COLOR_GRAY2BGR)
    kf = int(round(FOLGA_M * RES)) | 1
    for nn, regs in sorted(por_un.items()):
        if not any(r['tipo'] == 'unidade' for r in regs): continue
        m = np.isin(lab, [r['id'] for r in regs]).astype(np.uint8)
        m = cv2.dilate(m, np.ones((kf, kf), np.uint8))
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((kf * 2 | 1, kf * 2 | 1), np.uint8))
        cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        c = max(cs, key=cv2.contourArea)
        c = cv2.approxPolyDP(c, TOL_M * RES, True)[:, 0, :].astype(float)
        P = np.c_[c[:, 0] * ax + bx, c[:, 1] * ay + by]
        Pi = np.round(P).astype(np.int32)
        x0, y0 = np.maximum(Pi.min(0), 0); x1, y1 = np.minimum(Pi.max(0) + 1, [W, H])
        mk = np.zeros((y1 - y0, x1 - x0), np.uint8); cv2.fillPoly(mk, [Pi - [x0, y0]], 255)
        crop = im[y0:y1, x0:x1].copy(); crop[:, :, 3] = np.minimum(crop[:, :, 3], mk)
        a_unid = sum(r['area_m2'] for r in regs if r['tipo'] == 'unidade')
        tem_anexo = sorted({r['tipo'] for r in regs if r['tipo'] != 'unidade'})
        cor = (40, 40, 220)
        for andar in pv['andares']:
            cod = f'{andar}{nn[-2:]}'
            vistos.add(cod)
            s = spot.get(cod, {})
            arq = os.path.join(OUT, '02_UNIDADES', pv['id'], f"{EMP}_{pv['id']}_UN-{cod}_{ROT}.png")
            grava(arq, crop)
            garden_spot = float(s.get('garden_total_area') or 0) + float(s.get('terrace_balcony_total_area') or 0)
            obs = []
            if not s: obs.append('codigo fora do SpotSys')
            if garden_spot > 0 and not ({'terraco', 'jardim', 'jardineira'} & set(tem_anexo)): obs.append(f'FALHA: SpotSys tem garden/terraco {garden_spot} m2, recorte sem anexo')
            if s and not s.get('id'): obs.append('sem id no SpotSys')
            if ajustes.get(nn): obs.append(ajustes[nn])
            log.append(dict(pavimento=pv['id'], codigo=cod, szi_unit_id=s.get('id', ''), arquivo=os.path.basename(arq),
                            largura_px=x1 - x0, altura_px=y1 - y0, area_unidade_carol_m2=round(a_unid, 2),
                            area_poligono_img_m2=round(cv2.contourArea(P.astype(np.float32)) * (cm_px_img / 100) ** 2, 2),
                            anexos=';'.join(tem_anexo), observacao='; '.join(obs)))
            pins.append(dict(szi_unit_id=s.get('id', ''), codigo=cod, planta=os.path.basename(pv['imagem']), pin_type='polygon',
                             polygon_vertices=[dict(x=round(px / W, 5), y=round(py / H, 5)) for px, py in P],
                             x=round(P[:, 0].mean() / W, 5), y=round(P[:, 1].mean() / H, 5)))
        cv2.polylines(conf, [Pi], True, cor, max(3, W // 2500))
        cxp, cyp = Pi.mean(0).astype(int)
        cv2.putText(conf, nn, (int(cxp) - 60, int(cyp)), cv2.FONT_HERSHEY_SIMPLEX, W / 3000, (0, 0, 200), max(3, W // 2000))
    grava(os.path.join(OUT, '03_CONFERENCIA', f"{pv['id']}_poligonos.jpg"), cv2.resize(conf, None, fx=2400 / W, fy=2400 / W, interpolation=cv2.INTER_AREA))
    grava(os.path.join(OUT, '03_CONFERENCIA', f"{pv['id']}_poligonos_alta.jpg"), conf)

os.makedirs(os.path.join(OUT, '03_CONFERENCIA'), exist_ok=True); os.makedirs(os.path.join(OUT, '04_PUBLICACAO'), exist_ok=True)
with open(os.path.join(OUT, '03_CONFERENCIA', 'recortes_carol_log.csv'), 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.DictWriter(f, fieldnames=log[0].keys()); w.writeheader(); w.writerows(log)
json.dump(pins, open(os.path.join(OUT, '04_PUBLICACAO', f'pins_360_{ROT}.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
falta = sorted(set(spot) - vistos); extra = sorted(vistos - set(spot))
print(f'recortes {len(log)} | unidades SpotSys {len(spot)} | C8 {"OK" if not falta and not extra else "FALHA"} | faltam {falta} | extras {extra}')
print('FALHAS:', [(l['codigo'], l['observacao']) for l in log if 'FALHA' in l['observacao']])
print('ajustes:', [(l['codigo'], l['observacao']) for l in log if l['observacao'] and 'FALHA' not in l['observacao']][:20])
