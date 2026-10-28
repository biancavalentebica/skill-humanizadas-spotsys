---
name: substituir-plantas-pavimento
description: >
  Substitui as plantas de PAVIMENTO de um empreendimento no SpotSys 360 (Gerenciar empreendimento > Plantas) pelas novas
  de uma pasta (Drive ou local): troca a imagem das que existem, cria as que faltam, exclui as que sobram, acerta a ordem,
  desliga a Área desatualizada, confere e ajusta os pins no Editor do 360 (zoom 100%), confere se toda unidade tem pin e
  publica. Opera pelo Chrome Claude (MCP chrome-claude). USE quando a pessoa pedir: /substituir-plantas-pavimento,
  "substituir as plantas dos pavimentos no spotsys", "trocar as plantas de pavimento do <empreendimento>",
  "subir as plantas novas dos pavimentos", "aqui estão as plantas dos pavimentos do <empreendimento>" (com link/pasta).
  NÃO é para planta de UNIDADE (aba Por unidade) nem para vistas.
---

# substituir-plantas-pavimento

Fluxo testado no Salvador (16, feito pela Bianca em 20/10/2026), no Batel (1, pelo Claude em 21/10/2026) e no Lagoa (11, com pins por script, 22/10/2026).
Projeto de trabalho: `C:\Users\compu\seazone\processos\spotsys-navegador` (ler o `CLAUDE.md`, `lessons.md`
e o `docs/MANUAL-spotsys-360.md` §0 e §14 de lá antes de operar).

## Regras da Bianca (não perguntar de novo)

| Assunto | Regra |
|---|---|
| Empreendimento | pelo nome da pasta mãe; id em `memory.md` ou na lista de `spot-buildings` |
| Título | o do SpotSys; mudar só se precisar (ex.: arquivo "Cobertura" = planta "Rooftop"; "TERREO" = "1º Pavimento" quando ali estão as 101–1xx) |
| Planta que existe | **Editar → trocar a imagem** (mantém id, pins e associação) |
| Agrupamento mudou (ex.: "2º ao 6º" vira "2º" + "4º ao 6º") | criar **Nova planta** e **Excluir** a antiga |
| Ordem | sequência: Térreo/1º = 0, depois 1, 2, 3…, Rooftop/Cobertura por último |
| "Pavimento (texto)" e "Pavimentos cobertos" | deixar vazios |
| Área desatualizada | desligar **só nas plantas de pavimento** (não nas unidades) |
| Pins | conferir que cada unidade tem 1 pin e que ele cai na unidade com o mesmo número na planta; posicionar sozinho; **à mão** (Gerar com IA não funciona — testado 20/10) |
| Zoom do pin | **100%** (`pin_scale` 1) em toda planta com pins; Rooftop sem pins: não mexer |
| Publicar | sim, no fim (botão Publicar do Editor do 360) |
| Vistas / panoramas | fora |
| Arquivo | tamanho original; **> 50 MB não sobe → WEBP q92** (Batel Térreo 59 → 6,9 MB) |

Mostrar o plano e **esperar o OK** antes de gravar. Excluir planta = ação destrutiva: listar e esperar OK explícito.

## Antes de começar

1. Porta do Chrome Claude: `curl -s -m 5 http://127.0.0.1:9222/json/version`. Se o MCP travar em `initializeServer`, achar a
   aba travada via CDP (`/json/list` + `Runtime.evaluate` com timeout) e pedir à Bianca para fechar. Nunca fechar o navegador.
2. Ferramentas: `ToolSearch select:mcp__chrome-claude__browser_tabs,mcp__chrome-claude__browser_run_code_unsafe,mcp__chrome-claude__browser_evaluate,mcp__chrome-claude__browser_network_requests,mcp__chrome-claude__browser_wait_for`.
3. Abrir aba própria (`browser_tabs action=new`). Um script por vez; nunca duas chamadas ao navegador juntas.

Scripts: `~/.claude/skills/substituir-plantas-pavimento/scripts/`. Gerar cada um com
`python -I gerar.py <modelo> <nome> '<json>'` → sai em `<projeto>/.playwright-mcp/pav/run/<nome>.js`; rodar com
`browser_run_code_unsafe filename=<caminho absoluto>`.

## Passo a passo

### 1. Arquivos novos
- Drive: listar a pasta (`search_files parentId = '<id>'`), imprimir `file_id | nome | tamanho` e copiar os ids de lá.
  Baixar pelo Chrome: `tpl_baixar_drive.js` (`__IDS__`) → arquivos caem em `~/Downloads` → mover para
  `C:\Users\compu\seazone\processos\plantas-humanizadas\recorte\0 -SUBIDO\<Emp> SUBIDO\Plantas pavimento aprovado <versão>\`
  e conferir tamanho = Drive.
- Arquivo > 50 MB: gerar `.webp` q92 ao lado (PIL `save(..., 'WEBP', quality=92)`; WEBP aceita até 16383 px por lado).

### 2. Estado atual (só leitura)
- `tpl_estado.js` (`__ID__`) → resumo: plantas (id, título, ordem, zoom, área, pins), unidades, sem pin, repetidas, publicação.
- Salvar: `browser_evaluate "() => JSON.stringify(window.__estado)" filename=<projeto>/.playwright-mcp/pav/<id>_estado_antes.json`.
- A tabela da aba Plantas também lista plantas de unidade ("(sem título)", 0 pins): ignorar. As de pavimento são as do editor.

### 3. Plano
- Casar cada arquivo com uma planta (pelo nome do pavimento e pelas unidades que os pins dela cobrem).
- Prévia dos pins: `python -I pins.py <estado_antes.json> <pasta> <mapa.json>` com `{"<spot_image_id>": "<arquivo novo>"}` →
  `pins_<id>.jpg` com os pins atuais sobre a planta atual e a nova. Se o enquadramento mudou, os pins saem do lugar.
- Mostrar à Bianca uma tabela: planta | arquivo | ação (trocar/criar/excluir) | ordem | área | zoom | pins — e as imagens.
  Esperar o OK.

### 4. Executar (um script por vez, conferir cada retorno)
1. **Trocar imagem**: `tpl_trocar_imagem.js` (`__TITULO__`, `__ARQ__`), uma planta por chamada. Ele espera o upload
   ("Enviando...") terminar antes de Salvar — Salvar durante o envio é ignorado. Confere `PATCH spot_images` 204.
   Depois: `curl -sI <url nova> | grep -i content-length` = bytes do arquivo local.
   - Se a chamada voltar com erro de tempo (arquivo de 25–30 MB), o arquivo pode ter entrado mesmo assim: olhar o modal
     (`browser_evaluate` no último `body > div`) e a rede (`browser_network_requests filter=storage/v1/object|spot_images`)
     antes de repetir. Se a prévia já mostra a URL nova, só falta clicar em Salvar (conferindo o título do modal).
2. **Nova planta / Excluir** (agrupamento mudou): ainda não automatizado. Na primeira vez, abrir o modal "Nova planta",
   ler os campos, mostrar à Bianca e fazer junto; depois virar script. Excluir só com OK explícito.
3. **Ordem e Área**: `tpl_ordem_area.js` (`__ORDEM__` = {título: ordem} de todas as plantas de pavimento,
   `__AREA__` = [títulos]). Confere `POST spot_image_overlays` 200.
4. **Zoom**: `tpl_zoom.js` (`__TITULOS__` = plantas com pins). Funciona com a janela escondida. Confere `PATCH …/escala` 200.
5. **Pins**: reler o estado (`tpl_estado.js`, salvar `_estado_depois.json`) e desenhar sobre as imagens no ar:
   `python -I pins.py <estado_depois.json> <pasta>` → olhar cada `pins_<id>.jpg`: o pin tem que cair na unidade com o mesmo
   número (planta tipo: grupo de pins dos vários andares dentro da unidade do mesmo final).
   - Pin fora do lugar: `tpl_mover_pins.js` (`__TITULO__`, `__MOVER__` = {cota: [x%, y%]}) → PATCH floor-plan-pins 200.
   - **Muitos pins (planta tipo, empreendimento sem pins): pela API** — `POST /api/v1/portfolio360/editor/buildings/<id>/floor-plan-pins`
     `{"spot_image_id","x","y","szi_unit_id"}` → 201, um por vez, pulando quem já tem pin (modelo pronto:
     `<projeto>/.playwright-mcp/pav/run/30_pins_api.js`, Penha 28/10: 96 pins em ~1 min). Posição: centro do recorte da unidade
     (`plantas-humanizadasecorte\<Emp>\configs\*.json`) conferido com o print da Bianca; planta tipo = grade 4+3 (±1,2/3,6% x, ±2,2% y).
   - Unidade sem pin (poucas): `tpl_criar_pins.js` (`__TITULO__`, `__CRIAR__` = {cota: [x%, y%]}) → POST 201. Para se a cota já tem pin
     naquela planta. Pin na planta errada: apagar (selecionar pin → "Apagar pin" → clicar no pin → DELETE 204; ainda à mão,
     manual §14) e depois criar na certa. Alvos: grade em % sobre a planta nova (PIL). Detalhes no manual §14.
6. **Publicar**: `tpl_publicar.js` (sem diálogo). Confere `POST …/publicar` 200 e "Publicado em …".

### 5. Conferência final (obrigatória)
- `tpl_estado.js` de novo: toda unidade com exatamente 1 pin, ordem em sequência, zoom 1 nas plantas com pins, área
  desligada, publicação com a data de agora.
- Dizer na entrega: imagens conferidas por bytes; pins conferidos visualmente pela posição sobre a planta.

### 6. Registrar
- `registro/<id>-<empreendimento>.md`: data, pedido, antes (ids, ordem, zoom, área, URLs), o que mudou (rede e status),
  depois, origem dos arquivos, conversões, publicação.
- `memory.md`: linha do empreendimento / decisão nova. Erro novo → `lessons.md`. Receita nova → manual §14 e esta skill.

## Armadilhas já vistas

| Sintoma | O que fazer |
|---|---|
| `setInputFiles: Cannot transfer files larger than 50Mb` | converter para WEBP q92 (à mão também não sobe) |
| Salvar não grava, imagem da linha igual | clicou durante "Enviando..."; esperar a prévia com URL do storage |
| `document.visibilityState = "hidden"` (janela minimizada) | cliques pela sequência HIT e teclas por `dispatchEvent` (os scripts já fazem) |
| erro de `waitForResponse` "sobrando" na chamada seguinte | o script novo pode estar rodando: acompanhar pela rede antes de disparar outro |
| botão Editar não abre com clique normal | sequência HIT (pointerdown→mousedown→pointerup→mouseup→click) |
| modal "Editar planta" não aparece como `role=dialog` | é o último `div` do `body` |
| screenshot estoura o tempo | aba em segundo plano: `browser_tabs select` antes |
| criar pin pelo clique trava no 2º ("dialogos validos = 0", janela "x undefined%" aberta) | o diálogo fantasma reabre; recarregar a página e criar pela API (passo 5) |
| arquivo novo idêntico ao que está no ar (md5) | não trocar imagem; corrigir só título/ordem/área/pins (Penha 28/10: "Térreo" mostrava o 3º pav) |
| download do Drive "não chega" | o arquivo vai para `~/Downloads`, não para o evento do Playwright |
