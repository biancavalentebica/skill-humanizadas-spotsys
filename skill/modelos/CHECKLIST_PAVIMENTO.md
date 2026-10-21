# Ficha do pavimento: <EMP> · <PAVIMENTO>

Copie para `<EMP>/01_diagnostico/CHECKLIST_<PAV>.md`. Preencha na ordem e não pule nenhuma trava. Procedimento: `skill/SKILL.md`.
Legenda: `[x]` feito e conferido · `[!]` reprovado (anote o motivo) · `[P]` pendente de terceiro (anote quem decide).

## Identificação
- Empreendimento / pavimento / variantes do aprovado (andares):
- Imagens do SpotSys que esta ficha substitui (ID, conteúdo, com/sem texto, solar):
- Unidades ativas no SpotSys neste pavimento (quantidade e códigos):

## Etapa 1: entradas (checklist de entrada)
- [ ] PDF assinado do Autodoc 2.1.c.a, maior revisão: arquivo ______ Rev ___ data ___ (alvará ___)
- [ ] Página e clip (pt) deste pavimento: pág ___ clip ______
- [ ] Arquivo técnico da mesma revisão (ou "não existe" / "é só a prancha importada"): ______
- [ ] Humanizada de lançamento com texto (resolução ______) e sem texto (resolução ______), origem ______
- [ ] Interiores: tabela de tipologias ______ / plantas de tipologia ______ / RVT ______ (ou "não existe")
- [ ] Export do SpotSys com `id`: `00_entradas/spotsys/______.csv`, `project_version` = ______
- **Trava X1/X2:** [ ] ok

## Etapa 2: áreas
- [ ] SpotSys × aprovado: ___ de ___ iguais (`conferencia_spotsys_x_aprovado_<REV>.csv`)
- [ ] Interiores × aprovado: ___ de ___ iguais
- [ ] Arquivo base × aprovado: BATE / NAO_BATE / não se aplica
- Divergências e decisão:
- **Trava X3:** [ ] ok

## Etapa 3: diferenças e cenário
- Comando do registro (com **todos** os parâmetros): `______`
- Resultado: anisotropia ___ · mediana ___ cm · p90 ___ cm · ≤15 cm ___%
- [ ] Overlay global olhado: núcleo e paredes externas coincidem (X4)
- [ ] Mosaicos zona a zona lidos: `05_qc/alta/<PAV>_zona_*.jpg`
- [ ] Revisão nova? comparação em três camadas (tinta, unidade, saída) feita / não se aplica

| # | Item | Aprovado | Humanizada | Coordenada / evidência | Decisão (corrigir / manter por decisão de ___ / pendente ___) |
|---|---|---|---|---|---|
| 1 | | | | | |

- Nível da régua: ___ · Cenário proposto: A / B
- **[VALIDAÇÃO HUMANA]** cenário e lista confirmados por ______ em ___ · **Trava X5:** [ ] ok

## Etapa 4A ou 4B: execução
- Script(s) usado(s) e log: ______
- 4A: [ ] só os itens da tabela foram alterados · [ ] diferença 0 fora das caixas do log · [ ] aplicado em todas as versões da imagem
- 4B: [ ] fluxos de circulação · [ ] `INVENTARIO_AMBIENTES_<PAV>.md` · [ ] `tipologias_unidades_<emp>.csv` (fonte: ______) · [ ] escala real
- 4B.7 auditoria pré-render (achado → explicação):
- Fidelidade do mobiliário por unidade (`interiores`/`lancamento`/`adaptado`/`regra`/`minimo`/`sem cama`):

## Etapa 5: textos
- Versões geradas: com texto / sem texto / só numeração / solar
- [ ] Cada rótulo restante confere com a etapa 2 · [ ] rótulos removidos inspecionados a 100%

## Etapa 6: checklist de qualidade (SKILL.md, seção 5)
| Q | Resultado (OK / REPROVADO / PENDENTE) | Evidência |
|---|---|---|
| Q1 ★ geometria | | |
| Q2 ★ paredes, portas, escadas, acessos | | |
| Q3 ★ vagas e ambientes | | |
| Q4 mobiliário (medida de referência ___ m → ___ m) | | |
| Q5 texturas | | |
| Q6 ★ nada indevido | | |
| Q7 textos | | |
| Q8 qualidade gráfica | | |
| Q9 ★ comparativo | | |
| Q10 ★ divergências registradas | | |
| Q11 ★ auditoria pré-render | | |
| Q12 fidelidade do mobiliário | | |

## Etapa 7: validação do pavimento (TRAVA X8)
- Validado: S / N · validador ______ · data ______ · observações ______

## Etapas 8–9: recorte e pacote
- [ ] Extrator: ___ de ___ unidades com `OK` (X9)
- [ ] Recortes: ___ = unidades do SpotSys ___ (C8) · andares reais gerados: sim / não se aplica
- [ ] `QC_RELATORIO.md`: aprovados ___ · ressalva ___ · pendentes ___
- [ ] `VALIDACAO_HUMANA.csv` preenchida por ______ em ___ · `pins_360.json` com `szi_unit_id` em todas as linhas

## Etapas 10–13: SpotSys e 360 (manuais)
- [ ] URLs antigas guardadas (unidades e pavimento) em ______
- [ ] Unidades subidas por ______ em ___ · [ ] pavimento trocado (mesma imagem base dos pins, X10)
- [ ] Pins carregados por ______ em ___ · método ______ · resultado ______
- [ ] 360 percorrido unidade a unidade por ______ em ___
