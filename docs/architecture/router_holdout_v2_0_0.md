# Router Holdout 2.0.0

## Finalidade

O Router Holdout 2.0.0 é um conjunto interno de avaliação criado para medir o Router 1.1.0 fora dos dois conjuntos que já haviam participado de seu desenvolvimento ou diagnóstico. Ele não altera o roteador, não executa ferramentas, não chama LLM e não modifica as trilhas T01–T09.

## Congelamento anterior à medição

O arquivo `data/benchmarks/assistant_router_holdout_v2_0_0.csv` contém 40 casos, oito por família, IDs `BENCH-201` a `BENCH-240`, cobertura de T01–T09 e nenhuma pergunta exatamente repetida, após normalização, do Benchmark 1.0.0 ou do Router Holdout 1.0.0.

A versão válida do conjunto foi congelada no commit `5d15ad8f002505b42e9f9d357f55b10c5b3fba62`, com SHA-256 `df48a03af598e86e84bac797f122404db8135c8b77caf19b7024ca52079a298b`, antes da primeira execução que alcançou `evaluate_routing()`.

Uma tentativa anterior, run `31908988446`, falhou na validação Pydantic porque `BENCH-232` tinha uma coluna deslocada. A falha ocorreu durante `load_benchmark()`, antes de qualquer caso ser roteado. Por isso, ela é registrada como preflight de esquema e não como medição do Router 1.1.0.

## Primeira medição válida

A primeira execução válida ocorreu no run `31909120082`, head `fa6974448051551b3331955b7e7125cab61ba5c5`, e terminou com sucesso. O artefato `router-holdout-v2.0.0-first-valid-evaluation` tem ID `9253168342` e digest `sha256:9bc94210ed4fac816fd26bcb30bae262e710d951e9191d828f5fda4cf51c8e20`. O JSON interno da avaliação tem SHA-256 `76d12eddc3e8500e48181817346fd7ab1b1167ce7bb285f52d4072131895d999`.

Resultado: **23/40 rotas exatas, ou 57,5%**, com 17 erros preservados.

| Rota esperada | Casos | Acertos | Acurácia |
|---|---:|---:|---:|
| `knowledge` | 8 | 8 | 100% |
| `overview` | 4 | 1 | 25% |
| `ugs` | 2 | 2 | 100% |
| `suppliers` | 2 | 2 | 100% |
| `territorial` | 2 | 1 | 50% |
| `trails` | 6 | 6 | 100% |
| `methodology` | 12 | 3 | 25% |
| `composite` | 4 | 0 | 0% |

## Leitura diagnóstica

Os resultados mostram robustez nas perguntas conceituais/normativas simples, nas consultas de trilhas e nos rankings por UG e fornecedor. Permanecem fragilidades em três frentes principais: consultas quantitativas gerais ainda podem ser capturadas por `knowledge` quando contêm termos do domínio; explicações do Motor formuladas sem os padrões lexicais conhecidos tendem a cair em `trails`; e desafios de interpretação segura formulados de maneira nova ainda não acionam de forma consistente `composite`.

O Router 1.0.0 havia obtido 19/40 (47,5%) no Router Holdout 1.0.0. O Router 1.1.0 obteve 23/40 (57,5%) neste novo conjunto. A diferença de 10 pontos percentuais é um sinal favorável, mas os dois holdouts contêm perguntas diferentes; portanto, não constitui comparação pareada nem estimativa formal de ganho de acurácia.

## Governança

Os 17 erros deste conjunto não serão corrigidos no PR que os revelou. Enquanto permanecer assim, o Router Holdout 2.0.0 pode ser descrito como conjunto não usado no ajuste do Router 1.1.0. Se os erros forem usados para construir uma versão posterior do roteador, este conjunto passará a ser apenas regressão conhecida, e uma nova alegação de generalização exigirá outro conjunto independente.

A métrica de 57,5% é avaliação interna de roteamento. Ela não mede qualidade da futura resposta do LLM, precisão dos dados do Serving, qualidade da recuperação documental, acurácia de produção nem validação humana externa.

## Próximo uso

O conjunto pode apoiar o diagnóstico do Router 1.2.0 em incremento posterior. Antes de uma nova afirmação de generalização, deverá ser criado outro holdout independente. Em paralelo, a avaliação de recuperação lexical, semântica e híbrida permanece um problema separado do roteamento e deve usar métricas próprias.
