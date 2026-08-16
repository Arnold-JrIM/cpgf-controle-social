# Router 1.3.0

## Objetivo

O Router 1.3.0 é um incremento de tuning controlado criado após o diagnóstico post-hoc do Joint Retrieval Holdout 2.0. Seu objetivo é ampliar a generalização semântica do roteamento documental, mantendo o Retrieval Planner 1.1.0 congelado.

O Joint Holdout 2.0 já havia produzido evidência independente antes deste tuning. Por isso, todos os resultados obtidos neste incremento sobre esse conjunto são **regressão conhecida**, e não nova evidência de generalização.

## Evidência anterior preservada

A primeira medição independente do Joint Holdout 2.0, executada com Router 1.2.0 e Planner 1.1.0, produziu:

- 13/40 rotas exatas;
- 12/40 casos com concordância conjunta de rota, escopo e temporalidade;
- 30% de concordância conjunta.

O diagnóstico post-hoc posterior decompôs os 28 erros em:

- 15 `router_only`;
- 1 `planner_only`;
- 12 `router_and_planner`.

Esse diagnóstico estabeleceu um teto contrafactual conhecido de **27/40 = 67,5%** caso somente a rota fosse corrigida para a rota esperada, mantendo o Planner 1.1.0 inalterado.

Esses números continuam associados às versões que os produziram e não são recalculados como se tivessem sido observados originalmente com o Router 1.3.0.

## Mudanças semânticas

O Router 1.3.0 amplia famílias de sinais linguísticos sem consultar IDs de benchmark.

### Fontes científicas e acadêmicas

Foram incorporadas formulações como base acadêmica ou científica, trabalho e artigo acadêmico, pesquisa recente, estudo sobre determinado tema, aplicação empírica, suporte acadêmico e literatura de auditoria.

### Metodologia e interpretação analítica

O roteamento metodológico passa a reconhecer melhor perguntas sobre distribuição numérica, anomalia ou alerta estatístico, triagem, investigação e validação humana, além de aplicações de BI e IA à auditoria de recursos públicos.

### Consultas compostas

A rota `composite` foi ampliada para perguntas que combinam:

- literatura científica e normas vigentes;
- literatura e orientação institucional;
- controle externo e literatura;
- controle externo e normas gerais;
- transparência dos gastos do CPGF, competência informacional e controle social.

### Documentos oficiais

O Router reconhece formulações mais naturais envolvendo acórdãos, TCU, precedentes, pronunciamentos, portarias, atos e fontes oficiais.

### Preservação de consultas quantitativas

Uma menção a Benford não deve transformar automaticamente uma pergunta quantitativa sobre a T08 em pergunta metodológica. O Router preserva a precedência da intenção quantitativa quando o usuário pergunta por quantidade, incidência ou prevalência de sinais.

## Primeira tentativa de tuning

A primeira execução do Router 1.3.0 revelou cinco conflitos relevantes:

- BENCH-029 e BENCH-119 migraram indevidamente de `trails` para `methodology` devido à menção a Benford;
- JH2-022, JH2-023, JH2-025 e JH2-031 ainda não eram reconhecidos como `composite`.

O ajuste subsequente restringiu o tratamento metodológico de Benford a perguntas não quantitativas e ampliou famílias gerais de referência acadêmica/normativa. Não foram adicionadas condições por ID.

## Regressão conhecida final

No run `31969144504`, com head `0f55f290cd8a695b5ce6845b539db5219b5eba0f`, o Router 1.3.0 produziu:

| Conjunto | Resultado |
|---|---:|
| Assistant Benchmark 1.0.0 | 50/50 |
| Router Holdout 1.0.0 | 40/40 |
| Router Holdout 2.0.0 | 40/40 |
| Joint Holdout 2.0 — rota | 40/40 |
| Joint Holdout 2.0 — rota + escopo + temporalidade | 27/40 |

O mesmo resultado foi reproduzido em Python 3.11 e 3.12. Os artifacts dos dois ambientes têm o mesmo digest: `sha256:a7ad59896f260edae01aaa233c38479d4e1a8a6f8bc6f4d1e5a5a6d01f9924c3`.

O resultado de 27/40 coincide exatamente com o teto contrafactual estabelecido no diagnóstico do PR anterior. Isso é coerente com a hipótese de que o componente de roteamento diagnosticado foi resolvido **nos conjuntos já conhecidos**, mas não permite inferir desempenho em perguntas novas.

## Erros remanescentes

Com as 40 rotas do JH2 agora corretas, permanecem 13 divergências de filtros produzidos pelo Planner 1.1.0:

- JH2-003;
- JH2-016;
- JH2-021;
- JH2-023;
- JH2-025;
- JH2-027;
- JH2-028;
- JH2-029;
- JH2-030;
- JH2-031;
- JH2-032;
- JH2-033;
- JH2-034.

Esses casos passam a constituir o conjunto conhecido de trabalho para o Retrieval Planner 1.2.0. A concentração em consultas `cross_source` permanece consistente com o diagnóstico anterior.

## Governança histórica

Este incremento também consolida a separação entre evidência histórica e código operacional corrente.

O preflight do Joint Holdout 2.0 continua exigindo igualdade entre código e freeze enquanto o conjunto estiver em estado pré-medição. Depois de `MEASURED_INDEPENDENT`, contudo, o preflight valida o benchmark, o corpus e o freeze histórico sem impedir a evolução de Router ou Planner.

Da mesma forma, o diagnóstico post-hoc do Router 1.2 + Planner 1.1 passa a ser validado pelo manifesto congelado, e não recalculado com o Router corrente. Manifests antigos permanecem associados às versões que efetivamente produziram suas evidências.

## Limitações

Os resultados de 100% de roteamento no Joint Holdout 2.0 e de 67,5% no fluxo conjunto são resultados de **regressão conhecida após tuning**. Eles não substituem a medição independente de 30% registrada antes do tuning e não sustentam prontidão para produção.

Nenhum LLM, SQL, Retriever ou embedding externo foi utilizado neste incremento. A ativação do LLM permanece bloqueada.

## Próximos gates

A sequência recomendada é:

1. desenvolver Retrieval Planner 1.2.0 com Router 1.3.0 congelado;
2. tratar os 13 erros de filtros conhecidos sem regras por ID;
3. executar regressões em todos os conjuntos já conhecidos;
4. criar e congelar um **Joint Holdout 3.0 independente** antes da primeira medição pós-tuning;
5. somente depois dessa medição reconsiderar o gate para integração generativa/LLM.
