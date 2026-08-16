# Retrieval Planner 1.2.0

## Objetivo

O Retrieval Planner 1.2.0 refina a inferência determinística de escopo documental e temporalidade após o Router 1.3.0 ter recuperado 40/40 rotas no Joint Retrieval Holdout 2.0 conhecido.

O incremento é deliberadamente restrito ao Planner. O Router 1.3.0 permanece congelado, e o Joint Holdout 2.0 é usado apenas como regressão conhecida após sua primeira medição independente e o diagnóstico post-hoc subsequente.

## Padrões semânticos refinados

O tuning amplia famílias gerais, sem regras por IDs de benchmark:

- natureza jurídica e instrumentalidade do cartão em formulações como categoria própria, despesa autônoma e meio de pagamento;
- competência informacional e capacidade de compreender informação pública, distinguindo literatura metodológica de consultas explicitamente ligadas aos gastos do CPGF;
- repetição ou possível fracionamento quando a pergunta pede normas, orientações ou literatura para contextualização;
- combinação entre literatura metodológica e orientação institucional ou normativa atual;
- combinação entre controle externo e metodologia;
- combinação entre controle externo e normas gerais do suprimento de fundos.

## Governança

O objetivo conhecido de regressão é preservar 30/30 no Retrieval Benchmark 1.0.0, 30/30 no antigo Planner Holdout 1.0.0 e alcançar 40/40 de filtros no Joint Holdout 2.0 com Router 1.3.0 congelado.

Esses resultados, caso obtidos, não constituem evidência de generalização. O próximo teste de generalização deve usar um Joint Holdout 3.0 independente, congelado antes da primeira medição do par Router 1.3.0 + Planner 1.2.0.

O incremento não ativa LLM, não executa SQL, não chama o Retriever e não utiliza embeddings externos durante a avaliação de filtros.
