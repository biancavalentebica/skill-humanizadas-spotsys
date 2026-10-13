# Referências visuais e régua visual: plantas humanizadas Seazone

## Referências selecionadas

| # | Referência | Link verificável | O que aproveitar | O que NÃO copiar |
|---|---|---|---|---|
| 1 | **Visualizing Architecture – "Floor Plan Study"** (Alex Hogrefe) | https://visualizingarchitecture.com/floor-plan-study/ · imagem: https://visualizingarchitecture.com/wp-content/uploads/2015/07/Train_floor_plan_spread_1.jpg | Paredes cheias ("poché") como elemento de maior contraste. Mobiliário mínimo, só para ler a função do ambiente. Sombra leve só para separar parede de vidro. Praticamente nenhum texto. | A diagramação editorial (linhas de corte atravessando a página, composição de portfólio). |
| 2 | **Redraw – guia de planta humanizada, estilo "flat/clean"** (fonte comercial, usada só como parâmetro) | https://www.redraw.pro/en/blog/guia-prompts-plantas-humanizadas-ia | Parâmetros objetivos: paredes em preto fosco com espessura correta e bordas nítidas; móveis em branco/cinza claro sem textura realista; sombras difusas e discretas; piso liso cinza claro ou madeira dessaturada de baixo contraste. | O uso de IA generativa para **produzir** a planta. Foi o caminho da tentativa de 27/08 (49% de aproveitamento, distorções). Aqui a IA não desenha geometria. |
| 3 | **Padrão interno Seazone: humanizada "PROJETO LEGAL (10/03/26)" do Cachoeira Spot** (Raquel Tavares) e nomenclatura do Novo Campeche Spot III (`…-IMG-TER-LOJ-000-R01 - COM TEXTO` / `SEM COTA`) | Drive: `02 - Projetos/08 - Projeto Arquitetônico/04 - Plantas Humanizadas/PROJETO LEGAL (10/03/26)` · pasta NC3 `1hPG2wGp03salK_F_fg-S3BQK39XeLPJM` | É a linguagem que o time já produz e o comercial já conhece: paredes pretas, piso porcelanato claro, deck de madeira nos gardens, grama, louças e mobiliário em vista superior com sombra suave. É a base deste teste: a imagem é reaproveitada, não redesenhada. | Os textos (número, área, "S."/"G.", rótulos de ambiente), que saem na versão sem texto. |

## Régua visual única: teste Cachoeira Spot

A régua descreve o **padrão de aceite** da imagem final. Ela não autoriza alterar a arquitetura para "embelezar".

| Item | Regra |
|---|---|
| Paredes e divisórias | Preto sólido, espessura do desenho de origem. Nunca redesenhadas, deslocadas ou "limpas". |
| Portas, vãos, esquadrias | Exatamente como na humanizada de origem, conferida contra o aprovado. |
| Piso | Textura simples da origem (porcelanato claro, deck de madeira, grama). Sem novos materiais. |
| Mobiliário | Discreto, vista superior, o da origem. Não acrescentar nem remover móveis. |
| Sombras e efeitos | Só os da origem. Proibido acrescentar render, luz, reflexo ou perspectiva. |
| Texto | **Nenhum**: sem número de unidade, sem área, sem cota, sem rótulo de ambiente, sem "S."/"G.". A identificação vai no **nome do arquivo**. |
| Símbolos | Mantidos apenas os gráficos (acessibilidade, X de elevador/vazio). |
| Fundo da imagem individual | Transparente fora da unidade (PNG RGBA), com folga de 25 cm para incluir as paredes e 40 cm de margem. |
| Planta geral do pavimento | Mesmo enquadramento e resolução da origem (3840×2160 nos pavimentos tipo). |
| Escala | A imagem individual mantém a escala da planta geral (pixel a pixel). Na montagem duplex (térreo + mezanino), os dois níveis ficam na **mesma escala real**. |
| Proporção | Nunca esticar para caber num formato. A anisotropia medida contra o aprovado deve ficar entre 0,98 e 1,02. |
