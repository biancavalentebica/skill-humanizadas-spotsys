---
name: atualiza-humanizadas-spotsys
description: Gera ou atualiza as plantas humanizadas de pavimento de um empreendimento Seazone pela versão mais nova do projeto (aprovado no Autodoc ou executivo), recorta por unidade com a skill recortar-plantas da Bianca e prepara a carga no SpotSys e os pins do 360, com conferência e travas de validação em cada etapa. Dois cenários: A (corrigir a humanizada existente quando a mudança é pontual, como no Batel Spot) e B (método híbrido do Lagoa Spot: lançamento tal qual onde o projeto não mudou, redesenho só nas zonas que mudaram). Use quando pedirem "atualizar humanizada", "humanizada x projeto aprovado", "humanizada do zero", "planta sem texto", "recorte por unidade", "planta desatualizada no SpotSys", "pins do 360" ou citarem um empreendimento com is_outdated_area.
---

# Skill: plantas humanizadas pelo projeto aprovado (SpotSys / 360)

Versão do procedimento: **22/10/2026 (MVP)**, fechada depois do Lagoa Spot, que foi o primeiro empreendimento a passar de ponta a ponta até o recorte e os pins. Comece pelo **roteiro MVP** (seção 0.1); as seções seguintes detalham cada etapa. O histórico está na seção 11.

Arquivos que compõem a skill (mantenha-os consistentes entre si):

| Arquivo | Para que serve |
|---|---|
| `skill/SKILL.md` (este) | procedimento: cenários, hierarquia, etapas, travas, checklist |
| `skill/modelos/CHECKLIST_PAVIMENTO.md` | ficha que é preenchida e salva em `01_diagnostico/` para **cada pavimento**; é a prova de cada etapa |
| `skill/CASO_BATEL_SPOT.md` | caso de referência do Cenário A, etapa por etapa, com os testes de 16/10 |
| `skill/scripts/do_zero/lagoa/LEIA-ME.md` | **modelo validado do Cenário B** (método híbrido do Lagoa), com a ordem de execução |
| `skill/scripts/recorte/config_recorte_bianca.py` + `skill/exemplos/lagoa-spot_recorte.json` | configs da skill da Bianca e pins do 360 a partir da geometria da planta |
| skill `recortar-plantas` (Bianca), branch `pr-1-recortar-plantas` | recorte por unidade (obrigatória) |
| `skill/scripts/do_zero/LEIA-ME.md` | geradores do zero completo (Cachoeira, Campeche), não validados |
| `skill/UNIFICACAO_PLANTAS_HUMANIZADAS.md` | relação com as skills da Raquel (recorte/texto), do Arthur (Planta Viva) e da Carol |
| `skill/COMPARACAO_SKILL_CAROL.md` | comparação com a `atualizar-humanizada` (Carol), conflitos em aberto e proposta de integração em fases |

---

## 0. Como ler e executar este documento

**Três tipos de instrução.** Cada regra está marcada:
- **[OBRIGATÓRIO]**: não pode ser pulado. Se não for possível cumprir, a etapa para e o motivo é registrado.
- **[RECOMENDADO]**: é o caminho padrão. Desviar é permitido, desde que o motivo fique registrado na ficha do pavimento.
- **[VALIDAÇÃO HUMANA]**: a IA prepara a evidência, mas quem decide é uma pessoa (Rachel, Projetos ou Interiores). A IA não decide sozinha, não presume a resposta e não segue adiante sem ela.

**Travas.** Cada etapa termina com uma **Saída** e uma **Validação**. Se a validação acusar um **erro crítico** (lista na seção 6), a próxima etapa **não começa**. Uma etapa só conta como concluída quando a validação foi feita e registrada na ficha. **O arquivo ter sido gerado não prova nada.**

**Não inventar.** Caminho, revisão, área, tipologia ou layout que não foi lido num arquivo não entra na planta nem na documentação. Quando falta informação, registre a limitação na ficha (`PENDENTE: <o que falta> → <quem decide>`) e peça validação.

**Python neste ambiente (Windows):** use `py` (o comando `python` não está instalado). Todos os comandos abaixo são rodados **a partir da pasta do empreendimento** (ex.: `BATEL-SPOT/`), com os scripts em `../skill/scripts/`.

**Como a Rachel trabalha [OBRIGATÓRIO]:**
- Tarefas mecânicas dentro das pastas do projeto (arquivar versão superada em `04_saida/_DESCARTADO/`, regerar, organizar) são feitas sem perguntar. Publicar no SpotSys, no 360 ou no Drive, apagar originais, commitar e fazer push exigem o OK dela.
- Cada rodada de ajustes termina com as **plantas enviadas** a ela (prévia JPG) e com o LEIA-ME da entrega atualizado. Não responda "está gerando" sem mostrar o resultado quando ele existir.
- Toda regra nova que ela der vai para esta `SKILL.md` no mesmo dia, escrita de forma geral (não presa ao empreendimento), e o repositório `rachelsouto-source/skill-humanizadas-spotsys` é atualizado.
- A planta é para **leigo**: se alguém puder ficar em dúvida ao ler, está reprovada.

### 0.1 Roteiro MVP (próximo empreendimento)

| # | Etapa | O que fazer | Quem decide | Sai |
|---|---|---|---|---|
| 1 | Abrir o caso (0) | pastas + `RETOMAR_AQUI.md` + ficha por pavimento | — | estrutura |
| 2 | Entradas (1) | Autodoc 2.1.c.a (maior revisão) + executivo DWG/IFC/RVT + humanizada de lançamento em alta + interiores + export do SpotSys **com `id`** | **[VALIDAÇÃO HUMANA]** Rachel diz qual é a versão de referência (executivo ou legal) | `00_entradas/` |
| 3 | Áreas (2) | SpotSys × referência × arquivo base, unidade a unidade | Rachel aceita diferenças | CSVs |
| 4 | Diferenças e cenário (3) | registrar a referência no quadro do lançamento; overlay zona a zona; lista de tudo que mudou | **[VALIDAÇÃO HUMANA]** Rachel confirma lista e cenário | zonas que mudaram |
| 5 | Planta do pavimento (4A ou 4B) | A: corrigir só os itens. B: método híbrido do Lagoa (`scripts/do_zero/lagoa/`), regras de representação 1–17 | — | `*_SEM-TEXTO.png` |
| 6 | Nomes (5) | só "UNIDADE NN" dentro de cada unidade (`escreve_unidades.py`) | — | `*_FINAL.png` |
| 7 | QC e rodadas (6–7) | comparar trecho a trecho com o lançamento; mandar prévias; cada rodada superada vai para `_DESCARTADO/` com o defeito no nome | **[VALIDAÇÃO HUMANA]** Rachel aprova as plantas | plantas aprovadas |
| 8 | Recorte (8) | **sempre a skill `recortar-plantas` da Bianca**: config gerado da geometria (`scripts/recorte/config_recorte_bianca.py`), teste com 2–3 unidades | **[VALIDAÇÃO HUMANA]** Rachel aprova o teste, depois todas | `Plantas unidades/<pavimento>/` |
| 9 | Pins e pacote (9) | `pins_360_AGUARDANDO_VALIDACAO.json` dos mesmos contornos + cópia exata da planta do pavimento | — | `04_PUBLICACAO/` |
| 10 | SpotSys e 360 (10–13) | manual, por quem tem acesso; pins nunca testados no 360 | quem administra o 360 | — |

---

## 1. Objetivo e cadeia ponta a ponta

A skill entrega a cadeia que a Tati vai avaliar (Rachel, 15/10/2026). Cada elo precisa encaixar no seguinte:

```
projeto aprovado (Autodoc) ─► planta humanizada do PAVIMENTO ─► validação ─► recorte por UNIDADE
   ─► upload das unidades no SpotSys ─► troca da planta do pavimento ─► pins do 360 ─► 360 validado
```

O processo de **lançamento** é o mesmo, partindo do anteprojeto e criando os pins (em vez de reajustá-los).

**Estado real de cada elo (22/10/2026):**

| Elo | Situação | Prova |
|---|---|---|
| 1. Planta do pavimento, Cenário A | **executável** (Batel térreo) | `CASO_BATEL_SPOT.md` |
| 1. Planta do pavimento, Cenário B | **validado no Lagoa Spot** (térreo e 2º pav., aprovados pela Rachel em 22/10, depois de 8 rodadas). Cachoeira e Campeche (do zero completo) ficaram sem validação | `scripts/do_zero/lagoa/`; `LAGOA-SPOT/04_saida/LAGOA-SPOT_DO-ZERO_SKILL-CAROL_EXECUTIVO-R10_AGUARDANDO-VALIDACAO/LEIA-ME.md` (rodadas) |
| 2. Validação da planta | **feita no Lagoa** (rodadas com prévia + aprovação) | idem |
| 3. Recorte por unidade | **validado no Lagoa com a skill `recortar-plantas` da Bianca** (21 de 21 unidades, C8 OK, teste com 3 unidades aprovado antes). Também usada no Batel | `LAGOA-SPOT/Plantas unidades/`, `LAGOA-SPOT/configs/` |
| 4. Upload das unidades no SpotSys | **manual**, por quem tem acesso de escrita. A skill não escreve no sistema | — |
| 5. Troca da planta do pavimento | **manual**. Antes de trocar, é preciso saber qual imagem do SpotSys corresponde a cada pavimento | — |
| 6. Pins do 360 | **gerados, não testados.** `config_recorte_bianca.py` gera `pins_360_AGUARDANDO_VALIDACAO.json` (polígonos 0–1 por `szi_unit_id`) com os mesmos contornos do recorte, mas o arquivo nunca foi carregado no 360. Que os pins fiquem no lugar é **hipótese** até o teste da etapa 12 | — |
| 7. 360 validado | **não testado** | — |

> Ninguém pode afirmar que os pins funcionam enquanto o teste da etapa 12 não for feito e registrado.

---

## 2. Hierarquia de referências

**Regra geral [OBRIGATÓRIO]:** referência **geométrica** e referência **visual** nunca se misturam. A geometria vem só das fontes da coluna "manda". A humanizada de lançamento nunca define posição, tamanho ou forma de parede, unidade ou acesso.

| Tipo de informação | Manda (prevalece) | Complementa (só se compatível com quem manda) | Nunca usar para isso |
|---|---|---|---|
| Revisão vigente do projeto | PDF assinado do **Autodoc 2.1.c.a**, maior revisão. **Quando há executivo ou legal mais novo que o aprovado, a Rachel diz qual é a referência** (Lagoa: PDF "Legal" rev. 27/11/2024 nas zonas que mudaram + DWG do executivo R10 no resto) | — | cópias do Drive (`*APROVADO*.pdf`, "Arquivos - Investidores") sem conferir a revisão |
| Perímetro e divisas das unidades, paredes externas, núcleo (escada, elevador, shafts), circulações, acessos, vagas, equipamentos técnicos (E.T.) | **PDF aprovado** (vetor) | DWG/IFC/RVT **da mesma revisão** e com as **mesmas áreas** (etapa 2). O executivo serve para nomes, usos e representação (pilares, núcleo), nunca para mover o que o aprovado desenha | humanizada de lançamento, IA, medida "no olho" |
| Numeração e áreas das unidades (privativa, garden, sacada, mezanino) | **PDF aprovado** (A. COMP. etc.) **=** SpotSys | quadro de áreas xlsx | texto escrito na humanizada |
| Áreas que a prancha não escreve (ex.: total do garden no Batel) | **SpotSys** | — | humanizada |
| Layout interno das unidades (cama, sofá, cozinha, banheiro, marcenaria) | **Projeto de interiores**: tabela/mapa de tipologias + planta da tipologia + RVT | 1º gabarito da humanizada de lançamento, lido por unidade em zoom de 2–3x (método da Carol: peça, parede e posição relativa), quando não houver interiores ou quando coincidir com ele; 2º regra Spot (cama na lateral do sanitário, copa na oposta) ou mobiliário mínimo, **só** com nível registrado e validação humana | dedução da tipologia pela forma; layout inventado sem registro |
| Layout das áreas comuns (recepção, rooftop, frente) | **PDF aprovado** (o que está desenhado e escrito) | executivo / projeto de interiores da área comum | — |
| Materiais, texturas, objetos, cor, luz, linguagem gráfica | **Humanizada de lançamento** (`skill/estilo/lancamento` ou recortes da própria imagem) | — | cor chapada, ruído sintético, objetos de banco externo, IA |
| Cotas | valor escrito pelo arquiteto no PDF | — | medida feita na imagem |

**Quando as fontes divergem [OBRIGATÓRIO]:**
1. Registre a divergência na ficha: as duas fontes, os dois valores e a localização (prancha + coordenada, ou unidade).
2. Se a hierarquia acima resolve (ex.: humanizada × aprovado → vale o aprovado), aplique e registre como **"resolvido pela hierarquia"**.
3. Se a divergência envolve duas fontes do mesmo nível (ex.: PDF aprovado × SpotSys; área do interiores × A. COMP.), ou se o aprovado está omisso (ex.: piscina do rooftop do Batel), o item fica **PENDENTE → Projetos/Interiores** e não é desenhado por suposição.
4. Rótulo do PDF evidentemente trocado, com duas outras fontes concordando: correção documentada (`--correcoes`), status **ressalva** e validação da arquitetura.

---

## 3. Qual cenário usar

A escolha é feita **por pavimento**, ao fim da etapa 3, com base na lista de diferenças entre a humanizada de lançamento e o aprovado. **[VALIDAÇÃO HUMANA]** A Rachel confirma o cenário antes da etapa 4.

| Critério (todos lidos na etapa 3) | Cenário A: atualizar a existente | Cenário B: método híbrido (do zero onde mudou) |
|---|---|---|
| Existe humanizada de lançamento do pavimento, em alta resolução | sim | não importa (sem ela, é sempre B) |
| Numeração e número de unidades = aprovado | sim | não, ou não importa |
| Divisas das unidades caem nas paredes (QC da etapa 3) | sim, nas unidades | não, de forma espalhada |
| Área privativa do interiores = A. COMP. do aprovado | sim | não, em várias unidades |
| Diferenças da leitura zona a zona | **poucas e localizadas** (uma entrada, um E.T., um WC, uma vaga, rótulos) | acessos de unidades mudados, banheiros reposicionados, unidades que mudaram de lugar, pavimento reorganizado |
| Régua da seção 9 | nível 1 ou 2 | nível 3 ou 4 |
| Exemplo | **Batel Spot** (térreo: entrada, vaga de embarque, E.T., WC; demais pavimentos sem alteração) | **Lagoa Spot** (modelo validado: Administração/Rouparia/PNE no térreo, unidades 12/13 no 2º pav., área externa); **Cachoeira Spot** e **Campeche Spot** (do zero completo, sem lançamento aproveitável) |

Se um único critério cair na coluna B, use B **naquele pavimento**. Um empreendimento pode ter pavimentos A e B.

**Proibido nos dois cenários [OBRIGATÓRIO]:** remontar, esticar, costurar (seam carving) ou deformar a imagem de lançamento para encaixar no aprovado; usar IA para geometria; colar trechos de outro pavimento sem conferir a escala. No Cachoeira, essas tentativas deixaram acessos errados e banheiros fora de proporção (seção 7, E1/E2).

---

## 4. Passo a passo operacional

Pastas por empreendimento (os originais nunca são sobrescritos):
```
<EMP>/00_entradas/originais/   projeto_aprovado/, arquivo_base_dwg/, humanizada_lancamento_<REV>/{com_texto,sem_texto}/,
                               interiores/, spotsys_publicadas/
<EMP>/00_entradas/spotsys/     export do SpotSys (CSV com id)
<EMP>/01_diagnostico/          DIAGNOSTICO_<EMP>.md, PENDENCIAS_<EMP>.md, CHECKLIST_<PAV>.md, conferências .csv, INVENTARIO_AMBIENTES_<PAV>.md
<EMP>/03_trabalho/             intermediários, scripts específicos do empreendimento (cópia ajustada dos modelos)
<EMP>/04_saida/<EMP>_<SITUAÇÃO>_AGUARDANDO-VALIDACAO/
                               LEIA-ME.md (fontes, método, rodadas, pendências), 00_PREVIAS (JPG), 01_PLANTAS (_FINAL com
                               "UNIDADE NN" e _SEM-TEXTO), 02_CONFERENCIA (lançamento × final, folhas de recorte), 04_PUBLICACAO
                               (planta do pavimento exata + pins_360)
<EMP>/04_saida/_DESCARTADO/    cada rodada superada: <EMP>_v<NN>_<defeito-em-poucas-palavras>_<data>/
<EMP>/configs/                 recorte.json + <pav>.json (skill da Bianca)
<EMP>/Plantas unidades/<pavimento>/   "<Empreendimento> - <NN>.png" (uma subpasta por pavimento: Térreo, 2º Pavimento…)
<EMP>/05_qc/                   registros, sobreposições, alta/ (mosaicos zona a zona)
<EMP>/RETOMAR_AQUI.md          onde parou, próximo passo, comandos (atualizar ao fim de cada sessão)
```

### Etapa 0. Abrir o caso

- **Objetivo:** ter uma ficha por pavimento onde cada etapa deixa a sua prova.
- **Entrada:** nome do empreendimento; lista de pavimentos do SpotSys.
- **Ação:** crie as pastas acima. Copie `skill/modelos/CHECKLIST_PAVIMENTO.md` para `01_diagnostico/CHECKLIST_<PAV>.md` (uma por pavimento ou por grupo de pavimentos tipo). Crie `PENDENCIAS_<EMP>.md` e `RETOMAR_AQUI.md`. Instale a skill da Bianca se ela não aparecer na sessão: `git archive pr-1-recortar-plantas recortar-plantas | tar -x -C ~/.claude/skills/` (rodado na raiz deste repositório).
- **Critérios:** um pavimento tipo pode ter uma ficha só, desde que as variantes do aprovado (ex.: Batel 3º/7º, 4º/6º/8º, 5º) sejam listadas e conferidas uma a uma.
- **Validação:** existe uma ficha para cada imagem de pavimento que vai para o SpotSys.
- **Erros comuns:** esquecer pavimentos com mais de uma imagem publicada (com texto, sem texto, estudo solar). Batel: 6 imagens (854–859) para 4 pavimentos.
- **Saída:** pastas + fichas vazias.

### Etapa 1. Coletar e registrar as entradas

- **Objetivo:** trabalhar sobre as versões certas e saber exatamente de onde veio cada arquivo.
- **Entrada e onde encontrar:**

| Arquivo | Onde | Obrigatório? |
|---|---|---|
| PDF aprovado assinado | Autodoc: `SEAZONE › <Emp> › 02 - Projetos › 2.1 Projeto Arquitetônico › 2.1.c Projeto Legal › 2.1.c.a Projeto Legal Aprovado (versão assinada)`, **maior revisão**. Abrir no Claude in Chrome (sessão logada da usuária). Ex.: Cachoeira `CACHOEIRASPOT-PL-ARQ-DCT-GER-XXX-000-R06.pdf`; Batel `BATELSPOT-PL-ARQ-DCT-GER-ASS-001-R04.pdf` | **[OBRIGATÓRIO]** |
| Arquivo técnico do aprovado (DWG/IFC/RVT) | Autodoc 2.1.c (DWG), time de projetos | se existir |
| Humanizada de lançamento por pavimento, com e sem texto | Drive `08 - Projeto Arquitetônico/04 - Plantas Humanizadas/<versão>` ou Autodoc 2.1.g.a (Batel R01). Preferir a versão sem texto ou em camadas (PSD) da autora | **[OBRIGATÓRIO]** no Cenário A; estilo no B |
| Projeto de interiores | Drive `10 - Projeto de Interiores › 00 - Projeto Seazone`: `01 - Arquivos de projeto` (RVT), `04 - Arquivos para humanizadas` (PDF do anteprojeto, mapa de tipologias, PNG por tipologia), `02 - Imagens` (tabela de tipologias, ex.: `Tipologias - Cachoeira Spot.xlsx`) | **[OBRIGATÓRIO]** no Cenário B; conferência de áreas no A |
| Export do SpotSys | Nekt (consulta abaixo), salvo em `00_entradas/spotsys/spotsys_<emp>_<data>.csv` **com a coluna `id`** | **[OBRIGATÓRIO]** |
| Imagens publicadas no SpotSys | `sup_bd_szi_szi_spot_photos_association` → `sup_bd_szi_szi_spot_images.url` → `00_entradas/originais/spotsys_publicadas/` | **[OBRIGATÓRIO]** para saber o que vai ser substituído |

```sql
SELECT u.code, u.floor, u.typology, u.project_version, u.total_area, u.mezzanine_total_area,
       u.garden_total_area, u.terrace_balcony_total_area, u.is_outdated_area, u.status, u.id
FROM nekt_operacional_bronze.sup_bd_szi_szi_spot_building_units u
JOIN nekt_operacional_bronze.sup_bd_szi_szi_staging_spot_buildings b ON b.id = u.spot_building_id
WHERE b.short_name = '<Nome do Spot>' AND u.is_active = true ORDER BY u.code;
```

- **Ação:** baixe tudo para `00_entradas/originais/` com o nome original. Na tabela "Fontes" do `DIAGNOSTICO_<EMP>.md`, registre arquivo, revisão, data e origem. Abra o PDF e anote quais páginas e trechos (clip em pt) correspondem a cada pavimento. Monte a tabela **imagem publicada → pavimento** (ID da imagem no SpotSys, conteúdo, se tem texto ou estudo solar).
- **Critérios técnicos:** o PDF precisa ser vetorial (texto selecionável). A versão do projeto no SpotSys (`project_version`) precisa corresponder ao aprovado. O DWG do Projeto Legal pode ser só a prancha importada de PDF (camadas `PDF_*`, sem blocos, como no Batel R04); nesse caso ele não acrescenta nada.
- **Validação:** checklist de entrada da ficha totalmente marcado. Cada imagem publicada tem pavimento identificado.
- **Erros comuns:** usar a cópia do Drive (Cachoeira: Drive R00 × Autodoc R06); conector do Drive limitado a cerca de 10 MB (baixar à mão); export do SpotSys salvo sem `id` (os pins dependem dele); imagem publicada sem pavimento identificado.
- **Trava:** sem PDF assinado do Autodoc, sem export do SpotSys ou com versão do SpotSys ≠ aprovado → **para** (erro crítico C1/C2).
- **Saída:** `00_entradas/` completa; tabela de fontes e tabela de imagens publicadas no diagnóstico.

### Etapa 2. Conferir áreas entre as fontes

- **Objetivo:** provar que todas as fontes descrevem o mesmo projeto antes de desenhar qualquer coisa.
- **Entrada:** PDF aprovado, export do SpotSys, interiores, arquivo base (se houver).
- **Ação:**
  1. **SpotSys × aprovado**, unidade a unidade: privativa (total − garden − terraço) × A. COMP. → `01_diagnostico/conferencia_spotsys_x_aprovado_<REV>.csv`. No padrão Cachoeira, `extrai_rotulos_pdf.py` faz isso; em outros padrões de rótulo, faça a leitura do texto do PDF (`fitz get_text`) e registre o método.
  2. **Interiores × aprovado:** A. PRIV. do interiores × A. COMP., unidade a unidade → `conferencia_interiores_x_aprovado_<REV>.csv`.
  3. **Arquivo base × aprovado** (só quando houver DWG/IFC com zonas de área): `py ../skill/scripts/confere_areas_base_x_aprovado.py <pav.dxf> <quadro.json> <transform.json> <rotulos_aprovado.json> <saida.csv>` → veredito BATE / NAO_BATE.
- **Critérios técnicos:** tolerância de 0,02 m² (arredondamento). Total do garden: SpotSys (a prancha escreve só a grama).
- **Validação:** cada CSV tem uma linha por unidade ativa do SpotSys e nenhuma linha DIFERENTE sem explicação registrada.
- **Erros comuns:** comparar área total com privativa; tomar como "aprovado" um DWG do Drive de outra revisão (Cachoeira PB R09/R10 × R06: 314/414 com +1,32 m²).
- **Trava:** NAO_BATE no arquivo base → não usá-lo como base até achar o arquivo da mesma revisão ou corrigir e registrar cada unidade. A Rachel pode aceitar diferenças imperceptíveis **[VALIDAÇÃO HUMANA]**, como aceitou no Cachoeira em 13/10. Diferença SpotSys × aprovado → PENDENTE Projetos.
- **Saída:** CSVs de conferência e resumo no diagnóstico ("99 de 99 iguais").

### Etapa 3. Comparar lançamento × aprovado e escolher o cenário

- **Objetivo:** listar **tudo** o que mudou entre a humanizada de lançamento (ou a publicada) e o aprovado, com evidência, e decidir A ou B.
- **Entrada:** humanizada de lançamento/publicada com texto; PDF aprovado; páginas e clips da etapa 1.
- **Ação:**
  1. **Ajuste global (chamfer):** `py ../skill/scripts/sobrepoe_aprovado.py <aprovado.pdf> <pág> <x0,y0,x1,y1 pt> <humanizada.png> 05_qc/<PAV> [--limiar 70]`. O JSON grava os parâmetros (`parametros`) desde 16/10.
  2. **Abra o `_overlay.jpg` e confirme que o ajuste está certo:** o núcleo (escada e elevadores) e as paredes externas do aprovado caem sobre os do render. **Um número bom com overlay errado é falha do ajuste**, não aprovação (seção 7, E10).
  3. **Sobreposição em alta, zona a zona [OBRIGATÓRIO]:** `py ../skill/scripts/overlay_alta.py 05_qc/<PAV>_registro.json <render_cheio.png> <largura_do_render_usado_no_registro> <clip pt> 05_qc/alta/<PAV> --pdf <aprovado.pdf> [--tiles 3x2]`. Leia cada mosaico e preencha a tabela de diferenças da ficha, item por item: unidades (porta de acesso na circulação), E.T./equipamentos, vazios/shafts, escadas/rampas/plataformas, vagas (embarque e desembarque, bicicleta), lixeira, recepção/WC, piscina, muretas/guarda-corpos, abas de fachada, áreas externas.
  4. Para cada diferença: o que o aprovado desenha, o que a humanizada mostra, a coordenada e um recorte anotado (ex.: `05_qc/TERREO_entrada_anotada.png`).
  5. Classifique pela régua (seção 9) e proponha o cenário (seção 3).
  6. **Revisão nova de um projeto já trabalhado** (ex.: R10 → R11): arquive a saída anterior com o sufixo `-R<rev>` e compare em três camadas (método da Carol): (a) tinta dos dois PDFs, página a página, mostrando o que existe só de um lado; (b) polígonos e áreas por unidade; (c) saída, por hash e fração de pixels alterados. Toda unidade que mudou de área ou de tipo precisa ter explicação no projeto.
  7. Para ler o mobiliário do lançamento (Cenário B ou gabarito), use **zoom de 2–3x por unidade no PNG original**, nunca prévia ou faixa: o travesseiro "Seazone" marca a cabeceira, a manta cinza marca o pé e os criados ladeiam a cabeceira. No Cachoeira, duas leituras em faixa saíram erradas.
- **Critérios técnicos:** anisotropia entre 0,98 e 1,02; mediana ≤ 5 cm; ≥ 85% das divisas a até 15 cm. **Esses números só valem com os parâmetros registrados e o overlay conferido visualmente.** Quando ficarem abaixo do limite, explique a causa no overlay (ex.: Batel ático, 83,7%: cotas e limite do lote dentro da janela).
- **Validação [VALIDAÇÃO HUMANA]:** a Rachel confirma a lista de diferenças e o cenário. No Batel, foi ela quem apontou a entrada ("analise DIREITO") que o chamfer de 86% tinha deixado passar.
- **Erros comuns:** concluir "igual ao aprovado" pelo chamfer (E4); rodar o QC com limiar diferente entre o antes e o depois e comparar números que não são comparáveis (E10); esquecer as variantes do pavimento tipo.
- **Trava:** sem tabela de diferenças preenchida e cenário confirmado, a etapa 4 não começa.
- **Saída:** `05_qc/<PAV>_registro.json` + overlays + mosaicos; tabela de diferenças e cenário na ficha; resumo no diagnóstico.

### Etapa 4A. Cenário A: corrigir a humanizada existente

- **Objetivo:** levar a humanizada ao aprovado alterando **só** os itens da tabela de diferenças e preservando todo o resto, pixel a pixel.
- **Entrada:** humanizada em alta (com texto e, se existir, sem texto ou estudo solar); tabela de diferenças; prancha rasterizada no referencial da imagem (`05_qc/<PAV>_pt2px_<IMG>.json`, gerado pelo `overlay_alta.py`).
- **Ação:**
  1. Para cada item, decida com a Rachel o que entra **[VALIDAÇÃO HUMANA]**. No Batel, por exemplo, a escada original foi mantida no lugar da plataforma elevatória do aprovado, e o WC PCD foi retirado. Decisões que **afastam** a imagem do aprovado ficam registradas como "mantido por decisão de <pessoa>, <data>".
  2. Escreva um script específico em `03_trabalho/scripts/` (modelo: `skill/scripts/redesenha_entrada_terreo.py`) com as coordenadas lidas na prancha rasterizada. Cada superfície nova é montada com **pixels reais da própria imagem**: asfalto por *quilting* de blocos da rua, meio-fio e tinta da faixa recortados da avenida, piso refeito a partir de uma placa limpa alinhada à paginação, paredes copiadas de trechos existentes.
  3. Grave um `_log.json` por imagem, com os itens alterados e as coordenadas.
  4. Aplique o mesmo script em todas as versões da imagem (com texto, estudo solar), com o deslocamento de cada uma (`--dx/--dy`; Batel TER-000: dx=−2, dy=997).
  5. Guarde o "antes" (`03_trabalho/entrada/antes_<IMG>.png`).
- **Critérios técnicos:** sem cor chapada, sem ruído sintético, sem linhas desenhadas, sem IA. Luz e sombra contínuas. Escala real: a placa do piso tem o mesmo tamanho em px.
- **Validação:** refaça a etapa 3 sobre o resultado, **com o mesmo registro e os mesmos parâmetros** do antes. Cada item corrigido coincide com a prancha no mosaico. Fora das zonas editadas, a imagem é idêntica ao antes (diferença de pixels = 0 fora das caixas do log).
- **Erros comuns:** primeira versão com textura "desenhada", rejeitada pela Rachel no Batel ("quero as texturas realistas!!"); esquecer de aplicar a correção na versão com estudo solar; refazer elementos que estavam certos.
- **Saída:** `04_saida/<EMP>_CONFORME-APROVADO-<REV>/01_PLANTAS/<EMP>_<PAV>_HUM-COM-TEXTO_APROVADO-<REV>.png` (+ variantes) e `_entrada_log.json`.

### Etapa 4B. Cenário B: método híbrido (padrão) ou do zero completo

- **Objetivo:** desenhar o pavimento na geometria da versão de referência, com o layout de interiores e o acabamento do lançamento, sem nenhuma parede, porta ou linha que confunda um leigo.
- **Entrada:** versão de referência (PDF legal/aprovado e DWG/IFC/RVT do executivo, se tiver passado na etapa 2); humanizada de lançamento em alta; tabela de tipologias e plantas de tipologia do interiores.
- **Método híbrido [RECOMENDADO], sempre que existir humanizada de lançamento em alta** (modelo validado: `skill/scripts/do_zero/lagoa/`, com a ordem de execução no `LEIA-ME.md` da pasta):
  1. Rasterize o executivo e registre-o no quadro do lançamento; confira o overlay zona a zona.
  2. Marque as zonas em que o projeto mudou (diferença executivo/legal × lançamento + leitura humana). Todo o resto usa o desenho do lançamento **tal qual**, só sem as caixas de rótulo.
  3. Redesenhe só as zonas que mudaram, com as regras 1 a 17 abaixo; a emenda passa no núcleo preto de uma parede comum às duas fontes (regra 14).
  4. Área externa: use a do lançamento quando ela bater com a referência (regra 17); redesenhe só o que mudou (acesso, plataforma, lixo).
  5. Rode por pavimento, em paralelo e em segundo plano (8 a 10 minutos cada no Lagoa); grave sempre no rascunho e só copie para a entrega depois de conferir.
- **Do zero completo (Cachoeira, Campeche)** só quando não há lançamento aproveitável ou quando o pavimento foi reorganizado (régua nível 4). Geradores: `skill/scripts/do_zero/cachoeira/` e `campeche/`. Nenhum dos dois foi validado pela Rachel.
- **Nos dois casos, nesta ordem:**
  1. **Fluxos de circulação:** leia na prancha por onde se chega a cada unidade, loja, escada, elevador e WC. Registre na ficha.
  2. **Inventário de ambientes [OBRIGATÓRIO]:** `01_diagnostico/INVENTARIO_AMBIENTES_<PAV>.md`. Cada área do aprovado (e do executivo, só para nome e uso) entra com o que ela é, como será representada e de onde vem a textura: passeio, rua, concregrama, canteiro, deck, gramado, laje técnica, escada, bicicletário.
  3. **Tipologia por unidade [OBRIGATÓRIO]:** procure primeiro a tabela de tipologias (Cachoeira: abas "VERSÃO LANÇAMENTOS" e "VERSÃO PROJETO LEGAL") → `01_diagnostico/tipologias_unidades_<emp>.csv`. **Não deduza a tipologia pela forma** (no Cachoeira, a dedução trocou B/C e errou F). **Se não existir tabela** (Campeche), registre o que existe, ex.: "Unidades mezanino 38 m²", e leve o mapeamento à validação **[VALIDAÇÃO HUMANA]**. Se não houver nenhum layout de interiores para uma unidade, **não invente**: a unidade fica PENDENTE Interiores.
  4. **Geometria:** paredes, divisas, núcleo, portas de acesso e equipamentos a partir do vetor do PDF ou do DWG (`scripts/do_zero/<emp>/`, `gera_humanizada_dwg.py`). O que o DWG não desenha (bicicletas BR/BV/BC, elevadores, lixeira, piscina) é posicionado pelas etiquetas do PDF assinado.
  5. **Layout:** encaixe a planta da tipologia na divisa aprovada (espelhar ou girar quando preciso), **sempre na escala real**: móveis e louças mantêm a medida; quem se ajusta é a circulação interna. Se não couber (área ou porta diferente), a unidade fica PENDENTE Interiores.
  6. **Estilo:** pisos, paredes, louças e móveis com as texturas e os objetos reais do lançamento (`skill/estilo/lancamento`), na escala da planta. Não leve linhas da prancha para a imagem (cotas, carros, contornos de vaga); só entram degraus e elementos físicos.
  7. **Auditoria antes do render final [OBRIGATÓRIO]** (critérios da `auditar.py` da Carol, aplicados sobre a nossa segmentação ou máscara de ambientes). Liste os achados na ficha e explique cada um. **Achado sem explicação = não renderiza.**
     - unidades irmãs (mesmo tipo e rótulo no pavimento) com área 30% acima ou abaixo da mediana;
     - "bolsas brancas" ≥ 0,5 m² sem ambiente, encostadas no prédio (porta, área técnica, jardineira);
     - unidade sem sanitário, ou sem jardineira/terraço quando ≥ 60% das irmãs têm;
     - sanitário sem louça; jardineira cortada pela metade;
     - **nível de fidelidade do mobiliário por unidade:** `interiores` / `lancamento` / `adaptado` / `regra` / `minimo` / `sem cama`. Os níveis `regra`, `minimo` e `sem cama` vão para **[VALIDAÇÃO HUMANA]**, com o que faltou.
- **REGRAS DE REPRESENTAÇÃO [OBRIGATÓRIAS] (Rachel, Lagoa Spot 20–22/10/2026, todo empreendimento):** a humanizada é planta de venda para leigo, não desenho técnico. Modelo: `skill/scripts/do_zero/lagoa/render_hibrido.py`.
  1. **Versão de referência:** é a última versão do projeto, que varia por caso: executivo mais recente ou legal aprovado. Rachel indica qual. O lançamento é a referência de **representação e layout**, não de geometria.
  2. **Onde a geometria da versão de referência = lançamento** (confira por overlay, zona a zona), use a **representação do lançamento tal qual**, só sem os rótulos. Isso vale para paredes, portas, soleiras, louças, box e chuveiro. Redesenhar o que já está certo gerou paredes desalinhadas, linhas na frente das paredes e portas sobrepostas.
  3. **Redesenhe só as zonas que mudaram** (`ZONAS_LEGAL`/`ZDES`). Dentro delas use os mesmos símbolos e texturas do lançamento, com o layout de interiores do lançamento readaptado.
  4. **Paredes:** pretas, retas, no perfil do lançamento (contorno preto ~3 px, faixa branca ~7 px, núcleo preto). Nada de cunha ou "V" de hachura e shaft do CAD. Diagonal com face reta. Nenhuma parede para fora da janela: na fachada, a janela já é a parede.
  5. **Portas:** largura do executivo (nome do bloco, ex.: 80×210; unidades 80 e WC 60). O lado de abrir é o do lançamento, sempre para dentro da unidade ou do WC. A representação é a do lançamento: folha azul-acinzentada com contorno preto, puxador em "U" e arco fino. Uma porta por vão, nunca duas.
  6. **Soleira de granito:** só no vão da porta, rente à folha. A parede vai até a soleira, e a soleira não passa do perímetro da porta. Textura recortada do granito do próprio lançamento.
  7. **Bancadas e móveis:** sempre encostados na parede preta, no fundo e na lateral. Nunca atravessam parede, folha, giro da porta ou soleira. Cuba e vaso nunca dentro da parede nem no giro.
  8. **WC:** box = uma linha reta de vidro de parede a parede. O símbolo do chuveiro do lançamento fica **na mesma parede do vaso**, do outro lado do vidro, em todo box. Sem ralo solto.
  9. **Escadas:** degraus reais e iguais, sem eixo nem seta. A escada de acesso tem piso claro com degraus e corrimão.
  10. **Elevador:** porta do lançamento, com a moldura escalonada e a soleira de granito na metade do vão, como está desenhada lá. Não redesenhe o elevador quando a geometria não mudou: tire-o da zona redesenhada.
  11. **Área externa:** grama do lançamento só onde a versão de referência tem jardim. Onde tem vaga, entra o piso (sem demarcação). Muro e gradil no padrão do lançamento, sem linha solta.
  12. **Conferência:** antes de entregar, compare cada trecho em zoom com o lançamento (porta, soleira, bancada, box, parede, fachada, acesso). Se um leigo puder ficar em dúvida, está reprovado.
  13. **(Lagoa, 22/10) Paredes nas zonas redesenhadas:** nunca some a parede da versão nova (Legal) à do executivo ou do lançamento. O Legal vem 1 a 3 cm deslocado e mais grosso, e a soma deixa parede dupla. Desenhe retângulos retos com a espessura e o alinhamento do executivo (= lançamento), e use o Legal só para saber o que mudou. Parede fina nunca fica só com o contorno, com o miolo no tom do piso: núcleo preto sempre.
  14. **(Lagoa, 22/10) Emenda entre o redesenho e o lançamento:** a borda da zona redesenhada passa no **núcleo preto** de uma parede que as duas fontes têm no mesmo lugar, nunca no piso, nem na face nem dentro de uma soleira (a soleira do vão fica inteira de um lado só). Elementos que não mudaram dentro da zona (elevador e porta dele, WC igual) saem da zona e ficam com o lançamento.
  15. **(Lagoa, 22/10) Janelas sob as caixas de rótulo:** ao tirar a caixa de rótulo que encosta na fachada, refaça peitoril, vidro e sombra com a faixa limpa vizinha da mesma fachada (todas as colunas com o mesmo perfil vertical: sem pilar nem degrau), repetida espelhada. Onde a fachada é escalonada, cada lado da caixa preenche a sua metade. O que sobra da caixa fora da fachada volta a ser fundo (transparente ou o piso em volta). Cópia vertical (de cima) troca o peitoril por asfalto, e cópia larga traz pilar de outro trecho.
  16. **(Lagoa, 22/10) Shaft no meio da parede:** o shaft que o lançamento deixou com piso claro dentro da parede do corredor é fechado em preto, no perfil da parede ao lado.
  17. **(Lagoa, 22/10) Área externa legível para leigo:** se o lançamento já mostra a área externa como a versão de referência (lixo, garden com mureta + gradil de divisa, jardim, escada de acesso, plataforma), use o lançamento tal qual, sem rótulos, e ponha grama ou asfalto onde havia caixa ou texto de rótulo. Redesenhar pelas camadas do CAD deixa linhas sobrando. O garden de cada unidade tem de aparecer fechado pelo muro de divisa.
- **Critérios técnicos:** proporção real (banheiros e WCs de loja não podem ser espremidos); orientação igual à do lançamento quando a Rachel pedir (Campeche: legal girado −45°).
- **Validação:** etapa 3 sobre a planta nova (divisas nas paredes, leitura zona a zona). Por unidade: a porta de acesso está na circulação do aprovado e a tipologia é a da tabela.
- **Erros comuns:** acesso de unidade copiado do lançamento (Cachoeira 110/111); interiores aplicado sem conferir a área; frente "confusa" ou com aparência de desenho técnico (Campeche); no Lagoa, as rodadas 1 a 8 corrigiram, nesta ordem: portas de tamanhos desiguais, ponta da circulação torta, paredes desalinhadas e sobrepostas, janelas cortadas sob as caixas de rótulo, parede de WC no tom do piso, shaft claro, garden sem muro de divisa, porta do elevador diferente do lançamento. Confira esses pontos antes de mandar a primeira prévia.
- **Saída:** `01_PLANTAS/<EMP>_<PAV>_DO-ZERO_SEM-TEXTO.png` + inventário + CSV de tipologias + overlay + máscara de ambientes (`<P>_hib_amb.npz/json`, usada no recorte).

### Etapa 5. Textos e rótulos

- **Objetivo:** produzir as versões de texto que o SpotSys e o 360 usam, sem mexer na geometria.
- **REGRA [OBRIGATÓRIA] (Rachel, 19/10/2026, todo empreendimento):** a planta **não leva as caixas de rótulo do lançamento** ("Aloj 02 / 20,23 m² / 03 Hóspedes") nem áreas de garden. O único texto de unidade é **"UNIDADE NN"** (código do SpotSys), **dentro do ambiente** da respectiva unidade, com fonte, tamanho e cor iguais em todas, no maior trecho de piso livre perto do centro (modelo: `skill/scripts/do_zero/lagoa/tira_rotulos.py` + `escreve_unidades.py`). Paredes só as do executivo/aprovado: nada de traço de parede do lançamento sobrando ao lado (Rachel: "paredes sobrepostas... confusa").
- **Entrada:** planta da etapa 4; valores corretos (etapa 2).
- **Ação (conforme o pedido):**
  - **Corrigir valores de área escritos:** `py ../skill/scripts/corrige_rotulos_area.py <img.png> <rotulos.json> <saida.png> [--debug pasta]`. Troca só o número, com glifos recortados da própria imagem.
  - **Sem texto:** `remove_texto.py` (genérico, texto preto) ou um script do empreendimento com clonagem por trecho real vizinho (modelo: `remove_rotulos_terreo.py`, que usa caixas por OCR do Windows + posições fixas). A rosa dos ventos fica.
  - **Só numeração:** a mesma remoção com `--manter-und` (no modelo do Batel).
- **Critérios técnicos:** os textos que ficam batem com o SpotSys; nenhuma "sombra" de letra; texturas contínuas (tábuas, juntas).
- **Validação:** releia cada rótulo restante contra a conferência da etapa 2; inspecione cada rótulo removido no debug, em zoom de 100%.
- **Erros comuns:** contorno de letra sobre deck e grama ao mesmo tempo (Batel garden 113, corrigido com `limpa_garden113.py`); usar o "sem texto" do lançamento em outra resolução ou enquadramento (Batel: 2500 px, inutilizável).
- **Saída:** `..._HUM-SEM-TEXTO_...png`, `..._HUM-NUMERACAO-UND_...png`, `_rotulos_log.json`.

### Etapa 6. QC do pavimento e comparativo

- **Objetivo:** aplicar o checklist de qualidade (seção 5) e montar a evidência para quem valida.
- **Entrada:** saídas das etapas 4 e 5; registro da etapa 3.
- **Ação:** preencha a seção 5 da ficha, item a item. Monte o comparativo **lançada | aprovado | nova**: `py ../skill/scripts/monta_comparativo.py 03_trabalho/comparativo.json 04_saida/<...>/02_COMPARATIVO`, com as notas de cada pavimento (o que mudou, o que foi mantido por decisão, o que está pendente).
- **Validação:** nenhum item da seção 5 em "reprovado"; cada pendência listada em `PENDENCIAS_<EMP>.md` com responsável.
- **Saída:** ficha com o QC preenchido + comparativo PDF/JPG.

### Etapa 7. Validação humana do pavimento (TRAVA)

- **Objetivo:** ninguém recorta nem publica uma planta que não foi aprovada por uma pessoa.
- **Ação [VALIDAÇÃO HUMANA]:** envie a ficha + o comparativo à Rachel, ou a quem ela indicar. Registre na ficha: validado S/N, validador, data e observações. Para o pacote automático, registre também em `VALIDACAO_PLANTAS.csv` (pavimento, validado, validador, data, observação).
- **Rodadas de ajuste (como foi no Lagoa):** cada pedido da Rachel vira uma rodada. Antes de substituir a entrega, a versão anterior vai para `04_saida/_DESCARTADO/<EMP>_v<NN>_<defeito>_<data>/`. Regere no rascunho, confira o trecho apontado e o pavimento inteiro contra o lançamento, copie para a entrega e mande as prévias. O LEIA-ME da entrega ganha uma seção "Ajustes de <data> (<N>ª rodada)" com o que mudou, em linguagem simples. Quando ela marcar o defeito num print, corrija a causa (regra) e não só o ponto, e registre a regra nesta `SKILL.md`.
- **Trava:** sem validação registrada, **não existe etapa 8**. Reprovação → volta para a etapa 4 com as observações.
- **Saída:** ficha assinada.

### Etapa 8. Recorte por unidade (skill da Bianca)

- **Objetivo:** uma imagem por unidade, na resolução original da planta aprovada, com a unidade, o WC dela e o garden/terraço/sacada dela.
- **REGRA (Rachel, 22/10/2026) [OBRIGATÓRIO]:** o recorte das humanizadas é feito **sempre, em qualquer caso, pela skill `recortar-plantas` da Bianca Valente**. Não escreva recortador próprio (no Lagoa, um script próprio foi descartado por isso). Se a skill não estiver disponível na sessão, instale-a (abaixo) ou **pare e peça** o caminho.
- **Onde está:** pasta `recortar-plantas/` na branch `pr-1-recortar-plantas` deste repositório (commit 6ed51b0). Instalação, na raiz do repositório: `git archive pr-1-recortar-plantas recortar-plantas | tar -x -C ~/.claude/skills/`. Siga o `SKILL.md` dela.
- **Entrada:** planta do pavimento **aprovada** (etapa 7) com "UNIDADE NN"; máscara de ambientes que desenhou a planta (`<P>_hib_amb.npz/json`, etapa 4B); export do SpotSys com `id`.
- **Ação:**
  1. Escreva `<EMP>/configs/recorte.json` (modelo: `skill/exemplos/lagoa-spot_recorte.json`): nome do empreendimento, metros por pixel, export do SpotSys, padrão do nome do ambiente da unidade (`regex_unidade`, ex.: `ALOJ ([0-9]+)`) e do WC, e, por pavimento, a planta, a máscara de ambientes, o andar do SpotSys e a subpasta de saída.
  2. Gere os configs da skill e os pins com a mesma geometria: `py ../skill/scripts/recorte/config_recorte_bianca.py configs/recorte.json`. O terminal mostra a contagem por pavimento × SpotSys (**C8**) e cada WC atribuído por contato (sem vão direto), para conferir.
  3. Confira os contornos com a skill: `py ~/.claude/skills/recortar-plantas/scripts/grade.py <planta> --config configs/<pav>.json --saida <rascunho>/c.png` (Read).
  4. **Teste com 2 ou 3 unidades** (uma comum, uma com garden, uma da zona redesenhada), gravando no rascunho, e mande para a Rachel. **[VALIDAÇÃO HUMANA]** Só gere todas depois da aprovação.
  5. Gere todas: `py ~/.claude/skills/recortar-plantas/scripts/recortar.py configs/<pav>.json --folha <rascunho>/folha_<pav>.png`, um pavimento por vez. Copie as folhas para `02_CONFERENCIA/<PAV>_folha_recortes_skill-bianca.png`.
  6. Revise as folhas (Read): porta de entrada inteira, nada do vizinho, garden certo, número visível. Corrija o config e rode só a unidade com problema (`recortar.py cfg.json 12`).
- **Regras de contorno (Lagoa, 22/10) [OBRIGATÓRIO]:**
  - entre duas unidades, o contorno passa no **meio** da parede;
  - no corredor e na fachada, vai até a **face externa** da parede, com a **parede e a soleira da porta de entrada inteiras** (cortar a soleira ao meio deixou a porta "desconfigurada");
  - o vão da porta e o dono do WC são achados por **geometria**, nunca por cor (granito, asfalto e porcelanato se confundem; a detecção por cor chegou a gerar recortes do pavimento quase inteiro). O WC é da unidade cujo piso encosta direto no dele, o que só acontece pelo vão da porta;
  - fora do prédio (asfalto, gramado comum) nada entra; o garden entra só nas unidades que têm garden no SpotSys, limitado pelo gradil.
- **Padrão de entrega (Rachel):** `<EMP>/Plantas unidades/<pavimento>/<Empreendimento> - <NN>.png`, **uma subpasta por pavimento** (Térreo, 2º Pavimento…), o que difere do padrão da skill (pasta única) por pedido da Rachel em 22/10. Fundo branco, sem girar, sem texto de área, com o "UNIDADE NN".
- **Qualidade [OBRIGATÓRIO]:** resolução original da planta. Nunca redimensione, amplie, gire ou passe filtro.
- **OCR:** `verif.py` e `tem_numero.py` da skill exigem o Tesseract (`C:\Program Files\Tesseract-OCR`), e o `tem_numero.py` espera códigos de três dígitos. Sem eles, confira a numeração nas folhas e registre no LEIA-ME.
- **Pavimento tipo e andar real:** quando o SpotSys/360 usar uma planta por andar, gere **um arquivo por andar real** com o número exato de cada unidade (ex.: 301…312, …, 801…812), a partir da mesma planta validada do tipo (a skill da Bianca faz isso com ids "101 - 701"). **[VALIDAÇÃO HUMANA]** Confirme com quem administra o 360 qual das duas os pins usam.
- **Validação:** C1, C7 e **C8 (número de recortes = unidades ativas do SpotSys, por pavimento)**; folhas revisadas; teste aprovado pela Rachel. Confira os PNG grandes no disco, não as prévias.
- **Erros comuns:** porta de entrada cortada no meio da soleira (Lagoa 12); faixa de asfalto acima da fachada no recorte (Lagoa 02); WC atribuído à unidade errada por contato (Lagoa 10/11); emenda da planta aparecendo dentro do recorte (corrigir a planta, etapa 4B regra 14, e não o recorte).
- **Saída:** `Plantas unidades/<pavimento>/` + `configs/` + folhas em `02_CONFERENCIA/`.
- **Métodos anteriores (só referência):** extrator de rótulos do Cachoeira (`extrai_rotulos_pdf.py` → `celulas_pdf.py` → `registra_pdf_imagem.py` → `gera_recortes.py`), segmentação da Carol + `poligonos_carol.py` (Batel, teste de 16/10) e `gera_cfg_recorte.py` + recorte da Raquel. Podem servir para gerar os **polígonos** de um config quando não houver máscara de ambientes (Cenário A), mas o recorte é sempre o `recortar.py` da Bianca.

### Etapa 9. Pins do 360 e pacote de publicação

- **Objetivo:** deixar pronto, sem publicar, o que a pessoa com acesso vai subir.
- **Ação:**
  1. O `config_recorte_bianca.py` (etapa 8) já grava `04_PUBLICACAO/pins_360_AGUARDANDO_VALIDACAO.json`: um pin poligonal por unidade, com `szi_unit_id`, `codigo`, `andar`, `planta`, tamanho da imagem, vértices de 0 a 1 e centroide, com os **mesmos contornos** dos recortes.
  2. Copie para `04_PUBLICACAO/` a planta do pavimento **exata** que serviu de base (mesmo arquivo, mesma resolução, com "UNIDADE NN") e confira por hash que é igual à de `01_PLANTAS/`. Se a planta mudar depois, regere configs e pins.
  3. Pacote com validação por unidade (opcional, quando pedirem): `gera_pacote_publicacao.py` sai como `AGUARDANDO_VALIDACAO` com `VALIDACAO_HUMANA.csv`; **[VALIDAÇÃO HUMANA]** uma pessoa preenche; rodando de novo com `--validacao`, saem `pins_360.json` e `manifesto_publicacao.csv` só com as validadas.
- **Validação:** `szi_unit_id` preenchido em todos os pins (o script avisa e sai com erro se faltar); número de pins = número de recortes; planta de `04_PUBLICACAO/` com o mesmo hash da entrega.
- **Saída:** `04_PUBLICACAO/` com planta(s) do pavimento + `pins_360_AGUARDANDO_VALIDACAO.json`. **Nada é publicado.**

### Etapa 10. Upload das unidades no SpotSys (manual)

- **Objetivo:** substituir a imagem de cada unidade pela nova.
- **Quem:** pessoa com acesso de escrita. A skill **não escreve** no SpotSys.
- **Ação:** antes de qualquer troca, salve a URL da imagem atual de cada unidade (para poder reverter). Suba cada imagem do manifesto na unidade com o mesmo `szi_unit_id` e registre a data e o autor no manifesto.
- **Validação:** consulta `spot_photos_association` → a URL nova está na unidade certa (amostra de 100% das unidades no primeiro empreendimento).
- **Não testado** com a skill até 16/10.

### Etapa 11. Substituir a planta do pavimento (manual)

- **Objetivo:** trocar a imagem do pavimento pela planta validada da etapa 7.
- **Ação:** use a tabela imagem publicada → pavimento (etapa 1). Guarde a imagem antiga e a URL. Suba a nova **com o mesmo enquadramento** que foi usado para gerar os pins.
- **Critério:** a imagem que sobe é exatamente a que serviu de base ao `pins_360.json` (mesmo arquivo, mesma resolução). Se a imagem for diferente, os pins ficam errados.
- **Não testado** até 16/10.

### Etapa 12. Pins do 360 (NÃO TESTADO; precisa de validação técnica)

- **Objetivo:** cada unidade com o pin poligonal no lugar certo da nova planta, sem quebrar o 360.
- **Situação:** `pins_360.json` segue o formato `seazone360_floor_plan_pins` (`szi_unit_id`, `pin_type: polygon`, `polygon_vertices` 0–1, centroide). **Nunca foi carregado.** Não se sabe ainda (a) se o 360 aceita a carga por arquivo ou se ela é feita na tela, (b) se os pins existentes são substituídos ou duplicados, (c) se a coordenada 0–1 é relativa à imagem inteira (com margens) ou ao recorte.
- **Teste a fazer, com quem administra o 360 [VALIDAÇÃO HUMANA]:** (1) em ambiente de teste, ou em um pavimento escolhido, exporte os pins atuais; (2) carregue o `pins_360.json` de um pavimento só; (3) abra o 360 e confira unidade por unidade se o polígono cobre a unidade certa e se o clique leva à unidade certa; (4) registre o resultado e o procedimento aqui. Só depois disso a palavra "automático" pode ser usada.

### Etapa 13. Validação final do 360

- **Ação [VALIDAÇÃO HUMANA]:** percorra todas as unidades do pavimento no 360: imagem da unidade, área exibida, pin no lugar certo, navegação. Registre na ficha. Se algo falhar, reverta com as URLs guardadas nas etapas 10 e 11.

---

## 5. Checklist de qualidade (antes de considerar uma planta pronta)

Cada item é preenchido na ficha como **OK**, **REPROVADO** (volta para a etapa indicada) ou **PENDENTE** (depende de terceiro; vai para `PENDENCIAS_<EMP>.md`). Itens críticos (★) reprovados bloqueiam a etapa 7.

| # | Item | Como verificar | Aprova quando | Reprovado volta para |
|---|---|---|---|---|
| Q1 ★ | Geometria = aprovado | registro da etapa 3 refeito sobre a planta nova, com os mesmos parâmetros; overlay global olhado | anisotropia 0,98–1,02; mediana ≤ 5 cm; ≥ 85% ≤ 15 cm (ou causa explicada no overlay); núcleo e paredes externas coincidindo | 4 |
| Q2 ★ | Paredes, portas, escadas, acessos | mosaicos `overlay_alta`, zona a zona | cada porta de unidade abre na circulação do aprovado; escada/rampa/plataforma como o aprovado ou mantidas por decisão registrada | 4 |
| Q3 ★ | Vagas e ambientes | tabela de diferenças da etapa 3, item a item | todos os itens do aprovado presentes (vaga de embarque e desembarque, bicicletas, E.T., lixeira, recepção) ou PENDENTE com responsável | 4 |
| Q4 | Mobiliário: proporção e posição | medir no render um objeto de referência (cama 2,00 × 1,60 m, vaso, placa do piso) com a escala do registro; conferir a tipologia | erro ≤ 5% na medida; tipologia = tabela; nada atravessando parede ou bloqueando porta | 4 |
| Q5 | Texturas e materiais | inspeção a 100% nas zonas editadas | só texturas reais do lançamento; sem cor chapada, ruído, emendas, "fantasmas"; luz contínua | 4A/4B ou 5 |
| Q6 ★ | Nada indevido | comparar com o pedido: rótulos, áreas, cotas, carros, contornos, linhas da prancha | só os textos pedidos para aquela versão; sem linha de desenho técnico | 5 |
| Q7 | Textos corretos | cada rótulo restante × conferência da etapa 2 | 100% iguais ao SpotSys/aprovado | 5 |
| Q8 | Legibilidade e qualidade gráfica | ver a imagem inteira na resolução de exibição do SpotSys e a 100% | sem serrilhado, borrões ou desalinhamento; mesma resolução e enquadramento da imagem substituída | 4/5 |
| Q9 ★ | Comparativo original × aprovado × resultado | `monta_comparativo.py`, uma página por pavimento | cada diferença da etapa 3 aparece resolvida, mantida por decisão ou pendente | 6 |
| Q10 ★ | Divergências registradas | `PENDENCIAS_<EMP>.md` | toda divergência aberta tem responsável e situação | 6 |
| Q11 ★ | Auditoria pré-render (Cenário B; no A, só nas zonas editadas) | etapa 4B.7 | nenhum achado sem explicação; nenhuma bolsa branca; todo sanitário com louça; jardineiras inteiras | 4B |
| Q12 | Fidelidade do mobiliário | nível por unidade (4B.7) | `interiores`/`lancamento`/`adaptado` aprovam; `regra`/`minimo`/`sem cama` só com validação registrada | 4B |

Critérios do recorte por unidade (etapas 8–9), calculados por `relatorio_qc.py`:

| Critério | Medida | Aceite |
|---|---|---|
| C1 Identificação | código existe no SpotSys, tem polígono e está no nome | obrigatório |
| C2 Área | rótulos do PDF × SpotSys | igual (0,01 m²) ou conferido à mão e registrado |
| C3 Sem texto | detector reaplicado | 0 linhas residuais |
| C4 Sem distorção | anisotropia | 0,98–1,02 |
| C5 Aderência | mediana divisa → parede | ≤ 15 cm |
| C6 Recorte = planta | pixels opacos idênticos | diferença 0 |
| C7 Resolução | maior lado | ≥ 400 px |
| C8 Contagem | recortes por pavimento × unidades ativas do SpotSys | iguais (lição da Carol: uma regressão gravou 30 de 66) |

Status: **APROVADO** (tudo ok) · **APROVADO_COM_RESSALVA** (C4/C5 fora, área conferida à mão, observação cosmética) · **PENDENTE** (C1, C3 ou C6; divergência de área; observação bloqueante; arquivo ausente).

---

## 6. Erros críticos (bloqueiam a etapa seguinte)

| Código | Erro | Detectado na etapa |
|---|---|---|
| X1 | PDF não é o assinado do Autodoc, na maior revisão | 1 |
| X2 | Versão do SpotSys ≠ aprovado, ou export sem `id` | 1 |
| X3 | Área DIFERENTE entre SpotSys, aprovado e arquivo base sem decisão registrada | 2 |
| X4 | Overlay global errado (núcleo e paredes externas fora), mesmo com bons números | 3, 6 |
| X5 | Tabela de diferenças não preenchida ou cenário não confirmado | 3 |
| X6 | Tipologia deduzida pela forma, ou layout inventado sem fonte | 4B |
| X7 | Item do aprovado ausente sem decisão ou pendência registrada | 6 |
| X8 | Planta sem validação humana registrada | 7 |
| X9 | Extrator de rótulos com contagem `OK` ≈ 0 | 8 |
| X10 | Imagem do pavimento que sobe ≠ imagem base dos pins | 9, 11 |
| X11 | Recorte que não saiu do `recortar.py` da skill da Bianca, ou redimensionado | 8 |
| X12 | Recortes de todas as unidades gerados sem o teste de 2–3 unidades aprovado | 8 |

---

## 7. Erros já encontrados e correções

| # | Caso | Erro | Correção adotada (regra) |
|---|---|---|---|
| E1 | Cachoeira, 12–13/10 | Colagem do lançamento e preenchimento por IA (nano-banana) deformaram mezanino, térreo e rooftop | sem colagem e sem IA na geometria (seção 3) |
| E2 | Cachoeira, 15/10 | Remontagem do lançamento sobre o R06: acessos 110/111 errados, banheiros espremidos | Cenário B: do zero sobre o aprovado, com o layout do interiores |
| E3 | Cachoeira | Aprovado tirado do Drive (R00), enquanto o Autodoc tinha R06 | Autodoc 2.1.c.a, maior revisão (etapa 1) |
| E4 | Batel, 15/10 | Térreo dado como compatível pelo chamfer (86%), mas a entrada tinha plataforma, vaga e E.T. diferentes | leitura zona a zona obrigatória (etapa 3) |
| E5 | Cachoeira | Tipologias deduzidas pela forma (B/C trocadas, F errada) | tabela de tipologias obrigatória (4B) |
| E6 | Cachoeira | DWG PB do Drive com áreas diferentes do R06 | conferência de áreas do arquivo base (etapa 2) |
| E7 | Batel, 15/10 | Asfalto, meio-fio e tracejado com aparência de desenho | só pixels reais da própria imagem (4A) |
| E8 | Campeche, 16/10 | Frente confusa, carro na vaga, linhas da prancha na imagem | inventário de ambientes; sem linhas de prancha (4B) |
| E9 | Batel | Rótulo cruzando deck e grama deixou contorno | refazer o trecho com retângulos reais (`limpa_garden113.py`) |
| E10 | Batel, teste 16/10 | **QC não reproduzível:** o mesmo comando sobre a 856 deu 64% (registrado: 85,6%). Com limiar 70, imagens quase idênticas deram anisotropia 0,95 ou 1,04 (ajuste preso em mínimo local). Com limiar 110, deu 1,7 cm / 82% com o **overlay visivelmente errado** (prancha ~26% maior) | o registro grava `parametros`; o antes e o depois são medidos com os mesmos parâmetros; o overlay global é olhado sempre (X4); para conferir uma edição, reaproveitar o registro já validado |
| E11 | Batel, teste 16/10 | `overlay_alta.py` usava o PDF do Batel como padrão silencioso | `--pdf` agora é obrigatório |
| E12 | Batel, teste 16/10 | `extrai_rotulos_pdf.py` e `celulas_pdf.py` leram 0 de 99 unidades (padrão `UNIDADE 01 / A. COMP.`) | conferir a contagem antes do recorte (etapa 8, X9); no Batel, a segmentação da Carol leu 99/99 (fase 1), e `poligonos_carol.py` gerou 99 recortes e pins (fase 2, com defeitos abertos) |
| E17 | Batel, teste fase 1 | A segmentação da Carol leu o poché das paredes (preenchimento preto do prédio inteiro, recortado por clip path) como parede cheia: nenhuma região no 2º–5º | `classes` no config ignorando preenchimentos pretos; parede = contorno de 1,44 pt. Ao abrir um PDF novo, comparar o render da página com os `get_drawings()`: o que aparece só no vetor é clip ou camada |
| E18 | Batel, teste | `cv2.imwrite` não grava em caminho com acento ("ATÉ") e não avisa | gravar com `cv2.imencode(...)[1].tofile(caminho)` e conferir se o arquivo existe |
| E14 | Salvador (Carol) | Recorte por andar gravou 30 de 66 unidades; a regressão só olhava um andar | C8: contagem de recortes = SpotSys |
| E15 | Salvador (Carol) | Traço de 0,3 pt (vidro, divisa entre ambientes abertos) não virou barreira, e recepção/hall viraram jardim | ler os tipos de ambiente por página no debug; barreiras explícitas onde o traço é fino |
| E16 | Cachoeira (Carol) | Leitura do mobiliário do lançamento em faixa/prévia saiu errada duas vezes | ler só em zoom de 2–3x por unidade (etapa 3.7) |
| E19 | Lagoa, 20–21/10 | Paredes do PDF Legal com cunhas/"V" (hachura e shaft do CAD); redesenho de trechos iguais ao lançamento gerou paredes desalinhadas, portas duplicadas, soleira passando da porta, bancada solta, chuveiro na parede errada, parede fora da janela | geometria limpa (DWG) fora das zonas alteradas; nessas áreas, a representação do lançamento tal qual; regras 4B.1–12 |
| E20 | Lagoa, 22/10 | Legal somado ao executivo nas zonas redesenhadas: parede dupla, parede de WC no tom do piso, janelas cortadas sob as caixas de rótulo | regras 4B.13–15: retângulos no alinhamento do executivo; emenda no núcleo da parede; janela refeita com a faixa limpa vizinha |
| E21 | Lagoa, 22/10 | Área externa redesenhada pelas camadas do CAD ficou confusa ("linhas sobrando", garden sem muro de divisa) | regra 4B.17: lançamento tal qual quando bate com a referência |
| E22 | Lagoa, 22/10 | Recorte feito com script próprio em vez da skill da Bianca | etapa 8: sempre `recortar-plantas`; config gerado da geometria |
| E23 | Lagoa, 22/10 | Recorte cortou a soleira da porta de entrada ao meio; detecção da soleira por cor gerou recortes enormes; WC atribuído por contato à unidade errada | contorno até a face do corredor com o vão por geometria; WC pelo contato direto de piso (vão da porta) |
| E24 | Lagoa, 22/10 | Planta do pavimento em `04_PUBLICACAO/` ficou de uma rodada anterior à última correção | conferir por hash a planta base dos pins com a da entrega (etapa 9) |
| E13 | Batel | Scripts com coordenadas fixas do Batel (`redesenha_entrada_terreo.py`, `remove_rotulos_terreo.py`, `limpa_garden113.py`) ficam em `skill/scripts/` como se fossem genéricos | marcados como **modelo** na seção 8; copiar e ajustar, nunca rodar em outro empreendimento sem isso |

---

## 8. Referência dos scripts

| Script | Etapa | Uso | Tipo |
|---|---|---|---|
| `sobrepoe_aprovado.py` | 3, 6 | `<pdf> <pág> <clip pt> <img> <prefixo> [--limiar 70 --escala 100 --cm-px-img]` | genérico; ver E10 |
| `overlay_alta.py` | 3, 4A, 6 | `<registro.json> <render> <larg_registro> <clip pt> <prefixo> --pdf <pdf> [--tiles 3x2]` | genérico |
| `monta_comparativo.py` | 6 | `<comparativo.json> <pasta>` (modelo: `BATEL-SPOT/03_trabalho/comparativo.json`) | genérico |
| `corrige_rotulos_area.py` | 5 | `<img> <rotulos.json> <saida> [--debug]` | genérico (rótulo branco) |
| `remove_texto.py` | 5 | `<png> <saida> <debug> [--fundo-min 60]` | genérico (texto preto) |
| `confere_areas_base_x_aprovado.py` | 2 | `<dxf> <quadro.json> <transform.json> <rotulos.json> <saida.csv>` | genérico (DWG com zonas) |
| skill `recortar-plantas` (Bianca): `recortar.py`, `grade.py`, `montagem.py`, `paredes.py` | 8 | ver etapa 8 e o `SKILL.md` dela; instalada em `~/.claude/skills/recortar-plantas` | **obrigatória para recorte** |
| `recorte/config_recorte_bianca.py` | 8, 9 | `<configs/recorte.json>` (modelo: `exemplos/lagoa-spot_recorte.json`) → configs da skill da Bianca + `pins_360_AGUARDANDO_VALIDACAO.json` | genérico (máscara de ambientes); validado no Lagoa |
| `do_zero/lagoa/` | 4B, 5 | ver `do_zero/lagoa/LEIA-ME.md` (ordem de execução) | **modelo do método híbrido** (validado) |
| `extrai_rotulos_pdf.py`, `celulas_pdf.py`, `registra_pdf_imagem.py`, `registra_translacao.py` | 2, 8 | ver etapa 8 | **padrão de rótulo do Cachoeira** (E12) |
| `prepara_pdf_carol.py` | 8 | `<config.json>` (modelo: `BATEL-SPOT/03_trabalho/prepara_pdf_carol_batel.json`): uma planta por página, recorte por redação, contorno opcional | genérico |
| `poligonos_carol.py` | 8, 9 | `<config.json>` (modelo: `BATEL-SPOT/03_trabalho/poligonos_carol_teste.json`): polígonos da Carol → recortes + `pins_360` | genérico; testado no Batel (fase 2) |
| `gera_recortes.py`, `folha_contato.py`, `relatorio_qc.py`, `roda_pipeline.py` | 8 | recorte antigo | **substituídos pela skill da Bianca** (só referência) |
| `gera_pacote_publicacao.py` | 9 | pacote com validação por unidade | genérico |
| `gera_humanizada_dwg.py`, `gera_cfg_recorte.py`, `roda_unificado.py` | 4B, 8 | DWG com blocos e zonas | genéricos para DWG completo |
| `do_zero/cachoeira/`, `do_zero/campeche/` | 4B | ver `do_zero/LEIA-ME.md` | **modelos** por empreendimento |
| `redesenha_entrada_terreo.py`, `remove_rotulos_terreo.py`, `limpa_garden113.py` | 4A, 5 | coordenadas do térreo do Batel | **modelos** (E13) |
| skill da Carol (`seazone-tech/skill-atualizar-humanizada`: `planta.py`, `auditar.py`, `render.py`, `ferramentas/`) | 2, 4B, 8 | **externa; não copiada nem executada aqui**. Uso condicionado ao teste da fase 1 | candidata (`COMPARACAO_SKILL_CAROL.md`) |
| `gera_humanizada_aprovado.py`, `gera_planta_compatibilizada.py`, `gera_humanizada_lancamento_r06.py`, `mobilia_ia.py`, `remontagem/` | — | métodos descartados (E1, E2); `remontagem/` mantém utilitários (quilting, glifos, QC de divisas) | **não usar para gerar planta** |

---

## 9. Régua de níveis (para escolher o cenário)

| Nível | Evidência (etapa 3) | Cenário |
|---|---|---|
| 1. Sem alteração geométrica | numeração, perímetro e divisão iguais; só textos de área desatualizados | A (só etapa 5); Batel 2º, tipo e rooftop |
| 2. Alteração localizada | poucas zonas diferentes, restante idêntico | A; Batel térreo (entrada, E.T., WC, 8 gardens) |
| 3. Alteração relevante | diferenças espalhadas em várias unidades; mudança de layout ou acessos | B; Cachoeira (82 de 87 unidades) |
| 4. Alteração estrutural | numeração, número de unidades, núcleo ou fachada mudaram; versão do SpotSys ≠ aprovado | parar → reconciliar SpotSys e Projetos → B |

---

## 10. Saída, nomes e exceções

- **Nomes:** Cenário A: `<EMP>_<PAV>_HUM-<COM-TEXTO|SEM-TEXTO|NUMERACAO-UND|COM-TEXTO-SOLAR>_APROVADO-<REV>.png`. Cenário B: `<EMP>_<PAV>_DO-ZERO_FINAL.png` (com "UNIDADE NN") e `<EMP>_<PAV>_DO-ZERO_SEM-TEXTO.png`. Unidades: `Plantas unidades/<pavimento>/<Empreendimento> - <NN>.png` (padrão da skill da Bianca). Códigos de pavimento: `PAV-01`/`TERREO`, `MEZ`, `PAV-02`…, `COB`/`ROOFTOP`. Nunca sobrescrever uma revisão anterior.
- **Resolução:** a da imagem que será substituída; sem reamostragem.
- **Exceções:**
  - pavimentos repetitivos: conferir cada variante do aprovado;
  - unidade em dois níveis: os dois lado a lado, na mesma escala, com os níveis isolados em `niveis/`;
  - rooftop sem paredes: o registro pode herdar o de um pavimento vizinho (`"registro_de"`), confirmando que o núcleo coincide;
  - mezanino sem código na escala 1:100: usar o esquema 1:200 (`--janela`, `--esc 6`, `--escala 200`);
  - PDF escaneado: interromper e pedir o vetorial;
  - texto sobre deck, grama ou tapete: `--fundo-min 60` + revisão do debug.

---

## 11. Limitações e histórico

- O legal aprovado só garante perímetro, numeração e área. O layout interno é conferido contra o interiores, não contra o legal.
- O registro é global por pavimento (sem rotação nem deformação local), e uma deformação local pode passar no C4. Por isso o overlay é sempre lido.
- A remoção de texto é reconstrução de fundo e exige revisão visual.
- Conector do Drive limitado a cerca de 10 MB; o Slack só é lido com acesso ao canal.
- A skill não escreve no SpotSys nem no 360.
- **Histórico das regras:** 06/10, método do Fernando (ponta a ponta, sem texto, uma imagem por unidade e por pavimento) → 12–13/10, colagem e IA descartadas; base DWG do aprovado → 13/10, validação humana obrigatória antes da carga; conferência de áreas do arquivo base → 15/10, Autodoc sempre; humanizada do zero com o layout do interiores (Cachoeira); leitura zona a zona; texturas reais (Batel) → 16/10, inventário de ambientes (Campeche); **dois cenários** (A atualização pontual × B do zero, alinhado com a Bianca); hierarquia de referências; travas e ficha por pavimento; incorporadas as regras compatíveis da skill da Carol (auditoria pré-render, fidelidade do mobiliário, andar real, contagem de recortes, comparação de revisões). O estilo "desenho técnico humanizado" (render vetorial com paleta própria) continua como próxima etapa; estilizar o raster foi testado e rejeitado. → 19/10, só "UNIDADE NN" dentro do ambiente, sem caixas de rótulo (Lagoa) → 20–21/10, regras de representação 1–12 e método híbrido (lançamento tal qual onde não mudou) → 22/10, regras 13–17, plantas do Lagoa aprovadas na 8ª rodada; recorte sempre pela skill `recortar-plantas` da Bianca, com config gerado da geometria e pins dos mesmos contornos; unidades em subpasta por pavimento; **versão MVP fechada**.
