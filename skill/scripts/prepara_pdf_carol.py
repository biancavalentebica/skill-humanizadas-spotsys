"""Prepara o PDF aprovado para a segmentacao da skill da Carol (planta.py), que le a PAGINA INTEIRA e monta o raster a
partir das paredes (+ 1 m). Uma planta por pagina, mantendo as coordenadas da pagina original (os poligonos voltam para a
humanizada pelo registro de sobrepoe_aprovado.py, que esta em pt da prancha original).

- Recorte por REDACAO (apaga texto e tracos que tocam fora do clip + margem). show_pdf_page NAO serve: o vetor fora do clip
  continua sendo lido.
- "contorno" (opcional): retangulo de 1,44 pt desenhado em volta da planta. Use quando ambientes rotulados ficam fora da
  caixa das paredes (+ 1 m), como os gardens do lado da avenida no terreo do Batel: sem ele o flood bate na borda do raster
  e o ambiente e descartado. Desenhe o lado que coincide com uma divisa real NA divisa lida na prancha; registre no log.

Uso: py prepara_pdf_carol.py <config.json>
config: {"pdf": "<aprovado.pdf>", "saida": "<pasta_teste>/fontes/<nome>.pdf",
         "paginas": [{"pagina": 1, "clip": [x0, y0, x1, y1], "margem": 25, "contorno": [x0, y0, x1, y1]}, ...]}
"""
import sys, json, os
import fitz

cfg = json.load(open(sys.argv[1], encoding='utf-8'))
out = fitz.open()
for i, pv in enumerate(cfg['paginas'], 1):
    d = fitz.open(cfg['pdf']); p = d[pv['pagina'] - 1]; R = p.rect
    mg = pv.get('margem', 25)
    r = fitz.Rect(pv['clip']) + (-mg, -mg, mg, mg)
    for z in (fitz.Rect(R.x0, R.y0, R.x1, r.y0), fitz.Rect(R.x0, r.y1, R.x1, R.y1),
              fitz.Rect(R.x0, r.y0, r.x0, r.y1), fitz.Rect(r.x1, r.y0, R.x1, r.y1)):
        p.add_redact_annot(z)
    p.apply_redactions(images=0, graphics=2, text=0)
    if pv.get('contorno'):
        sh = p.new_shape(); sh.draw_rect(fitz.Rect(pv['contorno'])); sh.finish(color=(0, 0, 0), width=1.44); sh.commit()
    out.insert_pdf(d, from_page=pv['pagina'] - 1, to_page=pv['pagina'] - 1)
    n = sum(w[4].upper().startswith('UNIDADE') for w in out[-1].get_text('words'))
    print(f"pagina {i} (origem {pv['pagina']}, clip {pv['clip']}): {n} rotulos UNIDADE{' + contorno' if pv.get('contorno') else ''}")
os.makedirs(os.path.dirname(cfg['saida']), exist_ok=True)
out.save(cfg['saida'], garbage=3, deflate=True)
