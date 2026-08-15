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

O benchmark separa `gold_document_ids` de `supporting_document_ids`. O primeiro grupo é elegível para avaliação de recuperação. O segundo permite registrar fontes governadas relevantes que ainda são metadata-only, sem penalizar o retriever por um conteúdo que não está materializado em chunks.

## Baseline e evolução

O PR que introduz o benchmark **não modifica o roteador existente**. A baseline determinística é medida como ela se encontra. Isso permite que uma futura mudança de roteamento seja comparada contra um ponto de referência congelado, em vez de alterar simultaneamente o teste e o sistema testado.

A mesma lógica vale para recuperação: lexical, semântica e híbrida devem ser comparadas sobre o mesmo conjunto de perguntas e documentos-gabarito.

## Limites

O benchmark não afirma que uma única resposta textual é a única correta. `expected_concepts` registra elementos mínimos, enquanto `forbidden_claims` registra conclusões categóricas incompatíveis com a governança do projeto.

A avaliação automática de texto é deliberadamente simples. Antes de uso acadêmico como medida de qualidade final do LLM, deverá ser complementada por rubrica humana e, se necessário, avaliação cega por mais de um avaliador.

Casos marcados como `freshness_sensitive` não devem ser respondidos categoricamente com base apenas em memória do modelo. Quando a busca web controlada for implementada, esses casos também servirão para testar o acionamento da verificação de vigência.
