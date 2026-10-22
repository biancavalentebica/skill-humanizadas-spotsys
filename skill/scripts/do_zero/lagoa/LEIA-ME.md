# Lagoa Spot: modelo do método híbrido (aprovado pela Rachel em 22/10/2026)

É o **modelo de referência do Cenário B** (etapa 4B da `SKILL.md`). Os scripts têm caminhos, zonas e coordenadas do Lagoa: para outro empreendimento, copie a pasta para `<EMP>/03_trabalho/` e ajuste antes de rodar. Todos ficam na mesma pasta no empreendimento (o `render_hibrido.py` importa `kit_lagoa` e `tira_rotulos`).

## Ideia do método

- **Geometria limpa** da versão mais nova do projeto (DWG do executivo, ou o PDF legal, conforme a Rachel indicar), registrada no quadro da humanizada de lançamento.
- **Onde a geometria é igual à do lançamento**, a planta usa o desenho do lançamento tal qual, só sem as caixas de rótulo.
- **Só as zonas que mudaram** são redesenhadas, com os símbolos e as texturas do próprio lançamento.
- A emenda entre o redesenho e o lançamento passa sempre no núcleo preto de uma parede que as duas fontes têm no mesmo lugar.

## Ordem de execução

| # | Script | O que faz | O que ajustar no próximo empreendimento |
|---|---|---|---|
| 1 | `previa_dxf.py`, `raster_exec.py` | rasteriza o DXF do executivo: paredes, vidros, soleiras, portas, louças, escadas | caminhos do DXF; camadas do CAD |
| 2 | `registra_lanc.py` | registra o executivo no quadro do lançamento (no Lagoa foi translação pura, 0,4022 cm/px) | pontos de controle; conferir o overlay |
| 3 | `diff_exec_lanc.py` | diferença executivo × lançamento → onde o projeto mudou | limiar; ler o resultado zona a zona |
| 4 | `ambientes.py` | máscara de ambientes (`<P>_amb.npz/json`) por flood fill nas paredes | nomes dos ambientes |
| 5 | `legal_camadas.py`, `registra_legal.py`, `legal_masks.py`, `gera_pdf_legal.py` | levam as camadas do PDF legal (quando ele é a referência nas zonas que mudaram) para o quadro | páginas, clip e registro |
| 6 | `objetos_lancamento.py` | recorta os móveis do lançamento por ambiente | — |
| 7 | `render_hibrido.py` | **render final**: lançamento tal qual fora das zonas; redesenho dentro de `ZONAS_LEGAL`/`ZG`; área externa | `ZONAS_LEGAL`, `ZG`, `ZG_FORA`, `PONTA`, paredes das zonas (`par_z`), WC PNE, área externa |
| 8 | `escreve_unidades.py` | escreve "UNIDADE NN" dentro de cada unidade | código SpotSys de cada ambiente |
| 9 | `../../recorte/config_recorte_bianca.py` | configs da skill da Bianca + `pins_360` | `configs/recorte.json` (exemplo em `skill/exemplos/lagoa-spot_recorte.json`) |
| 10 | skill `recortar-plantas` (Bianca): `recortar.py` | recorte por unidade | — |

`gera_base.py`, `mobilia.py` e `kit_lagoa.py` são o kit das rodadas anteriores (base do executivo, mobiliário e texturas do lançamento). O `kit_lagoa.py` continua em uso pelo render.

**Comandos (pasta `03_trabalho/carol/` no Lagoa):**

```
py render_hibrido.py <TER|02P> <lancamento.png> <sem_texto.png>
py ../do_zero/escreve_unidades.py <P> <sem_texto.png> <final.png> --amb ../carol/<P>_hib
```

Cada render leva de 8 a 10 minutos por pavimento; rode os pavimentos em paralelo, em segundo plano.

As regras de representação estão em `skill/SKILL.md`, etapa 4B, regras 1 a 17.
