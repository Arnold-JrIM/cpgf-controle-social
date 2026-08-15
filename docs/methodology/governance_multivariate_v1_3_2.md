# Diagnóstico multivariado de redundância — Motor 1.3.2

## Finalidade

Esta etapa complementa as matrizes de sobreposição do Motor 1.3.2 com diagnósticos multivariados. O objetivo é investigar se as trilhas do núcleo acrescentam informação própria ou se combinações de regras apresentam dependência estrutural que não aparece integralmente em comparações par a par.

Os resultados são instrumentos de diagnóstico. Eles não alteram as Regras 1.2.0, não geram score de risco e não excluem automaticamente trilhas ou famílias.

## Unidades e conjuntos analisados

Os modelos permanecem separados nas duas unidades congeladas:

- `UG × fornecedor × ano`: T01–T06;
- `UG × ano`: T01–T07.

As famílias podem ser avaliadas em execução separada:

- fornecedor-ano: F1–F3;
- UG-ano: F1–F4.

Trilhas e famílias não devem ser incluídas simultaneamente no mesmo modelo, porque F1–F4 são funções determinísticas das próprias trilhas e produziriam dependência por construção.

T08 e T09 permanecem apenas como contexto e não entram no núcleo multivariado.

## Elegibilidade

A elegibilidade mantém o contrato já congelado para a camada estatística:

- mínimo de 30 positivos;
- mínimo de 30 negativos;
- flags sem variação são classificadas separadamente.

Flags raras ou constantes permanecem nas tabelas de elegibilidade e no motor. Elas apenas não participam dos cálculos que exigem variação suficiente. Não há descarte silencioso.

## VIF

Para cada variável elegível, o VIF é calculado a partir de uma regressão auxiliar OLS da flag contra as demais variáveis elegíveis:

`VIF_j = 1 / (1 - R_j²)`.

A implementação usa mínimos quadrados do NumPy com intercepto explícito. Quando `R²` é numericamente igual a 1, o resultado é registrado como dependência linear perfeita e `VIF = infinito`.

Não são adotados limiares automáticos como regra de exclusão. Valores elevados orientam investigação substantiva, sobretudo em conjunto com Jaccard, Phi, condicionais e contribuição marginal.

## Índice de condição

As variáveis elegíveis são padronizadas e utilizadas para formar a matriz de correlação. A partir de seus autovalores ordenados, calcula-se:

`CI_i = sqrt(lambda_max / lambda_i)`.

Autovalores numericamente nulos produzem índice de condição infinito e são marcados como singularidade. O código retorna os autovalores e índices brutos, sem converter faixas convencionais em decisão automática sobre permanência de regra.

## PCA

A PCA é executada sobre a matriz de correlação das flags binárias elegíveis. A saída contém:

- autovalor por componente;
- variância explicada;
- variância explicada acumulada;
- peso de cada variável no componente;
- carga de correlação;
- carga quadrada;
- comunalidade acumulada.

O sinal dos autovetores é orientado de forma determinística para tornar a saída reprodutível. A PCA é exploratória e descritiva. O uso da correlação de Pearson entre indicadores binários não deve ser interpretado como estimação de variável latente nem como substituto de modelos próprios para dados categóricos.

## Controle de exposição

Os diagnósticos podem ser repetidos por qualquer coluna de recorte. Para os universos congelados, os recortes principais são:

- `BANDA_EXPOSICAO_FORNECEDOR`;
- `DECIL_EXPOSICAO_ANUAL`.

A estratificação ajuda a verificar se a dependência entre sinais permanece quando unidades com oportunidades de disparo semelhantes são comparadas. Ela continua sendo controle descritivo e não ajuste causal.

## Implementação

A camada usa apenas NumPy e pandas, evitando dependências adicionais para matrizes de seis ou sete variáveis. Essa escolha mantém as fórmulas transparentes, reduz o acoplamento do projeto e facilita a reprodução dos cálculos.

Os testes sintéticos cobrem:

- flags binárias balanceadas e ortogonais;
- dependência linear perfeita;
- flag rara preservada sem VIF;
- singularidade no índice de condição;
- PCA com variância uniforme;
- PCA com duplicação perfeita;
- repetição dos diagnósticos por estrato de exposição.

## Salvaguardas de interpretação

Nenhum resultado de VIF, índice de condição ou PCA confirma erro, fraude, irregularidade ou inadequação de uma trilha. Uma regra pode permanecer necessária por fundamento normativo ou por representar fenômeno substantivamente distinto, mesmo quando sua ocorrência empírica estiver fortemente associada a outras flags.

Da mesma forma, redundância estatística não substitui a análise do fundamento normativo ou científico de cada trilha.

## Referências metodológicas

- Belsley, D. A.; Kuh, E.; Welsch, R. E. *Regression Diagnostics: Identifying Influential Data and Sources of Collinearity*. Wiley, 1980.
- O'Brien, R. M. A caution regarding rules of thumb for variance inflation factors. *Quality & Quantity*, 41, 673–690, 2007.
- Jolliffe, I. T.; Cadima, J. Principal component analysis: a review and recent developments. *Philosophical Transactions of the Royal Society A*, 374, 20150202, 2016.

## Limites desta entrega

Este bloco não executa a regressão integral do Motor 1.3.2 sobre o CSV canônico de 1.876.087 registros e não materializa os resultados finais para o serving do dashboard. O próximo gate deve executar matrizes, sobreposição, marginalidade e diagnóstico multivariado sobre a base canônica, registrar os resultados reprodutíveis e somente depois promover a integração ao produto.
