# Joint Retrieval Holdout 5.0.0 — freeze prospectivo

## Finalidade

O JH5 é o primeiro holdout criado **depois** da seleção da arquitetura semântica `B_llm_route`. Sua função é produzir evidência independente sobre a capacidade de generalização da candidata, sem reutilizar o JH4 como teste de validação.

A candidata foi congelada no PR #56 antes do início da autoria deste benchmark. Durante a construção e o preflight do JH5, nenhuma saída da candidata foi consultada e nenhuma chamada ao GPT-4o mini foi realizada.

## Desenho

O benchmark contém 48 perguntas:

- 12 `normative`;
- 12 `methodology`;
- 12 `cross_source`;
- 12 `control_external`.

As rotas-gabarito permanecem balanceadas conforme o protocolo prospectivo:

- 24 `knowledge`;
- 12 `methodology`;
- 12 `composite`.

Cada caso fixa antes da primeira medição:

- rota esperada;
- documentos-gabarito e documentos de apoio;
- escopos esperados;
- temporalidades esperadas;
- trilhas relacionadas, quando pertinentes;
- sensibilidade temporal.

O arquivo congelado possui SHA-256 `2695be52ff403043c394f0ca7f9f0a47f209fd2016172586146c69adf5595354`, contém 33 documentos-gabarito, 35 documentos referenciados e dois casos deliberadamente sensíveis a atualização normativa.

## Independência e novidade

A autoria foi feita a partir do corpus governado e dos objetivos temáticos do projeto, sem usar previsões da candidata B. O preflight compara o texto normalizado das 48 perguntas com todos os CSVs históricos do diretório `data/benchmarks` que contenham a coluna `question`.

Foram definidos antes da medição:

- sobreposição exata normalizada permitida: zero;
- similaridade máxima SequenceMatcher: 0,70;
- universo histórico esperado: 326 perguntas anteriores.

O limite é mais estrito que o utilizado no JH4 (0,75).

O preflight limpo `31983949246`, executado sobre o head de evidência `f014aa62ad8793bdaeae50be13db2b7c22f410e5`, passou em Python 3.11 e 3.12. Foram comparados oito benchmarks e 326 perguntas históricas, sem sobreposição exata normalizada. A maior similaridade foi `0.6801346801346801`, no caso `JH5-014`, portanto abaixo do limite prospectivo de 0,70. Os cinco maiores valores foram:

1. `JH5-014`: 0.6801346801346801;
2. `JH5-023`: 0.6666666666666666;
3. `JH5-048`: 0.6460674157303371;
4. `JH5-047`: 0.644927536231884;
5. `JH5-046`: 0.6311475409836066.

Os artifacts ZIP dos dois ambientes possuem metadados de empacotamento distintos, mas os arquivos `joint_retrieval_holdout_v5_preflight.json` internos são byte a byte idênticos, com 3.849 bytes e SHA-256 `4a1ac8eb94682c03bcfb7f40e8e2ff1281ebbe768cf6ff7510c22aaaa6c69c66`.

## Candidata congelada

A arquitetura que futuramente poderá ser executada sobre este benchmark é exclusivamente:

`pergunta -> GPT-4o mini (rota) -> Retrieval Planner 1.3 -> filtros`

O freeze inclui:

- `gpt-4o-mini-2024-07-18`;
- OpenAI SDK 3.1.0;
- três repetições;
- Structured Outputs estrito;
- Provider congelado por Git blob SHA;
- Planner 1.3 congelado por Git blob SHA;
- dependência de tipos do Router 1.4 congelada por Git blob SHA;
- nenhuma ferramenta externa, Retriever, SQL ou geração de resposta final.

O preflight falha se qualquer uma dessas dependências divergir do manifesto congelado antes da primeira medição.

## Gate prospectivo

A primeira medição do JH5 deverá ser preservada independentemente do resultado. Para que a candidata passe o gate amplo de generalização, todos os critérios abaixo precisam ser satisfeitos:

1. três repetições completas;
2. zero violações de schema;
3. exatidão conjunta média de B >= 50%;
4. ganho conjunto absoluto de B sobre A >= 10 pontos percentuais;
5. exatidão média de rota de B >= 75%;
6. estabilidade modal média >= 0,90;
7. exatidão conjunta média de B >= 25% em cada uma das quatro categorias.

Esses limites são regras de governança do projeto, não testes de significância estatística. Falhar em qualquer critério não autoriza tuning retrospectivo nem uma segunda tentativa sobre o JH5 como se fosse independente.

## O que este incremento não faz

Este freeze não:

- executa GPT-4o mini;
- executa o Router determinístico;
- executa o Planner;
- chama Retriever;
- usa embeddings externos;
- executa SQL;
- altera T01–T09;
- habilita LLM em produção.

Somente após o merge deste freeze e a aprovação do preflight será criado um incremento separado para a primeira medição independente.
