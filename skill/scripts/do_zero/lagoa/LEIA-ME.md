# Lagoa Spot: modelo de humanizada do zero (20–21/10/2026)

São scripts **modelo**, com coordenadas e zonas do Lagoa. Para outro empreendimento, copie e ajuste antes de rodar.

| Script | Função |
|---|---|
| `raster_exec.py` | rasteriza o DXF do executivo (máscaras de paredes, vidros, soleiras, portas, louças e escadas) |
| `registra_lanc.py` | registra o executivo no quadro do lançamento |
| `ambientes.py` | lê os ambientes |
| `legal_camadas.py`, `legal_masks.py`, `registra_legal.py`, `gera_pdf_legal.py` | levam as camadas do PDF Legal para o quadro do lançamento |
| `objetos_lancamento.py` | extrai os móveis do lançamento por ambiente |
| `render_hibrido.py` | **render final** |
| `tira_rotulos.py` | tira as caixas de rótulo do lançamento |
| `escreve_unidades.py` | escreve "UNIDADE NN" dentro de cada unidade |

O `render_hibrido.py` funciona assim:
- fora das zonas que mudaram, usa a representação do lançamento tal qual;
- dentro das zonas (`ZONAS_LEGAL`/`ZDES`), redesenha pelo Legal com os símbolos do lançamento;
- a área externa sai pelo Legal.

**Uso:**

```
py render_hibrido.py <TER|02P> <lancamento.png> <saida.png>
py escreve_unidades.py <P> <saida.png> <final.png> --amb ../carol/<P>_hib
```

As regras de representação estão em `skill/SKILL.md`, Etapa 4B, e no erro E19.
