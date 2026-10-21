# Caso de referência: Batel Spot (Cenário A)

Situação em 16/10/2026. Pasta: `BATEL-SPOT/`. Diagnóstico completo: `BATEL-SPOT/01_diagnostico/DIAGNOSTICO_BATEL_SPOT.md`. Pendências: `PENDENCIAS_BATEL_SPOT.md`.
Este arquivo mostra cada etapa do `SKILL.md` aplicada ao Batel: o que foi feito, a prova, o que falta e os testes de 16/10.

## Por que é Cenário A

As alterações do aprovado R04 em relação ao lançamento R01 são pontuais e se concentram na **entrada do térreo**: vaga de embarque e desembarque, E.T. de 4,00 m² em L, recepção sem WC PCD e plataforma elevatória. Além disso, há 8 rótulos de garden desatualizados. Numeração, divisas e áreas das 99 unidades batem com o aprovado e com o SpotSys, e o interiores AP R03 bate com o aprovado em 39 de 39 unidades. Por isso a humanizada existente foi **corrigida**, não refeita (alinhamento com a Bianca).

## Etapa por etapa

| Etapa | Feito | Prova | Situação |
|---|---|---|---|
| 0 Caso | pastas `00_entradas…05_qc`, diagnóstico, pendências | `BATEL-SPOT/` | ok; **fichas por pavimento ainda não preenchidas** (modelo novo de 16/10) |
| 1 Entradas | aprovado R04 (Autodoc 2.1.c.a, alvará 412884), DWG R04 (prancha importada, sem blocos), lançamento R01 (Autodoc 2.1.g.a), interiores AP R03 + tipologias A–I + RVT, imagens publicadas 854–859 | tabela "Fontes" do diagnóstico | export com `id` salvo em 16/10 (`00_entradas/spotsys/spotsys_batel_2026-10-16.csv`; Nekt: `spot_building_id = 1`, `is_active` vazio). **857 e 859 não estão mapeadas no diagnóstico.** Pela miniatura, 857 é o térreo com estudo solar (gardens com os valores antigos) e 859 é um pavimento tipo ("UND. FINAL 01–12"); confirmar |
| 2 Áreas | SpotSys × aprovado 99/99 iguais; interiores × aprovado 39/39 iguais; DWG não se aplica | `01_diagnostico/conferencia_*.csv` | ok |
| 3 Diferenças | chamfer por pavimento + leitura zona a zona em alta; entrada anotada | `05_qc/`, `05_qc/alta/`, `05_qc/TERREO_entrada_anotada.png` | ok, com ressalva E10 (parâmetros não registrados) |
| 3 Cenário | térreo nível 2 → A; 2º, tipo e rooftop nível 1 (sem alteração) | `03_trabalho/comparativo.json` | decisões da Rachel em 15/10 |
| 4A Correção | frente pavimentada com vaga (asfalto, guia e tinta reais da avenida), E.T. em L, WC PCD retirado; **escada original mantida** (decisão da Rachel, afasta a imagem do aprovado) | `03_trabalho/scripts/redesenha_entrada_terreo.py` (= `skill/scripts/`), `*_entrada_log.json` | feito, **aguardando validação** |
| 5 Textos | 8 gardens corrigidos; versões sem texto e só numeração | `corrige_rotulos_area.py`, `remove_rotulos_terreo.py`, `limpa_garden113.py`; `04_saida/.../01_PLANTAS/` | feito |
| 6 QC + comparativo | comparativo lançada × aprovado × nova (4 páginas) | `04_saida/.../02_COMPARATIVO/` | Q1–Q10 **não registrados em ficha**; teste de 16/10 abaixo |
| 7 Validação | — | — | **pendente** (Rachel) |
| 8 Recorte | segmentação da Carol (fase 1) + `poligonos_carol.py` (fase 2): 99 recortes, C8 ok | `05_qc/teste_2026-10-16/fase1_skill_carol/`, `fase2_recortes/` | **teste** sem falhas após as correções de 16/10 (gardens, 211, 113); falta: 2º/tipo sem texto, validação do térreo |
| 9 Pacote | `pins_360_TESTE-FASE2.json` (99, com `szi_unit_id`) | `fase2_recortes/04_PUBLICACAO/` | teste; falta QC + validação humana |
| 10–13 SpotSys/360 | — | — | não iniciado; pins nunca testados |

## Testes de 16/10/2026 (controlados; nada foi enviado)

Evidências em `BATEL-SPOT/05_qc/teste_2026-10-16/`.

1. **Reprodução do QC por chamfer (etapa 3/Q1).** Mesmo comando do diagnóstico (`sobrepoe_aprovado.py`, página 1, clip `1925,335,2772,922`, limiar padrão 70):
   - publicada 856: 1,0048 / 6,7 cm / **64%** (o diagnóstico registra 85,6%) → **o número de 15/10 não é reproduzível** sem os parâmetros usados;
   - lançamento R01, "antes" e nova (com texto e sem texto): anisotropia variando de 0,95 a 1,04 para imagens praticamente iguais → com limiar 70, o ajuste cai em mínimos locais;
   - limiar 90: lançamento e nova iguais (1,000 / 3,3 cm / 73%) → **sem regressão geométrica** fora da entrada;
   - limiar 110: 1,000 / 1,7 cm / 82% para todas, mas **o overlay está errado** (prancha ~26% maior, núcleo fora): `FALSO-POSITIVO_limiar110_overlay-errado.jpg`. Número bom com sobreposição errada = falha do ajuste (X4).
   - Correção aplicada: o `sobrepoe_aprovado.py` grava `parametros`; a etapa 3 exige olhar o overlay e medir o antes e o depois com os mesmos parâmetros (E10).
2. **Conferência da entrada (Q2/Q3).** `overlay_alta.py` com o registro validado de 15/10 (`05_qc/TERREO_registro.json`, largura 9375) sobre a nova TER-001: vaga de embarque e desembarque, E.T. 4,00 m² em L, vazio 0,59 m² e recepção sem WC coincidem com a prancha; a escada longa difere do aprovado (plataforma + escada curta), **por decisão registrada**. Evidência: `entrada_nova_x_aprovado_R04_registro-validado.jpg`. **Resultado: aprovado no Q2/Q3, com a ressalva da escada.**
3. **Recorte (etapa 8).** `extrai_rotulos_pdf.py` (páginas 1–2, SpotSys reconstruído a partir da conferência, sem `id`) → **0 de 99 unidades**; `celulas_pdf.py` falha (sem rótulos). Causa: o padrão `UNIDADE 01 / A. COMP.=19,17m²` não é reconhecido. **Resultado: a etapa 8 não é executável no Batel hoje.** Evidência: `extrai_rotulos_batel_0de99.csv`.
3b. **Segmentação da skill da Carol (fase 1, autorizada pela Rachel).** PDF R04 recortado em 6 plantas + `config.json` do Batel → **99 de 99 unidades** com os códigos do SpotSys; 90 de 99 com área a ±2% da A. COMP. A unidade final 12 (2º–8º) e a 115 ficam em −6%, a conferir. Foi preciso ignorar o poché recortado por clip path (E17). Detalhes: `COMPARACAO_SKILL_CAROL.md`, seção 6.
4. **Pins e 360.** Não testáveis: não há export com `id`, nem recortes, nem acesso de escrita ou ambiente de teste do 360.

## O que falta para o Batel ir ao SpotSys

1. Rachel validar o térreo (etapa 7), registrando a decisão da escada.
2. Mapear as imagens 857 e 859.
3. Gerar o sem texto em alta do 2º e do tipo; conferir zona a zona 104, 111 e o limite oeste de 101–105; depois, recortes definitivos a partir das plantas validadas.
4. Confirmar com Projetos as pendências do rooftop (critério de área, piscina) antes de trocar os textos do rooftop.
5. Testar os pins com quem administra o 360 (etapa 12).
