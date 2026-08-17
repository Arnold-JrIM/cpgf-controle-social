# Medição independente da candidata B no JH5 — protocolo 1.0.0

## Finalidade

Este incremento congela o harness que será usado na primeira medição independente da arquitetura `B_llm_route` sobre o Joint Retrieval Holdout 5.0.0. O JH5 foi congelado no PR #57 antes de qualquer execução da candidata, enquanto a própria candidata B havia sido congelada anteriormente no PR #56.

A medição real não é executada durante o pull request. O workflow de chamadas reais só pode rodar por `workflow_dispatch` a partir de `main`, depois do merge deste protocolo. Essa separação impede que o código de avaliação seja ajustado depois de observar o comportamento da candidata no JH5.

## Fluxos avaliados

A medição compara dois fluxos:

- `A_deterministic`: Router 1.4 -> Retrieval Planner 1.3, executado uma única vez como baseline;
- `B_llm_route`: GPT-4o mini classifica somente a rota documental -> Retrieval Planner 1.3 deriva deterministicamente escopos e temporalidades.

A candidata B não responde à pergunta, não seleciona documentos, não chama Retriever, não executa SQL, não acessa ferramentas externas e não atua como motor de auditoria.

## Execução congelada

A execução oficial fixa:

- benchmark JH5 com 48 casos e SHA-256 `2695be52ff403043c394f0ca7f9f0a47f209fd2016172586146c69adf5595354`;
- `gpt-4o-mini-2024-07-18`;
- OpenAI SDK 3.1.0;
- Python 3.12;
- três repetições completas da candidata B;
- 48 casos por repetição;
- 144 chamadas LLM esperadas;
- Structured Outputs estrito;
- `store=false`;
- nenhuma ferramenta externa;
- nenhum parâmetro de `workflow_dispatch` capaz de alterar modelo ou repetições.

O Provider, o Planner, a dependência de tipos do Router, o evaluator e o runner são verificados por Git blob SHA antes de qualquer chamada ao modelo.

## Evidência produzida

O artifact oficial registra, por caso e por repetição:

- rota esperada e rota prevista;
- escopos esperados e previstos;
- temporalidades esperadas e previstas;
- acerto de rota, escopo, temporalidade, filtros e joint;
- validade do schema;
- identificador da resposta da API;
- modelo efetivamente retornado;
- tokens de entrada e saída;
- latência;
- erros individuais, quando ocorrerem.

Também são produzidos agregados globais, por repetição e por categoria, além da estabilidade modal entre as três repetições.

## Gate prospectivo

O resultado só passa o gate amplo de generalização se todos os critérios já congelados forem satisfeitos:

1. três repetições completas;
2. zero violações de schema;
3. joint médio de B >= 50%;
4. ganho absoluto de joint de B sobre A >= 10 pontos percentuais;
5. route exact médio de B >= 75%;
6. estabilidade modal média >= 0,90;
7. joint médio de B >= 25% em cada uma das quatro categorias.

O workflow não falha porque a performance ficou abaixo desses limites. Desempenho ruim é resultado experimental e deve ser preservado. O workflow só deve falhar por quebra de integridade do protocolo, credencial ausente ou erro que impeça a formação do artifact governado.

## Regra da primeira medição

O primeiro `workflow_dispatch` concluído em `main` depois do merge deste protocolo é a medição oficial independente. Reexecuções posteriores podem ser preservadas como análise de sensibilidade, mas não recuperam o status de independência da primeira exposição do JH5 à candidata.

Depois da execução oficial, o artifact bruto deverá ser congelado integralmente em um incremento separado, com run ID, commit, artifact ID, digest, métricas, gate e análise descritiva. Nenhum tuning de prompt, modelo ou Planner poderá transformar uma eventual falha do JH5 em nova tentativa independente sobre o mesmo benchmark.
