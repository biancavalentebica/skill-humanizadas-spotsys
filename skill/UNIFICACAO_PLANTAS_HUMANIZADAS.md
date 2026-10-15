# Unificação das três skills de plantas humanizadas

Situação em 14/10/2026: proposta, ainda não combinada com a Raquel e com o Arthur.

| Skill | Repositório | Foco |
|---|---|---|
| **Atualização pelo aprovado** (esta) | `rachelsouto-source/skill-humanizadas-spotsys` | gerar a planta do pavimento do **projeto aprovado** a partir do arquivo técnico; conferir áreas, SpotSys e pins |
| **plantas-humanizadas** (Raquel Tavares) | `seazone-tech/plantas-humanizadas` | recorte por tipologia, cotas do PDF, texto/capacidade/solar (PNG + PSD) a partir do render do D5 |
| **Planta Viva** (Arthur) | `seazone-tech/szi-planta-humanizada`, PR #2 | bot que vigia o Drive, **deforma a humanizada de lançamento** para o projeto novo, painel, comparativo, ciclo de vida, planilha de áreas |

| **Humanizada do projeto aprovado** (Carol Montedo) | local, `humanizadas-lancamento/salvador-spot` (não versionado) | desenho vetorial do Projeto Legal aprovado (R10 conferido com a R11 assinada) com mobiliário vetorial nas medidas do manual Spot; só `UNIDADE nnn`; pavimentos, andares e 66 recortes para o 360 (Salvador Spot, 13–14/10/2026) |

A Carol chegou ao mesmo princípio desta skill: **geometria do vetor aprovado + estilo do lançamento, sem IA**. Diferenças: ela desenha os móveis em vetor (manual Spot: cama 2,00 × 1,60, copa 0,55, poltronas 0,62 × 0,72), com regras de layout ("cama na lateral do banheiro, copa na oposta", "louça em todo sanitário", "jardineira inteira") e checagem automática antes do render. Aqui os móveis são as imagens recortadas do lançamento, posicionadas pelos blocos do DWG. **Pendente:** ela publicar o código num repositório da `seazone-tech` para incorporar as regras de layout e a checagem.

A Raquel e o Arthur já convergiram em jul/2026: a Planta Viva usa a engine de texto/capacidade/solar da Raquel (`gerar_humanizada.py`).

## O que cada uma faz melhor

| Etapa | Melhor hoje | Por quê |
|---|---|---|
| Vigiar versões novas, painel, aprovar/pedir ajuste, ciclo de vida, publicação | **Planta Viva** | bot por hora, painel local, encerra obras entregues e inclui lançamentos novos sozinho |
| Fonte do projeto aprovado | **Esta skill** | Autodoc, versão assinada (2.1.c.a). A Planta Viva pega a versão mais recente do **Drive** (Legal/Executivo/Anteprojeto), que pode não ser a aprovada |
| Conferir se o arquivo base é o aprovado | **Esta skill** | `confere_areas_base_x_aprovado.py`: áreas do DWG × PDF aprovado, unidade por unidade |
| Mudança pequena (área, parede andando 5 cm–1 m, unidade mais rasa) | **Planta Viva** (deformação) | mantém o render de lançamento idêntico, só move paredes |
| Mudança de layout/topologia (banheiro novo, unidade que mudou de lugar, mezanino reorganizado) | **Esta skill** (render do DWG) | Na Planta Viva a IA do Hub tirou nota 2–4/10 (louça "derretida", parede faltando) e o trecho vai para revisão manual de 15–30 min no Photoshop. Aqui o trecho é desenhado do DWG com o acabamento do lançamento, sem IA |
| m² vindos do DWG | **Esta skill** | lê as zonas de cálculo de área com o número e o m² do arquiteto. A Planta Viva marca "m² ESTIMADO (±0,5)" quando o DWG legal não traz contorno de área |
| Recorte por tipologia | **Raquel** | corte reto, parede inteira, nome padrão; aqui as sementes saem automáticas do DWG (`gera_cfg_recorte.py`) |
| Cotas | **Raquel** | valor do PDF cotado, nunca medido na imagem |
| Texto, capacidade, solar | **Raquel** (já usado na Planta Viva) | padrão Novo Campeche II |
| SpotSys / 360 / pins | **Esta skill** + planilha da Planta Viva | pins por `szi_unit_id`, trava de QC |

## Fluxo unificado proposto

1. **Bot (Planta Viva)** detecta a versão nova e abre o pedido no painel.
2. **Fonte do aprovado = Autodoc** (esta skill, regra 1). O bot passa a ler o PDF assinado do Autodoc como referência, não a versão mais recente do Drive.
3. **Arquivo base aprovado** (DWG/IFC/RVT). Antes de usar, **conferência de áreas com o PDF aprovado** (esta skill, regra 4). No levantamento de 14/10, 11 de 19 Spots com modificação têm arquivo base no Autodoc (`01_diagnostico/ARQUIVO_BASE_AUTODOC_19_SPOTS.md`).
4. **Classificação por unidade** (Planta Viva já faz: igual / só área / mudou formato / nova / removida):
   - igual ou só área → **deformação** da humanizada de lançamento (Planta Viva);
   - mudou formato ou layout → **render a partir do DWG** com o acabamento do lançamento (esta skill), colado no lugar da unidade;
   - pavimento reorganizado (ex.: mezanino do Cachoeira) → pavimento inteiro renderizado do DWG.
5. **Revisão automática** (Planta Viva: materiais, paredes) + **conferência de paredes × divisas do aprovado** (esta skill).
6. **Recorte por tipologia, cotas, texto/capacidade/solar** (Raquel). As sementes e a posição de cada unidade saem do DWG.
7. **Painel: aprovar ou pedir ajuste** (Planta Viva).
8. **Planilha de áreas + pins do 360 + SpotSys** (Planta Viva + esta skill).

## Testes já feitos

- **Esta skill + Raquel (14/10, Cachoeira, 2º pav.):** planta do DWG (45 s) → `cfg` automático (8 s) → recorte da Raquel → **22 de 22 unidades** (~8 min), sem marcação manual. Pendências: sacada no recorte e granito do vizinho na borda.
- **Planta Viva (12–13/10, Novo Campeche II):** deformação funcionou para mudanças de área e paredes. A IA reprovou nas mudanças de layout (101/106 deixaram de ser PCD; bar do rooftop).

## Teste unificado das 3 skills (14/10/2026, Cachoeira, 6 pavimentos)

Executor: `skill/scripts/roda_unificado.py skill/exemplos/cachoeira-spot_unificado.json`. Total **2.990 s (~50 min)**, sem marcação manual.

| Pavimento | Planta (esta) | Recorte (Raquel) | Texto/capac./solar (Raquel) | Tipologias + solar (Arthur) |
|---|---|---|---|---|
| 2º | 44 s | **22/22** (6 min) | sim (10 s) | sim |
| 3º | 43 s | **20/20** (6 min) | — | sim |
| 4º | 46 s | **20/20** (16 min) | — | sim |
| Cobertura | 92 s | **7/7** (4 min) | — | sim |
| Mezanino | 90 s | 12/18, dos quais 2 errados (111, 114) | — | sim |
| Térreo | 85 s | 12/18 | — | sim |

- **Pavimentos 2 a 5: 69 de 69 unidades** recortadas, com planta de tipologias, estudo solar e texto (2º).
- **Térreo e mezanino:** o DWG escreve "APTO" e "MEZANINO" sem número. O número vem da etiqueta do PDF aprovado e falhou em 102, 105, 109, 111, 113 e na loja L3. Os mezaninos das lojas também ficaram de fora. Alguns recortes do térreo pegaram duas unidades (103).
- **Tipologias:** a aba do Projeto Legal na planilha "Tipologias - Cachoeira Spot" não tem letras. Os arquivos saem como `GRUPO Gnn (unidades) - SEM COTA.png` até alguém definir as letras.

## Próximo teste sugerido

**Cachoeira Spot na Planta Viva**: o JSON do Cachoeira já existe no repositório do Arthur, com `ativo: true` e `lancamento_conferido: false`.
- Rodar a deformação nos pavimentos tipo, onde a mudança é pequena.
- Usar o render do DWG desta skill no **mezanino e no térreo**, onde a topologia mudou.
- Comparar as duas saídas com o PDF aprovado R06.

Esse teste precisa ser feito com o Arthur, porque o bot depende do Revit, do AutoCAD e do Drive montado na máquina dele.

## Regras que valem para as três

- O projeto aprovado vem do **Autodoc** (versão assinada).
- O arquivo base precisa ter **as mesmas áreas** do PDF aprovado.
- **IA não define geometria.** Mudança de layout sai do arquivo técnico; a IA só pode entrar como revisora.
- Cota é o valor do arquiteto, nunca medida na imagem.
- Originais do Drive nunca são alterados; a saída vai para pasta nova.
- Aprovação humana no painel antes de publicar.
