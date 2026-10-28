"""Preenche um modelo tpl_*.js e grava o script pronto (so ASCII) na pasta do projeto.

O browser_run_code_unsafe so aceita arquivo de DENTRO da pasta do projeto, por isso a saida vai para
  <projeto>/.playwright-mcp/pav/run/<nome>.js

Uso:
  python -I gerar.py <modelo> <nome_saida> '<json com os placeholders>'
Exemplo:
  python -I gerar.py tpl_trocar_imagem.js 1_img_tipo '{"__TITULO__": "Pavimento Tipo", "__ARQ__": "C:/.../TIPO.png"}'
  python -I gerar.py tpl_zoom.js 1_zoom '{"__TITULOS__": ["2º Pavimento", "Pavimento Tipo"]}'

Valor texto entra como texto; lista/dict entra como JSON. Acento vira \\uXXXX (scripts carregados por arquivo: so ASCII).
Confere a sintaxe com node, se existir.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
PROJETO = r'C:\Users\compu\seazone\processos\spotsys-navegador'
SAIDA = os.path.join(PROJETO, '.playwright-mcp', 'pav', 'run')
BARRA = chr(92)


def ascii_js(s):
    return ''.join(c if ord(c) < 128 else BARRA + 'u%04x' % ord(c) for c in s)


def main():
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(1)
    modelo, nome, params = sys.argv[1], sys.argv[2], json.loads(sys.argv[3])
    texto = open(os.path.join(AQUI, modelo), encoding='utf-8').read()
    for k, v in params.items():
        if k not in texto:
            sys.exit('placeholder %s nao existe em %s' % (k, modelo))
        texto = texto.replace(k, v if isinstance(v, str) else json.dumps(v, ensure_ascii=False))
    texto = ascii_js(texto)
    sobra = re.findall(r'__[A-Z]+__', texto)
    if sobra:
        sys.exit('placeholder sem valor: %s' % sorted(set(sobra)))
    os.makedirs(SAIDA, exist_ok=True)
    destino = os.path.join(SAIDA, nome + '.js')
    open(destino, 'w', encoding='ascii').write(texto)
    if shutil.which('node'):
        tmp = os.path.join(tempfile.gettempdir(), 'chk_' + nome + '.js')
        open(tmp, 'w', encoding='ascii').write('(' + texto + ')')
        r = subprocess.run(['node', '--check', tmp], capture_output=True, text=True)
        if r.returncode:
            sys.exit('ERRO de sintaxe:\n' + r.stderr)
    print(destino)


if __name__ == '__main__':
    main()
