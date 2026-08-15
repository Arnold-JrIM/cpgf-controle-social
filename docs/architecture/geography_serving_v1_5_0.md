# Geo 1.1.0 no Serving 1.5.0

## Finalidade

O PR #23 corrige a lacuna entre a POC geográfica já congelada e a camada de produção. A metodologia geográfica permanece em **1.1.0**; a mudança é arquitetural e amplia o Serving para **1.5.0**.

A dimensão territorial associa `UG_ID` à `UF_UG`, preservando a interpretação de que a UF representa a **localização cadastral da Unidade Gestora**, e não necessariamente o local físico da compra, saque ou operação.

## Fonte e cobertura

O cadastro `siafi_dados_ug_2025.csv` é aceito no build canônico somente quando seu SHA-256 é `ee2064fb5e0ce5e729365e1a1f2d80f92a55a659da8160cddd10db7f438c0634`.

A dimensão reproduz a baseline congelada:

- 49.547 UGs do SIAFI 2025;
- 5 complementos manuais com proveniência explícita;
- 49.552 UGs na dimensão final;
- 2.148 de 2.153 UGs do CPGF associadas diretamente ao SIAFI;
- cobertura final de 100% após os cinco complementos.

## Referências temporais

A produção preserva as duas referências independentes do Geo 1.1.0:

- `TRANSACAO`: usa `ANO_TRANSACAO` e somente registros com `DATA TRANSAÇÃO` observável;
- `EXTRATO`: usa `ANO_EXTRATO_REF`, com o fallback técnico documentado para `COMPETENCIA_ARQUIVO` quando necessário.

Nenhum indicador combina as duas referências em um ano híbrido.

## Tabelas adicionadas ao Serving

O Serving passa de 68 para 73 objetos lógicos, mantendo intactos os 68 objetos já validados. São adicionados:

1. `dim_ug_geografica`;
2. `geo_uf_ano_transacao`;
3. `geo_uf_ano_extrato`;
4. `geo_uf_ano_dashboard_long`;
5. `geo_metric_catalog`.

O fato CPGF enriquecido de 1,87 milhão de registros não é duplicado no bundle. O dashboard deverá consumir os agregados leves e a dimensão curada, conforme o contrato metodológico.

## Baseline territorial

No snapshot congelado, o gate canônico exige:

- 405 linhas `UF × ano` na referência TRANSACAO;
- R$ 506.719.563,42 e 1.506.714 operações com data observável;
- 378 linhas `UF × ano` na referência EXTRATO;
- R$ 976.936.749,90 e 1.876.065 registros positivos sem ajustes;
- R$ 470.219.284,18 classificados como sigilosos;
- 369.355 registros sigilosos;
- 6.615 linhas na tabela longa do dashboard;
- 17 combinações referência–métrica.

Observabilidade e sigilo não são forçados a formar classes mutuamente exclusivas.

## Salvaguardas

A incorporação geográfica:

- não altera T01–T09;
- não altera o Motor/Governança 1.3.2;
- não cria T10;
- não infere município;
- não interpreta `UF_UG` como local físico da transação;
- não lê o fato bruto durante a navegação do dashboard.

A habilitação visual do mapa fica para a etapa seguinte, após a distribuição e o contrato do Serving 1.5.0 estarem congelados.
