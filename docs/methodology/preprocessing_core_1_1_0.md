# Núcleo de preprocessing — Preparação 1.1.0

Este módulo materializa as transformações compartilhadas que antecedem as trilhas analíticas. Ele não executa T01–T09.

## Contratos preservados

- `DATA TRANSAÇÃO` é a referência temporal das análises comportamentais e normativas; `ANO EXTRATO` e `MÊS EXTRATO` permanecem como referência de faturamento e não substituem datas ausentes.
- comparações monetárias exatas usam `VALOR_CENTAVOS` inteiro; `VALOR_NUM` é uma representação em reais para agregação e exibição.
- a classificação de compras, saques e ajustes utiliza os códigos congelados em `config/transaction_codes.yaml`.
- `PORTADOR_ID` segue a Preparação 1.1.0; `PORTADOR_ID_BASELINE` permanece disponível apenas para regressão da Preparação 1.0.0.
- fornecedor identificado exige identificador observável e exclui nomes marcados por sigilo ou sem informação.
- registros não são classificados automaticamente como irregulares a partir dessas flags.

## Colunas derivadas principais

`UG_ID`, `PORTADOR_ID`, `PORTADOR_ID_BASELINE`, `FAVORECIDO_ID`, `FAVORECIDO_IDENTIFICADO`, `DATA_DT`, `ANO_TRANSACAO`, `ANO_EXTRATO_REF`, `MES_EXTRATO_REF`, `COMPETENCIA_EXTRATO_REF`, `VALOR_CENTAVOS`, `VALOR_NUM`, `EH_COMPRA_EFETIVA`, `EH_COMPRA_NACIONAL`, `EH_SAQUE_EFETIVO`, `EH_AJUSTE_CONTESTACAO`, `EH_SIGILOSO`, `EH_OPERACAO_EFETIVA` e `EH_OPERACAO_POSITIVA_NAO_AJUSTE`.

A camada de staging preserva todas as colunas originais, inclusive campos opcionais de proveniência como `COMPETENCIA_ARQUIVO` e `ARQUIVO_ORIGEM` quando já existirem na base consolidada.
