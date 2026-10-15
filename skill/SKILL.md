---
name: atualiza-humanizadas-spotsys
description: Atualiza as plantas humanizadas de um empreendimento Seazone quando o projeto aprovado muda. Confere a planta contra o PDF aprovado e o SpotSys, remove texto (áreas, números, rótulos) sem alterar a geometria e gera uma imagem geral por pavimento e uma imagem por unidade para o cadastro do 360, com relatório de QC. Use quando pedirem "atualizar humanizada", "planta sem texto", "recorte por unidade", "humanizada x projeto aprovado", "planta desatualizada no SpotSys" ou citarem um empreendimento com is_outdated_area.
---

# Skill: atualização de plantas humanizadas (SpotSys / 360)

## A. Objetivo, escopo e limitações

> **REGRA FIXA 1: fonte do projeto aprovado = Autodoc.** O projeto aprovado usado na comparação vem **sempre** do Autodoc, na pasta da versão assinada:
> `SEAZONE › <Empreendimento> › 02 - Projetos › 2.1 Projeto Arquitetônico › 2.1.c Projeto Legal › 2.1.c.a Projeto Legal Aprovado (versão assinada)`
> (Cachoeira Spot: https://plataforma.autodoc.com.br/projetos/directories/folder/6a3aff985962717869290367, arquivo `CACHOEIRASPOT-PL-ARQ-DCT-GER-XXX-000-R06.pdf`, Rev 06).
> Use a **maior revisão** da pasta. Não use cópias do Drive (`Projeto aprovado/*APROVADO*.pdf`, "Arquivos - Investidores" etc.): elas podem estar defasadas. Registre no diagnóstico o código do arquivo, a revisão e a data do download.
>
> **REGRA FIXA 3: a planta humanizada é desenhada a partir de um arquivo técnico do projeto aprovado (DWG/IFC), no estilo da humanizada de LANÇAMENTO.** Paredes, escadas, portas, louças, marcenaria e mobiliário vêm do arquivo técnico (`gera_humanizada_dwg.py`); a humanizada de lançamento define só o estilo visual (cores e acabamentos). **Não usar colagem da imagem do lançamento nem IA para a geometria**: as duas tentativas no Cachoeira Spot deformaram as plantas onde o pavimento mudou (mezanino, térreo, rooftop). Não precisa de Revit: DWG → DXF no AutoCAD (`accoreconsole`) ou no ODA File Converter (gratuito).
>
> **REGRA FIXA 4: o arquivo base precisa ter as MESMAS ÁREAS do PDF aprovado.** Antes de gerar qualquer humanizada, rodar `confere_areas_base_x_aprovado.py`: cada área escrita no arquivo base (apto, garden, sacada, mezanino, loja) é comparada com a área do PDF aprovado do Autodoc na mesma unidade (tolerância 0,02 m², só arredondamento). Saída: CSV por pavimento (IGUAL / DIFERENTE / FALTA_NO_DWG) e veredito BATE / NAO_BATE.
> - **BATE** em todas as unidades: segue para a geração.
> - **NAO_BATE**: o arquivo não é o aprovado. Procurar o arquivo técnico da mesma revisão do PDF (Autodoc → 2.1.c Projeto Legal → DWG; time de projetos). Sem ele, corrigir no arquivo base as unidades divergentes até a área bater e registrar cada correção. Nenhuma unidade com área diferente do aprovado vai para validação ou publicação.
> - Registrar no diagnóstico: arquivo base, revisão, data, origem (Autodoc/Drive) e o resultado da conferência.
>
> **REGRA FIXA 5: o que o DWG não desenha vem do PDF aprovado, nunca é inventado.** Vagas de bicicleta (etiquetas BR/BV/BC), elevadores (hachura ELEVADORES), lixeiras (zona DEPÓSITO … LIXO) e piscina são posicionados pelas etiquetas do PDF assinado e desenhados com o objeto da humanizada de lançamento. O alinhamento PDF→planta é refeito sobre a planta gerada (`registra_pdf_imagem.py`; com escala fixa, `registra_translacao.py`).
>
> **UNIFICAÇÃO:** recorte por tipologia, cotas e texto/capacidade/solar usam a skill `seazone-tech/plantas-humanizadas`, com o `cfg` gerado do DWG por `gera_cfg_recorte.py`. Bot, painel, planta de tipologias e estudo solar usam a Planta Viva (`seazone-tech/szi-planta-humanizada`). Detalhes em `UNIFICACAO_PLANTAS_HUMANIZADAS.md`; executor de teste em `scripts/roda_unificado.py`.
>
> **REGRA FIXA 2: primeiro atualizar a planta, depois cortar.** O foco da skill é **atualizar a planta humanizada de cada pavimento** de acordo com o projeto aprovado. A comparação é **humanizada do lançamento × projeto aprovado (Autodoc)**, pavimento a pavimento e unidade a unidade. **Nenhum recorte por unidade é feito antes de a planta geral atualizada ser validada.**


**Problema.** Quando o projeto aprovado muda, a área nova sobe no SpotSys, mas a humanizada fica para trás. Hoje o time recorta à mão, tampa texto com retângulos e não confere a planta contra o aprovado. A geração direta do PDF por IA teve 49% de aproveitamento e produziu imagens distorcidas.

**O que a skill faz:**
1. Audita as fontes: humanizada existente, PDF aprovado e SpotSys.
2. Decide o nível de atualização, conforme a régua da seção K.
3. Reaproveita a humanizada válida e remove todo o texto **sem tocar na geometria**: só os pixels das letras são reconstruídos.
4. Registra a prancha vetorial aprovada sobre a imagem e mede objetivamente distorção e aderência.
5. Recorta cada unidade pelo polígono do **aprovado**, não por máscara manual.
6. Gera o relatório de QC por unidade e os pacotes de saída.

**Modo de operação (alinhado ao método do Fernando, thread de 06/10):** roda **ponta a ponta, sem parada manual**, a cada atualização do SpotSys, com um único comando:
```
python skill/scripts/roda_pipeline.py skill/exemplos/<empreendimento>.json
```
A última etapa aplica **duas travas**:
1. **Trava de QC (automática):** só as unidades aprovadas em todos os critérios entram no pacote. Ressalvas e pendências vão para `BLOQUEADOS.csv` com o motivo.
2. **Validação humana (obrigatória):** o pacote sai como `AGUARDANDO_VALIDACAO`, com `VALIDACAO_HUMANA.csv` (uma linha por unidade) e `LEIA-ME_NAO_CARREGAR.txt`. Uma pessoa confere as imagens e as folhas de contato e preenche `validado = S/N`, `validador`, `data` e `observacao`. O pipeline roda de novo com `"validacao_humana": "<planilha preenchida>"` no JSON, e só então gera `pins_360.json` e o manifesto de carga, apenas com as unidades validadas.

A carga no SpotSys/360 lê esse pacote validado e é feita por quem tem acesso de escrita. A skill não escreve nos sistemas.

**O que a skill NÃO faz:**
- Não desenha nem redesenha planta. Se a humanizada não corresponde ao aprovado (níveis 3 e 4), a skill aponta o problema e encaminha para desenho humano.
- Não publica no SpotSys nem no 360. A publicação é sempre humana e depende de validação.
- Não substitui a conferência de áreas: as áreas não aparecem nas imagens, mas são conferidas em separado.

## B. Pré-requisitos

- **Acesso de leitura ao Drive** do empreendimento (pasta `02 - Projetos`).
  - O conector usado baixa arquivos de até cerca de 10 MB. Humanizadas maiores precisam ser baixadas manualmente para `00_entradas/originais/`.
- **Acesso ao Nekt** (tabela `nekt_operacional_bronze.sup_bd_szi_szi_spot_building_units`), ou um export CSV equivalente do SpotSys.
- **Python 3.10+** com `pymupdf (fitz)`, `opencv-python`, `numpy`, `scipy` e `openpyxl`. Não precisa de OCR nem de GPU.
- **Scripts** em `skill/scripts/`.

## C. Entradas obrigatórias

| Entrada | Onde costuma estar | Observação |
|---|---|---|
| Humanizada vigente por pavimento (PNG) | `08 - Projeto Arquitetônico/04 - Plantas Humanizadas/<versão mais nova>` | Preferir a versão **sem texto ou em camadas** (PSD) da autora, se existir. Sem ela, a skill remove o texto. |
| PDF do projeto aprovado (vetorial) | **Autodoc** › 2.1 Projeto Arquitetônico › 2.1.c Projeto Legal › **2.1.c.a Projeto Legal Aprovado (versão assinada)**, maior revisão | É a referência de geometria e numeração. Precisa ser vetorial (texto selecionável). **Nunca usar a cópia do Drive.** |
| Humanizada do lançamento | Drive › `04 - Plantas Humanizadas/LANÇAMENTO` (ou equivalente) | É a base que será **atualizada** conforme o aprovado. |
| Quadro de áreas da versão vigente no SpotSys | Nekt (consulta abaixo) | É a referência de cadastro (versão, áreas, unidades ativas). |
| Identificação do empreendimento e das unidades | SpotSys (`code`, `floor`) | O código do SpotSys é o identificador canônico nos nomes de arquivo. |

Consulta ao SpotSys (Nekt):
```sql
SELECT u.code, u.floor, u.typology, u.project_version, u.total_area, u.mezzanine_total_area,
       u.garden_total_area, u.terrace_balcony_total_area, u.is_outdated_area, u.status, u.id
FROM nekt_operacional_bronze.sup_bd_szi_szi_spot_building_units u
JOIN nekt_operacional_bronze.sup_bd_szi_szi_staging_spot_buildings b ON b.id = u.spot_building_id
WHERE b.short_name = '<Nome do Spot>' AND u.is_active = true ORDER BY u.code;
```
Imagens já publicadas: `sup_bd_szi_szi_spot_photos_association` → `sup_bd_szi_szi_spot_images.url`.

## D. Fluxo de execução

Estrutura de pastas (nunca sobrescrever originais):
```
00_entradas/originais/   cópias intocadas (humanizadas, PDF, quadro)
01_diagnostico/          diagnóstico, comparativos de área
03_trabalho/             intermediários (sem_texto, células, rótulos, configs)
04_saida/<EMP>_<REV>/    01_PAVIMENTOS, 02_UNIDADES, 03_CONFERENCIA
05_qc/registro/          transformações e sobreposições
```

**O fluxo tem duas fases, nesta ordem:**

**FASE 1: atualizar a planta humanizada (foco principal).**

| Etapa | Ação | Saída | Critério para seguir |
|---|---|---|---|
| 1a. Baixar o aprovado do Autodoc | Pasta 2.1.c.a, maior Rev. Salvar em `00_entradas/originais/projeto_aprovado/` com o nome original. | PDF vetorial + registro (código, Rev, data) | Se a Rev do Autodoc for diferente da usada antes, **refazer a comparação inteira**. |
| 1b. Comparar lançamento × aprovado | Por pavimento: sobrepor a prancha aprovada à humanizada do lançamento (`registra_pdf_imagem.py`), extrair numeração e áreas (`extrai_rotulos_pdf.py`) e listar, unidade a unidade, o que mudou: numeração, posição, divisas, paredes, portas e esquadrias, sacadas, gardens, áreas comuns. | `01_diagnostico/comparativo_lancamento_x_aprovado_<PAV>.md` + overlay | Toda diferença tem evidência (prancha e coordenadas). |
| 1c. Atualizar a planta | `python gera_humanizada_aprovado.py <aprovado_autodoc.pdf> <celulas.json> <registro.json> <humanizada_ref_sem_texto.png> <saida.png> [--divergentes 505,506]`: gera a planta **na geometria e proporção do aprovado** (divisas viram paredes onde faltam; interiores reaproveitados da referência; unidades divergentes ficam sem interior e sinalizadas). Depois, ajustar a humanizada de cada pavimento ao aprovado: redesenhar só o que mudou, mantendo a linguagem gráfica do lançamento. Se já existir humanizada atualizada pelo time (ex.: "PROJETO LEGAL"), **conferi-la contra o aprovado do Autodoc** em vez de redesenhar. | Planta geral atualizada por pavimento (com e sem texto) | Overlay com o aprovado: anisotropia 0,98–1,02, chamfer ≤ 15 cm, numeração igual. |
| 1c'. **Método padrão (sem Revit, sem DWG, sem IA)** | Qualquer pessoa, só com o PDF do Autodoc e a humanizada de lançamento: (1) `powershell -File ocr_windows.ps1` sobre a saída de `prepara_ocr.py` (humanizada **com** texto) → números das unidades no lançamento (OCR nativo do Windows, nada a instalar); (2) `python gera_planta_compatibilizada.py <aprovado.pdf> <celulas.json> <lancamento_sem_texto.png> <saida.png> --ocr <ocr.json> [--escala 200 no mezanino]`. Cada contorno aprovado busca a mesma unidade no lançamento (ancorada pelo número), com ajuste de posição e escala X/Y limitada a ±15%; o interior é recortado **exatamente** no contorno aprovado (nada do vizinho entra) e as paredes do aprovado são redesenhadas onde faltam. Se houver DWG/Revit do layout no aprovado, `gera_humanizada_vetor.py` gera a versão vetorial (opcional, para conferência). | Planta do pavimento + `_conferencia.jpg` (divisas do aprovado em vermelho) + `_log.json` (esticamento por unidade) + `_comparativo.jpg` | `qc.divisa_parede_mediana_cm` ≤ 5 e `frac_divisas_ate_15cm` ≥ 0,80. Unidades **SINALIZADAS** (esticamento > 12% ou encaixe > 20 cm) vão para revisão/desenho antes da validação. |
| 1d. Validar a planta atualizada | Pessoa confere cada pavimento contra o aprovado e assina (`VALIDACAO_PLANTAS.csv`: pavimento, validado S/N, validador, data, observação). | Plantas gerais validadas | **Sem validação da planta geral, não existe Fase 2.** |

**FASE 2: recortes, pins e publicação** (só com as plantas da Fase 1 validadas). As etapas abaixo partem da planta geral atualizada e validada.

| Etapa | Comando / ação | Saída | Critério para seguir |
|---|---|---|---|
| 1. Inventário | Listar a pasta do Drive (humanizadas, quadros) e baixar o aprovado **do Autodoc** (Fase 1, etapa 1a). Baixar para `00_entradas/originais`. | lista de arquivos | Existem humanizada, PDF vetorial e SpotSys. Se não, ver F. |
| 2. SpotSys | Rodar a consulta da seção C e salvar o CSV. | `spotsys_<emp>_<data>.csv` | Versão do SpotSys = versão do PDF aprovado. Se divergir, **parar e perguntar**. |
| 3. Rótulos do aprovado | `python extrai_rotulos_pdf.py <pdf> <págs> <spotsys.csv> rotulos.json conferencia.csv` | áreas por unidade lidas do PDF × SpotSys | Itens "VERIFICAR" são conferidos manualmente na prancha e registrados. |
| 4. Quadro × SpotSys (opcional) | `python compara_areas.py <quadro.xlsx> <aba> <spotsys.csv> saida.csv` | divergências do quadro | Em divergência, o PDF aprovado desempata. |
| 5. Nível da mudança | Comparar a humanizada existente com o aprovado (numeração, perímetro, áreas escritas) e aplicar a régua K. | nível 1 a 4 | Níveis 1–2 seguem; 3–4 vão para desenho humano. |
| 6. Remover texto | `python remove_texto.py <png> <saida.png> <debug.png> [--fundo-min 60]` | PNG sem texto + `_remocao.json` | `texto_residual_linhas = 0` e `pixels_parede_alterados = 0`. Debug revisado (sem falso positivo em móveis). |
| 7. Células do aprovado | `python celulas_pdf.py <pdf> <pág> rotulos.json celulas.json debug.png [--janela x0,y0,x1,y1 --esc 6] [--correcoes corr.json]` | polígono de cada unidade | Todas as unidades com região. Revisar o debug (cores por unidade). |
| 8. Registro PDF→imagem | `python registra_pdf_imagem.py <pdf> celulas.json <sem_texto.png> 05_qc/registro/<PAV> [--escala 100]` | transformação + overlay | Anisotropia em [0,98; 1,02] e chamfer mediano ≤ 15 cm. Fora disso, **ressalva**. |
| 9. Recortes (só após 1d) | Montar `config_recortes.json` e rodar `python gera_recortes.py config.json` | planta geral + 1 PNG por unidade | Nenhuma unidade sem polígono. |
| 10. Folhas de contato | `python folha_contato.py <pasta> <saida.jpg>` | painel para revisão humana | Registrar observações em `revisao_visual.json`. |
| 11. QC | `python relatorio_qc.py config.json spotsys.csv conferencia.csv revisao_visual.json 05_qc/registro 03_trabalho/sem_texto` | `QC_RELATORIO.md` + `qc_unidades.csv` | Entregar para validação humana. |
| 12. Trava QC + pacote (aguardando validação) | `python gera_pacote_publicacao.py config.json spotsys.csv [--aceitar-ressalva]` | `04_PUBLICACAO/` com imagens aprovadas, `manifesto_publicacao.csv`, `pins_360.json` (polígonos 0–1 por `szi_unit_id`, formato `seazone360_floor_plan_pins`) e `BLOQUEADOS.csv` | Só o status APROVADO passa. |
| 13. **Validação humana** | Conferir imagens e folhas de contato; preencher `VALIDACAO_HUMANA.csv`; rodar de novo com `validacao_humana` no JSON. | `pins_360.json` + manifesto só com as validadas; reprovadas em `BLOQUEADOS.csv` | **Obrigatória.** Sem validador e data, a unidade não entra. |
| 14. Carga | Upload das imagens (SpotSys → floor_plan da unidade) e dos pins (360), a partir do pacote validado. | — | Feita por quem tem acesso de escrita. A skill não escreve nos sistemas. |

As etapas 1 a 12 rodam encadeadas pelo `roda_pipeline.py`, que grava `03_CONFERENCIA/tempos_etapas.csv`. As etapas 1 (inventário e download do Drive) e 2 (export do SpotSys) ainda são feitas por conector; o tempo delas depende do acesso.

## E. Regras de decisão

| Situação | Decisão |
|---|---|
| A humanizada existente tem a mesma numeração e o mesmo perímetro do aprovado, e as áreas escritas batem com o SpotSys. | **Reaproveitar**: remover texto e recortar (nível 1). |
| A humanizada difere do aprovado em detalhe localizado (uma porta, uma sacada, um rótulo) e o restante bate. | **Atualizar só a parte**: encaminhar o trecho para edição humana e recortar o restante (nível 2). |
| Mudou a numeração, a posição de unidades ou a divisão de ambientes. | **Refazer a unidade ou o pavimento**: desenho humano a partir do aprovado/executivo; não usar a humanizada antiga (nível 3–4). |
| A versão no SpotSys não é a do PDF aprovado. | **Pedir esclarecimento** a Projetos/SpotSys antes de qualquer imagem. |
| O PDF tem rótulo duplicado ou trocado, e duas outras fontes concordam entre si. | Aplicar **correção documentada** (`--correcoes`), marcar **ressalva** e pedir validação da arquitetura. |
| O PDF diverge do SpotSys e não há segunda fonte. | **Interromper o item** (pendente) e encaminhar a Projetos. |
| Anisotropia fora de [0,98; 1,02] ou chamfer > 15 cm. | Gerar o recorte com **ressalva** e encaminhar para conferência humana do pavimento. Nunca deformar a imagem para "encaixar". |
| Faixa de área sem divisa no aprovado (ex.: área coberta aberta contínua). | Recorte **pendente** até alguém definir a regra. |
| Arquivo indisponível ou PDF sem texto (escaneado). | **Interromper o pavimento** e registrar o motivo no QC. |

## F. Tratamento de exceções

| Exceção | Tratamento |
|---|---|
| Planta **sem texto** já disponível | Pular a etapa 6 e usá-la direto. |
| Planta com **área desatualizada** escrita | A remoção de texto elimina a área. A configuração ainda precisa ser conferida (etapa 5). |
| **Unidade modificada** | Régua K. Se for nível ≥ 3, sai do fluxo automático. |
| **Ausência de arquivos** | O pavimento fica pendente no QC com o motivo "arquivo indisponível". O resto segue. |
| **Documentos conflitantes** | Prioridade: PDF aprovado (geometria e numeração) > SpotSys (cadastro vigente) > quadro xlsx > humanizada (referência visual). Todo conflito é registrado e nunca resolvido em silêncio. |
| **PDF de baixa qualidade** (raster) | Os rótulos não são extraíveis. Pedir o PDF vetorial ou o DWG; a skill não lê aprovado escaneado. |
| **Pavimentos repetitivos** (tipo) | Rodar o fluxo em cada pavimento, porque numeração, sacadas e jardins mudam. A régua do QC detecta se um pavimento difere do outro. |
| **Alteração significativa de layout** | Nível 4: nova humanizada desenhada por pessoa, depois volta para a etapa 6. |
| **Texto sobre deck, grama ou tapete** | `--fundo-min 60`. O preenchimento por deslocamento preserva a textura; revisar os borrões no debug. |
| **Unidade em dois níveis** (térreo + mezanino) | Registrar os dois níveis. A imagem final mostra os dois lado a lado, na mesma escala real; os níveis isolados ficam em `niveis/`. |
| **Rooftop/pavimento com decks e áreas abertas sem parede** | O ajuste automático do registro pode falhar (chamfer alto, recortes deslocados). Use `"registro_de": "<pavimento vizinho>"` no JSON: herda a transformação de uma prancha da mesma folha e enquadramento. Confirme no overlay que o núcleo (escada/elevadores) coincide. |
| **Humanizada diverge do aprovado só em parte do pavimento** | Detectado na folha de contato (o recorte pelo polígono aprovado corta cômodos). Marcar as unidades como PENDENTE em `revisao_visual.json`: a trava bloqueia, e o desenho volta para correção (nível 2). |
| **Mezanino sem código na planta 1:100** | Usar o esquema 1:200 da mesma prancha (`--janela`, `--esc 6`, `--escala 200`). |

## G. Padrão de saída

```
04_saida/<EMP>_<REV>/
  01_PAVIMENTOS/<EMP>_<PAV>_GERAL_HUM-SEM-TEXTO_<REV>.png
  02_UNIDADES/<PAV>/<EMP>_<PAV>_UN-<código SpotSys>_HUM-SEM-TEXTO_<REV>.png
  02_UNIDADES/PAV-01+MEZ/niveis/...        (níveis isolados das unidades duplex)
  03_CONFERENCIA/QC_RELATORIO.md, qc_unidades.csv, recortes_log.json, folha_contato_*.jpg
```

- **Formato:** PNG RGBA. Fundo transparente fora da unidade.
- **Recorte da unidade:** pela face externa das paredes da própria unidade. O contorno do aprovado indica a unidade; o recorte se encaixa nas paredes reais da humanizada. Nada da unidade vizinha aparece e os cantos são retos. Se o encaixe falhar, o log registra `falhou_poligono_com_folga` e a unidade deve ser olhada.
- **Resolução:** a da humanizada de origem, sem reamostragem; nos pavimentos tipo, cerca de 0,9 cm/px. O mínimo aceito é 400 px no maior lado.
- **Códigos de pavimento:** `PAV-01` (térreo), `MEZ`, `PAV-02`…, `COB` (cobertura/rooftop).
- **Código da unidade:** o do SpotSys (`101`, `L1`).
- **Revisão:** `R01`, `R02`… Nunca sobrescrever a revisão anterior.

## H. Controle de qualidade (critérios objetivos)

| Critério | Como é medido | Aceite |
|---|---|---|
| C1 Identificação | Código existe no SpotSys, tem polígono no aprovado e está no nome do arquivo | obrigatório |
| C2 Área SpotSys × aprovado | Rótulos vetoriais do PDF × campos do SpotSys | igual (tolerância 0,01 m²) ou conferido manualmente e registrado |
| C3 Sem texto | Detector reaplicado na imagem limpa | 0 linhas residuais |
| C4 Sem distorção | Anisotropia do registro (escala x / escala y) | 0,98 a 1,02 |
| C5 Aderência ao aprovado | Distância mediana das divisas do aprovado até as paredes da imagem | ≤ 15 cm |
| C6 Recorte = planta geral | Pixels opacos do recorte idênticos aos da planta do pavimento | diferença 0 |
| C7 Resolução | Maior lado do recorte | ≥ 400 px |
| Visual | Folha de contato + overlay, revisados por pessoa e registrados em `revisao_visual.json` | sem pendência |

**Status:**
- **APROVADO:** todos os critérios ok.
- **APROVADO_COM_RESSALVA:** C4/C5 fora da tolerância, área conferida manualmente ou observação cosmética.
- **PENDENTE:** falha em C1, C3 ou C6; divergência de área; observação visual bloqueante; ou arquivo ausente.

**Nenhuma imagem vai para o SpotSys ou para o 360 sem validação humana registrada** (`VALIDACAO_HUMANA.csv`, com validador e data por unidade). A trava de QC reduz o trabalho de quem valida, mas não substitui essa conferência.

## I. Limitações conhecidas

- **Layout interno:** o legal aprovado só tem perímetro, numeração e área. Paredes internas, louças e mobiliário **não são conferíveis** contra ele. A humanizada é aceita como layout, e a conferência fina exige o executivo ou o IFC de interiores.
- **Remoção de texto:** é reconstrução de fundo. Em fundo com textura (deck, grama, piso) a skill copia o fundo vizinho; em fundo liso (cama, piso claro) usa preenchimento suave com acerto de tom, para não deixar o "fantasma" das letras. Sobre tapetes ainda podem sobrar borrões leves, que precisam de revisão visual. A versão sem texto da autora elimina o problema.
- **Texto que o detector não pega** (letra colada em esquadria ou linha): indicar a caixa em `caixas_manuais` no JSON do pavimento. Linhas que atravessam a caixa são preservadas.
- **Detector de texto:** calibrado para texto preto puro. Texto colorido, com contorno ou muito pequeno (< 14 px a 3840 px de largura) pode escapar, mas o C3 e o debug mostram isso.
- **Registro:** é global por pavimento (sem rotação). Uma humanizada com deformação local passa no C4 se a média estiver ok; o overlay precisa ser olhado.
- **Faixas sem divisa no aprovado:** a atribuição a uma unidade é arbitrária, e o item fica pendente.
- **Execução:** o conector do Drive limita os downloads a cerca de 10 MB, e o Slack só é lido com acesso ao canal.

## J. Como usar em um novo empreendimento (passo a passo)

1. Crie uma pasta de trabalho com a estrutura da seção D e copie `skill/scripts/`.
2. Baixe o PDF aprovado **do Autodoc** (2.1.c.a Projeto Legal Aprovado, versão assinada, maior Rev), a humanizada do lançamento por pavimento e o export do SpotSys (consulta da seção C).
3. **Fase 1:** compare lançamento × aprovado por pavimento, atualize a planta humanizada e valide cada planta geral antes de seguir.
3. Abra o PDF e anote as páginas das plantas de pavimento. Rode `extrai_rotulos_pdf.py` e resolva os itens "VERIFICAR" olhando a prancha. Registre tudo em `revisao_visual.json` → `area_conferida_manual`.
4. Classifique o nível da mudança (seção K). Se for nível 3 ou 4, pare e encaminhe para desenho.
5. Rode `remove_texto.py` em cada pavimento. Abra o `_debug.png` e confira que só texto ficou em vermelho.
6. Rode `celulas_pdf.py` em cada página. Abra o debug e confira que cada unidade tem uma região e que as áreas comuns ficaram cinza.
7. Rode `registra_pdf_imagem.py` e abra o `_overlay.jpg`: as linhas vermelhas precisam cair sobre as paredes.
8. Monte o `config_recortes.json` (veja o exemplo em `03_trabalho/config_recortes_R01.json` do Cachoeira) e rode `gera_recortes.py`.
9. Gere as folhas de contato, revise e registre as observações.
10. Rode `relatorio_qc.py` e envie `QC_RELATORIO.md` com as folhas de contato para validação (Carol/Projetos). Só depois disso alguém publica.

## K. Régua de decisão para mudanças futuras

| Nível | Enquadramento (evidência) | Estratégia | Conferência exigida | Aprovação | Encaminhar ao time quando |
|---|---|---|---|---|---|
| **1. Sem alteração geométrica** | Numeração, perímetro e divisão iguais ao aprovado. Só áreas ou textos desatualizados, ou planta sem versão sem texto. *(Cachoeira: humanizada 03/2026 × aprovado.)* | Reaproveitar: remover texto, registrar, recortar. | C1–C7 automáticos + folha de contato. | C1–C7 ok + revisão visual. | C4/C5 fora da tolerância ou artefato visível. |
| **2. Alteração localizada** | Uma ou poucas unidades com mudança pontual (porta, sacada, garden, rótulo) e o restante idêntico. Detectável no overlay como divisa do aprovado sem parede correspondente num trecho. | Recortar as unidades íntegras. Editar só o trecho alterado (humano, sobre a humanizada existente) e reprocessar a unidade. | C1–C7 + overlay da unidade alterada, conferido por pessoa. | Unidade editada com C5 ≤ 15 cm e validação de Projetos. | Sempre que houver edição de desenho. |
| **3. Alteração relevante** | Mudança de layout, de configuração ou de distribuição de ambientes em várias unidades; numeração mantida. Overlay com várias divisas sem parede. *(Cachoeira: lançamento R00 × aprovado, com 82 de 87 unidades com Δ coberta > 0,05 m², lojas e térreo reconfigurados.)* | Não reaproveitar a humanizada antiga. Pedir nova humanizada do pavimento (designer), a partir do aprovado/executivo. Depois, nível 1. | Conferência do desenho novo contra o aprovado (overlay) antes de remover texto e recortar. | Igual ao nível 1, sobre o desenho novo. | Na classificação. |
| **4. Alteração estrutural da planta** | Mudança de numeração, número de unidades, núcleo, fachada ou pavimentos, ou versão do SpotSys ≠ PDF. | Interromper. Atualizar o SpotSys e a documentação. Nova humanizada completa a partir do executivo/IFC. | Reconciliação PDF × SpotSys unidade a unidade + overlay completo. | Validação de Projetos + Comercial antes da publicação. | Imediatamente. |

**Como medir o nível sem limite numérico arbitrário:** rode as etapas 3, 7 e 8 com a humanizada existente.
- **Nível 1:** todas as divisas do aprovado têm parede correspondente no overlay, e os códigos batem.
- **Nível 2:** só algumas divisas não batem, todas concentradas em poucas unidades.
- **Nível 3:** as divisas não batem de forma espalhada pelo pavimento.
- **Nível 4:** os códigos ou o número de unidades não batem.

## L. Estilo "desenho técnico humanizado" (próxima etapa)

O método do Fernando pede o estilo técnico (cor chapada, textura simplificada, volume leve, não realista). Decisão de 12/10: para terça, entregar o render 2026 sem texto, que é a imagem já fiel ao aprovado. O estilo técnico fica como próxima etapa, por estes motivos:
- **Estilizar o raster não funciona:** com mean-shift + paleta reduzida, camas e móveis brancos se fundem ao piso e surgem manchas irregulares. O teste está em `03_trabalho/thumbs/estilo_comparacao.jpg`, e a abordagem foi rejeitada.
- **O caminho correto é renderizar o vetorial** (DWG do projeto básico aprovado: paredes, esquadrias e blocos de mobiliário) com a paleta da régua visual. É preciso garantir que o DWG usado é a mesma versão do SpotSys. O executivo PE R00 (05/10/2026) é mais novo que a 2.2.
- O QC (C1–C7), a trava e os pins valem igual para o novo estilo, porque o registro e os recortes não dependem do estilo da imagem.
