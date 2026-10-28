# -*- coding: utf-8 -*-
"""Caminhos e utilitarios do fluxo automatico de plantas (pastas "... OK")."""
import json, os, re, time, unicodedata

RAIZ_PLANTAS = os.environ.get('RAIZ_PLANTAS', r'C:\Users\compu\seazone\processos\plantas-humanizadas\recorte')
SUB_UNIDADES = os.environ.get('SUB_UNIDADES', 'Plantas unidades')   # pasta das plantas em <raiz>/<pasta> (19/10: v2 do Lagoa)
PROJ = r'C:\Users\compu\seazone\processos\spotsys-navegador'
AUTO = os.path.join(PROJ, '.playwright-mcp', 'auto')
OUT = os.path.join(AUTO, 'out')
RUN = os.path.join(AUTO, 'run')
LOCK = os.path.join(AUTO, 'LOCK')
LOCK_MAX_H = 3          # trava mais velha que isso e considerada abandonada
EXT_IMG = ('.png', '.jpg', '.jpeg', '.webp')
MAX_BYTES = 10 * 1024 * 1024

RE_OK = re.compile(r'^(.*?)[\s_\-]+OK$', re.I)
RE_COD = re.compile(r'^(\d{1,4}[A-Za-z]?|L\d{1,2})$')


def norm(s):
    s = unicodedata.normalize('NFD', s)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'\s+', ' ', s).strip().lower()


def chave(c):
    return [(0, int(x), '') if x.isdigit() else (1, 0, x) for x in re.findall(r'\d+|\D+', str(c))]


def ler_json(caminho):
    d = json.loads(open(caminho, encoding='utf-8').read())
    return json.loads(d) if isinstance(d, str) else d


def gravar_json(caminho, obj):
    open(caminho, 'w', encoding='utf-8').write(json.dumps(obj, ensure_ascii=False, indent=1))


def pastas_ok():
    """[(pasta, nome_sem_ok)] das pastas cujo nome termina em OK."""
    res = []
    for p in sorted(os.listdir(RAIZ_PLANTAS)):
        if not os.path.isdir(os.path.join(RAIZ_PLANTAS, p)):
            continue
        m = RE_OK.match(p.strip())
        if m:
            res.append((p, m.group(1).strip()))
    return res


AVISADOS = os.path.join(OUT, 'avisados.json')


def assinatura(pasta):
    """Muda se a pasta ou os arquivos de 'Plantas unidades' mudarem (nome, tamanho, data)."""
    import hashlib
    d = os.path.join(RAIZ_PLANTAS, pasta, SUB_UNIDADES)
    itens = [pasta]
    if os.path.isdir(d):
        for f in sorted(os.listdir(d)):
            st = os.stat(os.path.join(d, f))
            itens.append(f'{f}|{st.st_size}|{int(st.st_mtime)}')
    return hashlib.md5('\n'.join(itens).encode('utf-8')).hexdigest()


def avisados():
    return ler_json(AVISADOS) if os.path.exists(AVISADOS) else {}


def marcar_avisado(pasta, motivo):
    a = avisados()
    a[pasta] = {'assinatura': assinatura(pasta), 'motivo': motivo, 'quando': time.strftime('%Y-%m-%d %H:%M')}
    gravar_json(AVISADOS, a)


def lock_status():
    if not os.path.exists(LOCK):
        return None
    idade_h = (time.time() - os.path.getmtime(LOCK)) / 3600
    return idade_h
