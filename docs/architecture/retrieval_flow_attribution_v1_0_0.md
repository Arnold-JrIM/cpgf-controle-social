# Retrieval Flow Attribution Diagnostic 1.0.0

## Objetivo

Este incremento decompõe, de forma post-hoc, as divergências observadas no `Retrieval Planner Holdout 1.0.0` entre a contribuição do `Router 1.1.0` e a contribuição do `Retrieval Planner 1.0.0`.

O diagnóstico não altera nenhuma regra das duas camadas. O holdout já havia sido medido no PR #38 e, portanto, é tratado aqui como conjunto conhecido para diagnóstico e regressão, não como novo teste independente de generalização.

## Problema de atribuição

A primeira medição válida do holdout produziu 14/30 casos com concordância conjunta de escopo e temporalidade e 16 divergências. Entretanto, o Planner recebe como entrada a pergunta e a decisão produzida pelo Router. Assim, uma divergência do plano pode nascer em duas etapas diferentes:

1. o Router pode entregar uma rota incompatível com recuperação documental;
2. mesmo recebendo uma rota documental adequada, o Planner pode não inferir os filtros esperados.

Atribuir todas as 16 divergências ao Planner misturaria responsabilidades arquiteturais e poderia induzir tuning na camada errada.

## Método contrafactual

Para evitar criar manualmente um novo gabarito de rota depois de observar os erros, o diagnóstico utiliza um sweep contrafactual.

Para cada uma das 30 perguntas:

1. executa-se o fluxo real `route_question(question) -> plan_knowledge_retrieval(question, decision=...)`;
2. mantêm-se a pergunta e o oráculo documental do holdout fixos;
3. substitui-se somente a rota fornecida ao Planner por cada uma das rotas capazes de acionar recuperação documental/metodológica: `knowledge`, `methodology` e `composite`;
4. verifica-se se alguma dessas rotas torna simultaneamente exatos o escopo e a temporalidade.

O contrafactual não simula uma nova versão do Router e não estima desempenho futuro. Ele responde apenas se a decisão de rota é causalmente suficiente para explicar determinada divergência dentro das regras atuais do Planner.

## Classes de atribuição

### `pass`

A rota observada pertence ao conjunto documental e os filtros produzidos são exatos.

### `router_latent`

Os filtros são exatos, mas a rota observada é `overview`, `trails`, `unsupported` ou outra rota não pertencente ao conjunto documental. A métrica do Planner não registra erro, porém a orquestração contém uma fragilidade latente porque a camada de Knowledge pode não ser acionada corretamente.

### `router_blocking`

A rota real não é documental e o plano falha. Pelo menos uma rota documental contrafactual produz filtros exatos sem alterar o Planner. Nesse caso, a falha conjunta é explicável pelo Router.

### `router_selection`

A rota real já é documental, mas outra rota documental contrafactual produz filtros exatos. A fragilidade está na seleção entre intenções documentais, e não na incapacidade intrínseca do Planner de produzir o plano correto.

### `planner`

A rota real é documental e nenhuma rota documental contrafactual produz filtros exatos. A mudança de rota não é suficiente; as regras internas de inferência de escopo e/ou temporalidade são insuficientes para a formulação observada.

### `router_and_planner`

A rota real não é documental e, adicionalmente, nenhuma rota documental contrafactual consegue produzir os filtros esperados. Corrigir apenas uma camada não é suficiente.

## Resultados

A decomposição dos 30 casos foi:

| Classe | Casos |
|---|---:|
| `pass` | 7 |
| `router_latent` | 7 |
| `router_blocking` | 6 |
| `router_selection` | 1 |
| `planner` | 4 |
| `router_and_planner` | 5 |

Os 16 erros conjuntos de filtros se repartem em três grupos mutuamente exclusivos:

- **7 erros somente de Router**: seis `router_blocking` e um `router_selection`;
- **4 erros somente de Planner**;
- **5 erros compartilhados Router + Planner**.

Por consequência, o Router participa de 12/16 divergências conjuntas (75%), enquanto o Planner participa de 9/16 (56,25%). Esses percentuais se sobrepõem nos cinco casos compartilhados e não devem ser somados.

Além dos 16 erros de filtros, sete casos classificados como `router_latent` apresentaram filtros exatos apesar de uma rota não documental. Assim, 19/30 perguntas do holdout exibem algum problema de roteamento, sendo 12 com efeito observável sobre a concordância dos filtros e sete sem efeito nessa métrica específica.

## Contrafactual de correção apenas do Router

Dentro deste holdout conhecido, sete das 16 falhas tornam-se exatas ao substituir somente a rota por uma alternativa documental compatível. Mantendo o Planner 1.0.0 congelado, isso estabelece um limite diagnóstico de 21/30 casos com filtros conjuntamente exatos após uma seleção de rota idealizada.

Esse valor de 70% não é previsão de desempenho do futuro Router 1.2.0. Trata-se de um teto contrafactual calculado sobre casos já conhecidos e serve apenas para priorizar o desenvolvimento.

## Casos por atribuição

- `pass`: KRET-103, KRET-104, KRET-106, KRET-111, KRET-121, KRET-122, KRET-124;
- `router_latent`: KRET-101, KRET-105, KRET-109, KRET-110, KRET-112, KRET-125, KRET-130;
- `router_blocking`: KRET-113, KRET-115, KRET-116, KRET-117, KRET-118, KRET-126;
- `router_selection`: KRET-114;
- `planner`: KRET-102, KRET-108, KRET-120, KRET-129;
- `router_and_planner`: KRET-107, KRET-119, KRET-123, KRET-127, KRET-128.

## Implicação arquitetural

O resultado indica que o próximo incremento deve atuar primeiro no Router. Essa ordem reduz a chance de ampliar regras do Planner apenas para compensar perguntas que chegaram à camada documental com intenção inadequada.

A sequência recomendada é:

1. desenvolver `Router 1.2.0` usando os casos conhecidos como regressão, sem modificar o Planner 1.0.0;
2. medir o efeito do Router 1.2.0 nos benchmarks já conhecidos e identificar os erros documentais remanescentes;
3. desenvolver `Retrieval Planner 1.1.0` em incremento separado para os casos que continuam não solucionáveis por roteamento;
4. congelar um **novo holdout conjunto independente**, criado antes da primeira medição do fluxo ajustado;
5. somente então voltar a fazer alegações de generalização e avaliar o gate para ativação conversacional/LLM.

## Governança

O diagnóstico 1.0.0:

- não chama LLM;
- não executa SQL;
- não altera Router 1.1.0;
- não altera Retrieval Planner 1.0.0;
- não altera T01–T09, Motor, Serving, Geo ou Knowledge;
- não reutiliza o holdout conhecido como evidência independente;
- não realiza tuning neste incremento.

A validação inicial foi executada no GitHub Actions run `31964468682`, com Ruff e pytest aprovados em Python 3.11 e 3.12.
