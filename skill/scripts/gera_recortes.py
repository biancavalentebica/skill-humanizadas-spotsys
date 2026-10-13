"""Gera a imagem individual de cada unidade a partir da humanizada sem texto + poligono do projeto aprovado.

Para cada unidade da prancha:
  poligonos do aprovado (celulas_*.json) -> transformacao registrada (registro/*_transform.json) -> mascara
  na humanizada -> folga de parede (25 cm) -> recorte com fundo transparente (geometria intacta: so recorta).
Partes da unidade distantes do corpo principal (> 1,5 m) sao descartadas e registradas (sinal de rotulo
duplicado/trocado na prancha).

Uso: python gera_recortes.py <config.json>
config: {"empreendimento": "CACHOEIRA-SPOT", "revisao": "R01", "saida": "...",
         "pavimentos": [{"id": "PAV-02", "imagem": "...png", "celulas": "...json", "registro": "..._transform.json",
                         "escala": 100}],
         "duplex": [{"id": "PAV-01+MEZ", "inferior": "PAV-01", "superior": "MEZ"}]}
"""
import sys, json, os
import cv2, numpy as np

cfg = json.load(open(sys.argv[1], encoding='utf-8'))
EMP, REV, OUT = cfg['empreendimento'], cfg['revisao'], cfg['saida']
FOLGA_CM, MARGEM_CM, DESCARTE_CM = 25, 20, 150
log = []


def recorta(pav):
    im = cv2.imread(pav['imagem'], cv2.IMREAD_UNCHANGED)
    if im.shape[2] == 3:
        im = np.dstack([im, np.full(im.shape[:2], 255, np.uint8)])
    C = json.load(open(pav['celulas'], encoding='utf-8')); R = json.load(open(pav['registro'], encoding='utf-8'))
    A = np.array(R['A_pdfpx_para_img']); x0, y0 = C['clip_pt'][:2]; esc = C['esc']; cm_px = R['cm_por_px_imagem']
    # paredes da humanizada (componentes pretos grandes) e area livre
    g = cv2.cvtColor(im[:, :, :3], cv2.COLOR_BGR2GRAY)
    ink = ((g <= 40) & (im[:, :, 3] > 0)).astype(np.uint8)
    n_, lab_, st_, _ = cv2.connectedComponentsWithStats(ink, 8)
    kk = np.zeros(n_, bool); kk[1:] = np.maximum(st_[1:, 2], st_[1:, 3]) > im.shape[1] * 0.02
    paredes = kk[lab_]
    livre = (~paredes & (im[:, :, 3] > 0)).astype(np.uint8)
    ret = lambda cm: cv2.getStructuringElement(cv2.MORPH_RECT, (max(3, int(round(2 * cm / cm_px)) | 1),) * 2)

    def encaixa_nas_paredes(principal_full):
        """Ajusta a mascara a geometria real da humanizada: area livre da unidade (a partir do miolo do poligono
        aprovado) + as paredes que a envolvem. Corta na face externa da parede: nada do vizinho entra.
        Trabalha so numa janela ao redor da unidade (rapido)."""
        ys_, xs_ = np.where(principal_full > 0)
        mgp = int(60 / cm_px) + 4
        X0, Y0 = max(0, xs_.min() - mgp), max(0, ys_.min() - mgp)
        X1, Y1 = min(im.shape[1], xs_.max() + mgp + 1), min(im.shape[0], ys_.max() + mgp + 1)
        principal = principal_full[Y0:Y1, X0:X1]; liv = livre[Y0:Y1, X0:X1]; par_ = paredes[Y0:Y1, X0:X1]
        Z = cv2.dilate(principal, ret(35))
        sem = cv2.erode(principal, ret(30)) & (liv * 255)
        nl, ll = cv2.connectedComponents(((liv > 0) & (Z > 0)).astype(np.uint8), connectivity=4)
        manter = np.unique(ll[(sem > 0)]); manter = manter[manter > 0]
        R = np.isin(ll, manter) & (cv2.dilate(principal, ret(12)) > 0)   # porta aberta para o corredor: no maximo 12 cm
        W = par_ & (cv2.dilate(R.astype(np.uint8), ret(20)) > 0) & (Z > 0)
        m = ((R | W) * 255).astype(np.uint8)
        cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        cheio = np.zeros_like(m)
        if cs:
            big = max(cs, key=cv2.contourArea)
            for c in cs:
                if cv2.contourArea(c) >= 0.02 * cv2.contourArea(big): cv2.drawContours(cheio, [c], -1, 255, -1)
        out = np.zeros_like(principal_full); out[Y0:Y1, X0:X1] = cheio
        return out

    res = {}
    for code, cel in C['celulas'].items():
        reg = dict(pavimento=pav['id'], unidade=code, cm_por_px=cm_px, anisotropia_pavimento=R['anisotropia'],
                   chamfer_mediana_cm_pavimento=R['chamfer_mediana_cm'])
        if 'erro' in cel or not cel.get('poligonos_pt'):
            reg['status'] = 'PENDENTE'; reg['motivo'] = 'sem poligono no aprovado'; log.append(reg); continue
        m = np.zeros(im.shape[:2], np.uint8)
        partes = []
        for poly in cel['poligonos_pt']:
            P = np.array([[(x - x0) * esc, (y - y0) * esc, 1] for x, y in poly]) @ A.T
            pm = np.zeros_like(m); cv2.fillPoly(pm, [np.round(P).astype(np.int32)], 255)
            partes.append(pm)
        partes.sort(key=lambda p: -int((p > 0).sum()))
        principal = partes[0].copy()
        descartadas = 0
        for p in partes[1:]:
            d = cv2.distanceTransform(255 - principal, cv2.DIST_L2, 5)
            if d[p > 0].min() * cm_px <= DESCARTE_CM:
                principal = np.maximum(principal, p)
            else:
                descartadas += 1
        # poligono da unidade na planta do pavimento, normalizado 0-1 (formato dos pins do 360)
        cs, _ = cv2.findContours(principal, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cmax = max(cs, key=cv2.contourArea)
        ap = cv2.approxPolyDP(cmax, max(2.0, 5 / cm_px), True)[:, 0, :]
        reg['poligono_norm'] = [{'x': round(float(x) / im.shape[1], 5), 'y': round(float(y) / im.shape[0], 5)} for x, y in ap]
        reg['imagem_pavimento'] = pav['imagem']
        m = encaixa_nas_paredes(principal)
        area_pol = int((principal > 0).sum()); area_m = int((m > 0).sum())
        reg['encaixe_razao_area'] = round(area_m / max(1, area_pol), 3)
        if not (0.85 <= area_m / max(1, area_pol) <= 1.6):  # encaixe falhou: volta ao poligono com folga e registra
            reg['encaixe'] = 'falhou_poligono_com_folga'
            m = cv2.dilate(principal, ret(FOLGA_CM))
        else:
            reg['encaixe'] = 'paredes'
        ys, xs = np.where(m > 0)
        mg = int(MARGEM_CM / cm_px)
        bx0, by0 = max(0, xs.min() - mg), max(0, ys.min() - mg)
        bx1, by1 = min(im.shape[1], xs.max() + mg + 1), min(im.shape[0], ys.max() + mg + 1)
        cut = im[by0:by1, bx0:bx1].copy()
        mm = m[by0:by1, bx0:bx1]  # borda reta, sem suavizacao
        cut[:, :, 3] = (cut[:, :, 3].astype(np.uint16) * mm // 255).astype(np.uint8)
        reg.update(origem_px=[int(bx0), int(by0)], largura_px=int(cut.shape[1]), altura_px=int(cut.shape[0]), partes_descartadas=descartadas,
                   frac_mascara_fora_da_imagem=round(float(((m > 0) & (im[:, :, 3] == 0)).sum()) / max(1, (m > 0).sum()), 3))
        res[code] = (cut, reg)
    return res


def salva(img, rel):
    p = os.path.join(OUT, rel); os.makedirs(os.path.dirname(p), exist_ok=True)
    cv2.imwrite(p, img, [cv2.IMWRITE_PNG_COMPRESSION, 6]); return p

por_pav = {}
for pav in cfg['pavimentos']:
    por_pav[pav['id']] = recorta(pav)
    # imagem geral do pavimento (copia da humanizada sem texto, renomeada no padrao)
    geral = cv2.imread(pav['imagem'], cv2.IMREAD_UNCHANGED)
    salva(geral, f"01_PAVIMENTOS/{EMP}_{pav['id']}_GERAL_HUM-SEM-TEXTO_{REV}.png")

duplex_inf = {d['inferior']: d for d in cfg.get('duplex', [])}
duplex_sup = {d['superior'] for d in cfg.get('duplex', [])}
for pid, unids in por_pav.items():
    if pid in duplex_sup:
        continue
    for code, (cut, reg) in sorted(unids.items()):
        nome_un = f"UN-{code}"
        if pid in duplex_inf:
            d = duplex_inf[pid]; sup = por_pav.get(d['superior'], {})
            if code in sup:
                cut2_orig, reg2 = sup[code]
                f = reg2['cm_por_px'] / reg['cm_por_px']
                cut2 = cut2_orig  # mesma escala real nos dois niveis
                cut2 = cv2.resize(cut2_orig, (int(cut2_orig.shape[1] * f), int(cut2_orig.shape[0] * f)), interpolation=cv2.INTER_AREA if f < 1 else cv2.INTER_CUBIC)
                gap = int(60 / reg['cm_por_px'])
                H = max(cut.shape[0], cut2.shape[0]); W = cut.shape[1] + gap + cut2.shape[1]
                comb = np.zeros((H, W, 4), np.uint8)
                comb[(H - cut.shape[0]) // 2:(H - cut.shape[0]) // 2 + cut.shape[0], :cut.shape[1]] = cut
                comb[(H - cut2.shape[0]) // 2:(H - cut2.shape[0]) // 2 + cut2.shape[0], cut.shape[1] + gap:] = cut2
                p = salva(comb, f"02_UNIDADES/{d['id']}/{EMP}_{d['id']}_{nome_un}_HUM-SEM-TEXTO_{REV}.png")
                salva(cut, f"02_UNIDADES/{d['id']}/niveis/{EMP}_{pid}_{nome_un}_HUM-SEM-TEXTO_{REV}.png")
                salva(cut2_orig, f"02_UNIDADES/{d['id']}/niveis/{EMP}_{d['superior']}_{nome_un}_HUM-SEM-TEXTO_{REV}.png")
                reg = dict(reg, pavimento=d['id'], arquivo=p, largura_px=W, altura_px=H, nivel_superior=reg2)
                log.append(reg); continue
            reg = dict(reg, motivo_duplex='unidade sem nivel superior no aprovado')
        p = salva(cut, f"02_UNIDADES/{pid}/{EMP}_{pid}_{nome_un}_HUM-SEM-TEXTO_{REV}.png")
        log.append(dict(reg, arquivo=p))
json.dump(log, open(os.path.join(OUT, '03_CONFERENCIA', 'recortes_log.json') if os.makedirs(os.path.join(OUT, '03_CONFERENCIA'), exist_ok=True) is None else '', 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print(json.dumps(dict(unidades_geradas=sum(1 for r in log if 'arquivo' in r), pendentes=[r['unidade'] for r in log if r.get('status') == 'PENDENTE'],
                      com_partes_descartadas=[r['unidade'] for r in log if r.get('partes_descartadas')])))
