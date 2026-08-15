# Benchmark de Recuperação e Roteamento 1.0.0

## Finalidade

O benchmark cria uma base estável para avaliar o futuro Assistente IA do CPGF antes que alterações no roteador, no retriever ou no LLM sejam aceitas por impressão subjetiva.

A pergunta de avaliação deixa de ser apenas “o chatbot respondeu bem?” e passa a ser decomposta em:

1. a intenção foi roteada para a camada correta?
2. quando a resposta depende de dados, foi selecionada uma ferramenta read-only compatível?
3. quando depende de norma/literatura, documentos relevantes foram recuperados?
4. a resposta respeita temporalidade, escopo institucional e limites de inferência?
5. sinais analíticos foram apresentados como triagem, sem conclusão automática de irregularidade?

## Desenho

A versão 1.0.0 possui 50 casos em cinco famílias. As perguntas conceituais e normativas foram redigidas em linguagem próxima à encontrada nos materiais de perguntas e respostas fornecidos pelo usuário. Consultas ao Serving e às trilhas foram adicionadas para representar o uso real da plataforma; perguntas sobre T01–T09 garantem cobertura integral do motor; e casos adversariais leves avaliam inferências que o sistema deve evitar.

A distribuição congelada é: 16 casos `conceptual_normative`, 8 `serving_query`, 8 `trail_query`, 9 `motor_rule` e 9 `safety_interpretation`. No total, 29 casos exigem Knowledge, 17 exigem Serving e 6 são marcados como sensíveis à atualização ou vigência.

O benchmark separa `gold_document_ids` de `supporting_document_ids`. O primeiro grupo é elegível para avaliação de recuperação. O segundo permite registrar fontes governadas relevantes que ainda são metadata-only, sem penalizar o retriever por um conteúdo que não está materializado em chunks.

## Baseline de roteamento

O PR que introduz o benchmark **não modifica o roteador existente**. A baseline determinística foi executada sobre os 50 casos e resultou em 22 rotas exatas, correspondentes a acurácia global de 44%.

Essa métrica global não deve ser interpretada isoladamente. Dezesseis casos têm como rota-alvo `knowledge` e cinco têm como rota-alvo `composite`; essas rotas ainda não fazem parte do contrato do roteador atual. Considerando apenas os 29 casos cuja rota-alvo já é representável pela arquitetura existente, foram observados 22 acertos, equivalentes a 75,86%.

A diferença entre as duas métricas separa duas classes de lacuna. A primeira é arquitetural e deliberada, associada às futuras rotas `knowledge` e `composite`. A segunda decorre de ambiguidades reais entre rotas já existentes, que poderão ser tratadas em evolução posterior do roteador sem alterar o conjunto de referência.

A baseline foi validada pelo workflow `assistant-benchmark-smoke`, run `31905939264`, no commit `83f5715ee654072cb32828c5acb3ed4bf555b319`. O artefato `assistant-benchmark-routing-baseline` foi publicado com ID `9252338092` e SHA-256 `e3bf4fbf02b76e0b48dae7af5a6e5c26e0e7872c5d332bb487755a289a4bc2f3`. O manifesto congelado está em `data/manifests/assistant_benchmark_1_0_0.json`.

Depois da validação funcional, o workflow de smoke voltou a `workflow_dispatch` apenas. Isso preserva a possibilidade de repetir a avaliação sob demanda sem introduzir uma execução pesada ou redundante em cada push.

## Recuperação documental

A mesma lógica de congelamento vale para recuperação. Lexical, semântica e híbrida devem ser comparadas sobre o mesmo conjunto de perguntas e documentos-gabarito.

A infraestrutura de avaliação calcula, em nível documental, `Hit Rate@k`, `Mean Document Recall@k` e `MRR`. A versão 1.0.0 registra 12 documentos distintos utilizados como `gold_document_ids`.

A avaliação semântica ou híbrida não autoriza automaticamente chamadas externas. Quando um provedor de embeddings for utilizado, a execução deve permanecer explícita e separada do CI padrão, preservando os contratos de credencial e de governança do Knowledge.

## Avaliação de respostas

O benchmark não afirma que uma única resposta textual é a única correta. `expected_concepts` registra elementos mínimos, enquanto `forbidden_claims` registra conclusões categóricas incompatíveis com a governança do projeto.

A avaliação automática de texto é deliberadamente simples. Antes de uso acadêmico como medida de qualidade final do LLM, deverá ser complementada por rubrica humana e, se necessário, avaliação cega por mais de um avaliador.

Em particular, o benchmark preserva a distinção entre sinal analítico e irregularidade confirmada. Divergência estatística, recorrência, concentração, proximidade de referência financeira ou acionamento de uma trilha não produzem, por si sós, conclusão automática sobre fraude ou ilegalidade.

Casos marcados como `freshness_sensitive` não devem ser respondidos categoricamente com base apenas em memória do modelo. Quando a busca web controlada for implementada, esses casos também servirão para testar o acionamento da verificação de vigência.

## Regra de evolução

A versão 1.0.0 deve permanecer congelada como conjunto de referência. Melhorias de roteador, retriever ou LLM devem ser avaliadas contra este benchmark sem editar perguntas, rotas esperadas ou documentos-gabarito apenas para elevar métricas.

Se uma revisão acadêmica revelar erro material no gabarito, a correção deve ser documentada e resultar em nova versão do benchmark. Essa regra evita que o instrumento de avaliação se adapte retrospectivamente ao sistema que pretende medir.
