# Núcleo de governança do Motor 1.3.2

## Finalidade

Esta etapa porta para `src/` o contrato semântico do Motor/Governança 1.3.2 sem recalibrar as Regras 1.2.0 e sem alterar a cardinalidade das saídas T01–T09 já validadas pela regressão integral.

A camada distingue explicitamente três dimensões que não devem ser confundidas:

1. **família de evidência**, como agrupamento substantivo das trilhas;
2. **natureza/tipo de evidência**, como descrição do que o motor observou;
3. **status de validação**, como resultado de exame humano posterior.

Nenhuma dessas dimensões cria uma conclusão automática de fraude ou irregularidade.

## Famílias de evidência

As famílias permanecem agrupamentos substantivos e não declarações de independência estatística:

| Família | Denominação | Trilhas |
|---|---|---|
| F1 | Conformidade operacional observável | T01, T02 |
| F2 | Repetição e recorrência de aquisições | T03, T04, T05 |
| F3 | Estrutura e concentração de fornecedor | T06 |
| F4 | Comportamento de saque | T07 |
| F5 | Contexto estatístico forense | T08 |
| F6 | Contexto normativo-financeiro | T09 |

## Tipos de evidência

O código usa a taxonomia controlada abaixo:

- `FATO_DETERMINISTICO`: T01 e T02;
- `PADRAO_COMPORTAMENTAL`: T03, T04, T05 e T07;
- `PADRAO_ESTRUTURAL`: T06;
- `SINAL_ESTATISTICO`: T08;
- `CONTEXTO_NORMATIVO`: T09.

T01–T07 permanecem no núcleo de convergência. T08 e T09 são contextos e recebem `CONVERGENCIA_NUCLEO = false`.

Essa classificação descreve a natureza do resultado analítico. Ela não mede gravidade jurídica nem probabilidade de irregularidade.

## Protocolo de validação

Os valores permitidos de `STATUS_VALIDACAO` são:

- `NAO_VALIDADO`;
- `EM_ANALISE`;
- `CONFIRMADO`;
- `JUSTIFICADO`;
- `FALSO_POSITIVO`;
- `ERRO_DADO`;
- `INCONCLUSIVO`.

O padrão é `NAO_VALIDADO`. O motor não promove automaticamente um sinal para `CONFIRMADO`.

## Registro canônico de evidências

`cpgf.governance.consolidation.tag_evidence()` adiciona metadados de governança a uma saída primária de trilha sem recalculá-la, deduplicá-la ou alterar sua cardinalidade.

Campos canônicos acrescentados:

- `ID_EVIDENCIA`;
- `TRILHA`;
- `FAMILIA_EVIDENCIA`;
- `NOME_FAMILIA_EVIDENCIA`;
- `TIPO_EVIDENCIA`;
- `PAPEL_EVIDENCIA`;
- `UNIDADE_PRIMARIA`;
- `CONVERGENCIA_NUCLEO`;
- `STATUS_VALIDACAO`;
- `VERSAO_PREPARACAO`;
- `VERSAO_REGRAS`;
- `VERSAO_MOTOR`.

O adaptador exige unicidade do identificador dentro da saída primária de cada trilha. Ele não presume que identificadores iguais em trilhas diferentes representem a mesma evidência.

`consolidate_evidence()` apenas concatena as saídas já calculadas e etiquetadas. A sobreposição entre trilhas será medida em unidades diagnósticas próprias no bloco seguinte; não é resolvida por deduplicação de linhas.

## Limites desta entrega

Este PR não implementa ainda:

- construção dos universos `UG × fornecedor × ano` e `UG × ano`;
- bandas fixas de exposição do fornecedor;
- decis anuais de exposição da UG;
- Jaccard, Phi e probabilidades condicionais;
- contribuição marginal;
- VIF, índice de condição ou PCA.

Esses componentes permanecem parte do Motor 1.3.2 congelado e serão portados em blocos subsequentes, usando esta camada de governança como contrato comum.
