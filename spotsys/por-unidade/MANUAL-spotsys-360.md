# Manual de operações no SpotSys 360 (receitas testadas)

Tudo o que foi feito e validado em 08–09/10/2026 no `spotsys.seazone.dev/lancamentos/empreendimentos-360/<id>`.
Cada receita diz **onde fica na tela**, **o que vai pela rede**, **qual script usar** e **como conferir**.
Histórico de Drive/planilhas e o fluxo antigo: `docs/PROCESSO-imagens-360.md`.

> Caminho base dos scripts: `C:\Users\compu\seazone\processos\spotsys-navegador\.playwright-mcp\`
> Sempre rodar com `browser_run_code_unsafe` + `filename=<caminho absoluto>` (funciona em qualquer sessão).

---

## 0. Antes de qualquer coisa

1. **Porta do Chrome Claude:** `curl -s -m 5 http://127.0.0.1:9222/json/version`. Se falhar, pedir à Bianca para abrir pelo
   atalho "Chrome Claude". Nunca fechar/matar o navegador.
2. **Ferramentas:** `ToolSearch select:mcp__chrome-claude__browser_tabs,mcp__chrome-claude__browser_run_code_unsafe,mcp__chrome-claude__browser_evaluate,mcp__chrome-claude__browser_network_requests,mcp__chrome-claude__browser_network_request,mcp__chrome-claude__browser_handle_dialog`.
   Só o MCP `chrome-claude` — nunca a extensão Claude in Chrome.
3. **Aba:** trabalhar numa aba própria (`browser_tabs action=new`). Não fechar abas de outras sessões: a tarefa automática
   fecha "a aba dela" pelo índice — fechar outra aba muda os índices.
4. **Outra sessão no navegador?** `ListAgents` + `browser_tabs list`. Se a conexão do MCP travar em "initializeServer",
   alguma aba está com o renderizador travado: testar cada aba via CDP (`/json/list` + `Runtime.evaluate`) e pedir à Bianca
   para fechar a travada.
5. **Tarefa automática rodando?** Se existir `auto\LOCK` com menos de 3 h, ela está trabalhando — não subir plantas no
   mesmo empreendimento ao mesmo tempo. Para trabalho manual pesado, dá para criar o LOCK antes e apagar no fim.
6. **Um script por vez.** Nunca duas chamadas ao navegador no mesmo bloco (rodam juntas na mesma aba e se atropelam).
7. **Scripts carregados por arquivo: só ASCII.** Acento vira `\u00ed` etc. Cuidado: a ferramenta Write converte
   `\u0300` escrito no texto em caractere real — conferir com
   `python -I -c "print(all(ord(c)<128 for c in open('x.js',encoding='utf-8').read()))"` e, se der False, trocar por
   `chr(92)+'u%04x'`.

---

## 1. Mapa da tela 360

| Aba | O que tem | Usado para |
|---|---|---|
| **Por unidade** | card **Área desatualizada** (uma chave por unidade) + **Fotos por unidade** com seções **Plantas Baixas**, **Imagens Internas**, **Vistas da Unidade** | subir/trocar planta de unidade; área desatualizada da unidade |
| **Plantas** | tabela de plantas de pavimento: Preview, Título, Pavimento, **Pins**, Ordem, **Área desatualizada**, Ações | área desatualizada da planta de pavimento |

- A aba "Por unidade" demora a carregar e às vezes não troca no primeiro clique: clicar com a sequência **HIT** (pointerdown →
  mousedown → pointerup → mouseup → click) e repetir até `aria-selected="true"`. Todos os scripts já fazem isso.
- **Desde 28/10/2026** a aba "Por unidade" abre na subaba **Por cota** (lista de unidades). As seções Plantas Baixas / Imagens Internas / Vistas (com os botões Adicionar) ficam na subaba **Por imagem**. O `auto	pl_upload.js` já clica em "Por imagem" sozinho; `tpl_remover.js` e `tpl_area.js` ainda não (ajustar quando forem usados).
- A tabela de **Plantas** também lista as plantas de unidade (linhas "(sem título)", 0 pins). Só as de pavimento têm pins.
- IDs dos empreendimentos: `spot-buildings` na API (ver §2) ou `.playwright-mcp\buildings.json` (cache de 08/10).

---

## 2. Ler o estado pela API (só leitura, sem token aparecendo)

A página chama `https://api-spotsys.seazone.com.br/api/v1/...` com os headers `x-user-token`, `x-szi-api-key`,
`x-user-email`. Os scripts capturam esses headers de uma requisição da própria página (`page.waitForRequest`) e repetem a
chamada com `fetch` dentro da página — o token nunca é impresso.

| Endpoint (GET, sempre com `&per_page=100&page=N`) | Traz |
|---|---|
| `spot-buildings?sort=full_name` | empreendimentos (`id`, `short_name`) |
| `spot-building-units?building_id=<id>` | unidades (`id`, `code`, `is_outdated_area`) |
| `vistas-unit-images?building_id=<id>` | associações imagem↔unidade (`id` = vínculo, `spot_image_id`, `szi_unit_id`, `role` = `planta` / `vista_cota` / …, `url`) |

Scripts prontos:
- `auto\tpl_estado.js` (via `auto\scan.py`): por **nome** de empreendimento → `window.__autoEstado`.
- `lotes\ver_tpl.js` (placeholder `__ESP__` = `{"<id>": ["101","102",…]}` com as unidades que devem ter planta): devolve
  faltando / extras / duplicadas. (`lotes\gen_ver.py` gera esse `__ESP__`, mas lê o plano do lote de 08/10 — para outros
  casos, montar o `__ESP__` à mão ou usar o `_4_verificar` do fluxo automático.)
- Salvar resultado grande em arquivo: guardar em `window.__x` e depois
  `browser_evaluate "() => JSON.stringify(window.__x)" filename=<arquivo.json>`.
- Data de criação de uma planta: o nome do arquivo na URL é um ULID — os 10 primeiros caracteres são o timestamp.

---

## 3. Subir planta de unidade (Plantas Baixas, upload local)

**Tela:** Por unidade → Plantas Baixas → **Adicionar** → Passo 1 (arquivo) → **Próximo** → Passo 2 (chips das unidades) →
**Salvar (N)**. Uma imagem por modal; cada uma grava sozinha.

**Rede (as duas precisam dar 201):**
1. `POST /api/v1/spot-images` (cria a imagem)
2. `POST /api/v1/vistas-unit-images/bulk` (associa às unidades) — **pode falhar sozinha** (já aconteceu: imagem órfã, unidade
   sem planta). Por isso o script confere as duas.

**Script:** `auto\tpl_upload.js` (= `lotes\tpl2.js`). Placeholders `__ID__` e `__ITENS__` =
`[{"f": "<caminho absoluto do arquivo>", "u": ["101","201"]}, …]`, **8 itens por chamada**.
O log de cada item: `arquivo [unidades] img=201 bulk=201 antes->depois`. Para no primeiro bulk que não for 20x.

Detalhes que o script já trata:
- `input[type=file]` é oculto → `page.setInputFiles` direto (nunca clicar na área tracejada).
- Marcar chips e clicar em Salvar em renders separados; confere "(N selecionadas)" = nº de unidades antes de salvar.
- O contador da seção às vezes atrasa (`40->40` e depois `40->42`): não é erro.
- Planta é **única por unidade** (subir para unidade com planta substitui — upsert). Mezanino nunca entra como planta.
- Arquivo > ~10 MB: converter para WEBP q92 antes.

**Nome do arquivo → unidades:** `Empreendimento - 101.png` → 101; `- 101 A` → 101A; `- L1` / `- LOJA 01` (se existir assim
no SpotSys); `- 201 - 501` → **todos os andares** 201, 301, 401, 501 (regra da Bianca 09/10; se algum andar do meio tiver
arquivo próprio = conflito → parar e perguntar). Implementado em `auto\planejar.py` (`codigos()`).

---

## 4. Remover planta de unidade (o "×")

**Tela:** Por unidade → Plantas Baixas → no card, o **×** ao lado do código (`button[title="Remover 101"]`). Não existe botão
de excluir a imagem.
**Confirmação:** `confirm` nativo **"Remover 101 desta foto?"**.
**Rede:** `DELETE /api/v1/vistas-unit-images/<id do vínculo>` → **204**. A unidade sai da imagem; o arquivo continua no
storage (fica órfão, não aparece na tela).

**Script:** `auto\tpl_remover.js` (`__ID__`, `__UNIDS__`, blocos de 20). Ele:
- procura o × **só dentro da seção Plantas Baixas** (sobe do título até antes de "Imagens Internas" — Imagens Internas e
  Vistas também têm botões "Remover 101");
- troca `window.confirm` por uma função que só aceita a mensagem exata das unidades da lista (assim o MCP não intercepta
  o diálogo);
- espera até 10 s o card sumir (a lista recarrega devagar);
- unidade já sem planta é pulada (pode rodar de novo com segurança);
- **espera os cartões aparecerem** (botão `Remover …`, até 30 s) antes de procurar. Sem isso (até 13/10) a página ainda
  carregando fazia o script contar unidade COM planta como "já sem planta" (Cachoeira, 18 unidades). Se o resultado
  trouxer `ja_sem_planta > 0`, conferir pela API (`*_3_verificar.js`) antes de subir.

> Se o diálogo for tratado com `page.on('dialog')` em vez de trocar o `confirm`, o MCP devolve a chamada no primeiro
> diálogo e o script **continua rodando sozinho** em segundo plano — não disparar nada novo; acompanhar por
> `browser_network_requests` (filtro `vistas-unit-images/\d+`).

---

## 5. Trocar plantas (remover e subir)

Ordem usada: (1) ler estado e guardar antes, (2) remover (§4) só das unidades que têm arquivo novo, (3) conferir que
ficaram sem planta, (4) subir (§3), (5) conferir (§8). Unidade com planta e **sem** arquivo novo mantém a planta.
Imagem antiga compartilhada por várias unidades: o × tira só aquela unidade; as outras continuam com ela.

---

## 6. Área desatualizada da **unidade** (aba Por unidade)

**Tela:** Por unidade → card "Área desatualizada" → chave da unidade (`[role=switch]`, `aria-checked`). A linha da chave
tem só o código da unidade como texto.
**Rede:** `PATCH /api/v1/spot-building-units/<unit id>` com `{"is_outdated_area":false}` (ou `true`) → **200**.

Scripts:
- `auto\tpl_area.js` (`__ID__`, `__UNIDS__`): desmarca só as unidades listadas que estiverem marcadas.
- `lotes\area_tpl.js` (`__ID__`): desmarca **todas** as marcadas do empreendimento.
- Antes/depois pela API: `lotes\area_antes.js` (campo `is_outdated_area` de `spot-building-units`).
- **Marcar** (o inverso): `layout\tpl_area_marcar.js` (`__ID__`, `__UNIDS__`) liga só as desmarcadas e confere o PATCH 200 com
  `"is_outdated_area":true`. Usado em 13/10 na lista "depende de redesenho" (ex.: `troca\lagoa_area_marcar.js`).

---

## 7. Área desatualizada da **planta de pavimento** (aba Plantas)

**Tela:** aba **Plantas** → tabela → coluna **Pins** e chave **Área desatualizada** da linha.
**Rede:** vai **direto ao Supabase**, não à api-spotsys:
`POST https://vqwgsgwbetfyoybdjmbs.supabase.co/rest/v1/spot_image_overlays?on_conflict=spot_image_id`
com `{"spot_image_id": 706, "is_outdated_area": true}` → **200** (upsert).

**Script:** `plantas_area\tpl.js` (`__IDS__` = lista de ids, `__MODO__` = `ler` ou `marcar`):
- `ler`: só lê; devolve por empreendimento linhas, quantas com pins, quantas faltam marcar; guarda o detalhe em
  `window.__plantasArea` (salvar com `browser_evaluate … filename=plantas_area\antes_N.json`).
- `marcar`: liga a chave em toda linha com **Pins > 0** que estiver desligada, uma por vez, conferindo o POST acima (200 e
  `is_outdated_area:true`) e a chave ligada. Linhas com 0 pins não são tocadas.
- Até 5 empreendimentos por chamada. Conferir no fim rodando `ler` de novo (tem que dar `faltam: 0`).

**Ler direto do Supabase (só leitura):** as tabelas do 360 ficam no schema `seazone360` — mandar o header
`Accept-Profile: seazone360` (sem ele dá 404 `PGRST205`). Headers `apikey`/`authorization` capturados de um request da página.
- `spot_image_overlays` (planta de pavimento: `is_outdated_area`, `updated_at`…): `layout\troca\overlays_ler.js`.
- `floor_plan_pins` (pin de cada unidade numa planta de pavimento, `szi_unit_id`): `layout\troca\cotas_pins_ler.js` cruza
  unidades × planta da unidade × pin.
- A Nekt (`nekt_operacional_bronze.sup_bd_szi_seazone360_*`) tem essas tabelas, mas o stream de `spot_image_overlays` está
  parado desde 29/09 (13/10: 0 linhas depois dessa data na Nekt × 164 em produção). `vistas_unit_images` não está na Nekt.

---

## 8. Conferência final (obrigatória)

`auto\tpl_verificar.js` (gerado pelo `planejar.py` com `__ID__`, `__NOVAS__` = {unidade: bytes do arquivo local},
`__ANT__` = {unidade: [spot_image_id antigos]}, `__MANTER__` = {unidade: [ids que não podem mudar]}). Confere pela API:
1 planta por unidade, não é a antiga, `content-length` da imagem = tamanho do arquivo local, área desmarcada, unidades sem
arquivo intactas. Resultado em `window.__autoVer` (`ok: true` + `problemas: []`).

Para só listar quem está sem planta: `lotes\faltas_7.js` (trocar a lista `IDS`).

**Sempre dizer na entrega:** a validação foi por nome e bytes do arquivo, não pelo conteúdo visual.

---

## 9. Fluxo automático "pasta OK" (tarefa agendada `plantas-ok-spotsys`) — DESATIVADO desde 13/10/2026

> **Desativada em 13/10/2026** a pedido da Bianca (empreendimentos finalizados). Reativar só se ela pedir
> (`update_scheduled_task plantas-ok-spotsys enabled=true`). O `planejar.py` sobe a imagem de
> `Plantas unidades com mezanino\` quando existir uma com o mesmo nome (para não desfazer as plantas com mezanino).

- Pasta em `C:\Users\compu\seazone\processos\plantas-humanizadas\recorte\` cujo nome termina em **OK** = OK da Bianca.
- Passos: `auto\scan.py` (trava `LOCK`, gera `run\estado.js`) → `run\estado.js` + `browser_evaluate` → `out\estado.json` →
  `PYTHONIOENCODING=utf-8 python -I auto\planejar.py` (OK/BLOQUEADO + scripts em `run\`: `<id>_1_remover_NN`,
  `<id>_2_up_NN`, `<id>_3_area`, `<id>_4_verificar`) → rodar na ordem, um por vez → `browser_evaluate` do `__autoVer`
  → `python -I auto\finalizar.py <id>` (registra em `registro\` e renomeia a pasta para **SUBIDO**) → no fim
  `finalizar.py --soltar`.
- Para rodar já, sem esperar 15 min: `run_scheduled_task plantas-ok-spotsys` (= "Executar agora") ou seguir os passos aqui.
- Teste sem alterar nada: `python -I auto\scan.py --teste "<pasta>"` + estado + planejar (não rodar os scripts).
- Pasta bloqueada/falha fica em `auto\out\avisados.json` e não é reavisada até os arquivos mudarem.
- A Bianca move as pastas SUBIDO para `plantas-humanizadas-recorte\0 -SUBIDO\`; o scan só olha a raiz.
- Se a conexão cair no meio: rodar o `_4_verificar` do empreendimento para ver o que já gravou e retomar do primeiro lote
  que falta.

---

## 10. Armadilhas já vistas

| Sintoma | Causa / o que fazer |
|---|---|
| MCP não conecta (`initializeServer` timeout) | aba com renderizador travado — achar via CDP e pedir para fechar |
| `ECONNREFUSED 127.0.0.1:9222` | Chrome Claude fechado — pedir para abrir pelo atalho |
| `ReferenceError: window is not defined` | código de página fora do `page.evaluate` (run_code roda no Node) |
| imagem gravada mas unidade sem planta | `vistas-unit-images/bulk` falhou (CORS/rede) — reenviar só aquela |
| × removeu mas script diz "AINDA APARECE" | lista lenta — o script atual espera 10 s |
| confirm intercepta e a chamada volta antes | usar a troca de `window.confirm` (§4) |
| Python `TypeError '<' str/int` ao ordenar | chave de ordenação mista (L1 × 101) — `comum.chave` já trata |
| `UnicodeEncodeError` no Windows | rodar Python com `PYTHONIOENCODING=utf-8` |
| contagem da seção não bate na hora | atraso de render — conferir pela API, não pelo contador |
| chamadas dependentes no mesmo bloco | não fazer: o arquivo pode não existir ainda quando o Python lê |
| página do SpotSys em branco, `waitForRequest` estoura | deploy novo: o HTML em cache pede `assets/index-*.js` que não existe (404). Recarregar com cache desligado (CDP `Network.setCacheDisabled`) |
| script com `\n`/regex quebra (`SyntaxError`) | gerado por heredoc no bash: as barras somem. Escrever o .js com Python a partir de arquivo, usar `String.fromCharCode(10)` e conferir com `node --check` |
| `browser_run_code_unsafe` "File access denied" | o arquivo tem que estar dentro de `1. ALTERANDO SPOTSYS PELO NAVEGADOR\` (o scratchpad não serve) |
| Google pede "Confirme que é você" | login com senha: pedir para a Bianca fazer na aba do Chrome Claude |
| clique no Google Drive/Planilhas estoura ("waiting for element to be visible, enabled and stable") | usar `click({ force: true })` |
| upload no Drive: o script não volta e aparece "Modal state: File chooser" | o MCP intercepta a janela de arquivos: responder com `browser_file_upload` (só aceita arquivos dentro da pasta do projeto; copiar para uma pasta temporária lá dentro). Em 14/10 a Bianca preferiu subir ela mesma |

---

## 11. Onde está cada coisa

| Pasta / arquivo | Conteúdo |
|---|---|
| `.playwright-mcp\auto\` | fluxo automático: `comum.py`, `scan.py`, `planejar.py`, `finalizar.py`, `tpl_*.js`, `run\`, `out\` |
| `.playwright-mcp\lotes\` | receitas avulsas: `tpl2.js` (upload), `ver_tpl.js` (conferir), `area_tpl.js` (desmarcar área de todas as unidades), `area_antes.js` (área antes/depois pela API), `faltas_7.js` (quem está sem planta); `tpl.js`/`gen.py`/`gen_ver.py` são versões antigas; `m_*`, `n_*`, `r_*`, `ver_*`, `area_<id>.js` são gerados e descartáveis |
| `.playwright-mcp\plantas_area\` | área desatualizada da aba Plantas: `tpl.js` + `antes_*.json` (estado antes de 09/10) |
| `.playwright-mcp\layout\` | comparação de layout (`layout.py`, `decisoes.py`), planta com mezanino (`juntar_mezanino.py`, `preparar_mezanino.py`), `tpl_area_marcar.js`; scripts gerados em `troca\` |
| `registro\<id>-<empreendimento>.md` | tudo que foi alterado por empreendimento |
| `memory.md` | estado por empreendimento, decisões e pendências |
| `compartilhar\recortar-plantas.zip` | pacote da skill de recorte para mandar a outra pessoa (= PR #1 no GitHub da Rachel) |
| `.playwright-mcp\layout\comparativo_pdf.py` | PDF comparativo de recortes (atual × versão nova), 3 unidades por página |

---

## 12. Planta com mezanino (pavimento + mezanino numa imagem só)

O SpotSys aceita **uma** planta por unidade. Para duplex, a planta da unidade vira uma imagem com o pavimento à esquerda e o
mezanino à direita (fundo branco, mesma escala, alinhados). Formato aprovado pela Bianca em 13/10. Feito em todos os
empreendimentos com mezanino (Trancoso não tem; Novo Campeche III já veio pronto do lançamento).

1. **Gerar:** `python -I layout\juntar_mezanino.py "<Empreendimento>" [unidades…] [--saida <pasta de prévia>]`
   - lê `Plantas unidades\<Emp> - X.png` + `<Emp> - X - Mezanino.png` e grava `Plantas unidades com mezanino\<Emp> - X.png`;
   - **nunca sobrescreve** (pula e avisa); passe a lista de unidades quando o empreendimento já tem arquivos;
   - `ESCALA` no topo do script, por empreendimento: `mez`/`pav` (só reduz), `alinhar: 'topo'` e `dy` por unidade (px).
2. **Conferir escala e alinhamento** antes de subir: escala por um elemento comum aos dois renders (escada, móvel, largura da
   unidade); escada com escada; terraço/deck/garden embaixo da unidade → topo; render do mezanino deslocado (Campeche, Ilha
   do Campeche) → `dy` medido unidade a unidade. Painel de revisão no scratchpad, nunca na pasta do empreendimento.
3. **Subir:** `python -I layout\preparar_mezanino.py <lista.json> <prefixo> <plano.json>` com uma **lista fechada**
   (`{"<Emp>": ["<chave do arquivo>", …]}` — só o que foi revisado) gera em `troca\` os `<prefixo>N_1_remover_NN`,
   `_2_up_NN` (8 por script) e `_3_verificar`. Rodar na ordem, um por vez. Barra: arquivos `01–29` = unidades `101–129`.
4. **Registrar** em `registro\` (unidades, spot_image_id antigos, origem, validação).

Casos especiais: Jurerê Beach 101–106 não tinham recorte do térreo — o pavimento é a planta que já estava no SpotSys
(`comparacao-layout\spotsys\`), com o mezanino reduzido 0,6675. Canasvieiras 104: o terraço grande no nível do mezanino é da
unidade (19,83 m², 40,32 m² no SpotSys).

---

## 13. Planilha de controle (Tati): `Controle_Plantas_Humanizadas.xlsx`

Drive `1uRjioSURUy1EkWUnJrmZTgJ5mlDIEHjN` (dono Arthur Sérgio), aba **Conferencia** (gid 1914425836), linha 1 = cabeçalho.
Colunas: A empreendimento · B versão do projeto · C tem mezanino · D planta do mezanino no SpotSys · E/F/G unidades, com planta,
sem planta · H lista "depende de redesenho" · I unidades com marcação de área · J pavimento com marcação · K recorte conferido
com o projeto aprovado · L recortes trocados · M motivo do redesenho. Linhas 43–44: Jurerê Spot e Penha (sem projeto executivo).

**Editar pelo Chrome Claude** (o conector do Drive não edita .xlsx):
- `context.grantPermissions(['clipboard-read','clipboard-write'])`; caixa de nome `#t-name-box` (clique com `force`),
  digitar o intervalo + Enter;
- ler: selecionar o intervalo + `Control+c` + `navigator.clipboard.readText()` (conferir a coluna A antes de colar);
- escrever: `navigator.clipboard.writeText(TSV)` + `Control+v` (cola só valores, mantém a formatação da célula);
- formatação: copiar a coluna/linha modelo e `Control+Alt+v` (colar só formato); largura: botão direito no cabeçalho →
  "Redimensionar coluna".
- **Colar só nas células que mudaram**: a Bianca edita a planilha (Trancoso e Novo Campeche III na coluna D são dela).
- Login do Google com senha: quem faz é a Bianca.
- Resposta para a Tati: curta, só o que ela perguntou, estado atual — sem citar correções do caminho (`lessons.md`).

---

## 14. Plantas de pavimento: Editar, Ordem, zoom do pin e Publicar (20/10/2026)

Regras da demanda em `memory.md` (Decisões, 20/10). Exemplo completo: Salvador (16).
- **Aba Plantas → Editar** (o botão não abre com clique normal: usar a sequência HIT). O modal não tem `role=dialog`: é o
  último `div` do `body`. Campos: Imagem (Upload/URL; "trocar a imagem substitui o arquivo desta mesma planta — os pins e a
  associação são preservados"), Título (`placeholder="Ex: Planta tipo A"`), Pavimento (texto), Pavimentos cobertos, Ordem
  (`input[type=number]`). Salvar → `POST /rest/v1/spot_image_overlays` (Supabase) com `display_order` → 200.
- **Editor do 360:** botão por pavimento; **Editar Pins** liga o modo edição (clique na planta CRIA pin — cuidado).
  Trocar de pavimento sai do modo edição: entrar de novo em cada planta.
- **Zoom do pin:** slider `role=slider` "Escala dos pins" (0,3–3, passo 0,1; 1 = 100%). Focar + `ArrowRight/Left`; cada passo
  grava sozinho: `PATCH /api/v1/portfolio360/editor/buildings/<id>/escala` `{"spot_image_id","pin_scale"}`.
- **Conferência:** `GET /api/v1/portfolio360/editor/buildings/<id>` traz `floor_plans` (`sort_order`, `pin_scale`,
  `is_outdated_area`) e `floor_plan_pins` (`spot_image_id`, `szi_unit_id`, `x`, `y`, `units.unit_number`) → cruzar com
  `spot-building-units`: cada unidade com exatamente 1 pin.
- **Publicar:** botão "Publicar" → `POST /api/v1/portfolio360/buildings/<id>/publicar` → 200, sem diálogo de confirmação.
  Estado: `GET /api/v1/portfolio360/buildings/<id>/publicacao`.
- Screenshot só funciona com a aba na frente (`browser_tabs select`); em segundo plano estoura o tempo.
- **Trocar imagem (testado no Batel 21/10):** script `.playwright-mcp/pav/tpl_trocar_imagem.js` (`__TITULO__`, `__ARQ__`; gerar
  em ASCII). O upload vai ao storage assim que o arquivo entra (`POST /storage/v1/object/spot-photos/<id>/<uuid>.png`); o modal
  mostra "Enviando..." e **Salvar clicado nessa hora é ignorado** — esperar a prévia com a URL nova e só então Salvar. Salvar →
  `POST spot_image_overlays` 200 + `PATCH spot_images?id=eq.<id>` 204 com a URL nova (a URL muda; a antiga fica no storage).
  Conferir `content-length` da URL nova = bytes do arquivo local.
- **Limite de 50 MB:** `setInputFiles` não passa arquivo > 50 MB ao Chrome (e à mão também não subiu). Converter para WEBP q92
  (Térreo do Batel: 59 MB → 6,9 MB, mesma resolução, com transparência). Arquivo de 25–30 MB demora > 30 s no `setInputFiles`:
  a chamada pode voltar com erro de tempo mas o arquivo entra — conferir o modal e a rede antes de repetir.
- **Janela escondida/minimizada** (`document.visibilityState = "hidden"`): clique e tecla "reais" não funcionam. Usar a sequência
  HIT nos botões e, no slider, `el.focus()` + `dispatchEvent(new KeyboardEvent('keydown', {key:'ArrowRight'}))` — grava igual.
- Um `waitForResponse` que sobra de uma chamada anterior pode estourar na chamada seguinte e fazer o MCP devolver erro com o
  script ainda rodando: acompanhar pela rede antes de disparar outro.
- **Pins por script (testado no Lagoa 22/10/2026), janela escondida ok:** pin = `button[data-testid=editor360-pin][data-cota=<n>]`
  com `left/top` em % da imagem (`img[alt="Planta baixa"]`). **Mover:** arrastar por PointerEvent (down no pin, move em
  window, up) → `PATCH /portfolio360/editor/buildings/<id>/floor-plan-pins/<uuid>` `{x,y}` 200 (`tpl_mover_pins.js`).
  **Criar:** clique na planta → diálogo "Novo pin na planta" → combobox "Vincular a cota" (opção `data-value="<n> (<n>)"`)
  → Adicionar → `POST …/floor-plan-pins` 201 (`tpl_criar_pins.js`). O clique em Adicionar vaza e abre um diálogo
  "fantasma" (x undefined%): fechar pelo Close, nunca Adicionar. **Apagar:** clicar no pin (seleciona) → botão
  "Apagar pin" da barra liga o modo → clicar no pin → `DELETE …/floor-plan-pins/<uuid>` 204, sem confirmação. Recarregar
  a página depois para sair do modo apagar. Botão direito no pin não abre menu por evento sintético.
  Achar o alvo: grade em % sobre a planta nova (PIL, linhas a cada 5%) e ler o ponto dentro da unidade.
- **Pins pela API (Penha 28/10/2026, recomendado para muitos pins):** o clique na planta abriu o diálogo "fantasma" (x undefined%) de novo depois de fechado e travou a criação no 2º pin. A tela grava cada pin com `POST /api/v1/portfolio360/editor/buildings/<id>/floor-plan-pins` `{"spot_image_id","x","y","szi_unit_id"}` → 201 (`szi_unit_id` = `id` de `spot-building-units`). Script: `.playwright-mcp/pav/run/30_pins_api.js` (captura os headers da página, lê os pins existentes e pula quem já tem, para no primeiro status ≠ 201). 96 pins em ~1 min.
- **Baixar do Drive** pelo Chrome Claude: abrir `https://drive.usercontent.google.com/download?id=<id>&export=download&confirm=t`
  numa aba nova; o arquivo cai em `~/Downloads` (o evento de download do Playwright não chega pelo CDP). Mover para a pasta
  do empreendimento em `plantas-humanizadas-recorte  -SUBIDO\<Emp> SUBIDO\Plantas pavimento aprovado <versão>`.

## 15. Trocar o tipo de uma imagem (foto × planta) — 27/10/2026

- Caso: imagem de planta cadastrada como `image_type = photo` + `category = external` aparece no carrossel de fotos da LP
  do marketplace (pedido do Henrique, Salvador 730).
- **A tela não tem esse campo:** Galeria do 360 → "Editar imagem" só edita Título, Ordem e Categoria (Fachada / Área comum
  interna / De uma cota). O Salvar manda `PATCH /api/v1/spot-images/<id>` com `{category, spot_building_unit_id}`.
- **Receita:** capturar os headers de uma requisição da página (§2) e mandar o mesmo PATCH com `{"image_type":"floor_plan"}`
  → 200 devolve o registro já alterado. Conferir com `GET spot-images/<id>` (`image_type`, `category`, `updated_at`).
- `GET spot-images/<id>` traz `image_type`, `category`, `url`, `associations` (prédio/unidade/capa). O filtro
  `spot-images?building_id=` **não filtra** (devolve todas as 5 mil imagens).
- Registrar no `registro\<id>-….md` (antes/depois, status do PATCH).
