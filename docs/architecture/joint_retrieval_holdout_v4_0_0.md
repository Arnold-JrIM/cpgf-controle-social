# Joint Retrieval Holdout 4.0.0

## Finalidade

O Joint Retrieval Holdout 4.0.0 (JH4) foi concebido como o próximo gate independente de generalização do fluxo documental do assistente após os incrementos conhecidos Router 1.4.0 e Retrieval Planner 1.3.0.

O JH3 deixou de ser independente assim que foi medido e posteriormente utilizado para diagnóstico e tuning. Por isso, o resultado conhecido de 48/48 obtido com Router 1.4 + Planner 1.3 não pode ser usado como evidência de generalização. O JH4 separa novamente construção do teste e execução do sistema.

## Regra de independência

Este PR congela o benchmark sem executar suas perguntas no Router ou no Planner. A primeira medição deve ocorrer somente depois do merge, em um PR separado.

Durante a construção do candidato são permitidas apenas verificações que não dependem do comportamento do sistema:

- parsing e contrato estrutural do CSV;
- existência e elegibilidade dos documentos-gabarito no Knowledge governado;
- balanceamento das categorias e rotas esperadas;
- duplicidade interna;
- novidade textual contra benchmarks anteriores;
- hashes do benchmark e dos componentes congelados.

Não são permitidos nesta fase:

- `route_question`;
- `plan_knowledge_retrieval`;
- Retriever;
- LLM;
- SQL;
- embeddings externos;
- alteração do oráculo em resposta ao desempenho do sistema.

## Desenho do benchmark

O JH4 contém 48 perguntas, distribuídas igualmente entre:

- 12 `normative`;
- 12 `methodology`;
- 12 `cross_source`;
- 12 `control_external`.

As rotas esperadas totalizam:

- 24 `knowledge`;
- 12 `methodology`;
- 12 `composite`.

Cada caso congela antes da medição:

- rota esperada;
- documentos-gabarito e de apoio;
- escopos esperados;
- temporalidades esperadas;
- trilhas relacionadas, quando aplicável;
- sensibilidade à atualização documental.

## Novidade

O critério foi tornado mais rigoroso que no JH3.

Antes da primeira medição, o JH4 deve apresentar:

1. zero repetição exata após normalização;
2. zero duplicidade interna após normalização;
3. similaridade máxima por `SequenceMatcher` de 0,75 contra todos os 278 casos anteriores.

O primeiro candidate preflight válido, reproduzido em Python 3.11 e 3.12, encontrou:

- 48 casos válidos;
- zero sobreposição exata;
- maior similaridade: 0,6648648648648648;
- caso de maior similaridade: `JH4-033`;
- SHA-256 do benchmark: `a90867717d73407b586cee02ec2eeb8c075db2f86c345bb9985193e0ca31700a`.

O JSON do preflight foi idêntico byte a byte nas duas versões, com SHA-256 `4a20074607c63631d0c08f378505470ad08740054abf15712a08041707943b21`.

## Fluxo congelado

A primeira medição deverá usar exatamente:

- Router 1.4.0 — blob `89150b97e9c87d9af0d0b0f888870dcc74ef86b1`;
- Retrieval Planner 1.3.0 — blob `8fa1458c11eeabfdde155635b74a9b770e9960c1`;
- Knowledge 1.2.0.

Antes da primeira medição, o preflight falha se qualquer um desses componentes divergir do freeze.

## Critérios prospectivos de interpretação

Os critérios abaixo foram definidos antes da primeira medição. Eles são limites de governança do projeto, não testes de significância estatística:

- métrica primária: exatidão conjunta de rota + escopo + temporalidade;
- alvo conjunto: pelo menos 70%;
- piso de rota exata: 80%;
- piso de filtros conjuntos: 75%;
- piso conjunto por categoria: 50%.

O workflow de medição não poderá falhar simplesmente porque o desempenho ficar abaixo desses valores. O primeiro resultado válido deverá ser preservado integralmente, inclusive se for desfavorável.

Se todos os critérios forem atendidos, o resultado sustenta apenas avançar para uma avaliação independente do Retriever. Não sustenta prontidão de produção e não desbloqueia LLM.

## Relação com os holdouts anteriores

O JH2 teve primeira medição independente de 30% no critério conjunto. O JH3 teve primeira medição independente de 56,25%. Esses valores podem servir como contexto histórico, mas a comparação com o JH4 não é pareada porque as perguntas são diferentes.

Depois da primeira execução do JH4, suas 48 perguntas passam imediatamente a ser material conhecido. Qualquer tuning posterior baseado nelas exigirá um novo holdout independente para nova alegação de generalização.

## Sequência operacional

1. congelar JH4 neste PR;
2. fazer merge sem executar Router ou Planner sobre o JH4;
3. abrir PR separado de medição;
4. revalidar o freeze imediatamente antes da execução;
5. executar Router 1.4 + Planner 1.3 uma única primeira vez;
6. congelar o resultado independentemente do desempenho;
7. somente depois interpretar os critérios prospectivos e decidir entre diagnóstico adicional ou avaliação do Retriever.
