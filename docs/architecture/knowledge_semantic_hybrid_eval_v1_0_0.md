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

## Execução local planejada

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

A avaliação registra resultados `governed` e `unfiltered` para os três métodos, além de hashes, validações e telemetria lógica do provider.

## Regra de interpretação

A comparação deverá ser observacional e pareada no mesmo benchmark/corpus. Não será escolhido um método por impressão subjetiva. A decisão considerará Hit Rate@5, Mean Document Recall@5, MRR e MAP@5, com atenção específica à categoria normativa e aos quatro casos em que a baseline lexical governada não encontrou gold no top 5 (`KRET-001`, `KRET-004`, `KRET-010`, `KRET-013`).

Um documento fora do gabarito pode ainda ser materialmente pertinente; por isso as métricas medem aderência ao gabarito congelado, não verdade absoluta de relevância.
