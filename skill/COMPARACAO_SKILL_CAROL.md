# Comparação: nossa skill × `atualizar-humanizada` (Caroline Montedo)

Análise de 16/10/2026. Repositório `seazone-tech/skill-atualizar-humanizada` (privado), branch `main`, commit `410de79` (16/10/2026, Caroline Montedo), 23 arquivos.
Lido com a conta `rachelsouto-source` (somente leitura), num clone fora deste repositório. **Nada foi copiado, executado nem alterado no repositório da Carol.**

## 1. O que foi verificado e o que é só informado

| Afirmação | Situação |
|---|---|
| Lê o PDF vetorial e segmenta os ambientes | **verificado no código**: `planta.py` (778 linhas) separa traços por largura e cor (paredes ≥ 1 pt; médios 0,5–1; finos < 0,5, ou `classes` no config), fecha vãos de porta e faz *flood fill* a partir dos rótulos |
| Mobiliário vetorial pelo manual Spot | **verificado**: `moveis.py` (cama 2,00 × 1,60, criado 0,40, copa 0,55, poltrona 0,62 × 0,72, bacia, cuba, box) |
| Só `UNIDADE nnn`, sem cotas e sem áreas | **verificado** em `regras-layout.md` e `render.py` |
| Arquivo por pavimento, por andar real e recorte por unidade | **verificado no código e na documentação** (`render.py`, `recortes_unidades`) |
| Auditoria antes do render | **verificado**: `auditar.py` (irmãs ±30%, bolsas brancas, unidade sem sanitário ou sem jardineira, fidelidade do mobiliário) |
| Nível de fidelidade do mobiliário | **verificado**: `mobiliario-pagNN.json` com `lancamento / adaptado / regra / minimo / sem cama` |
| Comparação entre revisões | **verificado**: `ferramentas/comparar_seg.py`, `comparar_saida.py`, `lado_a_lado.py`, `unidade_r10_r11.py` (os caminhos `R10`/`R10-v6c` estão fixos: são ferramentas do case Salvador) |
| Salvador 66 unidades, Cachoeira 87 | **a lista de códigos documentada soma 66 e 87**. As imagens geradas **não estão no repositório** (`.gitignore` exclui `saida/`, `fontes/`, `*.png`), então não foi possível conferir o resultado nem a qualidade |
| Mezaninos e lojas | documentado (config do Cachoeira: `MEZANINO`, `LOJA`, `numeracao_por_posicao`); resultado não verificável |

## 2. Arquitetura lado a lado

| Aspecto | Nossa skill | `atualizar-humanizada` |
|---|---|---|
| Fonte da geometria | PDF assinado do **Autodoc 2.1.c.a** (obrigatório) + DWG da mesma revisão com áreas conferidas | "projeto aprovado" vetorial. **No Cachoeira, usou o compatibilizado ARQ LEGAL R10/R11 do Drive**, com a nota "a conferir com R00"; o aprovado assinado do Autodoc é o **R06**. No Salvador, desde 16/10, usa o R11 vetorial do Autodoc |
| Cenários | A (corrige a existente) e B (do zero) | só "do zero" (equivale ao nosso B) |
| Segmentação de ambientes | por empreendimento (`do_zero/<emp>/mapa*.py`) ou blocos do DWG | **genérica e parametrizada por `config.json`** (classes de traço, rótulos → tipo, faixas de área, órfãos: escada/elevador/sanitário sem rótulo) |
| Estilo | **realista**: texturas e objetos reais recortados do lançamento (decisão da Rachel, Batel/Campeche) | **"desenho técnico humanizado, textura simplificada, não realístico"**, com sprites de textura do lançamento e móveis desenhados em vetor |
| Mobiliário | **projeto de interiores** (tabela de tipologias) | **gabarito lido da humanizada de lançamento** (`layout_lancamento`) → regra Spot → mínimo, com o nível registrado |
| Auditoria pré-render | não tinha (QC depois do render: chamfer + zona a zona) | `auditar.py` (achado sem explicação = não renderiza) |
| Conferência com o aprovado | chamfer + sobreposição em alta, zona a zona; áreas SpotSys × aprovado × interiores × base | debug da segmentação lido por pessoa; área do flood só como ordem de grandeza; prévia lado a lado com o lançamento |
| Numeração | SpotSys; extrator só no padrão Cachoeira (falha no Batel, E12) | SpotSys; rótulos `AP. nnn`, `APTO`, número solto, `LOJA 01`, `prefixos_unidade` configurável; **por andar** (`{andar}{nn}`) e **por posição** |
| Saídas | pavimento (com/sem texto/numeração/solar), recorte por unidade, pacote com `pins_360.json` e trava de validação humana | pavimento, **um arquivo por andar real**, recorte por unidade (unidade + sanitário + jardineira) |
| SpotSys / 360 | pacote de publicação + pins (não testados); a skill não escreve | não publica ("é da Bica"); sem pins |
| Comparação de revisões | não tinha | três camadas: tinta do PDF, segmentação por unidade, saída (hash/pixels) |
| Regressão | não tinha | diff da segmentação de todas as pranchas; contagem de recortes = SpotSys |
| Dependências | pymupdf, opencv, numpy, scipy, ezdxf, PIL | pymupdf, opencv-headless, numpy, pillow, shapely |

## 3. Os oito recursos pedidos: como incorporar

| Recurso | O que já temos | O que a Carol tem | Proposta | Depende de |
|---|---|---|---|---|
| 1. Leitura do PDF vetorial | extração de rótulos (padrão Cachoeira), rasterização e chamfer | classificação de traços por largura/cor com `classes` por escritório; leitura de vários padrões de rótulo | **usar a leitura dela como extrator de unidades no Batel** (`prefixos_unidade: ["UNIDADE"]` + `andares`), no lugar de adaptar o nosso | teste controlado (seção 5) |
| 2. Segmentação e geração | geradores por empreendimento (B) | motor genérico `planta.py` + `render.py` | no Cenário B, o motor dela é **candidato a gerador da geometria e das máscaras**; nosso acabamento realista entra por cima | teste + decisão de estilo da Rachel |
| 3. Texturas e mobiliário Spot | texturas e objetos reais do lançamento | medidas do manual Spot; regras (cama na lateral do sanitário, jardineira inteira, louça em todo sanitário) | **adotadas agora como regras de conferência** (Q4/Q11); o estilo segue o nosso (realista) até decisão em contrário | — |
| 4. Pavimento, andar real, unidade | pavimento + unidade | + **andar real** com o número exato | **adotado agora**: a etapa 8 exige arquivo por andar real quando o SpotSys/360 usar planta por andar | confirmar como o 360 usa a planta de tipo |
| 5. Auditoria pré-render | — | `auditar.py` | **adotada agora como etapa 4B.7 (checklist)**; o script só depois do teste | — |
| 6. Fidelidade do mobiliário | — | níveis por unidade | **adotado agora**: cada unidade recebe nível; `regra`/`minimo` = validação humana | — |
| 7. Comparação de revisões | — | três camadas | **adotada agora** na etapa 3 (revisão nova do mesmo projeto) | — |
| 8. Recortes para o 360 | recorte pela face externa + pins | recorte unidade + sanitário + jardineira; contagem = SpotSys | **adotado agora**: C8 (contagem) e o conteúdo do recorte; pins continuam nossos | — |

## 4. Conflitos que precisam de decisão (não resolvidos por suposição)

1. **Fonte da geometria do Cachoeira.** A skill da Carol usou o compatibilizado R10/R11, e a nossa regra exige o R06 assinado do Autodoc. Antes de comparar os resultados das duas no Cachoeira, é preciso rodar a dela sobre o R06 ou conferir R10/R11 × R06 por sobreposição. → **Carol / Rachel**
2. **Estilo.** Realista (Rachel, Batel/Campeche: "quero as texturas realistas") × "desenho técnico humanizado, não realístico" (Carol; brief da Tati ao Fernando de 06/10). As duas versões se apoiam em pedidos diferentes. → **Rachel / Tati**
3. **Fonte do mobiliário.** Interiores (Rachel, 15/10) × gabarito do lançamento (Carol, 15/10). **Proposta de conciliação, já escrita na hierarquia:** interiores quando existir; gabarito do lançamento quando não existir interiores ou quando os dois coincidirem; regra Spot ou mínimo **só** com registro e validação humana. → **Rachel confirmar**
4. **Planta de tipo × andar real.** O SpotSys do Batel tem uma imagem de tipo ("UND. FINAL 01…12"). É preciso saber se o 360 precisa de um arquivo por andar (301…812). → **quem administra o 360**

## 5. Proposta de integração (em fases; nada estrutural sem OK)

| Fase | O que | Onde | Autorização |
|---|---|---|---|
| 0 (feito, 16/10) | regras compatíveis adotadas na documentação: auditoria pré-render, níveis de fidelidade, andar real, contagem de recortes, comparação de revisões, leitura do lançamento em zoom de 2–3x, conferir o arquivo grande no disco | `SKILL.md` | — |
| 1 (feito, 16/10; resultado na seção 6) | **teste controlado do extrator/segmentador dela no Batel** (térreo e tipo), num clone em pasta de teste, com `config.json` do Batel criado por nós: medir se lê 99/99 unidades e se os polígonos casam com as divisas (chamfer + zona a zona) | pasta de teste fora dos dois repositórios | **sua** (rodar o código da Carol) |
| 2 | se a fase 1 passar: usar `planta.py` como **dependência externa** (clone do repositório dela, como já fazemos com a Raquel e o Arthur em `roda_unificado.py`), sem copiar código, para gerar os polígonos do nosso recorte e dos pins | nosso `scripts/` (adaptador) | **sua + Carol** |
| 3 | Cenário B: motor dela para a geometria + nosso acabamento realista, ou o estilo dela, conforme a decisão do conflito 2 | — | **Rachel/Tati + Carol** |
| 4 | devolver à Carol o que a nossa tem e a dela não: fonte Autodoc obrigatória, conferência de áreas, leitura zona a zona, Cenário A, pacote com validação humana e pins | PR no repositório dela | **Carol** |

## 6. Resultado do teste da fase 1 (Batel Spot, 16/10/2026)

Autorizado pela Rachel em 16/10. A pasta de teste ficou isolada no scratchpad da sessão, e o código da Carol foi rodado direto do clone (`py -B`). `git status` do clone continua limpo, ou seja, nenhum arquivo dela foi alterado nem copiado. Evidências: `BATEL-SPOT/05_qc/teste_2026-10-16/fase1_skill_carol/` (config usado, log, medição por unidade, debug do térreo e do tipo, script de medição).

**Entrada preparada por nós (sem mexer no código dela):**
- PDF aprovado R04 do Autodoc recortado em 6 páginas, uma por planta (térreo, 2º, tipo 3º/7º, tipo 4º/6º/8º, tipo 5º, ático). Usamos redação (`apply_redactions(graphics=2)`) com margem de 25 pt: a skill lê a página inteira, e o Batel tem várias plantas por página.
- `config.json` com `pt_por_metro` 28,35 (1/100), `res_px_m` 250, `prefixos_unidade: ["UNIDADE"]`, `ambientes` (`UNIDADE`, `E.T.`, `GRAMA`, `TERRAÇO`), `faixa.unidade` 8–30 m², `paginas` → `andares` e `classes`.

**Resultados:**

| Medida | Resultado |
|---|---|
| Unidades lidas com região própria | **99 de 99**, códigos iguais aos do SpotSys (térreo 101–115, 2º 201–212, tipo expandido para 301–812). Nosso extrator lia 0 de 99 |
| Área da região × A. COMP. do aprovado | 90 de 99 a ±2%; 99 de 99 a ±7%. As 8 fora de ±3% são a **unidade final 12** do 2º ao 8º (17,9 × 19,10 m², −6%) e a **115** (17,92 × 19,09 m²). Por ser o mesmo desvio em todos os andares, a causa provável é um nicho ou shaft fora do *flood*; a conferir na leitura zona a zona |
| Polígonos × divisas | os polígonos saem do próprio vetor aprovado. Nos debugs do térreo e do tipo, as divisas das unidades, a circulação, o núcleo, o E.T. e o shaft estão separados corretamente |
| Tempo | ~7 min para as 6 plantas (segmentação) |

**Incompatibilidades encontradas no código da Carol (para levar a ela, sem alterar o repositório):**
1. **Poché recortado por *clip path*.** No Batel (AutoCAD), as paredes são um preenchimento preto do tamanho do prédio (camada `ARQ-PMC-PERÍMETRO`) que só aparece onde o clip deixa. A skill ignora o clip, e a primeira rodada deu o prédio inteiro como parede (nenhuma região nos pavimentos 2 a 5; térreo com 11 de 15). **Contorno pelo config:** `classes` ignorando os preenchimentos pretos e usando os contornos de 1,44 pt como parede.
2. **Uma planta por página.** A skill não aceita recorte (clip) de página; foi preciso gerar o PDF recortado.
3. **Numeração do térreo:** com `pagina_terreo` definido, o recorte grava `str(int("01")) = "1"` em vez de `101`, porque no Salvador o térreo só tinha 01 e 02. No Batel, `pagina_terreo` precisa ficar vazio, ou a regra precisa mudar.
4. **Sanitário não separado** em 88 de 99 unidades: o legal do Batel não rotula o banheiro, e as paredes internas não fecham recinto. O auditor dela daria 88 achados "unidade sem sanitário". Para o recorte e os pins isso não importa, porque a unidade inteira está certa. Para o mobiliário vetorial dela, importa.

**Não testado:** `render.py`, `auditar.py`, `sprites.py` e os recortes da Carol, que dependem da configuração do lançamento e do estilo, ainda em decisão (conflito 2). Também não foi testada a ligação dos polígonos dela com o nosso recorte e os pins (fase 2).

**Conclusão:** para o Batel, a leitura e a segmentação da Carol **resolvem o bloqueio do recorte (E12)**, com duas condições já documentadas: PDF recortado por planta e `classes` para o poché. Próximo passo (fase 2, precisa de OK): um adaptador nosso que leia `pagNN-rotulos.npz` + `pagNN.json` dela e entregue os polígonos ao `gera_recortes.py`/pins, levando pt do PDF → px da humanizada pelo registro já validado (`05_qc/*_registro.json`).

## 7. Resultado do teste da fase 2: adaptador para recorte e pins (Batel, 16/10/2026)

Autorizado pela Rachel em 16/10 ("pode prosseguir"). O script é nosso, `skill/scripts/poligonos_carol.py`: **lê só as saídas** da Carol (`pagNN.json` + `pagNN-rotulos.npz`), sem importar nem copiar o código dela. Ele leva cada polígono para a humanizada pelo registro já validado, recorta a unidade com seus anexos e gera `pins_360` (polígonos 0–1 por `szi_unit_id`).
- Configuração: `BATEL-SPOT/03_trabalho/poligonos_carol_teste.json`.
- Saídas: `BATEL-SPOT/05_qc/teste_2026-10-16/fase2_recortes/` (rótulo `TESTE-FASE2`, **não publicar**).
- Export do SpotSys com `id` baixado do Nekt nesta data: `BATEL-SPOT/00_entradas/spotsys/spotsys_batel_2026-10-16.csv`. No Nekt de hoje, o `is_active` do Batel está vazio; consultar por `spot_building_id = 1`.

| Medida | Resultado |
|---|---|
| C8: recortes × unidades do SpotSys | **99 = 99**, todos com `szi_unit_id` (330–428); `pins_360_TESTE-FASE2.json` com 99 polígonos |
| Alinhamento dos polígonos | térreo (nova humanizada sem texto), 2º (854) e tipo (858): os contornos caem nas paredes do render (`03_CONFERENCIA/*_poligonos.jpg`) |
| Escala | área do polígono na imagem (unidade + 15 cm de parede) coerente com a A. COMP. (ex.: 212: 19,15 × 19,10 m²) |
| Tempo | ~1 min para os 99 recortes |

**Defeitos encontrados (o teste não aprova o pacote):**
1. Os **gardens de grama a oeste (101–104) e o terraço da 211** ficam fora do recorte, porque o aprovado não os fecha como ambiente (o adaptador sinaliza: "SpotSys tem garden, recorte sem anexo"). Correção: `barreiras_extra` no config da Carol, ou anexar o garden pelo polígono do SpotSys/prancha. A 105 ganhou um "jardim", mas é preciso conferir se é o garden dela.
2. O recorte da **113** invade um trecho da circulação à esquerda (`amostra_recortes.jpg`). Correção: barreira ou máscara da circulação.
3. A **111** (tipo) tem o polígono em L até a circulação: conferir na leitura zona a zona.
4. **2º e tipo saem com texto** (áreas e "UND. FINAL nn"), porque não existe versão sem texto em alta dessas plantas (o "sem texto" do lançamento tem 2500 px). Falta a etapa 5 nesses pavimentos.
5. O **térreo ainda não foi validado** (etapa 7), e a trava continua valendo: estes recortes são só teste.
6. Os pins foram gerados, mas **não foram carregados** no 360 (etapa 12 continua não testada).

### 7.1 Correções e novo teste (16/10/2026, pedido da Rachel)

| Defeito | Causa encontrada | Correção | Resultado |
|---|---|---|---|
| Gardens 101–105 fora do recorte | (a) **erro nosso de preparação:** o recorte do PDF do térreo começava em x = 1900 pt, e os gardens ficam em x ≈ 1801–1925; (b) a divisa do lote é um traço-ponto em segmentos curtos, por onde o flood escapa; (c) o raster da Carol só vai 1 m além das paredes, então os gardens batiam na borda e eram descartados como "fora do lote" | clip do térreo ampliado (1790 pt); **contorno** de 1,44 pt desenhado no PDF de teste, com o lado oeste **na divisa do lote lida na prancha** (x = 1800,5 pt); `barreiras_extra` (mecanismo da Carol) para a divisa e os divisores dos gardens. Agora feito por `skill/scripts/prepara_pdf_carol.py` (`BATEL-SPOT/03_trabalho/prepara_pdf_carol_batel.json`) | os 5 gardens viram região e são anexados pela própria Carol às 101–105. Bônus: os E.T. de 3,99 e 1,84 m² passam a ser reconhecidos |
| 113 invadindo a circulação | um "sanitário órfão" de 1,00 m² (o nicho do E.T. entre 113 e 114), classificado só por vizinhança | resolvido pela segmentação nova (E.T. rotulado). Regra de proteção no adaptador: sanitário órfão descartado quando a unidade sozinha já bate com a A. COMP. (±3%), o que também limpou 201, 211, 301…801 | recorte da 113 sem circulação |
| Terraço da 211 fora | região de 46,95 m² segmentada, mas sem unidade | regra no adaptador: se o SpotSys tem área externa e o recorte não tem anexo externo, entra o anexo livre vizinho de área mais próxima (0,6–1,6×). **Conferido na prancha:** "TERRAÇO DESCOBERTO PRIVATIVO UNID. 11", em L até o muro de 1,80 m | 211 com o terraço (46,95 × 51,64 m² no SpotSys) |
| **Novo, achado na conferência:** a 105 levava a grama do garden da 106; as gramas das 107–111 ficavam sem dono | anexação pelo rótulo mais próximo | regra no adaptador: grama/jardineira vai para a unidade com a **maior divisa** (unidade + terraço + sanitário dela) | 106–111 com grama + deck, como na prancha; 105 sem a grama da vizinha |

**Novo resultado:** 99 recortes = 99 unidades do SpotSys (C8 OK), 0 falhas, todos com `szi_unit_id`. Cada ajuste aparece na coluna `observacao` de `recortes_carol_log.csv`. Evidências: `03_CONFERENCIA/TERREO_poligonos.jpg`, `PAV-02_poligonos.jpg`, `TIPO_poligonos.jpg`, `amostra_recortes_v2.jpg`.

**Ainda aberto (vai para a leitura zona a zona e a validação, não bloqueia o teste):**
- 101–105 vão até a divisa do lote do aprovado, alguns centímetros além do muro desenhado no render (render × aprovado);
- a 104 tem um pequeno apêndice no corredor; a 111 (tipo) tem o L até a circulação;
- a área dos anexos externos difere da do SpotSys (0,48× a 1,67×; ex.: 101 com 13,77 × 9,36 m²). O SpotSys usa outro critério de área de garden (já anotado no diagnóstico). O recorte segue a geometria do aprovado; o critério fica para Projetos;
- 2º e tipo ainda com texto (falta o sem texto em alta); térreo sem validação; pins não carregados.

**Para levar à Carol:** (1) margem do raster configurável, ou caixa a partir de `barreiras_extra`; (2) aceitar um recorte de página no config; (3) poché recortado por clip path; (4) numeração do térreo com `pagina_terreo`; (5) anexação de grama pela maior divisa.
