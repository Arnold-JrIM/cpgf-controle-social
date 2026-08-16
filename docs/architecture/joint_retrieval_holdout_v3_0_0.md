# Joint Retrieval Holdout 3.0.0

## Objetivo

O Joint Retrieval Holdout 3.0.0 mede, de forma independente, a generalização do fluxo determinístico `Router 1.3.0 -> Retrieval Planner 1.2.0` depois dos tunings realizados sobre conjuntos já conhecidos.

O holdout não avalia o Retriever nem um LLM. Sua métrica primária é a correspondência exata conjunta de **rota + escopos documentais + temporalidades**.

## Construção antes da medição

Foram definidos 48 casos, balanceados em 12 perguntas por categoria:

- `normative`;
- `methodology`;
- `cross_source`;
- `control_external`.

As rotas esperadas também foram fixadas antes da execução do fluxo: 24 `knowledge`, 12 `methodology` e 12 `composite`.

Para reduzir reutilização textual dos benchmarks anteriores, foi estabelecido prospectivamente o seguinte critério de novidade antes de qualquer chamada ao Router ou Planner:

1. zero repetição exata após normalização;
2. similaridade máxima `SequenceMatcher <= 0,80` contra 230 perguntas anteriores.

O primeiro candidato apresentou apenas um problema de serialização CSV; a correção alterou somente quoting. Depois disso, o preflight de novidade identificou um único caso acima do limiar: `JH3-033`, com similaridade 0,8099. A pergunta foi reformulada antes do freeze sem alterar rota, escopos, temporalidades ou documentos-gabarito.

O candidato final passou em Python 3.11 e 3.12 com zero sobreposição exata e similaridade máxima 0,7104. O CSV foi então congelado com SHA-256:

`d9598b3d1c04d2ddf776a931afba864dc972c4dea73dd0ef774b1e93185dd4a8`

## Fluxo congelado

- Router 1.3.0 — blob `7c82b42f4409110371dcb86e15672a328a0d54bd`;
- Retrieval Planner 1.2.0 — blob `7ee30359cb4457b0bd1a12b43d14f73be410ddaa`;
- Knowledge 1.2.0.

O preflight congelado passou em Python 3.11 e 3.12 antes da primeira medição.

## Primeira medição independente

Run `31971798204`, head `137a92c0e0fbe9a727985b1d0b5f6ac5722d1f1f`.

| Métrica | Acertos | Taxa |
|---|---:|---:|
| Rota | 31/48 | 64,58% |
| Escopo | 35/48 | 72,92% |
| Temporalidade | 35/48 | 72,92% |
| Filtros (escopo + temporalidade) | 33/48 | 68,75% |
| **Conjunto (rota + escopo + temporalidade)** | **27/48** | **56,25%** |

A execução em Python 3.12 reproduziu exatamente o resumo, os resultados por categoria, a matriz de confusão, os IDs divergentes e as métricas de precisão/recall por conjunto.

## Resultado por categoria

| Categoria | Rota | Filtros | Conjunto |
|---|---:|---:|---:|
| Normativa | 8/12 | 11/12 | 7/12 (58,33%) |
| Metodologia | 6/12 | 6/12 | 6/12 (50,00%) |
| Cross-source | 5/12 | 5/12 | 3/12 (25,00%) |
| Controle externo | 12/12 | 11/12 | 11/12 (91,67%) |

A maior fragilidade independente permanece nas consultas `cross_source`, seguidas pelas formulações metodológicas. Controle externo teve desempenho substancialmente mais estável.

## Leitura metodológica

O JH3 fornece nova evidência independente de generalização. O resultado conjunto de 56,25% é superior aos 30% observados na primeira medição independente do JH2, mas os dois percentuais **não formam uma comparação pareada**, pois os conjuntos contêm perguntas diferentes e o JH3 foi deliberadamente balanceado e submetido a critério de novidade mais forte.

Por isso, o resultado não deve ser apresentado como acurácia de produção nem como prova de prontidão do assistente. Ele mostra que os tunings posteriores ao JH2 produziram melhora que alcança material novo, mas ainda deixam uma taxa de falha relevante em formulações que combinam universos documentais.

A decomposição observada dos 21 erros conjuntos é apenas descritiva: 6 casos apresentam rota errada com filtros corretos, 4 apresentam rota correta com filtros errados e 11 apresentam divergências em ambas as camadas. Essa decomposição **não é causal**.

## Próximo gate

O próximo incremento deve realizar diagnóstico contrafactual post-hoc sobre o JH3, mantendo Router 1.3.0 e Planner 1.2.0 congelados. Somente depois dessa atribuição devem ser decididas mudanças de tuning.

Após qualquer tuning baseado no JH3, ele passa a ser apenas regressão conhecida; uma nova alegação de generalização exigirá um novo holdout independente. A ativação do LLM permanece bloqueada e também dependerá de um gate posterior de Retriever/end-to-end.
