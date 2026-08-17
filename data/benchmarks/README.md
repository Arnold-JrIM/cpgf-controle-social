# Benchmark do Assistente 1.0.0

Este diretório versiona o conjunto de referência para avaliar o Assistente IA antes da ativação de conversa com LLM.

O benchmark não é um conjunto de respostas prontas. Cada caso registra a intenção esperada, a camada de evidência, ferramentas read-only, documentos-gabarito, trilhas relacionadas, conceitos que uma resposta deve cobrir e afirmações categóricas que não devem ser produzidas.

## Famílias

- `conceptual_normative`: conceitos e normas sobre suprimento de fundos/CPGF;
- `serving_query`: consultas que devem ser respondidas pelo Serving;
- `trail_query`: consultas sobre prevalência e recorrência de T01–T09;
- `motor_rule`: explicação do funcionamento das regras do projeto;
- `safety_interpretation`: perguntas que testam inferências indevidas, temporalidade e cautela.

A versão 1.0.0 contém 50 perguntas: 16 conceituais/normativas, 8 consultas ao Serving, 8 consultas de trilhas, 9 perguntas sobre o motor T01–T09 e 9 casos de interpretação segura.

## Fontes que inspiraram a linguagem das perguntas

Dois materiais fornecidos pelo usuário orientaram a redação em linguagem cidadã: um FAQ institucional da UFJF/PROGEFI e a cartilha histórica da CGU `Suprimento de Fundos e Cartão de Pagamento — Perguntas & Respostas`.

Esses materiais **não são automaticamente o gabarito normativo atual**. Regras internas da UFJF não são generalizadas para toda a Administração Pública Federal; referências históricas da cartilha da CGU não substituem normas vigentes. Os `gold_document_ids` apontam apenas para documentos já governados no Knowledge 1.2.0.

## Métricas

`evaluate_routing` mede acerto exato da rota e separa os alvos que o roteador determinístico atual é capaz de representar.

`evaluate_retrieval` mede, em nível de documento:

- Hit Rate@k;
- Mean Document Recall@k;
- MRR.

A avaliação lexical pode ser executada integralmente de forma local. Avaliações `semantic` e `hybrid` só são executadas quando o operador fornece um índice real e opta explicitamente pelo envio das consultas ao provedor externo de embeddings.

`evaluate_answer_contract` prepara a etapa posterior de avaliação do LLM, medindo cobertura lexical de conceitos esperados e presença de afirmações proibidas. Essa checagem é um gate simples e não substitui avaliação humana.

## Execução

Apenas roteamento e contrato:

```bash
python scripts/evaluate_assistant_benchmark.py
```

Recuperação lexical no corpus local:

```bash
python scripts/evaluate_assistant_benchmark.py \
  --bundle-dir data/knowledge/processed \
  --retrieval-method lexical \
  --output data/knowledge/processed/benchmark_lexical.json
```

Semântico/híbrido, somente após geração do índice e com opt-in explícito:

```bash
python scripts/evaluate_assistant_benchmark.py \
  --bundle-dir data/knowledge/processed \
  --embeddings-dir data/knowledge/processed \
  --retrieval-method hybrid \
  --allow-external-embeddings
```

Os resultados locais permanecem fora do Git até serem revisados e congelados em manifesto próprio.

## Orchestration Holdout 2.0.0

`orchestration_holdout_v2_0_0.csv.gz` é o segundo holdout prospectivo do Semantic
Evidence Orchestrator. Ele contém 56 casos novos, balanceados entre as sete combinações
não vazias de `DATA`, `KNOWLEDGE` e `WEB`.

O OH2 foi congelado depois da normalização governada do Orchestrator 1.1.0 e antes de
qualquer execução das suas perguntas com `gpt-4o-mini`. Seu universo histórico de
novidade também é congelado: 10 benchmarks anteriores, 430 perguntas e inclusão
explícita do OH1, que já é conhecido.

Hash SHA-256 do arquivo gzip: `0a5c6eda6ffa2bd9cd6bbcf8ae983e4906f564b0c1884fab0c8f28c5e3244c3b`.

O preflight é totalmente offline. A primeira medição independente deve ocorrer somente
depois do merge do freeze e ser preservada mesmo se o gate prospectivo falhar.
