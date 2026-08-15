# Router 1.1.0 — generalização linguística controlada

## Objetivo

O Router 1.1.0 evolui o roteamento determinístico do Assistente a partir das fragilidades observadas na primeira medição do Router 1.0.0 em um holdout interno de 40 perguntas. A versão permanece sem LLM, sem execução automática de ferramentas e sem SQL livre.

O incremento não altera o significado das rotas nem os contratos de evidência. Seu foco é ampliar a robustez linguística das regras existentes, reduzindo dependência de formulações exatas usadas no benchmark de desenvolvimento.

## Base metodológica

O Router 1.0.0 obteve 50/50 rotas exatas no benchmark de desenvolvimento, mas 19/40 na primeira avaliação do Router Holdout 1.0.0. Essa diferença mostrou que a aderência in-sample não se transferia automaticamente para novas formulações.

Os 21 erros do holdout passaram a ser informação disponível para o desenvolvimento do Router 1.1.0. Em consequência, o arquivo `assistant_router_holdout_v1_0_0.csv` deixa de representar conjunto não visto para esta versão. Ele passa a ser usado exclusivamente como conjunto de regressão conhecido.

Nenhuma pergunta do benchmark de desenvolvimento ou do holdout 1.0.0 foi modificada neste incremento.

## Mudanças estruturais

### Consultas quantitativas

A detecção de intenção quantitativa passa a aceitar maior variedade de construções, incluindo verbos e expressões como `exiba`, `liste`, `apresente`, `quero ver`, `quero comparar`, `quantifique`, `montante`, `trajetória anual`, `incidência`, `ranking` e `maior recorrência`.

A precedência preserva a natureza da consulta: perguntas claramente quantitativas são encaminhadas ao Serving antes de uma classificação genérica como pergunta conceitual apenas pela presença de termos como CPGF.

### Unidade Gestora e território

O roteador reconhece `UG`, `UGs`, `unidade gestora` e `unidades gestoras`. Expressões como `unidade da Federação` e `unidades da Federação` passam a compor o vocabulário territorial.

Consulta a valor de uma UG específica, identificada por código e valor/montante, preserva a rota `overview`, conforme o contrato já congelado no benchmark de desenvolvimento. Rankings ou recorrências por UG permanecem na rota `ugs`.

### Explicação das trilhas

Pedidos metodológicos sobre T01–T09 deixam de depender apenas de `como funciona`. O Router 1.1.0 reconhece formulações como `descreva a lógica`, `qual regra`, `qual critério`, `de que forma`, `qual comportamento`, `qual é o raciocínio` e `por que`.

Essas perguntas continuam usando rota `methodology`, podendo declarar apoio simultâneo das camadas `methodology` e `knowledge`.

### Interpretação segura

A detecção de desafios categóricos foi ampliada para construções como `comprova`, `basta para afirmar`, `suficiente para concluir`, `autoriza concluir`, `evidência conclusiva` e `permite acusar`.

O objetivo é reconhecer quando a pergunta tenta transformar um sinal analítico em conclusão substantiva. A rota `composite` continua sendo apenas um plano de evidência. Ela não confirma fraude, irregularidade, fracionamento, favorecimento ou intenção de evasão de limite.

## Evidência de regressão

O Router 1.1.0 preserva 50/50 rotas exatas no Benchmark 1.0.0.

No Router Holdout 1.0.0, agora conjunto conhecido de regressão, a versão alcança 40/40 rotas exatas. Esse resultado demonstra incorporação dos padrões conhecidos e ausência de regressão nesses casos, mas **não constitui evidência fora da amostra** e não deve ser interpretado como acurácia de produção.

A primeira medição autoritativa do Router 1.0.0 nesse conjunto permanece registrada como 19/40 (47,5%). Ela não é substituída nem reescrita pelo resultado da versão 1.1.0.

## Próxima validação

A avaliação da generalização do Router 1.1.0 requer um novo conjunto de perguntas que:

1. seja criado e congelado antes da primeira execução contra o Router 1.1.0;
2. não repita perguntas dos conjuntos anteriores;
3. represente as mesmas famílias de intenção e cubra T01–T09;
4. seja medido sem corrigir o roteador no mesmo incremento.

Após essa primeira medição, o novo conjunto também poderá ser convertido em regressão para versões futuras, mas deixará de ser não visto para qualquer versão que utilize seus erros no ajuste.

## Limites preservados

- nenhuma chamada a LLM;
- nenhuma execução automática de ferramenta;
- nenhum SQL livre;
- nenhuma alteração em T01–T09, Motor, Serving, Geo ou Knowledge;
- nenhum sinal é convertido automaticamente em constatação de fraude ou irregularidade;
- T08 e T09 mantêm caráter contextual;
- roteamento e evidência permanecem contratos distintos.
