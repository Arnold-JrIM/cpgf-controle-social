# Knowledge Semantic/Hybrid Evaluation 1.0.0

## Objetivo

Comparar recuperação lexical, semântica e híbrida no mesmo Retrieval Benchmark 1.0.0 e no mesmo `chunks.parquet` usados na primeira baseline lexical do Knowledge 1.2.0.

Esta etapa avalia recuperação documental, não resposta final de LLM.

## Referência congelada

A execução é travada pelo manifesto `data/manifests/knowledge_lexical_baseline_1_0_0.json`.

O protocolo exige, antes de qualquer chamada externa:

- benchmark SHA-256 `6633babe7e17f4c0fefb0523ea477a11257bad87d3c0bc258dea7db1c33c1777`;
- chunks SHA-256 `43c7d61e8b963c5b8b1ad747ec24c2cdb5e464d403ea9b2b3776f19a5cb65b7c`;
- 30 perguntas e 24 documentos-gabarito cobertos pelo corpus;
- `k=5` para comparabilidade direta com a baseline lexical.

Se benchmark ou corpus divergirem, a execução deve falhar antes da medição.

## Provider semântico

A implementação de referência utiliza `text-embedding-3-small`, 768 dimensões, por opt-in explícito. O índice vetorial permanece local, fora do Git, e fica vinculado criptograficamente ao `chunks.parquet` por manifesto.

O provider mantém cache em memória para que uma mesma pergunta, repetida entre modos governado/sem filtros e entre métodos semântico/híbrido, não gere chamadas externas redundantes dentro da mesma execução.

## Consentimento e fronteira de dados

A construção do índice requer `--allow-external-embeddings`, porque o texto dos chunks será enviado ao provider de embeddings. A avaliação semântica/híbrida exige a mesma flag porque as perguntas do benchmark também serão enviadas ao provider.

Nenhuma chave de API deve ser versionada. A credencial é fornecida apenas pela variável de ambiente `OPENAI_API_KEY` da sessão local.

Nenhum LLM conversacional é chamado, nenhum SQL é executado e nenhum PDF ou índice vetorial é commitado.

## Execução local

Primeiro deve ser feito um preflight inteiramente local, sem chave de API e sem chamada externa:

```powershell
python scripts/build_semantic_index.py `
  --bundle-dir data/knowledge/processed `
  --output-dir data/knowledge/semantic_index `
  --model text-embedding-3-small `
  --dimensions 768 `
  --batch-size 64 `
  --dry-run
```

Somente após `KNOWLEDGE SEMANTIC INDEX PREFLIGHT: PASS`, a construção real pode ser executada com credencial de sessão e consentimento explícito:

```powershell
$env:OPENAI_API_KEY="<CHAVE_DA_SESSAO>"

python scripts/build_semantic_index.py `
  --bundle-dir data/knowledge/processed `
  --output-dir data/knowledge/semantic_index `
  --model text-embedding-3-small `
  --dimensions 768 `
  --batch-size 64 `
  --allow-external-embeddings
```

Depois:

```powershell
python scripts/evaluate_knowledge_retrieval.py `
  --methods lexical,semantic,hybrid `
  --k 5 `
  --semantic-index-dir data/knowledge/semantic_index `
  --allow-external-embeddings `
  --output data/evidence/knowledge_retrieval/semantic_hybrid_eval_v1_0_0.json
```

Ao final da sessão, a variável pode ser removida com:

```powershell
Remove-Item Env:OPENAI_API_KEY
```

## Evidência da execução

O índice local foi construído sobre 1.970 chunks com `text-embedding-3-small` e 768 dimensões. O artefato `embeddings.parquet` permaneceu fora do Git, com SHA-256 `f11396ef4b3d48efa6f5bcfbce574b52064a087cfcd6b485dcba8fec9fdfa351`. A construção utilizou 31 requisições externas e 1.970 textos incorporados.

O resultado completo da avaliação também permaneceu local. Seu SHA-256 é `d07c6ef4839718acd74636a9a8ed38917cdce13b49a0eb2fbb75309ec4078a22`; o resumo verificável foi congelado em `data/manifests/knowledge_semantic_hybrid_eval_1_0_0.json`.

A avaliação reutilizou exatamente o benchmark e o corpus da baseline lexical. A validação confirmou 30 casos, 24 documentos-gabarito e 24/24 gabaritos com chunks. A telemetria registrou 30 requisições para 30 perguntas, com cache de consultas habilitado.

## Resultados

No modo governado, os resultados agregados foram:

| Método | Hit Rate@5 | Mean Document Recall@5 | MRR | MAP@5 |
|---|---:|---:|---:|---:|
| Lexical | 0,8667 | 0,6944 | 0,6506 | 0,5184 |
| Semântico | **0,9667** | **0,8944** | 0,7167 | **0,6782** |
| Híbrido | **0,9667** | 0,8333 | **0,7344** | 0,6441 |

Em relação ao lexical governado, o semântico elevou o Hit Rate@5 em 10 pontos percentuais, o Mean Document Recall@5 em 20 pontos percentuais e o MAP@5 em aproximadamente 0,160. O híbrido também elevou o Hit Rate@5 em 10 pontos percentuais e apresentou o maior MRR agregado, embora com recall documental e MAP inferiores aos do semântico.

Na categoria normativa, o semântico apresentou Hit Rate@5 de 0,9333, Mean Document Recall@5 de 0,7889, MRR de 0,6722 e MAP@5 de 0,5993. O híbrido obteve os mesmos 0,9333 de Hit Rate@5, mas recall documental de 0,7667, MRR de 0,6467 e MAP@5 de 0,5581. A baseline lexical normativa havia obtido, respectivamente, 0,8000, 0,6444, 0,4544 e 0,3524.

Os quatro casos sem gold no top 5 do lexical governado eram `KRET-001`, `KRET-004`, `KRET-010` e `KRET-013`. Tanto o semântico quanto o híbrido recuperaram gold em `KRET-001`, `KRET-010` e `KRET-013`. O único caso que permaneceu sem gold no top 5 foi `KRET-004`.

A governança continuou útil nos métodos vetoriais. No semântico, o modo governado preservou o Hit Rate@5 de 0,9667 e elevou recall, MRR e MAP em relação ao modo sem filtros. No híbrido, o modo governado melhorou as quatro métricas agregadas em relação ao modo sem filtros.

## Interpretação

A comparação é observacional e pareada no mesmo benchmark/corpus. Os resultados não justificam selecionar um método apenas por uma métrica isolada. O semântico foi o método mais forte em cobertura documental e MAP; o híbrido apresentou o maior MRR agregado. Para um RAG em que omitir uma fonte normativa ou metodológica relevante é especialmente indesejável, o desempenho de recall do semântico é um sinal importante, mas a política de produção deve ser definida em incremento posterior e validada sem alterar este benchmark retroativamente.

Um documento fora do gabarito pode ainda ser materialmente pertinente; por isso as métricas medem aderência ao gabarito congelado, não verdade absoluta de relevância. Da mesma forma, esta etapa não avalia correção factual, redação, citações ou segurança da resposta final de um LLM.
