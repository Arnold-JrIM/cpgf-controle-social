# Router 1.2.0 — tuning determinístico controlado

## Objetivo

O Router 1.2.0 refina a classificação determinística de intenção do assistente após o diagnóstico do fluxo `Router 1.1.0 -> Retrieval Planner 1.0.0`. O incremento usa exclusivamente conjuntos já conhecidos para desenvolvimento e regressão. Portanto, os resultados registrados aqui **não constituem nova evidência de generalização**.

O Retrieval Planner permanece na versão 1.0.0 durante todo o incremento.

## Motivação

O Retrieval Planner Holdout 1.0.0 havia produzido 14/30 casos com concordância conjunta de escopo e temporalidade no fluxo com Router 1.1.0. A decomposição posterior mostrou que 7 das 16 falhas eram atribuíveis apenas ao Router, 4 apenas ao Planner e 5 às duas camadas, além de 7 fragilidades latentes de roteamento.

Esse resultado justificou corrigir primeiro a camada de classificação de intenção, evitando alterar o Planner para compensar erros originados a montante.

## Princípios do tuning

O ajuste não introduz exceções por ID de benchmark. As novas regras representam classes linguísticas gerais:

- paráfrases de explicação operacional de trilhas;
- perguntas metodológicas sobre primeiros dígitos sem exigir a palavra `Benford`;
- busca de literatura científica sobre auditoria, inteligência de negócios, IA e competência em informação;
- pedidos documentais por normas, atos, manuais e orientações oficiais;
- desafios inferenciais formulados como `autoriza dizer`, `é suficiente para`, `por si só demonstra` e expressões equivalentes;
- consultas quantitativas formuladas com `informe`, `valor agregado`, `série anual` e expressões equivalentes;
- comparações territoriais que enumeram múltiplas UFs;
- perguntas que realmente combinam literatura com evidência normativa ou de controle social específica do CPGF.

O último ponto foi deliberadamente restringido: referências genéricas a transparência governamental ou participação social não bastam para produzir `composite`; é exigido também um marcador explícito do domínio CPGF/cartão/Portal da Transparência.

## Preservação histórica

Dois testes antigos estavam acoplados à versão global corrente do Router. Esse comportamento seria metodologicamente inadequado após a evolução para 1.2.0, pois faria artefatos históricos dependerem do software atual.

Por isso:

- o diagnóstico do PR #39 permanece validado pelo manifesto congelado associado ao Router 1.1.0;
- o Router Holdout 2.0.0 permanece associado ao Router 1.1.0 em `data/manifests/assistant_router_holdout_2_0_0.json`;
- os testes históricos validam os respectivos manifestos, hashes e versões congeladas, em vez de exigir que `ROUTER_VERSION` permaneça para sempre em 1.1.0.

## Regressão conhecida

Todos os conjuntos abaixo já eram conhecidos antes da conclusão do Router 1.2.0.

| Conjunto | Resultado Router 1.2.0 | Interpretação |
|---|---:|---|
| Assistant Benchmark 1.0.0 | 50/50 = 100% | regressão conhecida |
| Router Holdout 1.0.0 | 40/40 = 100% | regressão conhecida |
| Router Holdout 2.0.0 | 40/40 = 100% | passou a ser regressão após ter medido 23/40 no Router 1.1.0 |
| Retrieval Planner Holdout 1.0.0 | 21/30 = 70% de filtros conjuntos exatos | regressão conhecida do fluxo com Planner 1.0.0 congelado |

No holdout documental, as 9 divergências remanescentes são:

`KRET-102`, `KRET-107`, `KRET-108`, `KRET-119`, `KRET-120`, `KRET-123`, `KRET-127`, `KRET-128` e `KRET-129`.

Sob o diagnóstico contrafactual vigente, todas as nove permanecem atribuíveis ao Planner. Não restam casos `router_blocking`, `router_selection`, `router_and_planner` ou `router_latent` nesse conjunto conhecido.

## O que os 100% não significam

Os 100% nos três conjuntos de roteamento não devem ser apresentados como acurácia esperada em produção. O Router 1.2.0 foi desenvolvido à luz desses dados, inclusive dos erros do antigo Holdout 2.0.0. Eles servem agora para assegurar ausência de regressões conhecidas e coerência interna das regras.

Da mesma forma, a passagem de 14/30 para 21/30 no holdout documental é uma comparação de regressão conhecida depois do tuning. Ela mostra que as correções de rota produziram o efeito esperado nos casos que motivaram o ajuste, mas não mede desempenho em formulações inéditas.

## Evidência de CI

O gate final foi validado no head `7b91f2219b2cc484bb6cd3baca2b4dd677e10ce9`.

Workflow `router-v1.2-regression`, run `31965654038`:

- Python 3.11, job `95210317499`: PASS;
- Python 3.12, job `95210317512`: PASS;
- regressão conhecida: PASS;
- suíte completa `pytest`: PASS nas duas versões.

CI geral, run `31965654065`:

- Python 3.11, job `95210317637`: Ruff + pytest PASS;
- Python 3.12, job `95210317607`: Ruff + pytest PASS.

Os detalhes consolidados estão em `data/manifests/assistant_router_1_2_0.json`.

## Próximo gate

O próximo incremento deve ser o **Retrieval Planner 1.1.0**, mantendo o Router 1.2.0 congelado durante o ajuste. Os nove casos remanescentes podem ser usados como regressão conhecida para melhorar a seleção de escopo e temporalidade.

Depois do tuning das duas camadas, deve ser criado um **novo holdout conjunto independente**, com perguntas inéditas e congelado antes da primeira medição. Apenas esse novo conjunto poderá sustentar uma nova alegação de generalização do fluxo ajustado.

A ativação conversacional/LLM permanece posterior a esse gate.
