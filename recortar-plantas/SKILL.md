---
name: recortar-plantas
description: >
  Recorta cada unidade de uma planta humanizada de pavimento (tipo, rooftop, garden, mezanino...)
  em uma imagem separada por unidade, com fundo branco, sem girar, na resolução original,
  incluindo varanda/terraço/sacada/garden da unidade e apagando os textos de área (m²) mas
  mantendo a numeração. Ignora áreas comuns (piscina, lazer, circulação). Aceita PNG/JPG e PDF.
  USE quando a pessoa pedir: /recortar-plantas, "recorta as unidades da planta",
  "uma imagem por unidade", "separar as plantas das unidades", "cortar a planta do tipo/rooftop",
  "planta de cada unidade para o book/tabela de vendas/site/Spotsys", "juntar a planta do mezanino com a do
  pavimento numa imagem só".
---

# recortar-plantas

Transforma a planta humanizada de cada pavimento em **uma imagem PNG por unidade**.
Padrão aprovado em out/2026 e já aplicado em Novo Campeche, Urubici, Santo Antônio,
Foz, Caraguá, Imbassaí e Santinho. Opcional: juntar pavimento + mezanino numa imagem só (seção 6).

## 1. Padrão de entrega (não precisa perguntar de novo)

### Nome do arquivo
`<Nome do empreendimento> - <número>.png`, com o nome da pasta do empreendimento.

| Situação | Exemplo de nome |
|---|---|
| Unidade comum | `Urubici Spot - 201.png` |
| **Planta tipo** (uma planta vale para vários pavimentos) | `Foz Spot - 101 - 701.png` (do 1º ao último pavimento do tipo) |
| Rótulo da planta já traz o intervalo ("401 - 501") | `Caraguá Spot - 401 - 501.png` (use o texto do rótulo) |
| **Mais de um bloco/torre** | `Santinho Spot - 101 A.png`, `Santinho Spot - 101 B.png` |
| **Duplex com mezanino**: parte de baixo | `Santinho Spot - 101 A.png` |
| **Duplex com mezanino**: mezanino | `Santinho Spot - 101 A - Mezanino.png` |
| **Unidade dupla** (ocupa 2 posições da planta) | uma imagem só com o espaço todo: `Urubici Spot - 105.png` |

No config: `"nome": "<Empreendimento> - {id}.png"`, e a chave da unidade é o resto
(`"101 - 701"`, `"101 A"`, `"101 A - Mezanino"`).

### Onde salvar
- Imagens: **uma única pasta** `<pasta do empreendimento>\Plantas unidades\`, **sem subpasta por
  pavimento** (todos os pavimentos juntos).
- Configs: `<pasta do empreendimento>\configs\<pavimento>.json` (+ o script `s_<pav>.py` que gerou,
  se usou o `config_helper`). Eles permitem gerar tudo de novo se a planta mudar.
- Arquivos temporários (grades, montagens, OCR) ficam na pasta de rascunho da sessão, nunca na pasta do empreendimento.

### Conteúdo da imagem
- **Sem girar.** A unidade fica na posição da planta, com fundo branco fora do contorno.
- **Contorno pelo meio das paredes**, incluindo varanda, terraço, sacada e garden **da unidade**.
  Ficam de fora as áreas comuns (circulação, piscina, lazer, lojas, hall, lixeira, bicicletário),
  os jardins externos e a rosa dos ventos.
- **Apagar todo texto de área**: "20,30 m²", e também as linhas **inteiras** de
  "S. 301 B 2,54 m²", "T. UN 506 12,8 m²", "VRN 5,48 m²", "Garden 7,29 m²".
- **Manter a numeração** ("UN 201 B", "UNIDADE 308", "210 a 410").
- **Resolução original.** Nunca ampliar com resize (foi reprovado como "qualidade péssima").

## 2. Antes de começar (1 mensagem para a pessoa)
Olhe **todas** as plantas da pasta (grade geral de cada uma) e confirme num quadro:
- quais arquivos são quais pavimentos (**o nome do arquivo nem sempre bate**: no Santinho o
  `01P-BLB` era o mezanino do 2º e o `1SB-BLB-002` era o 1º pavimento);
- se há **planta tipo** e quais pavimentos ela cobre;
- se há **blocos** e **mezaninos** (duplex) e quais unidades os têm;
- arquivos que podem ser ignorados (ex.: mesma planta mostrando o estacionamento);
- o que for dúvida (área técnica? terraço de quem?).

Se tudo bater com o padrão acima, não pergunte de novo sobre nome e pasta.

## 3. Entrada: formato e resolução
```bash
python -c "from PIL import Image; Image.MAX_IMAGE_PIXELS=None; im=Image.open(r'PLANTA.png'); print(im.size, im.mode)"
```
- **PNG/JPG com ≥ 4000 px de largura:** ótimo. Recorta direto.
- **PNG pequeno (~2000–4000 px):** procure versão maior em Downloads/pasta do empreendimento.
  Não achou: **pergunte**. No Santo Antônio quem pediu escolheu "recorta assim mesmo"
  (imagens de ~150–480 px). IA (`"ampliar_ia": true`) só se a pessoa pedir, porque a nitidez fica limitada.
- **PDF:** converta antes:
  ```bash
  python scripts/pdf_para_png.py PLANTA.pdf 300
  ```
  Se houver imagem embutida grande (render), ela sai na resolução original (`_p1_imagem.png`).
  Senão, a página é rasterizada a 300 dpi (`_p1.png`). **Se o PDF for prancha técnica (desenho de
  linha, não humanizada), avise e pergunte** se recorta assim ou se existe a humanizada.
  No Barra Spot (out/2026) quem pediu mandou recortar a prancha assim mesmo. Como o PDF é vetorial, o
  `exemplos/s_pdf.py` (do Barra Spot) apaga as linhas de área **no próprio PDF** (redação só de texto), não desenha as
  folhas das jardineiras (traços verdes) e rasteriza cada desenho a 420 dpi: resultado limpo, sem borrão.
  Deixe a área do recorte (clip) com folga além da fachada: na 1ª vez cortou 4 unidades.
- **Transparência:** o que é transparente na planta é cortado sozinho. Planta sem
  transparência (jardim renderizado em volta) exige contorno colado na face externa da parede.

## 4. Arquivos da skill

| Arquivo | Para que serve |
|---|---|
| `scripts/grade.py` | Grade de coordenadas (visão geral, zoom, conferir o config com `--config`) |
| `scripts/paredes.py` | Acha o centro das paredes pelo perfil de pixels escuros (`v y0 y1 [x0 x1]` / `h x0 x1 [y0 y1]`) |
| `scripts/recortar.py` | Lê o config, apaga os textos e recorta (+ `--folha` de conferência) |
| `scripts/plantas.py` | Funções comuns (frame de trabalho, rotação exata, máscaras) |
| `scripts/pdf_para_png.py` | PDF → PNG (imagem embutida ou página rasterizada) |
| `scripts/ocr.py` | OCR da planta inteira → JSON com os textos e posições |
| `scripts/auto_apagar.py` | A partir do OCR, gera as caixas de `apagar` (m² + rótulos S./T./VRN/Garden) |
| `scripts/config_helper.py` | `salvar(...)`: monta o config com contornos + caixas do OCR (+ sufixo de mezanino, limite da laje) |
| `scripts/rodar.sh` | Recorta → corrige restos via OCR (até 3×) → limpa restos de vizinho nas bordas |
| `scripts/corrigir.py` | OCR nos recortes: o que sobrou de m² vira item novo em `apagar` |
| `scripts/limpar_bordas.py` | Apaga pedaço de rótulo do vizinho que ficou na borda (protege o rótulo da unidade) |
| `scripts/grupos.py` | Detecta grupos de letras (usado pelos dois acima) |
| `scripts/verif.py` | Lista imagens com texto de área ainda visível |
| `scripts/tem_numero.py` | Lista imagens em que o OCR não acha o próprio número (pode ser alarme falso, então olhe) |
| `scripts/painel_textos.py` | Painel 4× de cada item de `apagar` com a caixa, para medir texto |
| `scripts/conferir_textos.py` | Painel do recorte final em volta de cada item apagado |
| `scripts/montagem.py` | Junta imagens (`pasta "padrão*.png" saida.png zoom`) para revisar |
| `scripts/juntar_mezanino.py` | Junta pavimento + mezanino numa imagem só (opcional, seção 6) |
| `scripts/esrgan.py` + `modelos/RealESRGAN_x4plus.pth` | Ampliação 4× com IA (só se pedirem; o modelo não vem no pacote, ver `modelos/LEIA-ME.txt`) |
| `exemplos/rooftop.json` | Novo Campeche rooftop: ala inclinada (`angulo`, frame `r`) |
| `exemplos/urubici-04p.json` | Planta reta, unidade dupla, fonte grande (`letra_max_*`) |
| `exemplos/foz-tipo.json` | Planta tipo (ids "101 - 701") |
| `exemplos/imbassai-01p-garden.json` | Garden horizontal e vertical |
| `exemplos/santinho-mezanino-bla.json` + `_script.py` | Mezanino com bloco, gerado pelo `config_helper` |
| `exemplos/s_pdf.py` | Barra Spot: prancha PDF vetorial → PNG sem as linhas de área e sem as folhas (420 dpi) |
| `exemplos/rotulos.py` | Campeche Spot: apaga rótulo com fundo branco translúcido (texto + fundo) e refaz o piso |

Nos exemplos, `<PASTA DAS PLANTAS>` marca o caminho da pasta onde ficam as pastas dos empreendimentos: troque
pelo seu antes de usar.

Requisitos: Python com `pillow`, `opencv-python`, `numpy`, `pymupdf` (PDF), `pytesseract` +
Tesseract em `C:\Program Files\Tesseract-OCR` (OCR); `torch` só para IA.

## 5. Passo a passo

**Coordenadas:** tudo no **frame de trabalho**, que é a planta reduzida para 2000 px de largura.
`grade.py` e `paredes.py` já devolvem nesse frame.

1. **Visão geral** de cada planta: `python scripts/grade.py PLANTA.png --passo 50 --saida geral.png` (Read).
2. **Medir paredes**:
   `python scripts/paredes.py PLANTA.png v 300 320 0 2000` dá os centros das paredes verticais
   cruzando a faixa y 300–320. Faça o mesmo com `h` para as horizontais. Confirme com zoom:
   `grade.py --regiao x0 y0 x1 y1 --zoom 2 --passo 10`. **Atenção à escala**: ao ler o zoom,
   use os números da grade, não os pixels da imagem.
   Ala inclinada: meça o ângulo e use `--angulo` / frame `"r"` (ver `exemplos/rooftop.json`).
3. **Textos a apagar**:
   - Planta com poucas unidades: liste os centros à mão (`apagar`).
   - **Planta grande ou com muitos rótulos (recomendado):** OCR.
     ```bash
     python scripts/ocr.py PLANTA.png ocr_pav.json
     ```
     E monte o config com `config_helper.salvar(...)`, que junta os contornos com as caixas do
     OCR. Ver `exemplos/santinho-mezanino-bla_script.py`.
4. **Escrever o config** (`configs/<pav>.json`). Unidade = soma de polígonos (unidade + terraço, L).
   Use `laje=(x0,y0,x1,y1)` no helper para não pegar nada fora do prédio.
5. **Conferir o config**: `grade.py PLANTA.png --config configs/<pav>.json --saida c.png`. Os contornos
   têm que estar no meio das paredes e as caixas laranja sobre os textos de área.
6. **Teste com 2–3 unidades** no **primeiro empreendimento** (ou num tipo novo de planta), mande
   para a pessoa (SendUserFile) e **espere aprovação**. Depois disso, siga sem parar.
7. **Gerar**: `bash scripts/rodar.sh configs/<pav>.json`. Rode em segundo plano quando for muita coisa.
8. **Revisar sempre**:
   - `montagem.py` de cada pavimento (Read): pedaço de vizinho, shaft, grama, número cortado;
   - `verif.py` (m² sobrando) e `tem_numero.py` (número sumiu), e abra as apontadas;
   - corrija o config e rode só as unidades com problema: `recortar.py cfg.json "311 B"`.
9. **Avisar a pessoa** com a contagem por pavimento e o que ficou imperfeito (borrão em cama, etc.).
   Se ela pedir para subir parte antes do fim, **só libere o que já passou pelas checagens**.

### Opções do config
- `largura_area`, `altura_texto`: tamanho padrão da linha de área (frame de trabalho).
- `letra_max_larg` / `letra_max_alt`: tamanho máximo de letra (padrão 16 × 14; fonte grande 32 × 20).
- `limiar_escuro`: 62–65 protege paredes e móveis escuros (texto ≈ 48, parede ≈ 75).
- Por item de `apagar`: `largura`, `altura`, `vertical`, `frame`, e o modo:
  - padrão: letra por letra, procurando a melhor posição a ±10 px;
  - `"caixa": true`: tudo que é escuro e sem cor dentro da caixa exata (planta pequena);
  - `"bloco": true`: junta todas as letras encostadas (rótulo S./T. inteiro);
  - `"bloco": "linha"`: só a mesma linha, para apagar o m² sem tocar no "UN 101" de cima.

## 6. Juntar pavimento + mezanino (opcional)
**Quando usar:** o sistema de destino aceita **uma planta por unidade** (ex.: SpotSys) e a unidade é duplex.
Junta `<Nome> - 101.png` + `<Nome> - 101 - Mezanino.png` lado a lado (pavimento à esquerda, mezanino à direita,
fundo branco, vão de 40 px, margem de 20 px) em `<pasta>\Plantas unidades com mezanino\<Nome> - 101.png`
(mesmo nome da planta, para subir no lugar dela). Nunca sobrescreve: para refazer, apague o arquivo antes.
```bash
python scripts/juntar_mezanino.py --pasta "<pasta>" --saida "<rascunho>/previa"   # prévia (não toca na pasta)
python scripts/juntar_mezanino.py --pasta "<pasta>" [101 102] [--ajustes "<pasta>/configs/mezanino.json"]
```
`<Nome>` = nome da pasta (`--prefixo` troca). Sem ajustes, alinha pela base, ou pelo prédio quando os
`configs/*.json` do recorte têm as duas unidades na mesma escala. Ajustes (opcional, guarde em `configs/mezanino.json`):
```json
{"mez": 0.88, "pav": 1.0, "alinhar": "topo", "dy": {"101": 153}}
```
- `mez` / `pav`: fator ≤ 1 que **reduz** o mezanino / o pavimento (só reduz, nunca amplia).
- `alinhar`: `"topo"` ou `"base"` para o empreendimento todo.
- `dy`: por unidade, px que o topo do mezanino fica abaixo do topo do pavimento (negativo = o pavimento desce). Vale mais que tudo.

Lições:
- **Confira a ESCALA dos dois renders** por um elemento comum (escada, móvel, largura da unidade). Se for diferente,
  reduza o maior (`mez` ou `pav`). Mezanino renderizado maior já aconteceu várias vezes (até 1,65×).
- **Alinhe escada com escada.** Confira na prévia antes de gravar.
- **Terraço/garden/deck embaixo da unidade** → `"alinhar": "topo"` (pela base, o mezanino fica baixo demais).
- **Renders deslocados** (o recorte de um começa na sacada e o do outro na fachada, ou o mezanino passa por cima do
  corredor): meça o deslocamento por unidade e ponha em `dy`.

## 7. Lições (não repetir)
- **Ampliar com resize/LANCZOS + nitidez** foi reprovado; **filtro de ruído** deixa cara de pintura.
- **Girar a imagem final** suaviza. Gire só para medir.
- **Pavimentos "iguais" mudam numeração e posição de rótulo** (Urubici: 4º tinha 403 dupla).
  Confira o rótulo de cada contorno em **cada** pavimento.
- **Nome do arquivo ≠ pavimento** (Santinho). Mapeie pelo que está escrito na planta.
- **Paredes:** não chute pela grade geral, use `paredes.py` (Foz 107 pegou faixa da 108).
  Shaft/elevador invadindo o retângulo pede polígono em L (Caraguá 106/406/606).
- **Parede entre unidades pode não estar onde o rótulo sugere**: o "UN 605 B" ficou cortado porque
  a divisa estava 50 px depois.
- **Caixa grande demais apaga a numeração** (Caraguá 9º; Santinho 303/304 B, por token do OCR
  com altura errada). O `auto_apagar` já descarta tokens fora do padrão, mas confira com `tem_numero.py`.
- **Limpeza de bordas** apagou alça de hidro (preto puro) e o "B" de "UN 211 B" perto da borda.
  Já corrigido: ignora preto puro e protege a linha do rótulo principal.
- **Texto sobre cama/poltrona/tapete:** fica um leve borrão. É aceitável, mas avise.
- **Planta pequena** (Santo Antônio): use `caixa` medida no `painel_textos.py` e `limiar_escuro` 65.
- **`limpar_bordas.py` estraga unidade estreita** (Cachoeira, Campeche, out/2026): borrou móveis, cabeceira,
  parede e até o "UN" do próprio rótulo. Gere com `recortar.py` + `corrigir.py` e só use o `limpar_bordas` se
  sobrar rótulo de vizinho, conferindo antes/depois.
- **Existe planta SEM texto + pasta "com texto"** (Canasvieiras, Jurerê II, Canas Beach, Bonito II, Morro das
  Pedras): recorte a SEM texto (`"apagar": []`) e use a com texto só para identificar as unidades. O enquadramento
  das duas pode ser diferente: meça sempre na sem texto.
- **Rótulo com fundo branco translúcido** (Campeche): apagar só as letras deixa um retângulo claro. Lá foi usado
  `exemplos/rotulos.py` (apaga texto + fundo e refaz o piso/deck).
- **Unidade igual a outra (mesmo layout) com recorte ruim:** dá para reaproveitar a planta da igual e apagar o rótulo
  "UN xxx" copiando o piso de cima com mesclagem (`cv2.seamlessClone`). Confira se não sobra mancha.
- **Se usar IA**: os números ficam borrados. Antes eles eram redesenhados em Arial (#373532) por cima,
  mas isso não está automatizado. Faça só se pedirem.

## 8. Modelo de IA (opcional)
A pasta `~/.claude/skills/recortar-plantas/` é autossuficiente, menos o modelo de IA (64 MB), que só serve para
`"ampliar_ia": true`. Se precisar, baixe
`https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth`
e salve em `~/.claude/skills/recortar-plantas/modelos/RealESRGAN_x4plus.pth` (e `pip install torch`).
