# Joint Retrieval Holdout 4.0.0

## Finalidade

O Joint Retrieval Holdout 4.0.0 (JH4) foi concebido como novo gate independente de generalização após os incrementos conhecidos Router 1.4.0 e Retrieval Planner 1.3.0.

O JH3 deixou de ser independente assim que foi medido e posteriormente utilizado para diagnóstico e tuning. Por isso, o resultado conhecido de 48/48 obtido com Router 1.4 + Planner 1.3 não podia ser usado como evidência de generalização. O JH4 separou novamente construção do teste e execução do sistema.

## Construção e independência

O benchmark foi criado e congelado no PR #50 sem executar suas perguntas no Router ou no Planner. Durante essa fase foram permitidas apenas verificações independentes do comportamento do sistema: parsing, contrato estrutural, catálogo governado, balanceamento, duplicidade, novidade textual e hashes.

O JH4 contém 48 perguntas, igualmente distribuídas entre `normative`, `methodology`, `cross_source` e `control_external`. As rotas esperadas são 24 `knowledge`, 12 `methodology` e 12 `composite`.

Cada caso congelou antes da primeira medição a rota, documentos-gabarito e de apoio, escopos, temporalidades, trilhas relacionadas e sensibilidade à atualização documental.

## Novidade

O JH4 adotou limite prospectivo mais rigoroso que o JH3:

- zero repetição exata após normalização;
- zero duplicidade interna;
- similaridade máxima por `SequenceMatcher` de 0,75 contra 278 perguntas anteriores.

O primeiro candidate preflight válido encontrou maior similaridade de 0,6648648648648648 (`JH4-033`) e nenhuma sobreposição exata. Nenhuma pergunta precisou ser reescrita depois desse preflight.

SHA-256 congelado do benchmark: `a90867717d73407b586cee02ec2eeb8c075db2f86c345bb9985193e0ca31700a`.

## Fluxo congelado

A primeira medição usou exatamente:

- Router 1.4.0 — blob `89150b97e9c87d9af0d0b0f888870dcc74ef86b1`;
- Retrieval Planner 1.3.0 — blob `8fa1458c11eeabfdde155635b74a9b770e9960c1`;
- Knowledge 1.2.0.

O preflight executado imediatamente antes da medição confirmou correspondência exata entre fluxo corrente e fluxo congelado.

## Critérios prospectivos

Antes da primeira medição foram registrados os seguintes limites de governança:

- métrica primária: exatidão conjunta de rota + escopo + temporalidade;
- alvo conjunto: pelo menos 70%;
- piso de rota exata: 80%;
- piso de filtros conjuntos: 75%;
- piso conjunto por categoria: 50%.

Esses limites não são testes de significância estatística e não determinam sucesso ou falha do workflow. O primeiro resultado válido deveria ser preservado mesmo se desfavorável.

## Primeira medição independente

A primeira medição válida ocorreu no run `31977328529`, head `fc77fa2340b9e3cf1ffed1ffa438ef74d38370f8`.

Resultados globais:

- rota exata: 20/48 = 41,67%;
- escopo exato: 28/48 = 58,33%;
- temporalidade exata: 25/48 = 52,08%;
- filtros conjuntos: 24/48 = 50,00%;
- rota + escopo + temporalidade: 18/48 = 37,50%.

Resultados conjuntos por categoria:

- `normative`: 7/12 = 58,33%;
- `methodology`: 5/12 = 41,67%;
- `control_external`: 5/12 = 41,67%;
- `cross_source`: 1/12 = 8,33%.

Python 3.11 e 3.12 produziram JSONs byte a byte idênticos. O SHA-256 comum do JSON de medição é `0004fd93146c36bd6218663b85ad3eb8604303cb46a7d83a1c093bd54458988e`.

## Confronto com os critérios prospectivos

Nenhum dos quatro critérios globais foi atendido:

- alvo conjunto de 70%: não atendido (37,50%);
- piso de rota de 80%: não atendido (41,67%);
- piso de filtros de 75%: não atendido (50,00%);
- piso de 50% em todas as categorias: não atendido.

Somente a categoria `normative` superou individualmente o piso de 50%. O resultado, portanto, **não desbloqueia a avaliação independente do Retriever**, não sustenta prontidão de produção e não desbloqueia LLM.

## Leitura metodológica

O JH4 fornece nova evidência independente de generalização, mas a evidência é insuficiente para os critérios de avanço definidos prospectivamente. O contraste com JH2 (30%) e JH3 (56,25%) é apenas histórico e não pareado, pois os conjuntos são diferentes.

O fato de Router 1.4 + Planner 1.3 alcançarem 48/48 nos conjuntos conhecidos e 18/48 no JH4 independente mostra por que resultados pós-tuning não devem ser confundidos com generalização para formulações novas.

Uma decomposição observacional das 48 perguntas registra:

- 18 passes;
- 6 casos com rota errada e filtros exatos;
- 2 casos com rota exata e filtros errados;
- 22 casos com rota e filtros divergentes.

Essa decomposição **não constitui atribuição causal**. Como no JH3, a próxima etapa deve usar contrafactual explícito, corrigindo apenas a rota para o gabarito e mantendo Planner e pergunta congelados.

## Governança após a medição

Após o run oficial, o JH4 passou imediatamente a ser material conhecido. O workflow de primeira medição ficou disponível apenas para reprodução manual. Nenhum tuning foi realizado neste PR, e `router.py` e `retrieval_planner.py` permanecem inalterados.

Qualquer tuning futuro com base no JH4 exigirá um novo holdout independente para nova alegação de generalização.

## Próximo passo

O próximo PR deve executar diagnóstico contrafactual post-hoc do JH4 antes de qualquer ajuste operacional. O objetivo é separar, entre as 30 falhas conjuntas, a contribuição do Router, do Planner e da interação entre as duas camadas. Somente depois desse diagnóstico poderá ser definida uma nova sequência de tuning, seguida obrigatoriamente por outro holdout independente.
