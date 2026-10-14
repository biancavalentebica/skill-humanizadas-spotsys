# Barra Spot - converte a prancha PDF (Mezanino + Superior) em duas plantas PNG, já sem os textos de área.
# O texto do PDF é vetorial: as linhas "A = 12,42m²" / "ÁREA= 25,42m²" são removidas no próprio PDF (redação só de
# texto, sem tocar no desenho) antes de rasterizar. "MEZ UN 01" / "UN 30" ficam.
# Rode: python s_pdf.py   -> gera BARRASPOT-...-R01_MEZANINO.png e _SUPERIOR.png na pasta do empreendimento.
# Exemplo real (Barra Spot, out/2026). Para usar em outro PDF: copie para "<pasta do empreendimento>/configs/" (a pasta
# acima de configs/ vira EMP) ou passe o PDF como argumento:  python s_pdf.py "<caminho>/PRANCHA.pdf"
# (os PNG saem ao lado do PDF). Ajuste CLIPS (pt) e a cor das folhas para o seu PDF.
import os, re, sys, fitz

EMP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF = os.path.join(EMP, "BARRASPOT-DC-ARQ-DCT-MEZ-000-R01.pdf")
if len(sys.argv) > 1:                                 # PDF passado por argumento
    PDF = os.path.abspath(sys.argv[1]); EMP = os.path.dirname(PDF)
STEM = os.path.splitext(os.path.basename(PDF))[0]    # "BARRASPOT-DC-ARQ-DCT-MEZ-000-R01" no exemplo
DPI = 420
CLIPS = {"MEZANINO": (240, 120, 970, 1555), "SUPERIOR": (1160, 120, 1890, 1555)}   # pt; sem título/escala
AREA = re.compile(r"^(A|ÁREA)\s*=")

d = fitz.open(PDF)
p = d[0]

# folhas das jardineiras = traços na cor 0.371094 0.496094 0 RG: troca o "S" (desenhar traço) por "n" (não desenhar)
xref = p.get_contents()[0]
verde, pilha, saida, nf = False, [], [], 0
for ln in p.read_contents().decode("latin-1").split("\n"):
    t = ln.strip()
    if t == "q":
        pilha.append(verde)
    elif t == "Q":
        verde = pilha.pop() if pilha else False
    elif t.endswith(" RG") or t.endswith(" G") or t.endswith(" K") or t.endswith(" SC") or t.endswith(" SCN"):
        verde = t == "0.371094 0.496094 0 RG"
    elif verde and t in ("S", "s"):
        ln, nf = "n", nf + 1
    saida.append(ln)
d.update_stream(xref, "\n".join(saida).encode("latin-1"))
print(nf, "traços de folha removidos")

linhas = {}
for w in p.get_text("words"):
    if w[0] < 2000:                                   # fora do carimbo
        linhas.setdefault((w[5], w[6]), []).append(w)
n = 0
for ws in linhas.values():
    if AREA.match(" ".join(w[4] for w in ws)):
        r = fitz.Rect(min(w[0] for w in ws), min(w[1] for w in ws), max(w[2] for w in ws), max(w[3] for w in ws))
        p.add_redact_annot(r + (-0.5, -0.3, 0.5, 0.3), fill=False)
        n += 1
    elif [w[4] for w in ws[:3]] == ["UN", "MEZ", "UN"]:          # "UN MEZ UN 20/23": tira o "UN" a mais do original
        p.add_redact_annot(fitz.Rect(ws[0][:4]) + (-0.3, -0.3, 0.3, 0.3), fill=False)
p.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE, graphics=fitz.PDF_REDACT_LINE_ART_NONE,
                   text=fitz.PDF_REDACT_TEXT_REMOVE)
print(n, "linhas de área removidas")
for nome, c in CLIPS.items():
    out = os.path.join(EMP, f"{STEM}_{nome}.png")
    pix = p.get_pixmap(dpi=DPI, clip=fitz.Rect(*c), alpha=False)
    pix.save(out)
    print(nome, pix.width, "x", pix.height, "->", os.path.basename(out))
