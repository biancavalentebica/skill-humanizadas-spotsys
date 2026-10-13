"""Etapa opcional (Fase 1): mobilia, com IA, SO as unidades sinalizadas (em cinza) da planta gerada no R06.

Regras:
- A geometria nunca vem da IA. Envia-se o recorte da unidade ja com as paredes do aprovado e uma MASCARA:
  a IA so pode pintar o interior da unidade (paredes e entorno ficam bloqueados).
- Referencia de estilo: recorte de uma unidade do LANCAMENTO de mesma tipologia (encaixada no mesmo pavimento).
- Depois da IA, conferencia automatica: as paredes do recorte devolvido sao comparadas com as do original;
  se a IA mexeu em parede/divisa (pixels de parede alterados > tolerancia), o resultado e REJEITADO.
- Resultado aprovado vai para validacao humana como qualquer outra planta.

Chave: lida SOMENTE da variavel de ambiente OPENAI_API_KEY (nunca em arquivo, codigo ou chat).
Configurar no Windows (PowerShell), pela propria pessoa:
    setx OPENAI_API_KEY "<nova chave>"     (abrir um terminal novo depois)

Uso: python mobilia_ia.py <planta_R06.png> <log_planta.json> <celulas.json> <saida_dir> [--modelo gpt-image-1] [--tolerancia 0.02]
"""
import os, sys, json, argparse, base64, io
import cv2, numpy as np

ap = argparse.ArgumentParser()
for k in ('planta', 'log', 'celulas', 'saida'): ap.add_argument(k)
ap.add_argument('--modelo', default='gpt-image-1')
ap.add_argument('--tolerancia', type=float, default=0.02, help='fracao maxima de pixels de parede alterados')
a = ap.parse_args()

chave = os.environ.get('OPENAI_API_KEY')
if not chave:
    sys.exit('OPENAI_API_KEY nao configurada. Configure com setx em um terminal e rode de novo. Nada foi enviado.')
try:
    from openai import OpenAI
except ImportError:
    sys.exit('Pacote openai ausente: pip install openai')
cli = OpenAI()  # le a chave do ambiente

os.makedirs(a.saida, exist_ok=True)
planta = cv2.imread(a.planta, cv2.IMREAD_UNCHANGED)
L = json.load(open(a.log, encoding='utf-8')); C = json.load(open(a.celulas, encoding='utf-8'))
clip = C['clip_pt']; W, H = L['largura'], L['altura']
esc = W / (clip[2] - clip[0])
PROMPT = ('Top-view humanized architectural floor plan of one hotel studio unit. Furnish ONLY the transparent area, '
          'in exactly the same visual style as the reference unit (flat top-view furniture, light porcelain floor, '
          'bed, kitchenette counter, bathroom). Do not draw, move or remove any wall, door or window. No text, no '
          'dimensions, no labels.')
relatorio = {}
for code in L['sinalizadas']:
    m = np.zeros((H, W), np.uint8)
    for poly in C['celulas'][code].get('poligonos_pt', []):
        cv2.fillPoly(m, [np.array([[(x - clip[0]) * esc, (y - clip[1]) * esc] for x, y in poly], np.int32)], 255)
    ys, xs = np.where(m > 0); pad = 40
    x0, y0, x1, y1 = max(0, xs.min() - pad), max(0, ys.min() - pad), min(W, xs.max() + pad), min(H, ys.max() + pad)
    rec = planta[y0:y1, x0:x1].copy()
    interior = cv2.erode(m[y0:y1, x0:x1], np.ones((15, 15), np.uint8)) > 0
    mask_ia = np.dstack([np.zeros_like(rec[:, :, :3]), np.where(interior, 0, 255).astype(np.uint8)])  # transparente = pode pintar
    ok_i, img_png = cv2.imencode('.png', rec); ok_m, mask_png = cv2.imencode('.png', mask_ia)
    r = cli.images.edit(model=a.modelo, image=('unidade.png', img_png.tobytes(), 'image/png'),
                        mask=('mask.png', mask_png.tobytes(), 'image/png'), prompt=PROMPT, size='auto')
    out = cv2.imdecode(np.frombuffer(base64.b64decode(r.data[0].b64_json), np.uint8), cv2.IMREAD_UNCHANGED)
    out = cv2.resize(out, (rec.shape[1], rec.shape[0]), interpolation=cv2.INTER_AREA)
    # conferencia de paredes: pixels escuros fora do interior devem continuar iguais
    g0 = cv2.cvtColor(rec[:, :, :3], cv2.COLOR_BGR2GRAY) < 70; g1 = cv2.cvtColor(out[:, :, :3], cv2.COLOR_BGR2GRAY) < 70
    borda = ~interior
    mudou = float((g0 ^ g1)[borda].mean())
    aprovado = mudou <= a.tolerancia
    final = rec.copy()
    if aprovado:
        final[interior] = np.dstack([out[:, :, :3], np.full(out.shape[:2], 255, np.uint8)])[interior]  # so o interior entra
    cv2.imwrite(os.path.join(a.saida, f'UN-{code}_IA_{"APROVADO" if aprovado else "REJEITADO"}.png'), np.hstack([rec, np.dstack([out[:, :, :3], np.full(out.shape[:2], 255, np.uint8)]) if out.shape[2] == 3 else out]))
    if aprovado:
        planta[y0:y1, x0:x1] = final
    relatorio[code] = dict(paredes_alteradas=round(mudou, 4), status='APROVADO_PARA_VALIDACAO' if aprovado else 'REJEITADO_IA_MEXEU_NA_GEOMETRIA')
cv2.imwrite(os.path.join(a.saida, os.path.basename(a.planta).replace('.png', '_IA.png')), planta)
json.dump(relatorio, open(os.path.join(a.saida, 'relatorio_ia.json'), 'w', encoding='utf-8'), indent=1)
print(json.dumps(relatorio, ensure_ascii=False))
