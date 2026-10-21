# Skill: atualização de plantas humanizadas pelo projeto aprovado (SpotSys / 360)

Gera a **planta humanizada do pavimento inteiro de acordo com o projeto aprovado** e confere o resultado com o aprovado e com o SpotSys:
- a geometria vem do **arquivo técnico do aprovado** (DWG/IFC/RVT), conferido contra o PDF assinado do **Autodoc** (2.1.c.a);
- o acabamento é o da **humanizada de lançamento**.

## Procedimento vigente (16/10/2026)

O passo a passo está em [skill/SKILL.md](skill/SKILL.md):
- dois cenários: **A**, corrigir a humanizada existente quando a mudança é pontual (caso [Batel](skill/CASO_BATEL_SPOT.md)); **B**, do zero sobre o aprovado com o layout do interiores (Cachoeira, Campeche);
- hierarquia de referências;
- 14 etapas, com entrada, ação, validação e saída, e travas entre elas;
- checklist de qualidade, numa ficha por pavimento ([skill/modelos/CHECKLIST_PAVIMENTO.md](skill/modelos/CHECKLIST_PAVIMENTO.md));
- comparação com a skill da Carol: [skill/COMPARACAO_SKILL_CAROL.md](skill/COMPARACAO_SKILL_CAROL.md).

A seção abaixo é o histórico do método de 14/10.

## Método de 14/10/2026 (histórico)

1. **Projeto aprovado:** PDF assinado do Autodoc (versão de referência).
2. **Arquivo base:** DWG/IFC/RVT do aprovado. Antes de gerar, confere unidade por unidade se as áreas batem com o PDF aprovado (`confere_areas_base_x_aprovado.py`). Não precisa de Revit: o DWG vira DXF no AutoCAD ou no ODA File Converter.
3. **Planta do pavimento:** `gera_humanizada_dwg.py`. Paredes, banheiros, cozinhas e móveis saem nas medidas do projeto, com o acabamento do lançamento:
   - porcelanato, deck, granito, madeira, vegetação, piscina;
   - camas, araras, cubas e cooktop;
   - banheiras na posição do lançamento;
   - vazios de pé-direito duplo com X.

   O que o DWG não desenha vem das etiquetas do PDF aprovado: vagas de bicicleta, elevadores, lixeiras e piscina. **Sem colagem de imagem e sem IA na geometria.**
4. **Conferência:** paredes geradas × divisas do aprovado (`registra_pdf_imagem.py`, ou `registra_translacao.py` quando a escala é fixa).
5. **SpotSys / pins do 360:** conferência das áreas e pacote de publicação, com trava de QC.

Evolução: colagem do lançamento → colagem + IA → contorno do PDF + OCR, todas descartadas. A versão atual usa o arquivo técnico aprovado com o acabamento do lançamento.

**Aprendizado:** é preciso sempre um arquivo base do projeto aprovado. No levantamento de 14/10, 11 dos 19 Spots com modificação têm esse arquivo no Autodoc ([01_diagnostico/ARQUIVO_BASE_AUTODOC_19_SPOTS.md](01_diagnostico/ARQUIVO_BASE_AUTODOC_19_SPOTS.md)).

## Unificação com as outras skills da Seazone

Ver [skill/UNIFICACAO_PLANTAS_HUMANIZADAS.md](skill/UNIFICACAO_PLANTAS_HUMANIZADAS.md).

| Skill | O que entra no fluxo unificado |
|---|---|
| **Esta** | projeto aprovado do Autodoc, conferência do arquivo base, planta do pavimento a partir do DWG, SpotSys e pins |
| **plantas-humanizadas** (Raquel Tavares, `seazone-tech/plantas-humanizadas`) | recorte por tipologia, cotas do PDF cotado, texto/capacidade/solar (PNG + PSD) |
| **Planta Viva** (Arthur, `seazone-tech/szi-planta-humanizada`) | bot que vigia o Drive, deformação para mudanças pequenas, painel de aprovação, planta de tipologias, estudo solar, planilha de áreas |
| **Humanizada do aprovado** (Carol Montedo, Salvador Spot) | regras de layout e checagem antes do render. O código ainda não está publicado |

Teste unificado no Cachoeira Spot, 6 pavimentos: `skill/scripts/roda_unificado.py` com `skill/exemplos/cachoeira-spot_unificado.json`.
- A configuração do recorte da Raquel sai automaticamente do DWG (`gera_cfg_recorte.py`).
- Do 2º pavimento à cobertura, 69 de 69 unidades foram recortadas.
- No térreo e no mezanino a numeração ainda está em ajuste.

O executor chama os scripts da Raquel e do Arthur a partir de um clone dos repositórios deles; este repositório não inclui o código deles.

## Arquivos

- Skill e regras: [skill/SKILL.md](skill/SKILL.md) · scripts: [skill/scripts/](skill/scripts/) · exemplos: [skill/exemplos/](skill/exemplos/)
- Case Cachoeira Spot: [LEIA-ME_ENTREGAVEIS.md](LEIA-ME_ENTREGAVEIS.md), [diagnóstico](01_diagnostico/DIAGNOSTICO_CACHOEIRA_SPOT.md), [referências visuais](02_referencias_visuais/REFERENCIAS_E_REGUA_VISUAL.md)

Ficam fora do repositório e no Drive/Autodoc: plantas, PDFs, DWGs, imagens geradas e as amostras de acabamento recortadas da humanizada de lançamento (`skill/estilo/`).
