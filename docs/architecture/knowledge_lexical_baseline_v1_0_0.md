# Knowledge — baseline lexical 1.0.0

## Objetivo

Este incremento registra a primeira medição da recuperação lexical sobre o corpus Knowledge real, usando o Retrieval Benchmark 1.0.0 congelado anteriormente. A medição não altera o benchmark, não ativa LLM, não executa SQL e não utiliza embeddings externos.

## Protocolo

- Knowledge: `1.2.0`
- Retrieval Benchmark: `1.0.0`
- método: `lexical`
- corte: `k = 5`
- benchmark SHA-256: `6633babe7e17f4c0fefb0523ea477a11257bad87d3c0bc258dea7db1c33c1777`
- chunks SHA-256: `43c7d61e8b963c5b8b1ad747ec24c2cdb5e464d403ea9b2b3776f19a5cb65b7c`
- JSON local completo SHA-256: `1a6293ea259ff3d0498f6123b4db9fe40f08e55efc435271e14be36b12833922`

O preflight confirmou 30 casos, 24 documentos-gabarito distintos e presença de chunks para 24/24 documentos-gabarito. Nenhum gold estava ausente.

## Corpus local medido

O build local validado produziu:

- 45 documentos catalogados;
- 44 documentos disponíveis localmente;
- 1 documento metadata-only;
- 41 documentos efetivamente ingeridos;
- 3 documentos disponíveis deliberadamente não ingeridos;
- 1.970 chunks;
- 1.610 chunks elegíveis para recuperação padrão;
- validação `PASS`.

Os três documentos disponíveis não ingeridos são as duas obras completas de Mark J. Nigrini mantidas apenas para descoberta e o PDF `Referencias - CPGF`, que não deve funcionar como evidência final. O capítulo específico de Nigrini usado no benchmark permanece ingerido.

## Atualizações de contrato anteriores à primeira medição

Duas fontes foram substituídas por versões text-searchable antes da primeira avaliação válida e tiveram seus contratos atualizados:

1. `carmo-inconformidade-cpgf-2018`: SHA-256 `a61af5a7d51ab780b766a0ab853bbad8761b28a1b3baf16e2e8aa2e6bb3835a2`, 12.563.016 bytes e 21 páginas.
2. `siafi-macrofuncao-021121-2026`: SHA-256 `b845718989fc14f774e22e8ed455e97fb1e277a3a9ba485cf6af01a20c097cb2`, 474.615 bytes e 23 páginas. A edição de 21/07/2026 passou a ser ingerida e elegível para recuperação padrão.

Essas mudanças ocorreram antes da primeira medição lexical real. O benchmark permaneceu congelado.

## Resultados agregados

| Métrica | Governed | Unfiltered | Diferença |
|---|---:|---:|---:|
| Hit Rate@5 | 0,8667 | 0,7333 | +0,1333 |
| Mean Document Recall@5 | 0,6944 | 0,5500 | +0,1444 |
| MRR | 0,6506 | 0,5694 | +0,0811 |
| MAP@5 | 0,5184 | 0,4443 | +0,0742 |

No benchmark utilizado, o modo governado superou o modo sem filtros nas quatro métricas agregadas. Isso é evidência favorável ao uso de filtros de escopo, temporalidade e recuperação padrão, mas não demonstra superioridade sobre métodos semânticos ou híbridos.

### Resultado por categoria — modo governado

| Categoria | Casos | Hit Rate@5 | Recall@5 | MRR | MAP@5 |
|---|---:|---:|---:|---:|---:|
| control_external | 1 | 1,0000 | 1,0000 | 1,0000 | 1,0000 |
| cross_source | 8 | 1,0000 | 0,7083 | 0,8375 | 0,5958 |
| methodology | 6 | 0,8333 | 0,7500 | 0,8333 | 0,7500 |
| normative | 15 | 0,8000 | 0,6444 | 0,4544 | 0,3524 |

A categoria normativa é o principal espaço de melhoria do ranking lexical, sobretudo porque fontes institucionais recentes e semanticamente próximas podem aparecer antes de normas primárias específicas.

## Casos sem gold no top 5 — modo governado

- `KRET-001`
- `KRET-004`
- `KRET-010`
- `KRET-013`

Esses casos devem ser preservados como erros da baseline lexical. Não serão corrigidos alterando o benchmark ou reponderando o método antes da comparação com recuperação semântica e híbrida.

## Interpretação e limites

A avaliação mede recuperação em nível de documento contra um gabarito previamente congelado. Um documento recuperado que não esteja no gold pode ainda ser materialmente pertinente; por isso, as métricas não equivalem a julgamento absoluto de relevância de cada fonte. A Macrofunção SIAFI, por exemplo, passou a ser uma fonte oficial recuperável antes desta medição e pode aparecer legitimamente em consultas normativas mesmo quando o gold privilegia a norma primária.

Esta baseline também não mede qualidade da resposta final do assistente. Nenhum LLM foi chamado. O resultado será usado como referência para comparar, no mesmo benchmark e corpus, recuperação lexical, semântica e híbrida.

## Evidência congelada

O manifesto versionado é `data/manifests/knowledge_lexical_baseline_1_0_0.json`. O JSON local completo da avaliação permanece fora do Git, mas sua integridade é verificável pelo SHA-256 registrado no manifesto.
