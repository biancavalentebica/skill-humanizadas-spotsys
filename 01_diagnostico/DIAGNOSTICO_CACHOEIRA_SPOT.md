# Diagnóstico: Cachoeira Spot (plantas humanizadas × projeto aprovado × SpotSys)

Levantamento de 09/10/2026. Empreendimento: **Cachoeira Spot** (ID-3330, Rua da Amizade 89, Cachoeira do Bom Jesus, Florianópolis). Não confundir com o *Cachoeira Beach Spot* (ID-3491), que é outro empreendimento.

Todos os números abaixo foram calculados a partir dos arquivos listados. Nenhum valor foi estimado.

---

## 1. Arquivos localizados e função de cada um

| # | Arquivo | Origem (Drive) | Função no processo |
|---|---|---|---|
| 1 | `plantas-humanizadas-auditoria-tati-2026-10-06.html` | pasta local | Briefing, histórico, números e prioridade. Para o Cachoeira Spot: versão 2.2 no SpotSys, 87 cotas, 22 recortes do Xande, "com texto bate = Sim", "sem texto = Não". |
| 2 | `NAU-SEA-CCH_ARQ_PL_00_APROVADO_R00.pdf` (13 págs., A1, **vetorial**, ArchiCAD) | 02-Projetos/08-Proj. Arquitetônico/06-Projeto Legal/Projeto aprovado | **Referência técnica.** Projeto Arquitetônico Aprovado nº 72673 (deferido em 16/12/2025, assinado em 05/01/2026). Plantas de pavimento nas págs. 4 a 9, escala 1:100. Traz o contorno das unidades, a numeração e as áreas (coberta, sacada, garden e mezanino). **Não traz layout interno** (paredes internas, banheiro, mobiliário). |
| 3 | `LANÇAMENTO/1..6 *.png` (4000×2000, 26/06/2024) | 08-Proj. Arq./04-Plantas Humanizadas/LANÇAMENTO | Humanizada do lançamento (R00). Referência de formato e linguagem visual. **Desatualizada.** |
| 4 | `PROJETO LEGAL (10/03/26)/*.png` (3840×2160, 09/03/2026, autora Raquel Tavares) | 08-Proj. Arq./04-Plantas Humanizadas/PROJETO LEGAL (10/03/26) | **Humanizada já refeita sobre o projeto legal aprovado.** Traz números de unidade e áreas escritas. Base de reaproveitamento. |
| 5 | `AREAS CACHOEIRA SPOT - VERSÃO FINAL.xlsx` (28/04/2026) | 08-Proj. Arq. | Quadro de áreas R00 Lançamento × R03 Aprovado × R04 × R05, com observações. |
| 6 | Export SpotSys (Nekt `sup_bd_szi_szi_spot_building_units`, consulta de 09/10/2026) → `00_entradas/spotsys_cachoeira_units_2026-10-09.csv` | Nekt | **Versão vigente cadastrada.** São 87 cotas ativas (84 aptos + 3 lojas), todas na versão "2.2 Projeto Legal – Aprovado com modificação de unidades". |
| 7 | Recortes publicados no SpotSys (storage público `spot-photos`) → `00_entradas/originais/spotsys_recortes_publicados/` | SpotSys | São os 22 recortes do Xande (unidades 201 a 222), publicados entre 01 e 03/09/2026. |
| 8 | DWGs PB R09/R10 "Projeto Básico (aprovado prefeitura)", PDFs "Compatibilizado – ARQ LEGAL" R10/R11, IFC `layouts de lançamentos` (385 MB), executivo PE/EX R00 (05–06/10/2026) | 02-Projetos/07-Proj. Executivo e /12 | Fontes vetoriais e de layout interno. Ficam como fonte secundária, porque não foram necessárias para este teste (ver seção 8). |

**Não acessível ou não localizado:**
- **Método do Fernando (teste de 06/10):** não está no HTML da Tati. No grupo de Slack de plantas humanizadas, o Fernando só entrou em 06/10, às 18h35, e não há mensagem dele depois disso. A thread não foi localizada.
- **`Controle_Plantas_Humanizadas.xlsx` e `relatorio_carga.html`:** nenhum arquivo com esses nomes foi encontrado no Drive acessível.
- **`4 PAV.png` (10,9 MB) e `ROOFTOP.png` (11,6 MB) da pasta PROJETO LEGAL (10/03/26):** existem, mas passam do limite de 10 MB do conector do Drive. É preciso baixá-los manualmente.
- **Pastas de referência do Rosa Sul citadas pela Tati:** sem permissão de listagem.
- **Autodoc:** sem acesso neste ambiente.

## 2. Planta humanizada existente para o Cachoeira Spot

Existem duas gerações:
- **R00 Lançamento (06/2024):** 6 pranchas por pavimento, com texto e áreas, layout do anteprojeto. Fica totalmente superada.
- **Projeto Legal (03/2026):** 6 pranchas (térreo, mezanino, 2º, 3º, 4º e rooftop), **com texto** (número da unidade, área coberta, rótulos "S. xxx", "G. xxx", "CIRCULAÇÃO" etc.). Os números e áreas escritos batem com o projeto aprovado (ver seção 5).

Não existe versão **sem texto**, o que bate com o "Existe sem texto? Não" da auditoria.

## 3. Versão mais recente do projeto aprovado

`NAU-SEA-CCH_ARQ_PL_00_APROVADO_R00.pdf`: aprovação nº 72673, com pranchas datadas de 13/11/2025, e alvará de construção de 25/03/2026. A cópia `…APROVADO_R03.pdf` (Arquivos-Investidores) tem o mesmo tamanho em bytes e provavelmente é o mesmo arquivo; isso não foi verificado byte a byte. Há projeto executivo mais novo (PE R00, 05/10/2026), mas **o SpotSys está na 2.2 (legal aprovado)**. A régua de referência é, portanto, o legal aprovado.

## 4. Pavimentos e unidades a atualizar

| Pavimento | Unidades (SpotSys) | Prancha aprovada | Humanizada 2026 disponível | Recorte publicado no SpotSys |
|---|---|---|---|---|
| Térreo (1º pav.) | 101 a 115, L1 a L3 (18) | 04/12 | sim | não |
| Mezanino (das unidades 101–115 e das lojas) | mesmas 18 (unidades em 2 níveis) | 05/12 | sim | não |
| 2º | 201 a 222 (22) | 06/12 | sim | sim, 22 (com área escrita) |
| 3º | 301 a 320 (20) | 07/12 | sim | não |
| 4º | 401 a 420 (20) | 08/12 | **sim, mas não baixada** (> 10 MB) | não |
| Cobertura/Rooftop | 501 a 507 (7) | 09/12 | **sim, mas não baixada** (> 10 MB) | não |

São 87 unidades e 6 pranchas de pavimento. **65 unidades não têm nenhuma imagem no SpotSys**, e as 22 que têm mostram área escrita.

## 5. Diferenças entre humanizada existente e projeto aprovado

- **Lançamento (R00) × Aprovado (R03).** A mudança é relevante em todos os pavimentos: **82 das 87 unidades** mudaram a área coberta em mais de 0,05 m². As maiores variações:
  - lojas: −4,00, −4,24 e −4,71 m²;
  - 101: +4,55 m²;
  - 316 e 416: −2,32 m²;
  - 503: −2,09 m².

  O térreo foi reconfigurado (lixeiras e medidores, vaga PCD, lojas com mezanino, gardens frontais 101/102 reduzidos). O 2º pavimento ganhou o garden 216 lateral, e as sacadas mudaram de dimensão. **A humanizada de lançamento não deve ser reaproveitada para a configuração.**
- **Humanizada 2026 × Aprovado.** Áreas e números escritos conferidos visualmente no térreo, mezanino e 2º pavimento: iguais ao aprovado (exemplos: 214 com 15,06; 216 com 19,11 + garden 7,81; Loja 01 com 20,07 + 9,08). A configuração (posição e numeração das unidades) é a mesma da prancha aprovada. **É a base correta para reaproveitamento.**

## 6. Projeto aprovado × SpotSys (verificável)

Script `skill/scripts/extrai_rotulos_pdf.py` (leitura dos rótulos vetoriais do PDF) e `compara_areas.py`. O resultado está em `conferencia_spotsys_x_pdf_aprovado.csv` e em `comparativo_areas_spotsys_x_aprovado.csv`.

| Verificação | Resultado |
|---|---|
| Área coberta SpotSys = rótulo do PDF aprovado | **87/87** |
| Área descoberta (sacada/garden) e mezanino SpotSys = PDF, conferência automática | 80/87 |
| Conferidas manualmente no PDF | 104, 105 e 106 (garden em 2 partes, a soma bate); L1, L2 e L3 (mezanino "LOJA – MEZANINO" sem código, valores 9,08, 9,20 e 9,41 batem) |
| **Divergência a validar** | **316**, descrito a seguir |

**316:** o PDF mostra "316 GARDEN 22,92 m²". O SpotSys registra 24,07 (terraço/varanda). Na prancha 07/12 há **dois rótulos "317 Sacada"**: um com 1,25 (sob a 317) e outro com 1,15, **posicionado sob a 316**. Como 22,92 + 1,15 = 24,07, o SpotSys está coerente se o segundo rótulo for, na verdade, "316 Sacada". **Atualização de 12/10:** com o texto da humanizada 2026 isolado, a própria humanizada rotula essa sacada como "S. 316 1,15m²". Duas fontes (humanizada e SpotSys) concordam entre si e contrariam a prancha, que tem um erro de rótulo. A correção foi aplicada de forma documentada, e a validação da arquitetura continua recomendada.

**O quadro xlsx "VERSÃO FINAL" diverge do PDF e do SpotSys em 3 unidades:**
- **107:** coberta 32,07 no xlsx, contra 22,10 + 10,97 = 33,07 no PDF.
- **112:** garden 10,38 no xlsx, contra 10,36 no PDF.
- **303:** sacada 6,25 no xlsx, contra 1,61 no PDF.

**O SpotSys está correto nesses três casos.** O xlsx não deve ser usado como fonte única.

## 7. Tabela de divergências

| Pavimento | Unidade | Identificação na planta existente | Identificação no projeto aprovado | Tipo de divergência | Evidência documental | Ação necessária | Status |
|---|---|---|---|---|---|---|---|
| Todos | 87 | Humanizada R00 (2024): layout do anteprojeto | Prancha aprovada 04 a 09/12 | Layout/configuração e área (82 unidades com Δ coberta > 0,05 m²) | xlsx R00×R03, PNG lançamento × PDF | Não usar R00. Usar a humanizada 2026 | Confirmado |
| 2º | 201–222 | Recorte SpotSys com "nnn + área coberta" escrita | Mesmo número, mesma área coberta | Imagem com **área escrita**, contra o critério "sem área". O valor mostrado (coberta) difere do total do SpotSys (ex.: 201 mostra 18,82; o total é 20,09) | Recortes baixados do storage; SpotSys | Substituir por recorte sem texto | Confirmado |
| 2º | 201, 202 e outras | Registros de imagem no SpotSys | — | **Link quebrado**: 2 dos 10 registros testados retornam 404 (img 1873 e 1874) | HTTP 404 `NoSuchKey` | Limpar as associações ao republicar (time SpotSys) | Confirmado (amostra de 10 de 56) |
| Térreo, 3º, 4º, 5º | 65 unidades | Sem imagem no SpotSys | — | Ausência de planta por unidade | Nekt `spot_photos_association` | Gerar recorte sem texto | Confirmado |
| 3º | 316 / 317 | Humanizada 2026: "V. 316 22,92m²" + **"S. 316 1,15m²"** | "316 GARDEN 22,92" + rótulo **"317 Sacada 1,15"** sob a 316 | Rótulo trocado na prancha 07/12 | PDF pág. 7 × humanizada 2026 × SpotSys (24,07 = 22,92 + 1,15) | Correção documentada aplicada (`03_trabalho/correcoes_rotulos.json`); arquitetura valida o rótulo | **Confirmado por 2 fontes, validação recomendada** |
| Térreo | 107 | — | 22,10 + 10,97 (mezanino) | Erro no quadro xlsx (32,07) | PDF págs. 4 e 5 | Corrigir o xlsx (não afeta imagem nem SpotSys) | Confirmado |
| Térreo | 112 | — | garden 10,36 | Erro no quadro xlsx (10,38) | PDF pág. 4 | Corrigir o xlsx | Confirmado |
| 3º | 303 | — | sacada 1,61 | Erro no quadro xlsx (6,25) | PDF pág. 7 | Corrigir o xlsx | Confirmado |
| 4º e cobertura | 401–420, 501–507 | Humanizada 2026 existe, mas não foi baixada | Pranchas 08 e 09/12 | Não verificável neste ambiente | Arquivo > 10 MB | Baixar manualmente e rodar o mesmo fluxo | **Pendente de arquivo** |

## 8. O que pode ser reaproveitado

- **Humanizada PROJETO LEGAL (10/03/26):** geometria, mobiliário, texturas e enquadramento. A geometria é preservada pixel a pixel, porque só os pixels de texto são alterados.
- **PDF vetorial aprovado:** posição de cada rótulo de unidade (coordenadas), usada para identificar e conferir os recortes e para validar as áreas.
- **SpotSys:** lista de unidades (identificação canônica) e áreas vigentes.

## 9. O que precisa ser corrigido, removido ou redesenhado

- **Remover** todo o texto das humanizadas 2026: número, área, "S."/"G.", "CIRCULAÇÃO", "ESCADA", "DML", "ELEV.", "HALL", "LOJA", "MEDIDORES" etc.
- **Gerar** um recorte por unidade, sem texto, no padrão de nome definido.
- **Nada precisa ser redesenhado:** a configuração da humanizada 2026 bate com o aprovado e com o SpotSys.

## 10. Informações ausentes ou não verificáveis com segurança

1. Método do Fernando (06/10).
2. Arquivos 4 PAV e ROOFTOP de 2026 (> 10 MB).
3. Confirmação da arquitetura sobre o rótulo 316/317 (prancha 07/12).
4. Se a autora das humanizadas 2026 tem a versão **sem texto** ou o arquivo em camadas (PSD), que eliminaria os artefatos da remoção automática.
5. Paredes internas e layout interno **não constam do legal aprovado**. A conferência do layout interno só pode ser feita contra o pré-executivo/executivo ou contra o IFC de interiores. Neste teste, a humanizada 2026 é aceita como layout de referência e conferida no **perímetro e na numeração**.
