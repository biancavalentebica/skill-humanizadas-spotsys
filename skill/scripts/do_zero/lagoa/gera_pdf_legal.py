"""PDF vetorial para a skill da Carol a partir do PDF LEGAL (executivo da pasta 07, rev. 27/11/2024), no quadro do
lancamento (mesmo quadro do executivo registrado). Le tudo da prancha:
- paredes (traco preto 1,8) preenchidas; muros, muretas e gradis (traco 0,6 vermelho fora das esquadrias)
- esquadrias da fachada (traco 0,6 onde o executivo tem vidro) -> linha media + barreira
- portas (arcos do traco 0,24, raio 0,5-1,2 m) e suas folhas -> curvas (a skill fecha o vao pelo arco)
- degraus das escadas, loucas e plataforma (traco 0,24 / verde) -> finos
- ambientes: flood das paredes+muros+esquadrias+portas, nomeados pelo executivo (mesma posicao) ou pela leitura da
  prancha (NOMES_MANUAIS, em px do quadro), com o codigo do SpotSys nos alojamentos
Saidas: <pdf> (pagina por pavimento), <P>_legal_amb.npz/.json (mesmo formato do do_zero/_amb), barreiras.json
Uso: py gera_pdf_legal.py <saida.pdf> TER 02P"""
import sys, json, re, numpy as np, cv2, fitz
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
DZ = '../do_zero/'
PT_M = 56.69; M_PX = 0.004022375816200381; K = PT_M * M_PX
pdf_out, *pavs = sys.argv[1:]
PAG = {'TER': 1, '02P': 2}
# codigo do executivo -> codigo SpotSys (o 01 do legal e a unidade 11 do SpotSys; o 11 do 2o pav. e a 22)
COD = {'TER': {'01': '11'}, '02P': {'11': '22'}}
# ambientes que o executivo DWG nao tem (ou mudou): nome e ponto (px do quadro do lancamento), lidos na prancha legal
ESCADAS = {'TER': [(3292, 482, 3872, 890), (3778, 2940, 4085, 3818), (4085, 2940, 4410, 3818)], '02P': [(3380, 1990, 3700, 2990), (3700, 1990, 4010, 2990)]}
NOMES_MANUAIS = {
    'TER': [('ADMINISTRACAO', 2700, 1500), ('ROUPARIA', 2420, 2060), ('PNE', 2790, 2060), ('RECEPCAO', 3600, 1600),
            ('ESCADA_ACESSO', 3560, 690), ('PLATAFORMA', 4030, 980), ('ESCADA', 3930, 3400), ('ESCADA', 4250, 3400), ('CIRCULACAO', 3600, 2400)],
    '02P': [('CIRCULACAO', 3000, 1750), ('PNE', 2060, 1190), ('ESCADA', 3540, 2600), ('ESCADA', 3860, 2600)],
}
doc = fitz.open(); barreiras = {}; src = fitz.open('legal_work.pdf')

def contornos(mask, simpl=1.5):
    cs, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    return [cv2.approxPolyDP(c, simpl, True)[:, 0, :] for c in cs if len(c) >= 3]
def poly(sh, pts):
    p = [fitz.Point(x * K, y * K) for x, y in pts]; sh.draw_polyline(p + [p[0]])
def interno(m):
    d = cv2.distanceTransform(m.astype(np.uint8), cv2.DIST_L2, 5); y, x = np.unravel_index(np.argmax(d), d.shape); return x, y

for npag, P in enumerate(pavs, start=1):
    A = np.load(DZ + P + '_amb.npz'); J = json.load(open(DZ + P + '_amb.json', encoding='utf8'))
    ids0, vid0, sol0 = A['ids'], A['vidro'], A['soleira']; H, W = ids0.shape
    Z = np.load(f'legal_{P}_masks.npz'); g = lambda k: (cv2.dilate((Z[k] > 15).astype(np.uint8), np.ones((3, 3), np.uint8)) > 0) if k in Z.files else np.zeros((H, W), bool)
    R = json.load(open(f'legal_{P}_reg.json')); Mp = np.array(R['pt_rot_para_px'])
    sp = src[PAG[P] - 1]; rotm = sp.rotation_matrix
    def px(pt):
        q = fitz.Point(pt) * rotm; return Mp @ np.array([q.x, q.y, 1.0])
    # paredes
    w18 = g('preto_1_8').astype(np.uint8)
    # paredes = contornos fechados do traco 1,8: preenche so os "buracos" finos (miolo de parede, espessura <= 40 cm),
    # sem fechamento morfologico (que entortava cantos e emendava paredes vizinhas)
    w18c = cv2.morphologyEx(w18, cv2.MORPH_CLOSE, np.ones((13, 13), np.uint8))
    par = w18c.copy()
    _ip = (1 - w18c).astype(np.uint8); _n, _l, _s, _ = cv2.connectedComponentsWithStats(_ip, 4)
    _dt = cv2.distanceTransform(_ip, cv2.DIST_L2, 5)
    _mx = np.zeros(_n); np.maximum.at(_mx, _l.ravel(), _dt.ravel())
    for _i in range(1, _n):
        x_, y_, w_, h_, a_ = _s[_i]
        if x_ == 0 or y_ == 0 or x_ + w_ >= W or y_ + h_ >= H: continue
        if _mx[_i] <= 50: par[_l == _i] = 1                        # miolo da parede (meia espessura <= 20 cm)
    par = par > 0
    # muros/esquadrias (vermelho 0,6 sem texto)
    red = cv2.morphologyEx(g('preto_0_6').astype(np.uint8), cv2.MORPH_CLOSE, np.ones((41, 41), np.uint8)) > 0
    red &= ~par
    red = cv2.dilate(red.astype(np.uint8), np.ones((9, 9), np.uint8)) > 0     # emenda os trechos de muro/gradil
    perto_vid = cv2.dilate((vid0 | sol0).astype(np.uint8), np.ones((41, 41), np.uint8)).astype(bool)
    n, lab, st, _ = cv2.connectedComponentsWithStats(red.astype(np.uint8), 8)
    vid = np.zeros((H, W), bool); muro = np.zeros((H, W), bool)
    for i in range(1, n):
        if st[i, 4] < 200: continue
        m = lab == i
        (vid if (m & perto_vid).sum() > 0.6 * m.sum() else muro)[m] = True
    # marcas de corte (tracejados curtos e simbolos A/B) nao sao muro: tira componentes pequenos soltos
    _n, _l, _s, _ = cv2.connectedComponentsWithStats(muro.astype(np.uint8), 8)
    perto_par = cv2.dilate(par.astype(np.uint8), np.ones((61, 61), np.uint8)).astype(bool)
    for _i in range(1, _n):
        if max(_s[_i, 2], _s[_i, 3]) < 330 and not (perto_par & (_l == _i)).any(): muro[_l == _i] = False
    # predio e ambientes
    barreira = par | muro | cv2.dilate(vid.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    # portas: arcos de 0,5-1,2 m de raio do traco 0,24 (folha + arco fecham o vao), em vetor
    arcos = []
    for dr in sp.get_drawings():
        if min(abs((dr.get('width') or 0) - 0.24), abs((dr.get('width') or 0) - 1.8), abs((dr.get('width') or 0) - 0.6)) > 0.02 or not dr.get('color') or max(dr['color']) > 0.05: continue
        for it in dr['items']:
            if it[0] != 'c': continue
            p0, p3 = px(it[1]), px(it[4]); corda = np.hypot(*(p0 - p3)) * M_PX
            if not 0.6 <= corda <= 1.7: continue
            # porta: quarto de circulo com o centro (dobradica) junto a uma parede
            pm = px(fitz.Point((it[1].x + 3 * it[2].x + 3 * it[3].x + it[4].x) / 8, (it[1].y + 3 * it[2].y + 3 * it[3].y + it[4].y) / 8))
            ax_, ay_ = p0; bx_, by_ = pm; cx_, cy_ = p3
            dd = 2 * (ax_ * (by_ - cy_) + bx_ * (cy_ - ay_) + cx_ * (ay_ - by_))
            if abs(dd) < 1e-6: continue
            ux = ((ax_**2 + ay_**2) * (by_ - cy_) + (bx_**2 + by_**2) * (cy_ - ay_) + (cx_**2 + cy_**2) * (ay_ - by_)) / dd
            uy = ((ax_**2 + ay_**2) * (cx_ - bx_) + (bx_**2 + by_**2) * (ax_ - cx_) + (cx_**2 + cy_**2) * (bx_ - ax_)) / dd
            r_ = np.hypot(ax_ - ux, ay_ - uy) * M_PX
            if not (0.55 <= r_ <= 1.2 and corda > 1.25 * r_): continue
            xi, yi = int(np.clip(ux, 0, W - 1)), int(np.clip(uy, 0, H - 1))
            if not par[max(yi - 25, 0):yi + 25, max(xi - 25, 0):xi + 25].any(): continue
            arcos.append([p0, px(it[2]), px(it[3]), p3, (ux, uy)])
    # soleira: corda do arco (fecha o vao para o flood, como a skill faz)
    sol = np.zeros((H, W), np.uint8)
    for a in arcos:
        # vao da porta = dobradica -> ponta do arco que encosta na parede oposta (porta fechada)
        c = [tuple(int(round(v)) for v in pt) for pt in a]
        def na_parede(q):
            x_, y_ = q; return par[max(y_ - 20, 0):y_ + 20, max(x_ - 20, 0):x_ + 20].sum()
        e = c[0] if na_parede(c[0]) >= na_parede(c[3]) else c[3]
        cv2.line(sol, c[4], e, 1, 5)

    barreira |= cv2.dilate(vid0.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool) & ~cv2.dilate(sol0.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool)
    # escadas: degraus do traco 0,24 dentro da caixa de cada escada -> contorno (fecho convexo) vira barreira e ambiente
    esc_hull = []
    d24 = g('preto_0_24')
    for (x0, y0, x1, y1) in ESCADAS[P]:
        sub = np.zeros((H, W), np.uint8); sub[y0:y1, x0:x1] = d24[y0:y1, x0:x1]
        sub &= ~cv2.dilate(par.astype(np.uint8), np.ones((15, 15), np.uint8)).astype(np.uint8) if False else sub
        pts = np.column_stack(np.nonzero(sub)[::-1]).astype(np.int32)
        if len(pts) < 50: continue
        hull = cv2.convexHull(pts); esc_hull.append(hull)
        cv2.polylines(sol, [hull], True, 1, 3)
    # folhas de porta (linhas diagonais/abertas do traco 1,8) sem arco: o vao e a folha girada 90 graus em torno da
    # dobradica, para o lado em que a ponta cai na parede (porta fechada)
    for dr in sp.get_drawings():
        if abs((dr.get('width') or 0) - 1.8) > 0.03 or not dr.get('color') or max(dr['color']) > 0.05: continue
        for it in dr['items']:
            if it[0] != 'l': continue
            a_, b_ = px(it[1]), px(it[2]); L = np.hypot(*(a_ - b_)) * M_PX
            if not 0.55 <= L <= 1.2: continue
            def wsum(q): x_, y_ = int(q[0]), int(q[1]); return par[max(y_ - 12, 0):y_ + 12, max(x_ - 12, 0):x_ + 12].sum()
            h_, t_ = (a_, b_) if wsum(a_) >= wsum(b_) else (b_, a_)
            if wsum(t_) > 0 and wsum(h_) == 0: continue
            v = t_ - h_
            best = None
            for r90 in (np.array([-v[1], v[0]]), np.array([v[1], -v[0]])):
                e = h_ + r90; sc = wsum(e)
                if best is None or sc > best[0]: best = (sc, e)
            if best[0] > 0:
                cv2.line(sol, tuple(int(round(x)) for x in h_), tuple(int(round(x)) for x in best[1]), 1, 5)
    # vaos de porta (ate 1,05 m) entre ombreiras das paredes, dentro do predio: fecho 1D horizontal e vertical
    p8 = par.astype(np.uint8); kv = 261
    vao = (cv2.morphologyEx(p8, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (kv, 1))) |
           cv2.morphologyEx(p8, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (1, kv)))) & ~p8
    vao = cv2.morphologyEx(vao, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    _n, _l, _s, _ = cv2.connectedComponentsWithStats(vao, 8); _ok = np.zeros(_n, bool)
    for _i in range(1, _n): _ok[_i] = min(_s[_i, 2], _s[_i, 3]) <= 48 and max(_s[_i, 2], _s[_i, 3]) >= 120   # so faixas de vao
    vao = _ok[_l].astype(np.uint8)
    sol |= vao
    livre = (~(barreira | (sol > 0))).astype(np.uint8)
    nn, lab2 = cv2.connectedComponents(livre, connectivity=4)
    st2 = np.bincount(lab2.ravel())
    # nomes: ambiente do executivo DWG na mesma posicao (mesma area +-30%) ou manual
    amb0 = {int(k): v for k, v in J['ambientes'].items()}
    info = {}
    for k in range(1, nn):
        a = st2[k]
        if a < 3000: continue
        m = lab2 == k
        if m[0, :].any() or m[-1, :].any() or m[:, 0].any() or m[:, -1].any(): continue
        ov = np.bincount(ids0[m].ravel(), minlength=ids0.max() + 1); ov[0] = 0
        k0 = int(ov.argmax()); nome = None
        if ov[k0] > 0.6 * a and 0.7 < a / max((ids0 == k0).sum(), 1) < 1.3: nome = amb0[k0]['nome']
        info[k] = dict(nome=nome, px=int(a))
    for nm, x, y in NOMES_MANUAIS[P]:
        k = int(lab2[y, x])
        if k in info: info[k]['nome'] = nm
    ids = np.zeros((H, W), np.int32)
    textos = []
    for k, v in info.items():
        m = lab2 == k; ids[m] = k; x, y = interno(m)
        nm = v['nome'] or ''
        mm = re.match(r'ALOJ (\d+)', nm)
        if mm: nm = 'ALOJ %02d' % int(COD[P].get(mm.group(1), mm.group(1))); v['nome'] = nm; t = nm
        elif nm.startswith(('WC', 'PNE')): t = 'XSANIT'
        elif nm == 'ELEVADOR': t = 'XELEV'
        elif nm.startswith('ESCADA'): t = 'XESCADA'
        elif nm in ('ADMINISTRACAO', 'ROUPARIA', 'PLATAFORMA'): t = {'ADMINISTRACAO': 'XADMIN', 'ROUPARIA': 'XROUPA', 'PLATAFORMA': 'XPLATA'}[nm]
        elif nm: t = 'XCIRC'
        else:   # externo sem nome: pelo que o lancamento mostra (grama ou piso)
            t = None
        v['caixa'] = [int(v_) for v_ in (*np.nonzero(m.any(0))[0][[0, -1]], *np.nonzero(m.any(1))[0][[0, -1]])]
        v['m2'] = round(v['px'] * M_PX ** 2, 2)
        if t: textos.append((t, x, y))
    # --- PDF --------------------------------------------------------------------------------------------------
    pg = doc.new_page(width=W * K, height=H * K)
    sh = pg.new_shape()
    for c in contornos(par | muro): poly(sh, c)
    sh.finish(color=(0, 0, 0), width=1.2); sh.commit()
    sh = pg.new_shape(); segs = []
    n, lab, st, _ = cv2.connectedComponentsWithStats(vid.astype(np.uint8), 8)
    for i in range(1, n):
        pts = np.column_stack(np.nonzero(lab == i)[::-1]).astype(np.float32)
        (cx, cy), (ww, hh), ang = cv2.minAreaRect(pts); L = max(ww, hh); t_ = np.deg2rad(ang if ww >= hh else ang + 90)
        d = np.array([np.cos(t_), np.sin(t_)]) * L / 2
        e = [float(v_) * K for v_ in (cx - d[0], cy - d[1], cx + d[0], cy + d[1])]
        segs.append([round(v_, 2) for v_ in e]); sh.draw_line(fitz.Point(e[0], e[1]), fitz.Point(e[2], e[3]))
    sh.finish(color=(0, 0, 0), width=0.6); sh.commit()
    sh = pg.new_shape()
    for a in arcos:
        P0, P1, P2, P3 = [fitz.Point(pt[0] * K, pt[1] * K) for pt in a[:4]]; sh.draw_bezier(P0, P1, P2, P3)
    sh.finish(color=(0, 0, 0), width=0.6); sh.commit()
    # vaos de porta e contorno das escadas (os mesmos que separaram os ambientes) como traco medio para a skill
    sh = pg.new_shape()
    for c in contornos(sol > 0, 1): poly(sh, c)
    sh.finish(color=(0, 0, 0), width=0.6); sh.commit()
    for t, x, y in textos:
        pg.insert_text(fitz.Point(x * K - len(t) * 2.2, y * K + 2), t, fontsize=8, fontname='helv')
    barreiras[str(npag)] = segs
    np.savez_compressed(f'{P}_legal_amb.npz', ids=ids, paredes=par | muro, muro=muro, vidro=vid, soleira=sol > 0, parede_so=par)
    json.dump([[[float(v_) for v_ in pt] for pt in a] for a in arcos], open(f'{P}_legal_arcos.json', 'w'))
    json.dump(dict(ambientes={str(k): v for k, v in info.items()}), open(f'{P}_legal_amb.json', 'w', encoding='utf8'), indent=1, ensure_ascii=False)
    sem = [(k, v['px']) for k, v in info.items() if not v['nome']]
    print(P, 'ambientes', len(info), 'nomeados', sum(1 for v in info.values() if v['nome']), 'arcos', len(arcos), 'esquadrias', len(segs))
    for k, v in sorted(info.items(), key=lambda kv: str(kv[1]['nome'])): print('  ', v['nome'], v['m2'], v['caixa'])
    rng = np.random.default_rng(1); cor = rng.integers(70, 255, (ids.max() + 1, 3)).astype(np.uint8); cor[0] = 255
    viz = cor[ids]; viz[par] = 0; viz[muro] = (90, 90, 90); viz[vid] = (0, 120, 255); viz[sol > 0] = (255, 0, 0)
    for k, v in info.items():
        x, y = interno(ids == k); cv2.putText(viz, str(v['nome'] or k), (x - 60, y), 0, 1.4, (0, 0, 0), 3)
    Image.fromarray(viz).resize((W // 4, H // 4)).save(f'{P}_legal_amb.jpg', quality=85)
doc.save(pdf_out); json.dump(barreiras, open('barreiras_legal.json', 'w'))
