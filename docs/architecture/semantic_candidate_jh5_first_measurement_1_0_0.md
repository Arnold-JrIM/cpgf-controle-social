# Primeira medição independente da candidata B no JH5 — 1.0.0

## Finalidade

Este documento registra a primeira medição independente da candidata `B_llm_route` sobre o Joint Retrieval Holdout 5.0.0. O JH5 foi escrito e congelado antes da candidata executar qualquer uma de suas 48 perguntas. O harness foi congelado no PR #58 e a primeira execução oficial ocorreu posteriormente, por `workflow_dispatch`, em `main`.

A medição é evidência de generalização independente da candidata B para este holdout. Como o JH5 passou a ser conhecido após essa execução, qualquer ajuste futuro de prompt, modelo ou Planner não poderá reutilizar o mesmo benchmark para sustentar uma nova alegação de independência.

## Execução oficial

- workflow: `semantic-candidate-jh5-measurement`;
- run: `31985351518`;
- job: `95259306590`;
- attempt: 1;
- evento: `workflow_dispatch`;
- branch: `main`;
- commit: `2dae7fb19a4d7fea91a0561ab85cb272193d826f`;
- conclusão do job: `success`;
- benchmark: JH5 5.0.0, 48 casos;
- benchmark SHA-256: `2695be52ff403043c394f0ca7f9f0a47f209fd2016172586146c69adf5595354`;
- candidata: `B_llm_route` 1.0.0;
- modelo solicitado e retornado em todas as 144 chamadas: `gpt-4o-mini-2024-07-18`;
- OpenAI SDK: 3.1.0;
- Planner: 1.3.0;
- Router 1.4 usado apenas como dependência de tipos;
- Retriever, SQL, ferramentas externas e LLM de resposta final: não utilizados.

O preflight de integridade passou antes da primeira chamada. O secret foi aceito sem exposição. As três repetições foram concluídas e o artifact foi validado e enviado pelo workflow.

## Evidência preservada

O artifact oficial é `semantic-candidate-jh5-first-measurement-v1.0.0`, ID `9273637125`, com digest do ZIP `sha256:46ac047f414946f3097feadfb1006efa3bfb89632e0dd41a955dc7f9b5699349`.

O JSON bruto possui 214.866 bytes e SHA-256 `b935b69b545c1e7536ac3da84e857ad9bc968932f586202b954433c369a8bcc2`. Ele é preservado no repositório em gzip determinístico em `data/evidence/semantic_candidate_jh5_first_measurement_1_0_0.json.gz`, com 12.247 bytes e SHA-256 `d8e8b0ebc2cf90891a4b2b923ff4ce78ae7e244ce675c5696ff4a9576836204c`.

Os testes recompõem o JSON, verificam ambos os hashes e confrontam as métricas do manifesto com o artifact bruto.

## Resultado global

A arquitetura determinística A obteve `joint_exact_rate = 0.5208333333` (25/48).

A candidata B obteve, na média das três repetições:

- joint exato: **0.6180555556** (61,81%);
- ganho absoluto sobre A: **0.0972222222** (+9,72 p.p.);
- rota exata: **0.8680555556** (86,81%);
- filtros conjuntos: **0.6805555556** (68,06%);
- pior repetição de joint: **0.6041666667** (60,42%);
- estabilidade modal: **0.9791666667** (97,92%);
- casos idênticos nas três repetições: 45/48;
- violações de schema: 0;
- erros de provider: 0;
- chamadas LLM: 144;
- tokens de entrada: 31.806;
- tokens de saída: 5.789.

As repetições produziram joint de 60,42%, 62,50% e 62,50%, respectivamente. Os únicos casos com variação de assinatura entre as três execuções foram `JH5-003`, `JH5-012` e `JH5-023`.

## Aplicação do gate prospectivo

O gate havia sido definido antes da primeira medição e exigia que **todos** os critérios fossem cumpridos simultaneamente.

| Critério | Regra | Observado | Resultado |
|---|---:|---:|---|
| 3 repetições completas | sim | sim | PASS |
| violações de schema | 0 | 0 | PASS |
| joint médio B | >= 50% | 61,81% | PASS |
| ganho B − A | >= 10 p.p. | 9,72 p.p. | **FAIL** |
| rota média B | >= 75% | 86,81% | PASS |
| estabilidade modal | >= 90% | 97,92% | PASS |
| joint por categoria | >= 25% em todas | todas >= 33,33% | PASS |

Resultado formal: **FAIL no gate prospectivo de generalização ampla**.

A candidata cumpriu 6 dos 7 critérios. O único critério não atingido foi o ganho absoluto mínimo sobre A. A diferença entre o ganho exigido (0,10) e o observado (0,0972222222) foi 0,0027777778, equivalente a aproximadamente **0,28 ponto percentual**.

Esse limiar não é alterado após a observação. Arredondar 9,72 p.p. para 10 p.p. ou reduzir a exigência converteria uma decisão prospectiva em uma decisão pós-hoc e, portanto, não é permitido.

## Resultado por categoria

| Categoria | A joint | B joint médio | Ganho B−A | B rota | B filtros |
|---|---:|---:|---:|---:|---:|
| normative | 75,00% | 75,00% | 0,00 p.p. | 75,00% | 100,00% |
| methodology | 66,67% | 72,22% | +5,56 p.p. | 72,22% | 72,22% |
| cross_source | 8,33% | 33,33% | +25,00 p.p. | 100,00% | 33,33% |
| control_external | 58,33% | 66,67% | +8,33 p.p. | 100,00% | 66,67% |

A camada semântica mostra contribuição especialmente clara em `cross_source`: a rota chegou a 100%, enquanto o joint permaneceu em 33,33%. Isso é compatível com a hipótese de que, nesses casos, o gargalo residual está nos filtros derivados pelo Planner, e não na escolha da rota. Em `control_external`, a rota também atingiu 100%, com joint de 66,67%.

Essa leitura é **descritiva e pós-hoc**. Ela pode orientar um diagnóstico contrafactual separado, mas não autoriza ajustar o Planner e reavaliá-lo no JH5 como se o benchmark continuasse independente.

## Interpretação metodológica

O resultado não sustenta a alegação de que a candidata B passou pelo gate de generalização ampla definido pelo projeto. Ao mesmo tempo, ele fornece evidência independente de que a camada semântica apresenta desempenho absoluto superior ao baseline A neste holdout, com alta estabilidade e sem violações de contrato.

A conclusão adequada é, portanto, mais restrita: a arquitetura B demonstrou capacidade de generalização parcial no JH5, mas **não cumpriu integralmente a régua prospectiva**. O resultado não desbloqueia Retriever, ativação de produção ou LLM de resposta final.

## Próximo passo permitido

O próximo incremento deve ser exclusivamente diagnóstico e pós-hoc. É permitido decompor os erros do JH5, identificar falhas de rota versus filtros e calcular contrafactuais para localizar o gargalo. Não é permitido tratar esse diagnóstico como nova evidência independente, nem alterar prompt/modelo/Planner e reutilizar o JH5 para reivindicar generalização.

Se uma nova arquitetura for desenvolvida a partir desse diagnóstico, sua validação independente deverá ocorrer em um novo holdout, congelado antes da arquitetura ajustada executá-lo.
