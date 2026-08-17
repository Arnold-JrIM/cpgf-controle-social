# Diagnóstico pós-hoc da candidata semântica B no JH5

## Status metodológico

Este documento analisa exclusivamente a primeira medição independente da candidata `B_llm_route` no Joint Retrieval Holdout 5.0.0, já congelada no PR #59. O JH5 é material conhecido desde essa execução. Nenhum resultado deste diagnóstico constitui nova evidência de generalização, nenhum ajuste é reaplicado ao JH5 como se fosse independente e nenhuma chamada a LLM, Retriever ou SQL é realizada.

A evidência bruta permanece identificada pelo SHA-256 `b935b69b545c1e7536ac3da84e857ad9bc968932f586202b954433c369a8bcc2`.

## Resultado observado

A candidata B havia obtido média conjunta de 61,81%, rota de 86,81%, filtros conjuntos de 68,06% e estabilidade modal de 97,92%. O gate prospectivo permaneceu em `FAIL` porque o ganho absoluto sobre A foi de 9,72 p.p., inferior ao mínimo congelado de 10 p.p.

A decomposição das 144 decisões das três repetições mostra:

| Medida | Contagem |
|---|---:|
| decisões conjuntas corretas | 89/144 |
| falhas conjuntas | 55/144 |
| falhas de rota | 19/144 |
| falhas de filtros conjuntos | 46/144 |
| falhas de escopo | 40/144 |
| falhas de temporalidade | 40/144 |

Usando `R/S/T` para rota, escopo e temporalidade, letras maiúsculas indicam acerto e minúsculas divergência. Os padrões observados foram `RST=89`, `RSt=6`, `RsT=6`, `Rst=24`, `rST=9` e `rst=10`.

Essa decomposição indica que a camada semântica de rota melhorou substancialmente, mas a maior parte das falhas remanescentes envolve a tradução da intenção em combinação documental e temporalidade.

## Direção dos erros de rota

Os 19 erros de rota possuem uma única direção:

- `knowledge -> composite`: 9;
- `methodology -> composite`: 10.

Não houve nenhuma falha `composite -> knowledge` ou `composite -> methodology`. As 36 decisões cuja rota esperada era `composite` foram classificadas como `composite` nas três repetições.

Portanto, o comportamento dominante não é subdetecção de consultas compostas, mas **sobre-roteamento para `composite`** em parte das perguntas normativas e metodológicas.

## Resultado modal por caso

A previsão modal das três repetições produz 30/48 casos conjuntos corretos, 42/48 rotas corretas e 33/48 filtros conjuntos corretos.

| Classe diagnóstica | Casos | Quantidade |
|---|---|---:|
| `route_only` | JH5-010, JH5-011, JH5-012 | 3 |
| `filters_only` | JH5-026, JH5-027, JH5-029, JH5-030, JH5-033, JH5-034, JH5-035, JH5-036, JH5-042, JH5-043, JH5-045, JH5-048 | 12 |
| `route_and_filters` | JH5-018, JH5-020, JH5-021 | 3 |
| `pass` | demais casos | 30 |

Os três casos instáveis entre repetições foram JH5-003, JH5-012 e JH5-023. Mesmo assim, a estabilidade modal global permaneceu elevada.

## Diagnóstico por categoria

| Categoria | Rota modal exata | Filtros modais exatos | Conjunto modal exato |
|---|---:|---:|---:|
| normative | 9/12 | 12/12 | 9/12 |
| methodology | 9/12 | 9/12 | 9/12 |
| cross_source | 12/12 | 4/12 | 4/12 |
| control_external | 12/12 | 8/12 | 8/12 |

O resultado `cross_source` é o principal achado arquitetural: a rota está correta em 100% dos casos modais e em 36/36 decisões das três repetições, mas os filtros frequentemente não representam a combinação de evidências exigida pela pergunta.

Em `control_external`, ocorre padrão semelhante: a rota permanece correta, enquanto parte das consultas perde o escopo `control_external`, adiciona `cpgf_core` indevidamente ou altera a temporalidade contextual.

## Padrões de escopo

As divergências mais frequentes foram:

- `methodology -> cpgf_core`: 10 ocorrências;
- `control_external -> cpgf_core`: 9;
- `cpgf_core + methodology -> cpgf_core`: 9;
- combinações com perda ou adição de `control_external`, `cpgf_core` ou `methodology`: 12 ocorrências adicionais.

Esses erros são compatíveis com uma limitação do contrato atual: a rota `composite` sinaliza apenas que há combinação de fontes, mas não transporta diretamente **quais necessidades de evidência** devem ser satisfeitas.

## Padrões de temporalidade

As 40 divergências de temporalidade concentram-se em:

- `contextual -> current`: 19;
- `contextual + current -> current`: 12;
- `contextual + current -> contextual`: 6;
- `contextual -> contextual + current`: 3.

O principal viés do Planner continua sendo reduzir contexto histórico/metodológico a `current` ou eliminar uma das duas temporalidades necessárias.

## Leitura arquitetural

O diagnóstico não sustenta novo tuning do JH5. Ele sustenta uma mudança de **representação do problema**.

A arquitetura `B_llm_route` responde à pergunta: “qual rota documental esta consulta pertence?”. O JH5 mostra que, em consultas compostas, essa pergunta é insuficiente. O próximo contrato deve responder: **“de quais evidências esta consulta precisa?”**.

A decisão arquitetural associada a este diagnóstico é documentada no ADR `evidence_orchestrated_assistant_2_0_adr.md` e adota um `EvidencePlan` multi-rótulo capaz de declarar necessidades `DATA`, `KNOWLEDGE` e `WEB`, preservando execução por componentes especializados e fronteiras determinísticas.

## Limite de interpretação

Este diagnóstico é pós-hoc e descritivo. A arquitetura futura será desenvolvida usando o JH5 apenas como material conhecido. Qualquer alegação de generalização do novo orquestrador exigirá um holdout prospectivo novo, congelado antes da primeira medição.
