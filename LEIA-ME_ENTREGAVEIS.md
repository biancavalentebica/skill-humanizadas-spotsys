# Desafio: atualização de plantas humanizadas (SpotSys), teste Cachoeira Spot

Situação em 13/10/2026. Prazo: 13/10/2026. Nada foi publicado no SpotSys, no 360 ou no Drive.

## Entregáveis

| # | Entregável | Arquivo |
|---|---|---|
| 1 | Diagnóstico das divergências | [01_diagnostico/DIAGNOSTICO_CACHOEIRA_SPOT.md](01_diagnostico/DIAGNOSTICO_CACHOEIRA_SPOT.md) + `comparativo_areas_spotsys_x_aprovado.csv` + `conferencia_spotsys_x_pdf_aprovado.csv` |
| 2 | Referências visuais e régua visual | [02_referencias_visuais/REFERENCIAS_E_REGUA_VISUAL.md](02_referencias_visuais/REFERENCIAS_E_REGUA_VISUAL.md) |
| 3 | Plantas humanizadas (geral por pavimento + 1 por unidade) | [04_saida/CACHOEIRA-SPOT_R04/](04_saida/CACHOEIRA-SPOT_R04/) |
| 4 | Relatório de QC e pendências | [04_saida/CACHOEIRA-SPOT_R04/03_CONFERENCIA/QC_RELATORIO.md](04_saida/CACHOEIRA-SPOT_R04/03_CONFERENCIA/QC_RELATORIO.md) + `qc_unidades.csv` + folhas de contato + [05_qc/registro_R04/](05_qc/registro_R04/) (sobreposições aprovado × humanizada) |
| 4b | Apresentação da evolução | https://claude.ai/artifact/Sh7XUZMALMNLqVAbq1n6gQ |
| 5 | Skill documentada | [skill/SKILL.md](skill/SKILL.md) + `skill/scripts/` |
| 6 | Régua de decisão para mudanças futuras | [skill/SKILL.md, seção K](skill/SKILL.md) |
| 7 | Limitações, riscos e validação humana | abaixo + [skill/SKILL.md, seção I](skill/SKILL.md) |

## Alinhamento com o método do Fernando (thread de 06/10)

| Pedido | Status |
|---|---|
| Case Cachoeira (lançamento × aprovado) | Feito. O diagnóstico mostra 82 de 87 unidades alteradas entre o lançamento e o aprovado. |
| Estilo desenho técnico humanizado | **Adiado (decisão de 12/10).** Para terça, o render 2026 sem texto, já fiel ao aprovado. O estilo técnico a partir do DWG está em `skill/SKILL.md`, seção L. A estilização do raster foi testada e rejeitada: deforma o mobiliário. |
| Sem texto de área; uma planta por unidade e uma por pavimento | Feito: 6 pranchas e 87 unidades. |
| Ponta a ponta, sem validação no meio | Feito: `python skill/scripts/roda_pipeline.py skill/exemplos/cachoeira-spot.json` roda tudo sem parada. **Ajuste de 13/10: validação humana obrigatória antes da carga.** O pacote sai como `AGUARDANDO_VALIDACAO` com `VALIDACAO_HUMANA.csv`; só as unidades validadas (com validador e data) entram nos pins e no manifesto. |
| Atualizar o 360 e refazer os pins | Pacote pronto: `04_PUBLICACAO/pins_360.json` (polígonos 0–1 por `szi_unit_id`) + `manifesto_publicacao.csv`. A **carga** depende de acesso de escrita ao SpotSys/360, que não existe neste ambiente. |
| Tempo de cada etapa | Tabela abaixo (`03_CONFERENCIA/tempos_etapas.csv`). |

## Tempo de cada etapa (execução R04, 6 pranchas, 87 unidades)

| Etapa | Tempo |
|---|---|
| Rótulos e áreas do aprovado × SpotSys + quadro | 15,7 s |
| Remoção de texto | 33,8 s |
| Células das unidades no aprovado | 47,2 s |
| Registro aprovado × humanizada | 114,8 s |
| Recortes por unidade + plantas gerais | 69,2 s |
| Folhas de contato + QC | 12,5 s |
| Trava QC + pacote + pins + planilha de validação | 0,3 s |
| **Total automatizado** | **293 s (~4,9 min)** |

Fora do script: download do Drive, consulta ao SpotSys e o tempo da validação humana.

O desenvolvimento e a calibração do método (diagnóstico, ajustes dos detectores) não entram nessa conta. Num novo empreendimento, o tempo humano previsto é a configuração (páginas do PDF e janela do mezanino, se houver) mais a revisão das folhas de contato.

## O que mudou na R04 (13/10)
- **Recorte preciso:** o corte agora encaixa nas paredes reais da humanizada (face externa), sem paredes e móveis do vizinho e sem cantos arredondados. 87/87 unidades encaixaram.
- **Sem "fantasma" de texto:** em fundo liso, o preenchimento usa acerto de tom; louças e granito não são mais confundidos com texto; resto de rótulo sobre fundo transparente removido.
- **Validação humana obrigatória** antes da carga (ver acima).
- **Mais rápido:** QC de ~2 min para 5 s.

## Resultado do teste (números do QC)

| Indicador | Total |
|---|---|
| Unidades identificadas (SpotSys) | 87 |
| Unidades processadas | 87 |
| Unidades conferidas | 87 |
| Aprovadas | 58 |
| Aprovadas com ressalva | 24 |
| Pendentes | 5 |
| **No pacote, aguardando validação humana (com pins)** | **58** |

- **Imagens gerais geradas:** 6 de 6 (térreo, mezanino, 2º, 3º, 4º e rooftop).
- **Pendentes (5):** 108 e L3 (faixas sem divisa no aprovado); 505, 506 e 507 (o rooftop da humanizada 2026 diverge do aprovado no lado direito: posição dos quartos 506/507). Para essas três, corrigir a humanizada (nível 2/3 da régua).

## Precisa de decisão ou validação humana

0. **Projeto aprovado do Autodoc (regra nova da skill):** o teste usou `NAU-SEA-CCH_ARQ_PL_00_APROVADO_R00.pdf` do Drive. No Autodoc (2.1.c.a, versão assinada) está `CACHOEIRASPOT-PL-ARQ-DCT-GER-XXX-000-R06.pdf`, **Rev 06**. É preciso baixar o R06 e refazer a Fase 1 (comparação lançamento × aprovado e atualização da planta) antes de qualquer recorte. Os recortes R04 ficam suspensos até isso.

1. **Rooftop 505, 506 e 507:** a humanizada 2026 não segue o aprovado (prancha 09/12) no lado direito. A autora precisa corrigir o desenho; depois disso, a skill reprocessa.
2. **Térreo:** a humanizada mostra anisotropia de 1,035 contra o aprovado, ou seja, possível desproporção de cerca de 3,5% num eixo. Os recortes estão com ressalva. Conferir com a autora (Raquel Tavares) e/ou com a arquitetura.
3. **Rótulo "317 Sacada 1,15" na prancha 07/12:** humanizada e SpotSys indicam que é da 316. A correção foi aplicada de forma documentada; a arquitetura valida.
4. **L3 e 108:** faixas sem divisa no aprovado. É preciso definir se entram no recorte.
5. **Quadro "AREAS … VERSÃO FINAL.xlsx":** 3 erros (107, 112 e 303) contra o PDF e o SpotSys. Corrigir o quadro; o SpotSys está certo.
6. **Imagens já publicadas no SpotSys** (22 recortes do 2º pavimento): têm área escrita e há links quebrados (404). Substituir após a validação; é tarefa humana no SpotSys.
7. **Pedir à autora** a versão sem texto ou o PSD em camadas: elimina os borrões da remoção automática sobre deck e tapetes.
8. **Formato do 360:** confirmar se o fundo transparente e a resolução nativa (cerca de 400 a 1100 px) atendem. Se não, ajustar a etapa 9 da skill.
9. **Estilo técnico humanizado (pedido do Fernando):** decidir se vale investir na renderização a partir do DWG aprovado após terça (ver `skill/SKILL.md`, seção L).

## Riscos e limitações

- O layout interno não pode ser conferido contra o legal aprovado, que só traz perímetros. A conferência fina exige o executivo ou o IFC.
- A remoção de texto reconstrói o fundo: os artefatos são cosméticos, mas existem e precisam de revisão visual.
- A segmentação depende dos rótulos do PDF. Rótulos trocados ou faixas sem divisa geram pendência, nunca uma escolha silenciosa.
- **Incidente:** durante a tentativa de leitura do Slack, duas mensagens foram enviadas por engano ("humanizada" em #lideranças e "humanizadas" no grupo de plantas humanizadas, em 09/10). Só a autora pode apagá-las.
