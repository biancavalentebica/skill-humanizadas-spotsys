# -*- coding: utf-8 -*-
"""Junta a planta do pavimento com a do mezanino numa imagem so (para sistemas que aceitam 1 planta por unidade,
ex.: SpotSys).

  python juntar_mezanino.py --pasta "<pasta do empreendimento>" [unidade ...] [--ajustes ajustes.json]
                            [--saida <pasta de previa>] [--prefixo "<Nome>"]

Le "<pasta>/Plantas unidades/<Nome> - <X>.png" + "<Nome> - <X> - Mezanino.png" (Nome = nome da pasta, como no recorte;
--prefixo troca) e grava "<pasta>/Plantas unidades com mezanino/<Nome> - <X>.png" (mesmo nome da planta, para subir no
lugar dela). Sem unidades na linha de comando: todas que tem mezanino.
- Lado a lado: pavimento a esquerda, mezanino a direita, fundo branco, resolucao original (nunca amplia).
- Alinhamento vertical, nesta ordem (o de baixo vale mais):
    1. base com base (padrao);
    2. pelo predio: se ha configs/*.json do recorte com as duas unidades ("X" e "X - Mezanino"), na mesma escala e com o
       mezanino em cima da unidade, poe as duas na mesma altura (escada com escada). So sem 'mez'/'pav'/'alinhar';
    3. 'alinhar' do ajustes.json ("topo" ou "base"), para o empreendimento todo;
    4. 'dy' do ajustes.json, por unidade (medido em px).
- NUNCA sobrescreve: se o arquivo de destino ja existe, pula a unidade (apague antes, de proposito, para refazer).
- --saida <pasta>: grava em outra pasta (previa/conferencia), sem tocar em "Plantas unidades com mezanino".

ajustes.json (opcional, um por empreendimento; sugestao: guardar em <pasta>/configs/mezanino.json):
  {"mez": 0.88, "pav": 1.0, "alinhar": "topo", "dy": {"101": 153}}
  mez / pav : quando as humanizadas do pavimento e do mezanino NAO tem a mesma escala. Fator <= 1 que REDUZ o mezanino /
              o pavimento (so reduz, nunca amplia; 1 = nao mexe). Meca por um elemento que aparece nos dois pisos
              (escada, sofa, largura da unidade) e reduza o maior.
  alinhar   : "topo" quando o terraco/garden/deck fica EMBAIXO da unidade; "base" (padrao) quando fica em cima.
  dy        : por unidade, quantos px (da montagem, ja com a escala) o topo do mezanino fica ABAIXO do topo do pavimento;
              negativo = o pavimento e que desce. So as unidades listadas usam; vale mais que tudo acima.
"""
import argparse, glob, json, os, sys
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
VAO = 40          # espaco entre as duas plantas (px)
MARGEM = 20       # borda branca em volta
SUF_MEZ = ' - Mezanino.png'


def ler_ajustes(cam):
    """Le e confere o ajustes.json. Devolve {} sem arquivo."""
    if not cam:
        return {}
    try:
        aj = json.load(open(cam, encoding='utf-8'))
    except Exception as e:
        sys.exit(f'ajustes invalido ({cam}): {e}')
    if not isinstance(aj, dict):
        sys.exit(f'ajustes invalido ({cam}): esperado um objeto {{"mez": ..., "dy": {{...}}}}')
    desconhecidas = set(aj) - {'mez', 'pav', 'alinhar', 'dy'}
    if desconhecidas:
        sys.exit(f'ajustes: chave(s) desconhecida(s) {sorted(desconhecidas)} (use mez, pav, alinhar, dy)')
    for k in ('mez', 'pav'):
        if k in aj:
            v = aj[k]
            if not isinstance(v, (int, float)) or not 0 < v <= 1:
                sys.exit(f'ajustes: "{k}" = {v!r}. So reduz: use um fator entre 0 e 1 no MAIOR dos dois '
                         f'(ex.: em vez de ampliar o mezanino 1,2x, reduza o pavimento: "pav": 0.83).')
    if 'alinhar' in aj and aj['alinhar'] not in ('topo', 'base'):
        sys.exit(f'ajustes: "alinhar" = {aj["alinhar"]!r} (use "topo" ou "base")')
    dy = aj.get('dy') or {}
    if not isinstance(dy, dict) or not all(isinstance(v, int) for v in dy.values()):
        sys.exit('ajustes: "dy" tem que ser {"<unidade>": <px inteiro>, ...}')
    aj['dy'] = {str(k): v for k, v in dy.items()}
    return aj


def bboxes(pasta):
    """{chave da unidade no config: (x0, y0, x1, y1) no frame} de todos os configs da pasta."""
    out = {}
    for f in glob.glob(os.path.join(pasta, 'configs', '*.json')):
        try:
            c = json.load(open(f, encoding='utf-8'))
        except Exception:
            continue
        if not isinstance(c, dict):
            continue
        for k, u in (c.get('unidades') or {}).items():
            pts = [p for pol in u.get('poligonos', []) for p in pol.get('pts', [])]
            if pts and all(pol.get('frame', 'o') == 'o' for pol in u['poligonos']):
                xs, ys = [p[0] for p in pts], [p[1] for p in pts]
                out.setdefault(k, (min(xs), min(ys), max(xs), max(ys)))
    return out


def branco(im):
    im = im.convert('RGBA')
    bg = Image.new('RGBA', im.size, (255, 255, 255, 255))
    bg.alpha_composite(im)
    return bg.convert('RGB')


def montar(a, m, ya, ym):
    """Pavimento a esquerda (descido ya px), mezanino a direita (descido ym px), fundo branco, margem e vao."""
    W = MARGEM * 2 + a.width + VAO + m.width
    H = MARGEM * 2 + max(ya + a.height, ym + m.height)
    out = Image.new('RGB', (W, H), 'white')
    out.paste(a, (MARGEM, MARGEM + ya))
    out.paste(m, (MARGEM + a.width + VAO, MARGEM + ym))
    return out


def gravar(out, cam):
    """Grava sem nunca sobrescrever (devolve False se o arquivo ja existe)."""
    if os.path.exists(cam):
        print('JA EXISTE, nao sobrescrevi:', cam)
        return False
    out.save(cam, optimize=True)
    return True


def juntar(pasta, unidades=None, dest=None, ajustes=None, prefixo=None):
    pasta = os.path.abspath(pasta)
    pu = os.path.join(pasta, 'Plantas unidades')
    if not os.path.isdir(pu):
        sys.exit(f'nao achei a pasta "{pu}"')
    pref = prefixo or os.path.basename(pasta.rstrip('\\/'))
    esc = ajustes or {}
    dest = dest or os.path.join(pasta, 'Plantas unidades com mezanino')
    mezs = sorted(glob.glob(os.path.join(pu, glob.escape(pref) + ' - *' + SUF_MEZ)))
    if not mezs:
        outros = glob.glob(os.path.join(pu, '*' + SUF_MEZ))
        print(f'nenhum "{pref} - <unidade>{SUF_MEZ}" em {pu}'
              + (f'. Ha {len(outros)} mezanino(s) com outro nome (ex.: {os.path.basename(outros[0])}): use --prefixo.'
                 if outros else '.'))
        return []
    os.makedirs(dest, exist_ok=True)
    bb = bboxes(pasta)
    esc_glob = (esc.get('mez', 1) < 1 or esc.get('pav', 1) < 1 or bool(esc.get('alinhar')))  # 'dy' sozinho nao muda as outras
    feitos, vistos = [], set()
    for mez in mezs:
        base = os.path.basename(mez)[:-len(SUF_MEZ)]
        chave = base[len(pref) + 3:]
        vistos.add(chave)
        if unidades and chave not in unidades:
            continue
        pav = os.path.join(pu, base + '.png')
        if not os.path.exists(pav):
            print('SEM PAVIMENTO para', os.path.basename(mez)); continue
        cam = os.path.join(dest, base + '.png')
        if os.path.exists(cam):
            print('JA EXISTE, nao sobrescrevi:', cam); continue
        a, m = branco(Image.open(pav)), branco(Image.open(mez))
        if esc.get('mez', 1) < 1:
            m = m.resize((round(m.width * esc['mez']), round(m.height * esc['mez'])), Image.LANCZOS)
        if esc.get('pav', 1) < 1:
            a = a.resize((round(a.width * esc['pav']), round(a.height * esc['pav'])), Image.LANCZOS)
        # alinhamento vertical
        ba, bm = bb.get(chave), bb.get(chave + ' - Mezanino')
        modo = 'base'
        ya, ym = max(0, m.height - a.height), max(0, a.height - m.height)   # padrao: bases alinhadas
        if esc.get('alinhar') == 'topo':
            ya, ym, modo = 0, 0, 'topo'
        # pelo predio so se as duas humanizadas estao alinhadas: mesma escala e o mezanino em cima da unidade (x sobrepostos)
        sobre = 0
        if ba and bm:
            sobre = max(0, min(ba[2], bm[2]) - max(ba[0], bm[0])) / max(1e-6, min(ba[2] - ba[0], bm[2] - bm[0]))
        if ba and bm and not esc_glob and sobre >= 0.6:
            sa, sm = a.height / (ba[3] - ba[1]), m.height / (bm[3] - bm[1])
            if abs(sa - sm) / sa < 0.03:
                d = round((bm[1] - ba[1]) * sa)          # quanto o topo do mezanino fica abaixo do topo do pavimento
                ya, ym = (0, d) if d >= 0 else (-d, 0)
                modo = 'predio'
        dyu = (esc.get('dy') or {}).get(chave)           # medido por unidade: vale mais que tudo acima
        if dyu is not None:
            ya, ym = (0, dyu) if dyu >= 0 else (-dyu, 0)
            modo = f'medida da unidade (dy={dyu})'
        out = montar(a, m, ya, ym)
        if not gravar(out, cam):
            continue
        feitos.append(chave)
        print(f'{chave}: {a.size} + {m.size} -> {out.size} (alinhado pela {modo}) {os.path.getsize(cam)} bytes')
    for u in (unidades or []):
        if u not in vistos:
            print(f'AVISO: unidade "{u}" sem "{pref} - {u}{SUF_MEZ}"')
    sobra = [u for u in (esc.get('dy') or {}) if u not in vistos]
    if sobra and not unidades:
        print(f'AVISO: dy sem mezanino correspondente (confira o numero): {", ".join(sobra)}')
    print(f'{len(feitos)} imagens em {dest}')
    return feitos


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='Junta pavimento + mezanino numa imagem so (pavimento a esquerda).')
    ap.add_argument('--pasta', required=True, help='pasta do empreendimento (a que tem "Plantas unidades")')
    ap.add_argument('unidades', nargs='*', help='so estas unidades (ex.: 101 "101 A"); padrao: todas com mezanino')
    ap.add_argument('--ajustes', help='JSON com mez/pav/alinhar/dy (ver o topo deste arquivo)')
    ap.add_argument('--saida', help='grava a previa nesta pasta, sem tocar em "Plantas unidades com mezanino"')
    ap.add_argument('--prefixo', help='nome do empreendimento nos arquivos (padrao: nome da pasta)')
    a = ap.parse_args()
    juntar(a.pasta, a.unidades or None, a.saida, ler_ajustes(a.ajustes), a.prefixo)
