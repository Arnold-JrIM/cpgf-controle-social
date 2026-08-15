# Universos diagnósticos e controle de exposição — Motor 1.3.2

## Finalidade

Este bloco porta para `src/cpgf/governance/exposure.py` a camada de exposição utilizada pelo Motor/Governança 1.3.2 congelado. A implementação não recalibra T01–T09 e não cria score de risco.

O objetivo é oferecer denominadores diagnósticos estáveis para as análises posteriores de sobreposição e contribuição marginal, reduzindo a possibilidade de interpretar maior volume de operações como maior convergência substantiva de sinais.

## Janela temporal

Para diagnósticos longitudinais, o contrato considera:

- 2013–2025: `COMPLETO`;
- 2012 e 2026: `PARCIAL`.

As funções preservam os períodos parciais por padrão e oferecem `complete_years_only=True` para análises que exigem apenas anos completos.

## Universo `UG × fornecedor × ano`

A unidade relacional é construída somente com registros que atendem simultaneamente a:

- compra efetiva;
- ausência de ajuste/contestação;
- valor positivo em centavos;
- data real da transação observável;
- UG identificada;
- fornecedor identificado;
- ano da transação observável.

Campos agregados:

- `CODIGO_UG`;
- `CHAVE_ENTIDADE`;
- `ANO`;
- `N_COMPRAS_FORNECEDOR`;
- `VALOR_COMPRAS_FORNECEDOR`;
- `N_PORTADORES_FORNECEDOR`;
- `N_DIAS_COMPRA_FORNECEDOR`.

A baseline congelada do Motor 1.3.2 registra **522.053** unidades `UG × fornecedor × ano` nos anos completos. Esse valor é mantido no código como contrato de regressão integral, não como assertiva de fixture unitária.

### Bandas fixas de exposição

A V1.3.2 não usa decis para fornecedor-ano, porque a distribuição de `N_COMPRAS_FORNECEDOR` é discreta e contém muitos empates. As seis bandas congeladas são:

| Ordem | Código | Faixa |
|---:|---|---|
| 1 | `B01_1` | 1 compra |
| 2 | `B02_2` | 2 compras |
| 3 | `B03_3_4` | 3–4 compras |
| 4 | `B04_5_9` | 5–9 compras |
| 5 | `B05_10_19` | 10–19 compras |
| 6 | `B06_20_MAIS` | 20+ compras |

Toda unidade elegível deve receber exatamente uma banda.

## Universo `UG × ano`

A unidade UG-ano considera operações efetivas positivas de compra ou saque, com data real, UG e ano observáveis, excluindo ajustes/contestações.

Campos agregados:

- `N_COMPRAS_UG` e `VALOR_COMPRAS_UG`;
- `N_SAQUES_UG` e `VALOR_SAQUES_UG`;
- `N_OPERACOES_EFETIVAS`;
- `N_PORTADORES_UG`;
- `N_FORNECEDORES_UG`, restrito a fornecedores observáveis em compras;
- `N_DIAS_ATIVOS_UG`.

A baseline congelada registra **13.785** unidades `UG × ano` nos anos completos.

### Decis anuais de exposição

A exposição da UG é medida por `N_OPERACOES_EFETIVAS`. O cálculo é feito separadamente dentro de cada ano:

1. `rank(method="average", pct=True)` preserva os empates;
2. o percentil é registrado em `PERCENTIL_EXPOSICAO_ANUAL`;
3. `ceil(percentil × 10)` produz `DECIL_EXPOSICAO_ANUAL`, limitado ao intervalo 1–10.

O procedimento replica o Motor 1.3.2. Ele não força artificialmente a existência de dez grupos com igual cardinalidade quando há empates.

## Uso nas próximas etapas

Esses universos serão a base do próximo bloco, no qual as flags de T01–T07 serão projetadas nas unidades diagnósticas adequadas. Somente depois serão calculados Jaccard, Phi, probabilidades condicionais e contribuição marginal, globalmente e dentro dos estratos de exposição.

T08 e T09 permanecem contextos e não aumentam a convergência núcleo.
