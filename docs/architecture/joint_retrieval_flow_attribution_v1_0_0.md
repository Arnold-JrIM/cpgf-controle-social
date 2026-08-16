# Joint Retrieval Flow Attribution Diagnostic 1.0.0

## Objetivo

Este incremento decompõe, de forma post-hoc e contrafactual, as 28 divergências observadas na primeira medição independente do `Joint Retrieval Holdout 2.0.0` entre a contribuição do `Router 1.2.0` e a contribuição do `Retrieval Planner 1.1.0`.

O diagnóstico não altera regras de nenhuma das duas camadas. O Joint Holdout 2.0 já foi medido no PR #42 e, portanto, passa a ser tratado como conjunto conhecido para diagnóstico e regressão. O resultado independente de **12/40 = 30%** permanece preservado e não é recalculado como nova evidência de generalização.

## Por que a decomposição descritiva não era suficiente

O PR #42 registrou 12 passes limpos e 28 erros conjuntos. Pela observação direta das saídas, esses 28 erros se dividiam em:

- 9 casos com rota divergente e filtros exatos;
- 1 caso com rota exata e filtros divergentes;
- 18 casos com rota e filtros divergentes.

Essa decomposição é útil, mas não é causal. O Planner recebe como entrada a pergunta e a decisão do Router; assim, um filtro incorreto observado junto com uma rota incorreta pode ser consequência da rota recebida ou pode persistir mesmo depois de corrigir a rota.

## Método contrafactual

O Joint Holdout 2.0 possui uma diferença importante em relação ao holdout anterior do Planner: **a própria rota faz parte do oráculo congelado**.

Por isso, para cada pergunta o diagnóstico executa duas etapas complementares:

1. reproduz o fluxo real `route_question(question) -> plan_knowledge_retrieval(question, decision=...)`;
2. substitui somente a `RouteDecision` real pela **rota esperada congelada**, mantendo a pergunta, o Planner, os escopos esperados e a temporalidade esperada exatamente iguais.

Esse segundo passo é o contrafactual principal de atribuição. Se a correção isolada da rota também torna os filtros exatos, a falha pode ser recuperada apenas no Router. Se os filtros continuam divergentes mesmo quando o Planner recebe a rota esperada, há contribuição do Planner.

Como diagnóstico secundário, executa-se ainda um sweep das três rotas documentais disponíveis:

- `knowledge`;
- `methodology`;
- `composite`.

O sweep verifica se alguma rota alternativa consegue produzir os filtros esperados, mas não substitui o contrafactual principal baseado na rota esperada.

## Classes de atribuição

### `pass`

A rota real é a rota esperada e os filtros de escopo e temporalidade também são exatos.

### `router_only`

A rota real diverge do oráculo. Quando apenas a rota é substituída pela rota esperada, mantendo o Planner 1.1.0 inalterado, os filtros tornam-se exatos. Corrigir o Router é suficiente para recuperar o caso dentro das regras atuais.

### `planner_only`

A rota real já é a rota esperada, mas o Planner produz escopo e/ou temporalidade divergentes. A correção de roteamento não é necessária; a fragilidade observada está nas regras internas do Planner.

### `router_and_planner`

A rota real diverge e, mesmo quando o Planner recebe a rota esperada, os filtros continuam divergentes. Nesse grupo, corrigir apenas uma camada não basta para alcançar o oráculo conjunto.

## Resultados

A decomposição dos 40 casos foi:

| Classe | Casos |
|---|---:|
| `pass` | 12 |
| `router_only` | 15 |
| `planner_only` | 1 |
| `router_and_planner` | 12 |

Assim, entre as **28 falhas conjuntas**:

- **15/28 = 53,57%** são recuperáveis corrigindo somente o Router;
- **1/28 = 3,57%** é exclusivamente do Planner;
- **12/28 = 42,86%** exigem mudanças nas duas camadas.

Considerando os casos compartilhados, o Router participa de **27/28 = 96,43%** das falhas e o Planner participa de **13/28 = 46,43%**. Essas participações se sobrepõem nos 12 casos `router_and_planner` e, por isso, não devem ser somadas.

## Resultado por categoria

| Categoria | Pass | Router only | Planner only | Router + Planner |
|---|---:|---:|---:|---:|
| `normative` | 7 | 2 | 0 | 1 |
| `methodology` | 2 | 7 | 0 | 1 |
| `cross_source` | 1 | 2 | 1 | 10 |
| `control_external` | 2 | 4 | 0 | 0 |

O padrão ajuda a localizar a fragilidade arquitetural. A maior parte dos erros metodológicos e todos os erros de controle externo observados são recuperáveis por roteamento. Em contraste, os casos `cross_source` concentram a interação entre as camadas: **10 dos 12 erros compartilhados** estão nessa categoria.

## Casos por atribuição

`pass`:
JH2-001, JH2-004, JH2-005, JH2-006, JH2-007, JH2-008, JH2-010, JH2-011, JH2-012, JH2-024, JH2-035 e JH2-036.

`router_only`:
JH2-002, JH2-009, JH2-013, JH2-014, JH2-015, JH2-017, JH2-018, JH2-019, JH2-020, JH2-022, JH2-026, JH2-037, JH2-038, JH2-039 e JH2-040.

`planner_only`:
JH2-021.

`router_and_planner`:
JH2-003, JH2-016, JH2-023, JH2-025, JH2-027, JH2-028, JH2-029, JH2-030, JH2-031, JH2-032, JH2-033 e JH2-034.

## Contrafactual de correção apenas do Router

Dos 28 erros, 15 tornam-se passes completos quando apenas a rota real é substituída pela rota esperada congelada. Mantendo o Planner 1.1.0 sem alteração, o número de passes subiria, no contrafactual diagnóstico, de **12/40 para 27/40 = 67,5%**.

Esse valor não é uma estimativa do desempenho de um futuro Router 1.3.0. Ele é um limite diagnóstico calculado sobre perguntas já conhecidas e serve somente para priorizar desenvolvimento e testar se a falha é recuperável por roteamento.

Um resultado adicional reforça essa interpretação: exatamente 27/40 casos possuem filtros exatos sob a rota esperada e também 27/40 possuem filtros exatos sob pelo menos uma das três rotas documentais testadas. Portanto, o sweep por rotas alternativas não revela capacidade adicional de recuperação além daquela já identificada pelo contrafactual da rota esperada.

## Leitura das famílias de erro

### Router

Os 15 casos `router_only` concentram-se em três famílias:

- perguntas metodológicas formuladas sem os marcadores lexicais mais explícitos usados no tuning anterior;
- consultas de controle externo que produzem filtros corretos, mas são classificadas como `unsupported`;
- algumas consultas normativas ou compostas que caem em `overview`/`unsupported` apesar de o Planner conseguir produzir o plano correto quando recebe a intenção documental adequada.

Isso indica que o próximo Router deve melhorar a identificação semântica da intenção documental e, principalmente, a distinção entre `knowledge`, `methodology` e `composite`, sem ampliar indiscriminadamente regras lexicais específicas para os 40 casos conhecidos.

### Planner

O único caso `planner_only`, JH2-021, envolve repetição/fracionamento e exige temporalidade `current + contextual`, embora a rota `knowledge` já esteja correta.

Os 12 casos compartilhados mostram uma questão mais ampla. Dez são `cross_source` e exigem composição de universos que o Planner 1.1.0 não representa adequadamente mesmo quando recebe a rota esperada. Entre os padrões observados estão:

- `cpgf_core + methodology`;
- `control_external + methodology`;
- `control_external + cpgf_core`;
- combinação de fontes `current + contextual`.

Assim, o Planner 1.2.0 deve ser desenvolvido depois do Router e focar a inferência de escopos compostos e temporalidade multifuente, em vez de compensar erros de roteamento.

## Sequência recomendada

A decomposição sustenta a seguinte ordem de trabalho:

1. **Router 1.3.0** em incremento separado, com Planner 1.1.0 congelado, priorizando os 15 casos `router_only` e o componente de roteamento dos 12 casos compartilhados;
2. regressão do Router novo sobre todos os conjuntos já conhecidos, incluindo Joint Holdout 2.0 apenas como regressão;
3. **Retrieval Planner 1.2.0** em incremento separado, priorizando JH2-021 e os 12 casos compartilhados, especialmente as combinações `cross_source`;
4. regressão conjunta sem alterar o Joint Holdout 2.0;
5. criação e congelamento de um **Joint Holdout 3.0 independente** antes da primeira medição do fluxo ajustado;
6. somente após esse novo teste independente reavaliar prontidão do fluxo e o gate para ativação do LLM.

## Validação e reprodutibilidade

O diagnóstico inicial foi executado no GitHub Actions run `31968231927`.

Python 3.11:

- job `95216550651`;
- artifact `9269070250`;
- digest `sha256:b7e4129eecaa6243a9fe96da848dc291bcf99a67e8f72f064711b99e4cb03d7f`.

Python 3.12:

- job `95216550699`;
- artifact `9269071719`;
- digest `sha256:ec979583df2c9820d2fe774ce3e7de1cc25f1b5cc412d567531e57aab8e06c79`.

O conteúdo JSON produzido pelos dois ambientes foi idêntico, com SHA-256 `9fc67bb66dc2da3c43f75c11444799a9b95467124de47860bf0a0adbb7075bef`.

## Governança

O diagnóstico 1.0.0:

- preserva integralmente a primeira medição independente do PR #42;
- trata Joint Holdout 2.0 como conjunto conhecido;
- não altera Router 1.2.0;
- não altera Retrieval Planner 1.1.0;
- não altera perguntas ou oráculos;
- não chama LLM;
- não executa SQL;
- não chama Retriever ou embeddings externos;
- não realiza tuning neste incremento;
- não constitui nova alegação de generalização;
- mantém bloqueada a ativação do LLM até novo gate independente após tuning.
