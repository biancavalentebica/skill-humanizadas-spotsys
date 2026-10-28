# Processo: imagens de empreendimentos no Spotsys 360

> **Manual atualizado (09/10/2026): `docs/MANUAL-spotsys-360.md`** — receitas de upload, remoção (×), área desatualizada
> (unidade e pavimento), conferência por API e fluxo automático. Este arquivo continua valendo para Drive, planilhas e histórico.

Receita para associar plantas, vistas e imagens internas às unidades.
Baseado nas execuções de 17–18/08 e 01/10/2026.

---

## 1. Antes de começar — escolher o caminho

Há duas formas de levar imagem para o Spotsys. **Apresentar as duas à Bianca e deixar
ela escolher.** Não decidir sozinho.

```
As imagens já estão no Drive?
  ├─ Sim ................................... Fluxo A (pasta do Drive)
  └─ Não, estão na máquina dela
       ├─ Poucas (até ~10) ................. Fluxo A, se ela topar subir ao Drive
       └─ Muitas, ou perder uma sai caro ... Fluxo B (upload local)
```

| | **A — Pasta do Drive** | **B — Upload local** |
|---|---|---|
| Ação manual dela | subir os arquivos ao Drive | nenhuma |
| Modais | 1 para todas | 1 por imagem |
| Gravação | um save para o lote | um save por imagem |
| Falha típica | **parte do lote some, sem erro** | uma imagem isolada |
| Nome do arquivo | precisa conter as unidades | idem (é o que o script lê) |

**O tempo de upload não some no fluxo A** — o Spotsys copia os arquivos do Drive para
o storage dele na hora do save. O ganho do A é eliminar os modais, não o tráfego.

> Não dá para subir arquivos locais ao Drive por mim: o `create_file` do MCP exige
> o conteúdo em base64 como parâmetro, o que é inviável para arquivos de centenas de KB.
> Quem sobe ao Drive é ela, arrastando.

---

## 2. Onde ficam as coisas

Empreendimentos, pastas e estado atual: ver **`memory.md`** deste projeto.

### Planilha principal (Rateamento Projetos_PDA Imagens Comercial)

ID `1z845zO19I_Ugb6wSx4p2LrsIqvszYkmZ` — é um **.xlsx hospedado no Drive**, não um
Google Sheets nativo.

| Aba | Coluna do link | Colunas de dados |
|---|---|---|
| `🖼️ Imagens de vista` (sheet4) | **K** | B = Empreendimento, G = UNDs (códigos) |
| `📐 Plantas a gerar` (sheet3) | **M** | C = Empreendimento, H = UNDs atendidas |

Cabeçalho na linha 3, dados a partir da linha 4.

---

## 3. Extrair os links da planilha

O texto exportado pelo Drive **não traz as URLs**. Baixar o .xlsx e ler os hyperlinks
do XML: `download_file_content` → base64 (vai para arquivo em disco, por ser grande) →
decodificar → abrir como zip.

**Descobrir em que coluna estão os links** (a aba muda):

```python
from collections import Counter
Counter(re.findall(r'<hyperlink\b[^>]*ref="([A-Z]+)\d+"', sheet))
# -> {'M': 50}  → coluna M
```

```python
# -*- coding: utf-8 -*-
import zipfile, re

z = zipfile.ZipFile('planilha.xlsx')

ss = z.read('xl/sharedStrings.xml').decode('utf-8')
shared = [''.join(re.findall(r'<t[^>]*>(.*?)</t>', si, re.S))
          for si in re.findall(r'<si>(.*?)</si>', ss, re.S)]

def unesc(s):
    return (s.replace('&lt;', '<').replace('&gt;', '>')
             .replace('&quot;', '"').replace('&apos;', "'").replace('&amp;', '&'))

sheet = z.read('xl/worksheets/sheet3.xml').decode('utf-8')
srels = z.read('xl/worksheets/_rels/sheet3.xml.rels').decode('utf-8')

rel = {}
for m in re.finditer(r'<Relationship\b([^>]*)/>', srels):
    a = m.group(1)
    i = re.search(r'Id="([^"]+)"', a); t = re.search(r'Target="([^"]+)"', a)
    if i and t: rel[i.group(1)] = unesc(t.group(1))

hl = {}   # {"M4": "https://drive.google.com/file/d/..."}
for m in re.finditer(r'<hyperlink\b([^>]*)/?>', sheet):
    a = m.group(1)
    ref = re.search(r'ref="([^"]+)"', a); rid = re.search(r'r:id="([^"]+)"', a)
    if ref and rid: hl[ref.group(1)] = rel.get(rid.group(1))

rows = {}
for rm in re.finditer(r'<row[^>]*r="(\d+)"[^>]*>(.*?)</row>', sheet, re.S):
    cells = {}
    for cm in re.finditer(r'<c\b([^>]*)>(.*?)</c>|<c\b([^>]*)/>', rm.group(2), re.S):
        attrs = cm.group(1) or cm.group(3) or ''; body = cm.group(2) or ''
        ref = re.search(r'r="([A-Z]+)(\d+)"', attrs)
        if not ref: continue
        t = re.search(r't="([^"]+)"', attrs); t = t.group(1) if t else 'n'
        v = re.search(r'<v>(.*?)</v>', body, re.S)
        if t == 's' and v:      val = shared[int(v.group(1))]
        elif t == 'inlineStr':  val = ''.join(re.findall(r'<t[^>]*>(.*?)</t>', body, re.S))
        elif v:                 val = v.group(1)
        else:                   val = ''
        cells[ref.group(1)] = unesc(val).strip()
    rows[int(rm.group(1))] = cells

fid = lambda u: (re.search(r'/d/([A-Za-z0-9_-]+)', u or '') or [None, None])[1]
```

---

## 4. Nomear e organizar no Drive

| Ação | Ferramenta MCP |
|---|---|
| Renomear | `update_file(fileId, title=...)` |
| Mover | `update_file(fileId, parentId=...)` |
| Copiar | `copy_file(fileId, parentId=..., title=...)` |
| Criar pasta | `create_file(title, mimeType='application/vnd.google-apps.folder', parentId)` |
| Listar pasta | `search_files("parentId = 'XXX'")` |

### Convenção

```
Empreendimento - UND UND UND.ext          ← uma imagem para aquelas unidades
Empreendimento - UND UND - 01.ext         ← várias imagens para o mesmo conjunto
```

- unidades separadas por **espaço**, em ordem crescente
- **manter a extensão** — pegar de `fileExtension` no metadata, não do texto da célula
  (em algumas abas a célula contém a própria URL, não o nome do arquivo)
- sufixo `- 01`, `- 02` quando a mesma tipologia tem várias fotos

> ⚠️ Nome com muitas unidades estoura 255 caracteres (a tipologia A do Natal deu 334).
> No Drive funciona, mas quebra ao baixar no Windows. Se passar disso, propor o formato
> curto (`Natal Spot - Tipologia A - 01`) **antes** de renomear.

### Um arquivo que serve a várias linhas da planilha

| Contexto | O que fazer |
|---|---|
| Vistas (aba K) | mesclar os códigos num nome só |
| Plantas (aba M) | uma cópia por linha, cada uma com os UNDs daquela linha |

---

## 5. Fluxo A — pasta do Drive

```
/lancamentos/empreendimentos-360/<id>
  → aba "Por unidade"
    → seção (Plantas Baixas | Imagens Internas | Vistas da Unidade) → + Adicionar
      → Origem: "Pasta do Drive" → colar link → "Buscar imagens"
      → em cada imagem: "Unidades" → marcar → "Confirmar"
    → "Salvar (N img)"
```

O `alt` de cada `<img>` é o nome do arquivo — é dele que saem as unidades.
Depois de confirmar, o botão do card muda de `Unidades` para `N unidade(s)`,
o que serve de marcador para retomar de onde parou.

**As imagens carregam em ondas** — ao buscar, pode aparecer só parte delas.
Conferir a contagem antes de atribuir; esperar e contar de novo.

```javascript
const sleep = ms => new Promise(r => setTimeout(r, ms));
const findConfirm = () => [...document.querySelectorAll('button')]
      .find(b => /^Confirmar \(/.test(b.textContent.trim()));
const getImgs = () => [...document.querySelectorAll('img')]
      .filter(i => /^NOME DO EMPREENDIMENTO - /.test(i.alt));
const cardBtn = im => {
  let c = im.parentElement;
  for (let k = 0; k < 6 && c; k++) { if (c.querySelector('button')) break; c = c.parentElement; }
  return c.querySelector('button');
};

for (const im of getImgs()) {
  const btn = cardBtn(im);
  if (/unidade\(s\)/.test(btn.textContent)) continue;            // já feito
  const codes = im.alt.replace(/^.*? - /, '')
                      .replace(/ - \d+\.\w+$/i, '').replace(/\.\w+$/i, '').split(/\s+/);
  btn.click(); await sleep(450);
  let cb = findConfirm(); if (!cb) break;
  let root = cb;
  while (root && !root.querySelector('input[placeholder*="Buscar por"]')) root = root.parentElement;
  const chips = [...root.querySelectorAll('button')]
        .filter(b => /^\d{3,4}$/.test(b.textContent.trim()));
  codes.forEach(c => { const b = chips.find(x => x.textContent.trim() === c); if (b) b.click(); });
  await sleep(200);
  cb = findConfirm(); if (cb) cb.click();
  await sleep(400);
}
```

Processar em **lotes de 3 a 5** — o canal de execução estoura em 45s e o loop
continua rodando na página depois do erro. Não refazer: conferir o estado e retomar.

---

## 6. Fluxo B — upload local

O input é `multiple: false`: **uma imagem por modal**, e cada uma grava sozinha ao
confirmar (não existe "Salvar" geral no fim).

O `input[type="file"]` tem `class="hidden"`, então:

- `browser_click` nele falha (espera ficar visível)
- clicar na área tracejada abre o seletor nativo e trava a chamada
- `waitForSelector` precisa de `{ state: 'attached' }`

O que funciona é `setInputFiles` direto, que ignora o seletor nativo:

```javascript
async (page) => {
  const base = 'C:\\Users\\compu\\Downloads\\PASTA\\';
  const nomes = ['201 a 401.png', '202 a 402.png'];   // lotes de 5
  const HIT = `el => { const b = el.getBoundingClientRect(), cx = b.x+b.width/2, cy = b.y+b.height/2;
    const o = {bubbles:true,cancelable:true,composed:true,clientX:cx,clientY:cy,
               button:0,buttons:1,pointerId:1,pointerType:'mouse',isPrimary:true};
    el.dispatchEvent(new PointerEvent('pointerover',o)); el.dispatchEvent(new MouseEvent('mouseover',o));
    el.dispatchEvent(new PointerEvent('pointerdown',o)); el.dispatchEvent(new MouseEvent('mousedown',o));
    try{el.focus()}catch(e){}
    el.dispatchEvent(new PointerEvent('pointerup',{...o,buttons:0}));
    el.dispatchEvent(new MouseEvent('mouseup',{...o,buttons:0}));
    el.dispatchEvent(new MouseEvent('click',{...o,buttons:0})); }`;
  const press = (sel) => page.evaluate(([h, s]) => {
    const hit = eval('(' + h + ')');
    let el;
    if (s === 'add')       el = [...document.querySelectorAll('button')].filter(b => b.textContent.trim() === 'Adicionar')[0];
    else if (s === 'prox') el = [...document.querySelectorAll('button')].find(b => /Próximo/.test(b.textContent));
    else if (s === 'save') el = [...document.querySelectorAll('button')].find(b => /^Salvar \(/.test(b.textContent.trim()));
    if (!el) return false; hit(el); return true;
  }, [HIT, sel]);

  for (const nome of nomes) {
    const fin = nome.match(/^\d(\d{2})/)[1];
    const unds = ['2'+fin, '3'+fin, '4'+fin];            // ajustar à regra do caso
    await press('add');
    await page.waitForSelector('input[type="file"]', { state: 'attached', timeout: 25000 });
    await page.setInputFiles('input[type="file"]', base + nome);
    await page.waitForTimeout(2000);
    await press('prox');
    await page.waitForTimeout(2200);
    await page.evaluate(([h, u]) => {                     // 1º render: marcar
      const hit = eval('(' + h + ')');
      const chips = [...document.querySelectorAll('button')].filter(b => /^\d{3}$/.test(b.textContent.trim()));
      u.forEach(c => { const b = chips.find(x => x.textContent.trim() === c); if (b) hit(b); });
    }, [HIT, unds]);
    await page.waitForTimeout(1200);                      // deixa o React re-renderizar
    await press('save');                                  // 2º render: salvar
    await page.waitForTimeout(11000);
  }
}
```

### Marcar e salvar precisam de renders separados

Marcar os chips e clicar em `Salvar` no **mesmo** `page.evaluate` não funciona: o
handler do Salvar lê o estado antigo (0 selecionadas) e a requisição não sai. O modal
fica aberto no Passo 2 e nada grava. Vale para os dois fluxos.

### Salvar faz duas chamadas — a segunda pode falhar sozinha

Cada Salvar dispara `POST /api/v1/spot-images` (cria a imagem) e depois
`POST /api/v1/vistas-unit-images/bulk` (associa às unidades). Em 08/10 (Morro das Pedras, 216)
a primeira deu 201 e a segunda caiu com erro de CORS/rede: a imagem ficou no storage **sem
unidade** e não aparece na tela. Por isso o template atual (`.playwright-mcp/lotes/tpl2.js`)
registra o status do `bulk` e **para o lote no primeiro bulk que não for 20x**. Reenviar a
imagem resolve (a unidade continua sem planta); a cópia órfã fica no storage.

### Excluir planta: só pelo × da unidade

O card não tem botão de excluir imagem. O × ao lado do código (`button[title="Remover 101"]`) abre um
`confirm` nativo **"Remover 101 desta foto?"** e, aceito, faz `DELETE /vistas-unit-images/<id>` (204):
a unidade sai da imagem e o card some da seção. O arquivo continua no storage.

O MCP captura o `confirm` como "modal state" e devolve a chamada antes do fim do script; se o script
tiver `page.on('dialog')`, ele **continua rodando sozinho** em segundo plano. Nesse caso não disparar
nada novo: acompanhar por `browser_network_requests` (filtro `vistas-unit-images/\d+`) até acabar.
O handler deve aceitar só a mensagem exata da unidade esperada e recusar o resto (09/10, Morro das Pedras).

### "FALHOU" no log nem sempre é falha

A espera pelo fechamento do modal estoura com frequência, mas a imagem **foi gravada**.
Nunca refazer por causa do log — conferir a contagem real primeiro, senão duplica.

---

## 6b. Fluxo automático "pasta OK" (tarefa `plantas-ok-spotsys`) — DESATIVADO desde 13/10/2026

> **Desativada em 13/10/2026** (empreendimentos finalizados). Reativar só se a Bianca pedir. Plantas com mezanino:
> ver `MANUAL-spotsys-360.md` §12.

Scripts em `.playwright-mcp/auto/`, sempre nesta ordem:

| Passo | Arquivo | O que faz |
|---|---|---|
| 1 | `scan.py` | acha pastas terminando em OK; trava (`LOCK`, 3 h) contra execução dupla; gera `run/estado.js` |
| 2 | `run/estado.js` + `browser_evaluate` → `out/estado.json` | lê empreendimento, unidades, plantas e Área desatualizada pela API |
| 3 | `planejar.py` | cruza pasta × SpotSys; BLOQUEADO se nome fora do padrão, unidade inexistente, conflito de intervalo ou arquivo > 10 MB; gera `run/<id>_1_remover.js`, `_2_up_NN.js`, `_3_area.js`, `_4_verificar.js` |
| 4 | scripts `run/<id>_*` | × (só "Remover <u> desta foto?" é confirmado), upload com bulk conferido, área, conferência por API + bytes |
| 5 | `finalizar.py <id>` | registra em `registro/` e renomeia OK → SUBIDO; com `--falha` só registra; `--soltar` libera a trava |

Pasta bloqueada ou com falha fica em `out/avisados.json` e não é avisada de novo até os arquivos mudarem.
Teste sem alterar nada: `python -I scan.py --teste "<pasta>"` + estado + `planejar.py` (não rodar os scripts).

## 7. Verificação — obrigatória

O save perde imagens em silêncio, sem erro na tela. Já aconteceu três vezes:

| Caso | Enviadas | Gravadas |
|---|---|---|
| Jurerê III (42), imagens internas | 13 | 7 |
| Natal (41), imagens internas | 8 | 7 |
| Marista (28), plantas | — | precisou de lotes de 3 |

**Jeito mais seguro (08/10): pela API.** `.playwright-mcp/lotes/ver_tpl.js` + `gen_ver.py <ids>`
recarregam a página, capturam os headers de autenticação de uma requisição da própria página
(sem imprimir token) e leem `spot-building-units` e `vistas-unit-images?building_id=<id>`
(role `planta`). Devolvem por empreendimento: imagens, unidades com planta, `faltando`, `extras`
e `dup` contra a lista esperada (antes ∪ novas). Foi assim que se achou a 216 do Morro das Pedras.

Alternativa pela tela, comparando a quantidade de unidades de cada imagem com o que o nome do
arquivo diz:

```javascript
const h = [...document.querySelectorAll('*')]
      .filter(e => e.children.length === 0 && e.textContent.trim() === 'Imagens Internas')[0];
let s = h; for (let i = 0; i < 6 && s; i++) { if (s.querySelectorAll('img').length) break; s = s.parentElement; }
const imgs = [...s.querySelectorAll('img')];
imgs.map(im => { let c = im.parentElement;
  for (let k = 0; k < 5; k++) { if (c.parentElement && c.parentElement.querySelectorAll('img').length > 1) break; c = c.parentElement; }
  return [...c.querySelectorAll('button[title^="Remover "]')].map(b => b.title.replace('Remover ','')); });
```

### Descobrir qual imagem faltou

O Spotsys não guarda o nome do arquivo — mas o tamanho em bytes bate com o do Drive:

```javascript
for (const im of imgsDaSecao) {
  const r = await fetch(im.src, { method: 'HEAD' });
  console.log(r.headers.get('content-length'));
}
```

Cruzar com o `fileSize` que o `search_files` devolve. Foi assim que achamos que faltava
a imagem 03 da tipologia B do Natal (`3677032`).

---

## 8. Padrões de unidade

### Prumada (mesmo final = mesma posição)

```javascript
const alvo = alt => {
  const o = alt.replace(/^.*? - /, '').replace(/\.\w+$/i, '').split(/\s+/);
  const fin = o[0].slice(-2);
  const s = new Set(o);                         // preserva o que veio da planilha
  for (let p = 1; p <= 12; p++) s.add(String(p) + fin);
  return [...s];
};
```

**Só vale quando todos os pavimentos têm a mesma quantidade de unidades.**
No Bonito II são 8/10/10/7 cotas por andar — a regra não se aplica, as correspondências
têm que vir da Bianca. O último andar costuma ser diferente e precisa de mapa manual
(no Marista: 1301=1201, 1302=1202, 1303=1203, 1304=1210, 1305=1211, 1306=1212).

### Intervalo no nome do arquivo

`"217 a 417.png"` → 217, 317, 417 (mesmo final, pavimentos 2 a 4). Confirmar o
intervalo com ela antes de assumir.

---

## 9. Armadilhas

### Drive

- **"Requested entity was not found"** tem duas causas com a mesma mensagem:
  1. arquivo **na lixeira** — visível pelo link, mas não copiável; só o dono restaura
  2. **sem permissão** — o navegador mostra "Você precisa ter acesso"

  Diagnóstico: abrir o link no navegador (banner de lixeira × tela de solicitar acesso).
  **Conceder acesso não desfaz a exclusão** — são dois pedidos diferentes ao dono.
- Arquivo na lixeira não oferece "Fazer uma cópia" no menu Arquivo.
- `read_file_content` em imagem volta vazio. Para ver o conteúdo, abrir no navegador.
- Resultados grandes (base64 de xlsx) vão para arquivo em disco — ler de lá com Python.

### Spotsys / navegador

- **Clique em aba não funciona** com `.click()` nem com coordenada de screenshot
  (a escala do screenshot não bate com a viewport CSS). Usar a sequência `HIT` completa
  de eventos de ponteiro.
- Com a aba em segundo plano, o `click()` do Playwright trava em "waiting for element
  to be stable" (Adicionar, Próximo). `click({ force: true })` às vezes passa, mas logo
  depois de navegar o clique não abre nada. O que funcionou em 08/10 (Imbassaí, Urubici,
  Caraguá, Foz: 175 imagens sem nenhuma falha): sequência `HIT` via `locator.evaluate` em
  **todos** os botões (Adicionar, Próximo, chips, Salvar) e repetir até a tela mudar
  (`input[type=file]` existir / aparecer "Passo 2 de 2"). Lotes de 8 imagens por chamada.
  Os scripts ficam em `.playwright-mcp/lotes/` (`tpl.js` + `gen.py`).
- Script carregado por `filename` no `browser_run_code_unsafe`: usar só ASCII
  (acentos e `'\\'` quebram o parse).
- O contador da seção às vezes atrasa um save (`58->58`), mas a gravação aconteceu.
  Conferir sempre recarregando a página.
- Input controlado por React precisa do setter nativo:

```javascript
const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
setter.call(inp, valor);
inp.dispatchEvent(new Event('input', { bubbles: true }));
```

- A aba costuma **não trocar no primeiro clique** depois de navegar (hidratação).
  Conferir `aria-selected` e repetir.
- A aba "Por unidade" demora a carregar (até ~10s) e o nome do empreendimento aparece
  como "Empreendimento #N" enquanto carrega. Esperar sumir o "Carregando...".

### Dados

- Códigos com lixo: `"905 e 906"` — filtrar tokens não numéricos.
- Linhas com `—` em todas as colunas: ainda não gerada, não é erro.
- Nomes genéricos (`Frente.JPG`, `Atrás.JPG`) repetidos em pastas diferentes:
  o mesmo nome não é o mesmo arquivo. Sempre usar o **file ID**.
- Um arquivo linkado em linhas com **faces diferentes** costuma ser erro de
  preenchimento da planilha — sinalizar, não corrigir por conta.
- Checar se a seção já tem conteúdo antes de adicionar, para não duplicar.
  Em Plantas Baixas a tela avisa: *"Planta é única por unidade — adicionar para uma
  unidade que já tem planta substitui a anterior."*

---

## 10. Checklist

1. [ ] **Oferecer os dois caminhos e deixar a Bianca escolher**
2. [ ] Identificar a aba e a coluna dos links na planilha
3. [ ] Extrair `empreendimento | unidades | url` e resolver os file IDs
4. [ ] Conferir: linhas sem link, arquivos repetidos, nomes finais duplicados
5. [ ] Buscar metadata (extensão real, dono, se está acessível)
6. [ ] **Mostrar o plano `nome atual → novo nome` e confirmar antes de executar**
7. [ ] Renomear / copiar para a pasta do empreendimento
8. [ ] Ver o que a seção já tem no Spotsys, para não duplicar
9. [ ] Carregar as imagens e conferir se vieram todas (carregam em ondas)
10. [ ] Validar que todos os códigos existem nos chips
11. [ ] Atribuir as unidades, em lotes de 3 a 5
12. [ ] Conferir `N unidade(s)` × quantidade de códigos no nome
13. [ ] **Confirmar antes de Salvar**
14. [ ] **Conferir a contagem depois de salvar** — o lote perde imagem em silêncio
15. [ ] Dizer que a validação foi por nome, não por conteúdo
