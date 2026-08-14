# Portabilidade das trilhas T03–T05 — Regras 1.2.0

Este documento registra a migração da família F2 — repetição e recorrência de aquisições — do notebook congelado para `src/cpgf/trails/`.

## Contrato preservado

As regras continuam em `1.2.0`. A migração não recalibra limiares e não altera o Motor 1.3.2.

### T03 — repetição exata

T03-A mantém a chave:

`UG + portador + favorecido + data + valor em centavos + tipo de transação`

São elegíveis compras efetivas, não classificadas como ajuste/contestação, com valor positivo, data, UG, portador e favorecido identificados. O grupo é sinalizado com `N >= 2`; `N >= 3` recebe `REFORCADO`.

T03-B permanece apenas diagnóstico de repetição integral observável. A assinatura usa os 15 campos de negócio originalmente publicados pelo Portal e exclui registros sigilosos/incompletos conforme o contrato congelado. T03-B não aumenta convergência do núcleo.

### T04 — repetição multiportador

Mantém-se a unidade:

`UG + fornecedor + data + valor em centavos`

O sinal exige pelo menos duas transações e dois portadores distintos. A triagem permanece:

- 2 portadores: `ATENCAO`;
- 3–4: `REFORCADO`;
- 5 ou mais: `MUITO_ELEVADO`.

A saída não permite inferir identidade do objeto adquirido nem fracionamento de uma mesma despesa.

### T05 — recorrência de aquisições

A regra-base permanece:

- compra nacional positiva;
- agrupamento por `UG + fornecedor + ano da transação`;
- janela inclusiva iniciada em cada data com compra, de `DT_INICIO` até `DT_INICIO + 30 dias`;
- `N_TRANSACOES >= 5`;
- `N_PORTADORES >= 2`;
- `CV <= 0,20`;
- `REFORCADO` quando `CV <= 0,10`.

Também são preservados mediana, Q1, Q3, IQR e a participação das compras dentro de ±20% da mediana. `SIMILARIDADE_ROBUSTA_ALTA` usa referência de 80%.

Janelas sobrepostas do mesmo `UG + fornecedor + ano` são organizadas em blocos de sobreposição. Em cada bloco permanece a janela mais forte, na ordem congelada: maior número de transações, maior número de portadores, menor CV, maior materialidade e data inicial mais antiga. As janelas não são fundidas.

Materialidade e recorrência continuam sendo apresentadas por percentis dentro de cada exercício. Não é produzido score opaco.

## Preparação 1.0.0 e 1.1.0

A baseline congelada foi produzida com Preparação 1.0.0, cuja identidade histórica do portador era baseada no CPF mascarado normalizado. A Preparação 1.1.0 adota a chave composta `UG + CPF mascarado + nome normalizado`.

O gate empírico de identidade demonstrou que T03, T04 e T05 mantiveram os mesmos totais na base congelada sob as duas identidades. Ainda assim, o código aceita explicitamente `PORTADOR_ID_BASELINE` para regressão histórica; produção utiliza `PORTADOR_ID`.

## Baseline de regressão

Para `CPGF_201301_a_202607.csv`, SHA-256 `300789f9bd866f313df4ca5ee5dfca7234050ef2452443b61b1e58425ca0997b`:

- T03-A: 7.534 grupos;
- T03-B: 7.523 grupos integralmente observáveis, diagnóstico;
- T04: 1.384 grupos;
- T05: 1.693 episódios finais.

O CI ordinário usa fixtures pequenas e determinísticas. A regressão integral da base de aproximadamente 500 MB permanece uma verificação controlada e não é baixada automaticamente pelo GitHub Actions.

## Interpretação

T03–T05 produzem sinais ou padrões para triagem. Nenhuma dessas saídas confirma, isoladamente, pagamento indevido, duplicidade, fracionamento, favorecimento ou outra conclusão jurídica. A base aberta não contém todos os documentos e atributos necessários para esse juízo.
