# Exemplo real (Santinho Spot, mezanino do bloco A = arquivo 02P-BLA).
# 1) python scripts/ocr.py PLANTA.png ocr_02P-BLA.json
# 2) python este_script.py "<pasta do empreendimento>"  -> <pasta>/configs/02P-BLA.json
# 3) bash scripts/rodar.sh "<pasta>/configs/02P-BLA.json"
import os, sys
sys.path.insert(0, os.path.join(os.path.expanduser('~'), '.claude', 'skills', 'recortar-plantas', 'scripts'))
from config_helper import R, salvar

# Pasta do empreendimento (onde estao a planta, configs/ e Plantas unidades/): 1o argumento ou edite aqui.
EMP = sys.argv[1] if len(sys.argv) > 1 else r"<PASTA DAS PLANTAS>/Santinho Spot"

# contornos no frame de trabalho (2000 px), medidos com paredes.py
xs = [410, 510, 604, 704, 799, 896, 993, 1090, 1187, 1288, 1382, 1476, 1573, 1670, 1772]
u = {f'{101 + i} A': [R(xs[i], 185, xs[i + 1], 357)] for i in range(14)}
u['115 A'] = [R(1772, 210, 1980, 305)]
u['116 A'] = [R(1822, 305, 1980, 405)]
u['117 A'] = [R(1772, 405, 1980, 498)]
for n, x0, x1 in [(122, 405, 612), (121, 612, 820), (120, 820, 1030), (119, 1349, 1560), (118, 1560, 1772)]:
    u[f'{n} A'] = [R(x0, 407, x1, 498)]

salvar(planta=f"{EMP}/SANTINHOSPOT-DC-ARQ-IMG-02P-BLA-000-R00.png",
       ocr="ocr_02P-BLA.json",
       cfg=f"{EMP}/configs/02P-BLA.json",
       saida=f"{EMP}/Plantas unidades",
       empreendimento="Santinho Spot",
       uns=u,
       sufixo=' - Mezanino',          # gera "Santinho Spot - 101 A - Mezanino.png"
       laje=(400, 185, 1980, 500))    # nada fora do predio
