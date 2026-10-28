"""Desenha os pins de cada planta de pavimento sobre a imagem, para conferir se cada pin cai na unidade certa.

Uso:
  python -I pins.py <estado.json> <pasta_saida> [mapa.json]

- estado.json: o window.__estado salvo pelo tpl_estado.js (browser_evaluate ... filename=...).
- Sem mapa: desenha sobre a imagem que esta no ar (image_url) -> conferencia DEPOIS de subir.
- Com mapa ({"<spot_image_id>": "<caminho do arquivo novo>"}): desenha os pins atuais sobre o arquivo novo, lado a lado com
  o atual -> previa ANTES de subir (pins sao guardados em % da imagem: se o enquadramento mudou, eles saem do lugar).
Saida: <pasta_saida>/pins_<id>.jpg + resumo (pins por planta, unidades sem pin / repetidas).
Planta tipo: os pins dos varios andares aparecem lado a lado na mesma unidade; o rotulo mostra o numero da unidade.
"""
import json
import os
import sys
import urllib.request

from PIL import Image, ImageDraw, ImageFont

Image.MAX_IMAGE_PIXELS = None


def carregar(p):
    d = json.load(open(p, encoding='utf-8'))
    return json.loads(d) if isinstance(d, str) else d


def fonte(n):
    try:
        return ImageFont.truetype('arial.ttf', n)
    except OSError:
        return ImageFont.load_default()


def desenhar(im, pins, largura):
    t = im.convert('RGB').resize((largura, int(im.size[1] * largura / im.size[0])))
    dr = ImageDraw.Draw(t)
    f = fonte(max(14, largura // 80))
    for p in pins:
        x, y = p['x'] / 100 * t.size[0], p['y'] / 100 * t.size[1]
        dr.ellipse((x - 8, y - 8, x + 8, y + 8), fill=(230, 40, 40), outline='white', width=2)
        dr.text((x + 9, y - 15), str((p.get('units') or {}).get('unit_number')), fill=(200, 0, 0), font=f)
    return t


def main():
    if len(sys.argv) not in (3, 4):
        print(__doc__)
        sys.exit(1)
    est = carregar(sys.argv[1])
    saida = sys.argv[2]
    mapa = carregar(sys.argv[3]) if len(sys.argv) == 4 else {}
    os.makedirs(saida, exist_ok=True)
    ed = est['editor']
    for f in ed['floor_plans']:
        fid = str(f['id'])
        pins = [p for p in ed['floor_plan_pins'] if str(p['spot_image_id']) == fid]
        cache = os.path.join(saida, 'atual_' + f['image_url'].split('/')[-1])
        if not os.path.exists(cache):
            urllib.request.urlretrieve(f['image_url'], cache)
        atual = Image.open(cache)
        if fid in mapa:
            nova = Image.open(mapa[fid])
            a, n = desenhar(atual, pins, 1600), desenhar(nova, pins, 1600)
            c = Image.new('RGB', (3220, max(a.size[1], n.size[1]) + 40), 'white')
            c.paste(a, (0, 40))
            c.paste(n, (1620, 40))
            dr = ImageDraw.Draw(c)
            dr.text((10, 5), 'ATUAL: ' + f['title'], fill='black', font=fonte(28))
            dr.text((1630, 5), 'NOVA com os mesmos pins', fill='black', font=fonte(28))
            print(fid, f['title'], 'pins', len(pins), '| atual', atual.size, '| nova', nova.size,
                  '| proporcao', round(atual.size[0] / atual.size[1], 3), round(nova.size[0] / nova.size[1], 3))
        else:
            if not pins:
                print(fid, f['title'], 'sem pins')
                continue
            c = desenhar(atual, pins, 2400)
            print(fid, f['title'], 'pins', len(pins), atual.size)
        c.save(os.path.join(saida, 'pins_%s.jpg' % fid), quality=85)
    por = {}
    for p in ed['floor_plan_pins']:
        por[p['szi_unit_id']] = por.get(p['szi_unit_id'], 0) + 1
    print('unidades', len(est['units']), '| pins', len(ed['floor_plan_pins']),
          '| sem pin', [u['code'] for u in est['units'] if u['id'] not in por],
          '| repetidas', [u['code'] for u in est['units'] if por.get(u['id'], 0) > 1])


if __name__ == '__main__':
    main()
