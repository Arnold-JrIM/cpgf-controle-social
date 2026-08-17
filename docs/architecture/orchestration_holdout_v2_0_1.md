# Orchestration Holdout 2.0.1 — correção prospectiva de reachability

## Status

**FROZEN_CORRECTED_BEFORE_MEASUREMENT**

O OH2.0.1 corrige incompatibilidades estruturais identificadas depois do freeze do OH2.0.0 e **antes de qualquer execução de suas perguntas com `gpt-4o-mini`**.

O OH2.0.0 permanece preservado com seus hashes e manifesto originais. Ele foi invalidado para fins de primeira medição porque testes offline com provider-oráculo demonstraram que cinco gabaritos eram inalcançáveis após a normalização determinística já congelada no candidato.

## Problemas identificados

A normalização `1.0.0` aplica contratos determinísticos a KNOWLEDGE e WEB. O gate estático detectou dois tipos de incompatibilidade entre a redação das perguntas e os próprios oracles congelados:

- `OH2-017`: o oracle WEB exige janela de 15 dias, mas a pergunta dizia “quinze dias”; a normalização reconhece janelas explícitas numéricas como “15 dias”;
- `OH2-038`, `OH2-052`, `OH2-053` e `OH2-054`: os oracles exigem KNOWLEDGE junto com WEB, mas os enunciados não continham marcador explícito de intenção de corpus governado e, por isso, KNOWLEDGE era removido.

Esses comportamentos ocorreram mesmo quando um provider estático entregou ao Orchestrator exatamente as fontes e os parâmetros do gabarito. Portanto, não se tratava de desempenho do LLM, mas de incompatibilidade entre benchmark e política determinística.

## Evidência temporal

As incompatibilidades foram detectadas nos testes offline do então rascunho do harness de medição e nos preflights corretivos subsequentes. Os jobs de `live-measurement` existentes no rascunho inicial permaneceram `skipped` e não houve chamada do candidato sobre o OH2.

A correção foi realizada sem observar qualquer saída do `gpt-4o-mini`, sem alterar thresholds e sem tuning do candidato.

## Escopo da correção

O OH2.0.1 contém os mesmos 56 casos, IDs, categorias e oracles do OH2.0.0. Somente o campo `question` muda em cinco casos:

- `OH2-017`: “quinze dias” passa a “últimos 15 dias”;
- `OH2-038`: explicita consulta à **base normativa**;
- `OH2-052`: explicita consulta às **fontes do projeto**;
- `OH2-053`: explicita consulta à **base normativa**;
- `OH2-054`: explicita consulta à **orientação institucional**.

Não são alterados `expected_sources`, ferramenta ou argumentos DATA, scopes/temporalidade/classes KNOWLEDGE, parâmetros WEB, categoria, notas ou gate de aceitação.

O CSV corrigido é reserializado com `csv.DictWriter`, de modo que vírgulas presentes nos novos enunciados sejam corretamente escapadas. O preflight compara OH2.0.0 e OH2.0.1 já parseados e falha se qualquer campo além de `question` divergir.

## Gate adicional de reachability

Antes de permitir qualquer medição, o preflight injeta um **provider-oráculo estático**, sem OpenAI, que fornece exatamente o plano esperado de cada caso. Em seguida, o plano atravessa o mesmo `plan_evidence` e a mesma normalização determinística usados pela candidata.

Para o freeze ser válido, esse oracle precisa obter Source Set Exact Match, precisão e recall de fontes, DATA tool, DATA arguments, KNOWLEDGE filters, WEB parameters, full-plan exact e estabilidade modal iguais a 1,00, além de zero violações de schema, falhas de provider ou falhas de plano.

Esse gate não mede inteligência nem qualidade do modelo. Ele testa apenas se o benchmark é **estruturalmente alcançável** pela arquitetura congelada.

## Candidata preservada

Nenhum componente da candidata foi alterado:

- Semantic Evidence Orchestrator `1.1.0` / policy `1.1.0`;
- normalização `1.0.0`;
- modelo `gpt-4o-mini`;
- prompt SHA-256 `9255a15213b96a9ba219fd43fb402e8d797842064c73d5a9e629d73f0b3269c2`;
- Evidence Contracts/Workers `1.0.0`;
- Web Evidence Worker/Policy `1.0.0`;
- OpenAI SDK `3.1.0`.

Os mesmos blobs Git registrados no OH2.0.0 são novamente verificados pelo preflight.

## Novidade e gate prospectivo

O OH2.0.1 é novamente submetido ao mesmo universo histórico congelado de 10 benchmarks e 430 perguntas, com zero overlap normalizado e teto de similaridade `0,70`.

Os limiares da futura primeira medição permanecem exatamente os mesmos definidos antes do OH2.0.0. Nenhum threshold foi ajustado em resposta a resultados, pois nenhum resultado do candidato foi observado.

## Integridade do artefato

- SHA-256 do gzip: `427174c3d6217bd4ae2770779d38e83e1f9366d39f7ac4a3fc5d41afe64dbcb6`;
- SHA-256 do CSV descomprimido: `574a46a330a1783494d7b7cbe39e9f7d62f29d33f84754fcbef9b934343af6e6`;
- blob Git do gzip: `c8098808ca4e2ce225e90d07f7b97c4c75f87558`.

## Próxima etapa

A primeira medição somente poderá ser preparada **depois do merge deste freeze corretivo**. Um novo PR deverá congelar o harness e, após esse segundo merge, executar três repetições completas dos 56 casos com `gpt-4o-mini`.

A separação preserva a precedência temporal: benchmark corrigido em `main` primeiro; instrumento de medição depois; execução do candidato por último.
