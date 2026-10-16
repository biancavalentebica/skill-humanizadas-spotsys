# Humanizada do zero (regra fixa 0 da SKILL.md)

Geradores usados no térreo de dois Spots. São a referência para os próximos empreendimentos: copie a pasta e ajuste os caminhos e as coordenadas de cada prancha.

| Pasta | Empreendimento | Base de geometria | Layout | Estilo |
|---|---|---|---|---|
| `cachoeira/` | Cachoeira Spot, térreo (aprovado R06) | `r06_base.py`: vetor do legal R06 a 1 cm/px; `mapa_ids.py`: ambientes; `escadas.py`: escadas em Γ | tabela de tipologias do interiores (A–G) | `kit.py`: objetos e texturas do lançamento; `motor.py`: paredes, portas, vidros e escadas |
| `campeche/` | Campeche Spot, térreo (legal R00) | `base.py` + `mapa.py`: legal R00 girado −45° como o lançamento; `registra_exec.py` → `exec_masks.py` → `prep_exec.py`: paredes, pilares e núcleo do executivo R01 registrado sobre o legal; `externo.py`: frente e acesso (ruas, canteiros, fruição, plataforma, árvores, bicicletários) | interiores "Unidades mezanino 38 m²" | `kit.py` + `glifos.py`: textos com as letras do lançamento |

Ordem para rodar (Campeche): `mapa.py` → `registra_exec.py` → `exec_raster.py` → `exec_masks.py` → `prep_exec.py` → `externo.py` → `gera_terreo.py <saida.png>` (cerca de 8 min).

Antes de pintar, monte o inventário de ambientes (`01_diagnostico/INVENTARIO_AMBIENTES_<PAV>.md`): cada área do aprovado e do executivo, o que ela representa e com qual textura do lançamento entra. Não leve linhas da prancha, carros nem cotas para a imagem.

`../remontagem/`: ferramentas da tentativa de remontar o lançamento (descartada no Cachoeira) que continuam úteis: quilting, letras do próprio render, QC de divisas e overlay por âncoras.
