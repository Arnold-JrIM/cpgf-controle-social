# Validação integral T01–T09 — PASS canônico

A regressão integral do motor foi executada em 14 de agosto de 2026 sobre o arquivo canônico `CPGF_201301_a_202607.csv`, com 1.876.087 registros e SHA-256 `300789f9bd866f313df4ca5ee5dfca7234050ef2452443b61b1e58425ca0997b`.

A execução ocorreu no GitHub Actions, workflow run `31847885454`, sobre o commit técnico `a194db07ca96c5e26d0e38abbfa5c00f9c83f409`. O relatório foi preservado como artifact `9236666405`, digest `sha256:8a6d733c87f86e7ad5393221d7a1a971e24c2f6329713f90b80f2091bfd97fd5`.

## Resultado

O gate retornou `PASS` nos dois modos de preparação.

| Trilha | Baseline 1.0.0 | Produção 1.1.0 |
|---|---:|---:|
| T01 | 49.675 | 49.675 |
| T02 | 14 | 14 |
| T03 | 7.534 | 7.534 |
| T04 | 1.384 | 1.384 |
| T05 | 1.693 | 1.693 |
| T06 | 233 | 233 |
| T07 | 1.089 | 1.088 |
| T08 | 12 | 12 |
| T09 | 46.941 | 46.941 |

Todos os deltas contra as expectativas versionadas foram zero. A única diferença entre os modos é a T07, já esperada e documentada: a Preparação 1.1.0 usa a identidade composta do portador e separa uma colisão histórica que existia na chave da Preparação 1.0.0.

Esse resultado valida a reprodução integral das contagens congeladas pelo código portado para `src/`. Ele não altera a interpretação substantiva das trilhas: as saídas permanecem sinais, padrões ou contextos para triagem e não constituem conclusão automática de fraude ou irregularidade.
