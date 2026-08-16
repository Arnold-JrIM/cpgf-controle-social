# Joint Retrieval Flow Attribution v3 — 1.0.0

## Objetivo

Decompor, de forma post-hoc, as 21 falhas conjuntas observadas na primeira medição independente do Joint Retrieval Holdout 3.0 entre as camadas Router 1.3.0 e Retrieval Planner 1.2.0.

Este incremento não faz tuning. O JH3 tornou-se material conhecido após a primeira medição independente do PR #46. Portanto, os resultados abaixo são diagnósticos sobre um conjunto conhecido e não constituem nova evidência de generalização.

## Medição de origem

O JH3 contém 48 perguntas. A primeira medição independente registrou 27/48 acertos conjuntos (56,25%) e 21 falhas. A decomposição puramente observacional dessas 21 falhas havia produzido:

- rota errada com filtros corretos: 6;
- rota correta com filtros errados: 4;
- rota errada com filtros errados: 11.

Essa decomposição não permite atribuir todos os 11 últimos casos, porque parte dos erros de filtro pode ser consequência da rota entregue ao Planner.

## Contrafactual

Para cada caso, o diagnóstico:

1. executa o Router e o Planner reais;
2. mantém pergunta e oráculo congelados;
3. substitui apenas `RouteDecision.route` pela rota esperada;
4. executa novamente o Planner com essa decisão contrafactual;
5. verifica se escopos e temporalidades passam a coincidir exatamente com o gabarito.

A atribuição primária usa exclusivamente a rota esperada. Um sweep pelas três rotas documentais (`knowledge`, `methodology`, `composite`) é mantido apenas como diagnóstico secundário.

## Classes

- `pass`: rota e filtros reais corretos;
- `router_only`: rota real errada, mas a correção apenas para a rota esperada recupera integralmente os filtros e o caso conjunto;
- `planner_only`: rota real já correta, mas os filtros permanecem errados;
- `router_and_planner`: rota real errada e, mesmo com a rota esperada, os filtros permanecem errados.

## Resultado

Dos 48 casos:

- `pass`: 27;
- `router_only`: 12;
- `planner_only`: 4;
- `router_and_planner`: 5.

Entre as 21 falhas:

- Router-only: 12/21 = 57,14%;
- Planner-only: 4/21 = 19,05%;
- compartilhadas: 5/21 = 23,81%;
- Router participa de 17/21 = 80,95%;
- Planner participa de 9/21 = 42,86%.

As participações de Router e Planner se sobrepõem nos cinco casos compartilhados e, portanto, não devem ser somadas.

### Por categoria

| Categoria | Pass | Router-only | Planner-only | Router+Planner |
|---|---:|---:|---:|---:|
| normative | 7 | 4 | 1 | 0 |
| methodology | 6 | 6 | 0 | 0 |
| cross_source | 3 | 2 | 2 | 5 |
| control_external | 11 | 0 | 1 | 0 |

O padrão é arquiteturalmente informativo. Em `methodology`, todas as seis falhas são recuperáveis pela correção da rota. Em `cross_source`, cinco dos nove erros exigem mudanças nas duas camadas, mostrando que o problema não se limita ao Router. `control_external` permanece forte e apresenta apenas um erro de Planner.

## Reclassificação dos 11 erros observacionais em ambas as camadas

A análise contrafactual mostra que 6 dos 11 casos que originalmente apresentavam rota e filtros errados são, na realidade operacional do fluxo, recuperáveis pela correção da rota sozinha. Por isso, a atribuição final passa de uma leitura descritiva 6/4/11 para 12 Router-only, 4 Planner-only e 5 compartilhados.

## Teto contrafactual com Planner congelado

Se, post-hoc, a única mudança fosse substituir a rota produzida pelo Router pela rota esperada em todos os casos, 39/48 casos teriam rota, escopo e temporalidade corretos, ou 81,25%.

Esse número é um limite superior diagnóstico sobre o JH3 já conhecido. Ele não é previsão de desempenho de um futuro Router nem evidência de generalização.

## Casos

### Router-only

`JH3-002`, `JH3-006`, `JH3-009`, `JH3-012`, `JH3-013`, `JH3-014`, `JH3-015`, `JH3-016`, `JH3-018`, `JH3-021`, `JH3-025`, `JH3-031`.

### Planner-only

`JH3-003`, `JH3-027`, `JH3-029`, `JH3-037`.

### Router e Planner

`JH3-028`, `JH3-030`, `JH3-033`, `JH3-034`, `JH3-036`.

## Padrões de rota

Nos casos Router-only, predominam intenções de metodologia encaminhadas para `unsupported`, `overview`, `trails` ou `knowledge`, além de consultas normativas encaminhadas para `unsupported`/`overview`. Dois casos `cross_source` esperavam `composite`, mas foram encaminhados para `knowledge`.

Nos cinco casos compartilhados, todos pertencem a `cross_source`: quatro esperavam `composite` e foram roteados para `knowledge`; um foi roteado para `methodology`. Mesmo corrigindo a rota para `composite`, o Planner ainda deixa de compor corretamente escopos e/ou temporalidades.

## Governança e sequência recomendada

O diagnóstico indica Router como a primeira camada de tuning, mantendo Planner 1.2.0 congelado. Depois, uma etapa separada deve tratar os quatro casos Planner-only e os cinco casos compartilhados. Nenhuma regra deve ser criada por ID de benchmark; o tuning deve usar famílias semânticas gerais.

Como o JH3 será usado para orientar esse tuning, ele passa a ser apenas regressão conhecida. Qualquer nova alegação de generalização exigirá um novo holdout independente, criado e congelado antes da primeira execução das versões ajustadas.

O LLM permanece bloqueado e a prontidão de produção continua não sustentada.
