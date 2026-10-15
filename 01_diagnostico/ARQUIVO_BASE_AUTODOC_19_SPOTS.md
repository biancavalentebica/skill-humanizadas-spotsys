# Arquivo base (DWG / IFC / Revit) no Autodoc: 19 Spots com modificação

Levantamento automático no Autodoc em 14/10/2026 (`SEAZONE › <Spot> › 02 - Projetos › 2.1 Projeto Arquitetônico`).

Busca até 4 níveis e até 45 pastas por Spot, só nas pastas de arquitetura (sem Imagens, Engenharia e Decor). Foram contados os arquivos `.dwg`, `.ifc`, `.rvt` e `.nwc`. Arquivos fora dessa estrutura (Drive, outra pasta do Autodoc) não entram.

| # | Spot | Arquivo base do aprovado ou posterior | Etapa(s) encontrada(s) | Serve como base? |
|---|---|---|---|---|
| 1 | Barra Spot | DWG (16) + IFC + RVT do **Projeto Legal** (R21–R22); Pré-Executivo e Executivo | Legal, Pré-Exec, Exec | **Sim** |
| 2 | Batel Spot | — | Estudo Preliminar, Anteprojeto | Não |
| 3 | Cachoeira Spot | — (pastas DWG do Legal e do Básico vazias). O DWG usado veio do **Drive** | Estudo Preliminar | Não no Autodoc |
| 4 | Cachoeira Beach Spot | DWG (11) + IFC do **Pré-Executivo** (R02/R05) | EP, Anteprojeto, Pré-Exec | **Sim** (conferir áreas) |
| 5 | Campeche Spot | DWG (34) + IFC do **Executivo** | EP, Anteprojeto, Executivo | **Sim** (conferir áreas) |
| 6 | Canas Beach Spot | IFC do **Projeto Básico** (R00); DWG + IFC do Pré-Executivo | EP, Anteprojeto, Básico, Pré-Exec | **Sim** |
| 7 | Canasvieiras Spot | DWG (38) + IFC do **Executivo** | EP, Anteprojeto, Executivo | **Sim** (conferir áreas) |
| 8 | Caraguá Spot | DWG do **Projeto Legal Aprovado (2.1.c.a)** R00 + Legal R06; Pré-Executivo | Legal aprovado, Pré-Exec | **Sim** |
| 9 | Ilha do Campeche Spot | — | EP, Anteprojeto | Não |
| 10 | Ingleses Spot | DWG do **Projeto Legal** (R01) | Anteprojeto, Legal | **Sim** |
| 11 | Jurerê Beach Spot | DWG (20) + IFC do **Executivo** | EP, Executivo | **Sim** (conferir áreas) |
| 12 | Jurerê Spot II | — (só Anteprojeto: versão de lançamento, compatibilizada e unidades cotadas) | Anteprojeto | Não |
| 13 | Lagoa Spot | — (nenhum arquivo) | — | Não |
| 14 | Marista 144 Spot | DWG (11) + IFC do **Projeto Legal** (R04–R06); Pré-Executivo e Executivo | EP, Legal, Pré-Exec, Exec | **Sim** |
| 15 | Morro das Pedras Spot | — | EP, Anteprojeto | Não |
| 16 | Salvador Spot | 2 DWG do **Executivo** | EP, Anteprojeto, Executivo | Parcial (só 2 arquivos) |
| 17 | Santo Antônio Spot | — | Estudo Preliminar | Não |
| 18 | Urubici Spot | DWG (9) do **Executivo** (R00) | EP, Executivo | **Sim** (conferir áreas) |
| 19 | Urubici Spot II | — | Estudo Preliminar | Não |

## Resumo

- **11 de 19** têm arquivo técnico de etapa igual ou posterior ao aprovado (Legal, Básico, Pré-Executivo ou Executivo). Um deles, o Salvador, é parcial: só 2 DWG.
  - Só **5** têm do próprio Legal/Básico: Barra, Canas Beach, Caraguá, Ingleses e Marista 144.
  - Os outros 6 têm Pré-Executivo ou Executivo: Cachoeira Beach, Campeche, Canasvieiras, Jurerê Beach, Salvador e Urubici. Essas etapas vêm depois do aprovado e costumam seguir a geometria dele, mas **as áreas precisam ser conferidas** com o PDF aprovado. É a regra 4 da skill (`confere_areas_base_x_aprovado.py`).
- **8 de 19** não têm arquivo do aprovado no Autodoc: Batel, Cachoeira, Ilha do Campeche, Jurerê II, Lagoa, Morro das Pedras, Santo Antônio e Urubici II.
  - Para esses, o arquivo precisa vir do time de projetos ou do Drive (como no Cachoeira). Revit e IFC de Anteprojeto ou Estudo Preliminar não servem, porque são anteriores ao aprovado.

## Recomendação

Padronizar no Autodoc, para cada Spot, o DWG ou IFC da **mesma revisão do PDF aprovado** na pasta `2.1.c Projeto Legal › DWG` / `Arquivos 3D`. Hoje essas pastas existem na estrutura, mas estão vazias na maioria dos Spots.
