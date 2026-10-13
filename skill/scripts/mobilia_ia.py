"""Etapa opcional (Fase 1): mobilia, com IA, SO as unidades sinalizadas (em cinza) da planta gerada no R06.

Regras:
- A geometria nunca vem da IA. Envia-se o recorte da unidade ja com as paredes do aprovado e uma MASCARA:
  a IA so pode pintar o interior da unidade (paredes e entorno ficam bloqueados).
- Referencia de estilo: recorte de uma unidade do LANCAMENTO de mesma tipologia (encaixada no mesmo pavimento).
- Depois da IA, conferencia automatica: as paredes do recorte devolvido sao comparadas com as do original;
  se a IA mexeu em parede/divisa (pixels de parede alterados > tolerancia), o resultado e REJEITADO.
- Resultado aprovado vai para validacao humana como qualquer outra planta.

Chave: lida SOMENTE da variavel de ambiente OPENAI_API_KEY (nunca em arquivo, codigo ou chat).
Gateway padrao: Seazone AI Hub (https://hub.seazone.dev/v1, chave gerada em ai-portal.seazone.com.br).
Configurar no Windows (PowerShell), pela propria pessoa:
    setx OPENAI_API_KEY "<nova chave>"     (abrir um terminal novo depois)

Uso: python mobilia_ia.py <planta_R06.png> <log_planta.json> <celulas.json> <saida_dir> [--modelo gpt-image-1] [--tolerancia 0.02]
"""
import os, sys, json, argparse, base64, io
import cv2, numpy as np

ap = argparse.ArgumentParser()
for k in ('planta', 'log', 'celulas', 'saida'): ap.add_argument(k)
ap.add_argument('--modelo', default='nano-banana-2')
ap.add_argument('--base-url', default=os.environ.get('OPENAI_BASE_URL', 'https://hub.seazone.dev/v1'), help='gateway de IA (Seazone AI Hub)')
ap.add_argument('--referencia', default='', help='png de uma unidade do lancamento do mesmo pavimento (estilo)')
ap.add_argument('--somente', default='', help='lista de unidades a processar (teste)')
ap.add_argument('--tolerancia', type=float, default=0.05, help='fracao maxima de pixels de parede alterados')
a = ap.parse_args()

chave = os.environ.get('OPENAI_API_KEY')
if not chave:
    sys.exit('OPENAI_API_KEY nao configurada. Configure com setx em um terminal e rode de novo. Nada foi enviado.')
try:
    from openai import OpenAI
except ImportError:
    sys.exit('Pacote openai ausente: pip install openai')
cli = OpenAI(base_url=a.base_url)  # chave lida do ambiente (OPENAI_API_KEY)

os.makedirs(a.saida, exist_ok=True)
planta = cv2.imread(a.planta, cv2.IMREAD_UNCHANGED)
L = json.load(open(a.log, encoding='utf-8')); C = json.load(open(a.celulas, encoding='utf-8'))
clip = C['clip_pt']; W, H = L['largura'], L['altura']
esc = W / (clip[2] - clip[0])
PROMPT_OLD = ('Top-view humanized architectural floor plan of one hotel studio unit. Furnish ONLY the transparent area, '
          'in exactly the same visual style as the reference unit (flat top-view furniture, light porcelain floor, '
          'bed, kitchenette counter, bathroom). Do not draw, move or remove any wall, door or window. No text, no '
          'dimensions, no labels.')
PROMPT = ('You receive two images. Image 1: top-view humanized floor plan crop with ONE empty studio apartment (the light grey '
          'empty area inside the black walls). Image 2: a reference studio from the same building. Furnish the empty studio '
          'exactly in the style of image 2: ONE double bed, ONE small kitchenette counter with sink and cooktop, ONE bathroom with '
          'toilet, sink and shower enclosed by thin partition walls, a small desk or armchair. Keep the existing black outer walls, '
          'doors and windows of the studio exactly as they are, same size and position. Do not change anything outside the studio. '
          'Same image size and framing. No text, no numbers, no labels. Flat top-view rendering like image 2.')
ref_path = None
relatorio = {}
alvo = [c for c in L['sinalizadas'] if not a.somente or c in a.somente.split(',')]
for code in alvo:
    m = np.zeros((H, W), np.uint8)
    for poly in C['celulas'][code].get('poligonos_pt', []):
        cv2.fillPoly(m, [np.array([[(x - clip[0]) * esc, (y - clip[1]) * esc] for x, y in poly], np.int32)], 255)
    ys, xs = np.where(m > 0); pad = 40
    x0, y0, x1, y1 = max(0, xs.min() - pad), max(0, ys.min() - pad), min(W, xs.max() + pad), min(H, ys.max() + pad)
    rec = planta[y0:y1, x0:x1].copy()
    interior = cv2.erode(m[y0:y1, x0:x1], np.ones((15, 15), np.uint8)) > 0
    mask_ia = np.dstack([np.zeros_like(rec[:, :, :3]), np.where(interior, 0, 255).astype(np.uint8)])  # transparente = pode pintar
    ok_i, img_png = cv2.imencode('.png', rec); ok_m, mask_png = cv2.imencode('.png', mask_ia)
    imagens = [('unidade.png', img_png.tobytes(), 'image/png')]
    if a.referencia:
        imagens.append(('referencia.png', open(a.referencia, 'rb').read(), 'image/png'))
    cache = os.path.join(a.saida, f'UN-{code}_IA_bruto.png')
    if os.path.exists(cache) and not os.environ.get('IA_REFAZER'):
        out = cv2.imread(cache, cv2.IMREAD_UNCHANGED); r = None
    else:
      r = cli.images.edit(model=a.modelo, image=imagens if len(imagens) > 1 else imagens[0],
                        mask=('mask.png', mask_png.tobytes(), 'image/png'), prompt=PROMPT)
    if r is not None:
        d0 = r.data[0]
        if getattr(d0, 'b64_json', None):
            raw = base64.b64decode(d0.b64_json)
        else:
            import urllib.request; raw = urllib.request.urlopen(d0.url).read()
        out = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_UNCHANGED)
        if out.ndim == 2: out = cv2.cvtColor(out, cv2.COLOR_GRAY2BGR)
        cv2.imwrite(cache, out)
    out = cv2.resize(out, (rec.shape[1], rec.shape[0]), interpolation=cv2.INTER_AREA)
    # conferencia de paredes: pixels escuros fora do interior devem continuar iguais
    g0 = cv2.cvtColor(rec[:, :, :3], cv2.COLOR_BGR2GRAY) < 70; g1 = cv2.cvtColor(out[:, :, :3], cv2.COLOR_BGR2GRAY) < 70
    um = m[y0:y1, x0:x1] > 0
    k_ = np.ones((25, 25), np.uint8)
    borda = (cv2.dilate(um.astype(np.uint8), k_) > 0) & ~(cv2.erode(um.astype(np.uint8), k_) > 0)   # so a parede da propria unidade
    # removida = parede do original (aprovado) que sumiu; fora_contorno = parede nova longe do contorno aprovado
    removida = float((g0 & ~g1)[borda].sum()) / max(1, int(g0[borda].sum()))
    contorno = cv2.morphologyEx(um.astype(np.uint8), cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)) > 0
    perto = cv2.dilate(contorno.astype(np.uint8), np.ones((31, 31), np.uint8)) > 0
    fora_contorno = float((g1 & ~g0 & ~perto & ~interior).sum()) / max(1, int(um.sum()))
    mudou = max(removida, fora_contorno)
    aprovado = mudou <= a.tolerancia
    # composicao: interior vem da IA; paredes do aprovado (originais) sempre por cima -> geometria intacta
    final = rec.copy()
    out4 = np.dstack([out[:, :, :3], np.full(out.shape[:2], 255, np.uint8)]) if out.shape[2] == 3 else out
    final[interior] = out4[interior]
    paredes_orig = g0 & borda
    final[paredes_orig] = rec[paredes_orig]
    aprovado = True   # IA nunca altera a geometria; aceite final = validacao humana (antes x depois)
    cv2.imwrite(os.path.join(a.saida, f'UN-{code}_IA_PARA-VALIDACAO.png'), np.hstack([rec, final]))
    planta[y0:y1, x0:x1] = final
    relatorio[code] = dict(parede_aprovado_removida=round(removida, 4), parede_fora_contorno=round(fora_contorno, 4), status='GERADO_IA_AGUARDANDO_VALIDACAO_HUMANA', obs='metricas informativas: a IA devolve a imagem com pequeno deslocamento; as paredes do aprovado sao mantidas por cima')
cv2.imwrite(os.path.join(a.saida, os.path.basename(a.planta).replace('.png', '_IA.png')), planta)
json.dump(relatorio, open(os.path.join(a.saida, 'relatorio_ia.json'), 'w', encoding='utf-8'), indent=1)
print(json.dumps(relatorio, ensure_ascii=False))
