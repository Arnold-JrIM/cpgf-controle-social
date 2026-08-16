# Notas de tuning — Retrieval Planner 1.2.0

O Joint Holdout 2.0 deixou de ser independente após sua primeira medição e os incrementos subsequentes de Router e Planner. Por isso, qualquer ajuste desta versão usa o conjunto exclusivamente como regressão conhecida.

A linha histórica preservada é:

1. Router 1.2.0 + Planner 1.1.0: primeira medição independente do JH2, 12/40 no fluxo conjunto;
2. diagnóstico post-hoc: 15 falhas atribuídas somente ao Router, 1 somente ao Planner e 12 compartilhadas;
3. Router 1.3.0 + Planner 1.1.0: 40/40 de rotas e 27/40 no fluxo conjunto conhecido;
4. Planner 1.2.0: tuning direcionado exclusivamente aos 13 filtros remanescentes, sem alterar o Router.

A próxima alegação de generalização exige um novo Joint Holdout 3.0 congelado antes da primeira medição.
