---
name: atualiza-humanizadas-spotsys
description: Gera ou atualiza as plantas humanizadas de pavimento de um empreendimento Seazone de acordo com o projeto aprovado (Autodoc), recorta por unidade e prepara a carga no SpotSys e os pins do 360, com conferência e travas de validação em cada etapa. Dois cenários: A (corrigir a humanizada existente quando a mudança é pontual, como no Batel Spot) e B (humanizada do zero sobre o aprovado com o layout do interiores, como no Cachoeira e no Campeche). Use quando pedirem "atualizar humanizada", "humanizada x projeto aprovado", "humanizada do zero", "planta sem texto", "recorte por unidade", "planta desatualizada no SpotSys", "pins do 360" ou citarem um empreendimento com is_outdated_area.
---

# Skill: plantas humanizadas pelo projeto aprovado (SpotSys / 360)

Versão do procedimento: **16/10/2026**. Ela substitui as seções A–L da versão de 15/10. As regras técnicas foram mantidas e reorganizadas; o histórico está na seção 11.

Arquivos que compõem a skill (mantenha-os consistentes entre si):

| Arquivo | Para que serve |
|---|---|
| `skill/SKILL.md` (este) | procedimento: cenários, hierarquia, etapas, travas, checklist |
| `skill/modelos/CHECKLIST_PAVIMENTO.md` | ficha que é preenchida e salva em `01_diagnostico/` para **cada pavimento**; é a prova de cada etapa |
| `skill/CASO_BATEL_SPOT.md` | caso de referência do Cenário A, etapa por etapa, com os testes de 16/10 |
| `skill/scripts/do_zero/LEIA-ME.md` | geradores do Cenário B (Cachoeira, Campeche) |
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

---

## 1. Objetivo e cadeia ponta a ponta

A skill entrega a cadeia que a Tati vai avaliar (Rachel, 15/10/2026). Cada elo precisa encaixar no seguinte:

```
projeto aprovado (Autodoc) ─► planta humanizada do PAVIMENTO ─► validação ─► recorte por UNIDADE
   ─► upload das unidades no SpotSys ─► troca da planta do pavimento ─► pins do 360 ─► 360 validado
```

O processo de **lançamento** é o mesmo, partindo do anteprojeto e criando os pins (em vez de reajustá-los).

**Estado real de cada elo (16/10/2026):**

| Elo | Situação | Prova |
|---|---|---|
| 1. Planta do pavimento, Cenário A | **executável** (Batel térreo) | `CASO_BATEL_SPOT.md`; sobreposição da entrada conferida em 16/10 |
| 1. Planta do pavimento, Cenário B | **executável, aguardando validação** (Cachoeira e Campeche térreo) | `scripts/do_zero/`; nenhuma planta B foi validada até agora |
| 2. Validação da planta | **procedimento definido** (seção 5 + ficha) | — |
| 3. Recorte por unidade | **executável no padrão de rótulo do Cachoeira** (87 unidades na R04, base antiga). No Batel, o nosso extrator leu 0 de 99 (E12). Com a segmentação da Carol (fase 1) + `poligonos_carol.py` (fase 2), saíram **99 recortes e 99 pins com `szi_unit_id`** em teste (16/10), depois das correções de 16/10 sem falhas (C8 OK; gardens, terraço da 211 e 113 corrigidos), mas com 2º/tipo ainda com texto e o térreo sem validação | `COMPARACAO_SKILL_CAROL.md`, seções 6 e 7 |
| 4. Upload das unidades no SpotSys | **manual**, por quem tem acesso de escrita. A skill não escreve no sistema | — |
| 5. Troca da planta do pavimento | **manual**. Antes de trocar, é preciso saber qual imagem do SpotSys corresponde a cada pavimento (Batel: 854–859, das quais 857 e 859 não foram mapeadas) | — |
| 6. Pins do 360 | **não testado.** `gera_pacote_publicacao.py` gera `pins_360.json` (polígonos 0–1 por `szi_unit_id`), mas o arquivo nunca foi carregado no 360. O reposicionamento automático é uma **hipótese**: os pins saem da mesma geometria do recorte, o que deveria mantê-los no lugar, mas isso ainda não foi provado | — |
| 7. 360 validado | **não testado** | — |

> Ninguém pode afirmar que os pins funcionam enquanto o teste da etapa 12 não for feito e registrado.

---

## 2. Hierarquia de referências

**Regra geral [OBRIGATÓRIO]:** referência **geométrica** e referência **visual** nunca se misturam. A geometria vem só das fontes da coluna "manda". A humanizada de lançamento nunca define posição, tamanho ou forma de parede, unidade ou acesso.

| Tipo de informação | Manda (prevalece) | Complementa (só se compatível com quem manda) | Nunca usar para isso |
|---|---|---|---|
| Revisão vigente do projeto | PDF assinado do **Autodoc 2.1.c.a**, maior revisão | — | cópias do Drive (`*APROVADO*.pdf`, "Arquivos - Investidores") |
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

| Critério (todos lidos na etapa 3) | Cenário A: atualizar a existente | Cenário B: do zero |
|---|---|---|
| Existe humanizada de lançamento do pavimento, em alta resolução | sim | não importa (sem ela, é sempre B) |
| Numeração e número de unidades = aprovado | sim | não, ou não importa |
| Divisas das unidades caem nas paredes (QC da etapa 3) | sim, nas unidades | não, de forma espalhada |
| Área privativa do interiores = A. COMP. do aprovado | sim | não, em várias unidades |
| Diferenças da leitura zona a zona | **poucas e localizadas** (uma entrada, um E.T., um WC, uma vaga, rótulos) | acessos de unidades mudados, banheiros reposicionados, unidades que mudaram de lugar, pavimento reorganizado |
| Régua da seção 9 | nível 1 ou 2 | nível 3 ou 4 |
| Exemplo | **Batel Spot** (térreo: entrada, vaga de embarque, E.T., WC; demais pavimentos sem alteração) | **Cachoeira Spot** (82 de 87 unidades alteradas, térreo e mezanino reorganizados); **Campeche Spot** |

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
<EMP>/03_trabalho/             intermediários, scripts específicos do empreendimento
<EMP>/04_saida/<EMP>_<SITUAÇÃO>-<REV>/   01_PLANTAS, 02_COMPARATIVO, 02_UNIDADES, 03_CONFERENCIA, 04_PUBLICACAO
<EMP>/05_qc/                   registros, sobreposições, alta/ (mosaicos zona a zona)
```

### Etapa 0. Abrir o caso

- **Objetivo:** ter uma ficha por pavimento onde cada etapa deixa a sua prova.
- **Entrada:** nome do empreendimento; lista de pavimentos do SpotSys.
- **Ação:** crie as pastas acima. Copie `skill/modelos/CHECKLIST_PAVIMENTO.md` para `01_diagnostico/CHECKLIST_<PAV>.md` (uma por pavimento ou por grupo de pavimentos tipo). Crie `PENDENCIAS_<EMP>.md`.
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

### Etapa 4B. Cenário B: humanizada do zero

- **Objetivo:** desenhar o pavimento inteiro sobre a geometria do aprovado, com o layout do interiores e o acabamento do lançamento.
- **Entrada:** PDF aprovado (e DWG/IFC/RVT da mesma revisão, se tiver passado na etapa 2); tabela de tipologias e plantas de tipologia do interiores; kit de estilo do lançamento.
- **Ação, nesta ordem:**
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
- **REGRAS DE REPRESENTAÇÃO [OBRIGATÓRIAS] (Rachel, Lagoa Spot 20–21/10/2026, todo empreendimento):** a humanizada é planta de venda para leigo, não desenho técnico. Modelo: `LAGOA-SPOT/03_trabalho/carol/render_hibrido.py`.
  1. **Versão de referência:** é a última versão do projeto, que varia por caso: executivo mais recente ou legal aprovado. Rachel indica qual. O lançamento é a referência de **representação e layout**, não de geometria.
  2. **Onde a geometria da versão de referência = lançamento** (confira por overlay, zona a zona), use a **representação do lançamento tal qual**, só sem os rótulos. Isso vale para paredes, portas, soleiras, louças, box e chuveiro. Redesenhar o que já está certo gerou paredes desalinhadas, linhas na frente das paredes e portas sobrepostas.
  3. **Redesenhe só as zonas que mudaram** (`ZONAS_LEGAL`/`ZDES`). Dentro delas use os mesmos símbolos e texturas do lançamento, com o layout de interiores do lançamento readaptado.
  4. **Paredes:** pretas, retas, no perfil do lançamento (contorno preto ~3 px, faixa branca ~7 px, núcleo preto). Nada de cunha ou "V" de hachura e shaft do CAD. Diagonal com face reta. Nenhuma parede para fora da janela: na fachada, a janela já é a parede.
  5. **Portas:** largura do executivo (nome do bloco, ex.: 80×210; unidades 80 e WC 60). O lado de abrir é o do lançamento, sempre para dentro da unidade ou do WC. A representação é a do lançamento: folha azul-acinzentada com contorno preto, puxador em "U" e arco fino. Uma porta por vão, nunca duas.
  6. **Soleira de granito:** só no vão da porta, rente à folha. A parede vai até a soleira, e a soleira não passa do perímetro da porta. Textura recortada do granito do próprio lançamento.
  7. **Bancadas e móveis:** sempre encostados na parede preta, no fundo e na lateral. Nunca atravessam parede, folha, giro da porta ou soleira. Cuba e vaso nunca dentro da parede nem no giro.
  8. **WC:** box = uma linha reta de vidro de parede a parede. O símbolo do chuveiro do lançamento fica **na mesma parede do vaso**, do outro lado do vidro, em todo box. Sem ralo solto.
  9. **Escadas:** degraus reais e iguais, sem eixo nem seta. A escada de acesso tem piso claro com degraus e corrimão.
  10. **Elevador:** porta do lançamento (0,80 m, inox). Não redesenhar quando a geometria não mudou.
  11. **Área externa:** grama do lançamento só onde a versão de referência tem jardim. Onde tem vaga, entra o piso (sem demarcação). Muro e gradil no padrão do lançamento, sem linha solta.
  12. **Conferência:** antes de entregar, compare cada trecho em zoom com o lançamento (porta, soleira, bancada, box, parede, fachada, acesso). Se um leigo puder ficar em dúvida, está reprovado.
- **Critérios técnicos:** proporção real (banheiros e WCs de loja não podem ser espremidos); orientação igual à do lançamento quando a Rachel pedir (Campeche: legal girado −45°).
- **Validação:** etapa 3 sobre a planta nova (divisas nas paredes, leitura zona a zona). Por unidade: a porta de acesso está na circulação do aprovado e a tipologia é a da tabela.
- **Erros comuns:** acesso de unidade copiado do lançamento (Cachoeira 110/111); interiores aplicado sem conferir a área; frente "confusa" ou com aparência de desenho técnico (Campeche).
- **Saída:** planta do pavimento + inventário + CSV de tipologias + overlay.

### Etapa 5. Textos e rótulos

- **Objetivo:** produzir as versões de texto que o SpotSys e o 360 usam, sem mexer na geometria.
- **REGRA [OBRIGATÓRIA] (Rachel, 19/10/2026, todo empreendimento):** a planta **não leva as caixas de rótulo do lançamento** ("Aloj 02 / 20,23 m² / 03 Hóspedes") nem áreas de garden. O único texto de unidade é **"Unidade NN"**, **dentro do ambiente** da respectiva unidade (modelo: `LAGOA-SPOT/03_trabalho/do_zero/tira_rotulos.py` + `escreve_unidades.py`). Paredes só as do executivo/aprovado: nada de traço de parede do lançamento sobrando ao lado (Rachel: "paredes sobrepostas... confusa").
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
- **Trava:** sem validação registrada, **não existe etapa 8**. Reprovação → volta para a etapa 4 com as observações.
- **Saída:** ficha assinada.

### Etapa 8. Recorte por unidade

- **Objetivo:** uma imagem por unidade, recortada pelo polígono do aprovado e encaixada nas paredes reais da planta validada.
- **Entrada:** planta **validada** sem texto; polígonos das unidades; registro PDF→imagem; export do SpotSys.
- **Ação (padrão de rótulo `101 | 20,22 m²`, como no Cachoeira):**
  1. `py ../skill/scripts/extrai_rotulos_pdf.py <pdf> <págs> <spotsys.csv> rotulos.json conferencia.csv`
  2. `py ../skill/scripts/celulas_pdf.py <pdf> <pág> rotulos.json celulas.json debug.png [--janela ... --esc 6] [--correcoes corr.json]`
  3. `py ../skill/scripts/registra_pdf_imagem.py <pdf> celulas.json <sem_texto.png> 05_qc/registro/<PAV> [--escala 100]`
  4. `config_recortes.json` → `py ../skill/scripts/gera_recortes.py config.json`
  5. `py ../skill/scripts/folha_contato.py <pasta> <saida.jpg>` → revisão em `revisao_visual.json`
  - Alternativa com DWG que tenha zonas de área: `gera_cfg_recorte.py` + recorte da Raquel (`UNIFICACAO_PLANTAS_HUMANIZADAS.md`).
- **Antes de rodar em um empreendimento novo [OBRIGATÓRIO]:** confira se o padrão de rótulo do PDF é reconhecido. Rode o passo 1 e veja a contagem `OK`. **Se for 0 ou muito menor que o número de unidades, pare**: o extrator precisa ser adaptado. No Batel, o rótulo é `UNIDADE 01 / A. COMP.=19,17m²` e o pavimento vem da prancha; o teste de 16/10 deu 0 de 99 (E12). Solução testada para o Batel: a segmentação da skill da Carol (`prefixos_unidade: ["UNIDADE"]` + `andares` por página → código `{andar}{nn}`) leu 99 de 99. Ela exige (a) um PDF com uma planta por página (recorte por redação) e (b) `classes` no config ignorando o poché recortado por clip path. O adaptador `poligonos_carol.py` leva esses polígonos à humanizada pelo registro validado e gera recortes + `pins_360` (fase 2, `COMPARACAO_SKILL_CAROL.md`, seção 7). Ele aplica regras de anexo pela hierarquia (sanitário órfão descartado quando a unidade já = A. COMP.; grama pela maior divisa; anexo externo pelo SpotSys) e registra cada ajuste. Antes de usar o resultado: conferir `*_poligonos.jpg` zona a zona e a coluna `observacao` do log; qualquer `FALHA` bloqueia.
- **Pavimento tipo e andar real:** quando o SpotSys/360 usar uma planta por andar, gere **um arquivo por andar real** com o número exato de cada unidade (ex.: 301…312, …, 801…812), a partir da mesma planta validada do tipo. A planta de tipo ("UND. FINAL 01…12") pode continuar existindo como imagem do pavimento. **[VALIDAÇÃO HUMANA]** Confirme com quem administra o 360 qual das duas os pins usam.
- **Conteúdo do recorte:** unidade + sanitário + jardineira/garden/terraço/sacada da própria unidade.
- **Critérios técnicos:** recorte pela face externa das paredes da própria unidade; nada do vizinho; cantos retos; PNG RGBA com fundo transparente; resolução de origem (mínimo de 400 px no maior lado); nome com o código do SpotSys.
- **Validação:** C1, C6, C7 e **C8 (número de recortes = número de unidades ativas do SpotSys, por pavimento)**; folha de contato revisada; nenhuma unidade sem polígono ou com `falhou_poligono_com_folga` sem revisão. Confira os PNG grandes no disco (data e hash), não as prévias. No OneDrive, o cliente de sincronização às vezes devolve a versão anterior (lição da Carol).
- **Erros comuns:** recorte que pega duas unidades (Cachoeira 103); número da unidade ausente no DWG do térreo e do mezanino; faixas sem divisa no aprovado (108, L3), que ficam pendentes.
- **Saída:** `02_UNIDADES/<PAV>/<EMP>_<PAV>_UN-<código>_HUM-SEM-TEXTO_<REV>.png` + `recortes_log.json` + folhas de contato.

### Etapa 9. QC por unidade e pacote de publicação

- **Objetivo:** só entram no pacote as unidades aprovadas no QC **e** validadas por uma pessoa.
- **Ação:**
  1. `py ../skill/scripts/relatorio_qc.py config.json spotsys.csv conferencia.csv revisao_visual.json 05_qc/registro 03_trabalho/sem_texto` → `QC_RELATORIO.md`, `qc_unidades.csv`
  2. `py ../skill/scripts/gera_pacote_publicacao.py config.json spotsys.csv [--aceitar-ressalva]` → sai como `AGUARDANDO_VALIDACAO` com `VALIDACAO_HUMANA.csv`
  3. **[VALIDAÇÃO HUMANA]** Uma pessoa preenche `validado`, `validador`, `data` e `observacao` por unidade.
  4. Rode de novo com `--validacao VALIDACAO_HUMANA.csv` → `pins_360.json` + `manifesto_publicacao.csv` só com as validadas; o resto vai para `BLOQUEADOS.csv`.
- **Atalho:** `roda_pipeline.py <emp>.json` encadeia as etapas 8–9 (e remove texto com `remove_texto.py`). **Só use depois da etapa 7**, porque ele recorta.
- **Validação:** cada unidade do SpotSys aparece no manifesto ou em `BLOQUEADOS.csv`, com motivo. `szi_unit_id` preenchido em todas as linhas do `pins_360.json` (exige o `id` no export).
- **Saída:** `04_PUBLICACAO/` validado.

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
| X10 | Imagem do pavimento que sobe ≠ imagem base dos pins | 11 |

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
| `extrai_rotulos_pdf.py`, `celulas_pdf.py`, `registra_pdf_imagem.py`, `registra_translacao.py` | 2, 8 | ver etapa 8 | **padrão de rótulo do Cachoeira** (E12) |
| `prepara_pdf_carol.py` | 8 | `<config.json>` (modelo: `BATEL-SPOT/03_trabalho/prepara_pdf_carol_batel.json`): uma planta por página, recorte por redação, contorno opcional | genérico |
| `poligonos_carol.py` | 8, 9 | `<config.json>` (modelo: `BATEL-SPOT/03_trabalho/poligonos_carol_teste.json`): polígonos da Carol → recortes + `pins_360` | genérico; testado no Batel (fase 2) |
| `gera_recortes.py`, `folha_contato.py`, `relatorio_qc.py`, `gera_pacote_publicacao.py`, `roda_pipeline.py` | 8, 9 | ver etapas 8–9 | genéricos, dependem dos anteriores |
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

- **Nomes:** `<EMP>_<PAV>_HUM-<COM-TEXTO|SEM-TEXTO|NUMERACAO-UND|COM-TEXTO-SOLAR>_APROVADO-<REV>.png`; unidades `<EMP>_<PAV>_UN-<código SpotSys>_HUM-SEM-TEXTO_<REV>.png`. Códigos de pavimento: `PAV-01`/`TERREO`, `MEZ`, `PAV-02`…, `COB`/`ROOFTOP`. Nunca sobrescrever uma revisão anterior.
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
- **Histórico das regras:** 06/10, método do Fernando (ponta a ponta, sem texto, uma imagem por unidade e por pavimento) → 12–13/10, colagem e IA descartadas; base DWG do aprovado → 13/10, validação humana obrigatória antes da carga; conferência de áreas do arquivo base → 15/10, Autodoc sempre; humanizada do zero com o layout do interiores (Cachoeira); leitura zona a zona; texturas reais (Batel) → 16/10, inventário de ambientes (Campeche); **dois cenários** (A atualização pontual × B do zero, alinhado com a Bianca); hierarquia de referências; travas e ficha por pavimento; incorporadas as regras compatíveis da skill da Carol (auditoria pré-render, fidelidade do mobiliário, andar real, contagem de recortes, comparação de revisões). O estilo "desenho técnico humanizado" (render vetorial com paleta própria) continua como próxima etapa; estilizar o raster foi testado e rejeitado.
