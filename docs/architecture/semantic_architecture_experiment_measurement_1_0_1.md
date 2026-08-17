# Medição real do Experimento de Arquitetura Semântica 1.0.1

## Situação experimental

A primeira execução real do protocolo 1.0.1 ocorreu no GitHub Actions, run `31981818344`, sobre a `main` no commit `78cb64a4f0ded0e1e429d2990ef67cc55fee4fab`. O artifact oficial foi `semantic-architecture-experiment-v1.0.1` (artifact `9272652427`), com digest ZIP `sha256:f4d9f97e7377b2672c374b6a9b041464bd2e005536600f2f430b9a2751ea43c4`. O JSON de resultado possui SHA-256 `eab4001e46707e208dd76527f175d2a796e306bd10c8a79aba6c86b89f6e11a1`.

A execução utilizou o snapshot `gpt-4o-mini-2024-07-18`, três repetições para as arquiteturas com LLM, `store=false`, Structured Outputs estrito e nenhuma ferramenta externa. O JH4 já era material conhecido, de modo que esta etapa serve exclusivamente para desenvolvimento e seleção arquitetural, não para sustentar generalização.

## Resultado global

| Arquitetura | Rota exata média | Filtros exatos médios | Conjunto exato médio | Pior repetição | Estabilidade modal | Schema |
|---|---:|---:|---:|---:|---:|---:|
| A — determinística | 41,67% | 50,00% | 37,50% | 37,50% | determinística | 0 violações |
| B — LLM route-only | 88,19% | 61,81% | **54,86%** | 54,17% | **98,61%** | 0 violações |
| C — híbrida adjudicada | **92,36%** | 41,67% | 41,67% | 39,58% | 86,81% | 0 violações |

B superou A em 17,36 pontos percentuais na métrica conjunta e cumpriu os três critérios prospectivos: ganho mínimo de 10 p.p., estabilidade modal média de pelo menos 0,90 e ausência de violações de schema. C apresentou ganho de apenas 4,17 p.p. e estabilidade inferior ao limiar. Portanto, o protocolo selecionou `B_llm_route` como única candidata a um futuro JH5.

## Repetições

B apresentou 26/48, 26/48 e 27/48 acertos conjuntos nas três repetições, respectivamente. C apresentou 19/48, 21/48 e 20/48. Apenas dois casos de B variaram entre as repetições (`JH4-023` e `JH4-033`), enquanto C variou em 17 casos.

## Interpretação do resultado

O resultado sugere que o ganho do LLM está concentrado na interpretação semântica necessária para escolher a rota documental. B elevou a exatidão de rota de 41,67% para 88,19%, preservando o Planner 1.3 como camada determinística responsável por escopo e temporalidade. Esse desenho produziu o melhor desempenho conjunto e a maior estabilidade.

C, por sua vez, alcançou a maior exatidão de rota, 92,36%, mas o ganho não se traduziu em desempenho conjunto. Ao permitir que o LLM também adjudicasse escopos e temporalidades, a exatidão conjunta dos filtros caiu para 41,67%. O erro mais recorrente foi tratar evidência `contextual` como `current`: foram observadas 44 ocorrências desse padrão em C, contra 28 em B, cujo Planner permaneceu determinístico.

Esse comportamento é metodologicamente relevante. O experimento não aponta para maior autonomia do agente como solução. Ao contrário, favorece uma arquitetura em que o LLM resolve uma tarefa semântica estreita e estruturada, enquanto regras determinísticas preservam decisões de governança documental. Em outras palavras, o melhor resultado foi obtido pela combinação de capacidade semântica generativa com restrição explícita do grau de liberdade.

## Resultado por categoria

Na categoria `methodology`, B atingiu 88,89% de exatidão conjunta, ante 41,67% de A. Em `normative`, passou de 58,33% para 66,67%. Em `cross_source`, aumentou de 8,33% para 22,22%, mas a categoria permanece como principal dificuldade. Em `control_external`, B passou a acertar 100% das rotas, porém o resultado conjunto permaneceu em 41,67% porque os filtros produzidos pelo Planner ainda limitam o desempenho.

Assim, o experimento separa dois problemas. O primeiro, interpretação de intenção/rota, foi substancialmente reduzido pelo LLM. O segundo, planejamento de filtros para consultas `cross_source` e `control_external`, permanece como limitação do Planner. Essa limitação não deve ser corrigida usando o JH4 para alegar generalização; qualquer ajuste posterior continuará sendo desenvolvimento sobre material conhecido.

## Custo e latência registrados

Foram realizadas 288 chamadas ao LLM, totalizando 97.092 tokens de entrada e 12.372 tokens de saída. B consumiu 30.987 tokens de entrada e 5.570 de saída; C consumiu 66.105 e 6.802, respectivamente. A latência média registrada foi de aproximadamente 1,115 s por chamada em ambas as arquiteturas.

O custo monetário não é congelado neste manifesto porque preço de API é variável no tempo. A estimativa deve ser calculada a partir dos tokens registrados e da tabela oficial vigente na data da análise.

## Governança e próximo passo

Nenhum prompt, regra, benchmark, Router ou Planner é alterado neste incremento. O objetivo é apenas congelar a primeira medição real e sua interpretação antes de qualquer desenvolvimento posterior.

`B_llm_route` passa a ser a arquitetura candidata, mas ainda não está validada para generalização e não é ativada em produção. O próximo passo é congelar formalmente a especificação da arquitetura B e, somente depois, construir e congelar um novo Joint Holdout 5.0.0 sem executar a candidata sobre suas perguntas. A primeira execução da arquitetura selecionada no JH5 deverá ocorrer apenas depois desse freeze prospectivo.
