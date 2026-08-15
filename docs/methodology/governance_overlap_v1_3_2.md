# Matrizes diagnósticas, sobreposição e contribuição marginal — Motor 1.3.2

## Finalidade

Esta etapa porta para `src/` a parte do Motor 1.3.2 destinada a examinar se as trilhas do núcleo acrescentam informação própria ou se aparecem predominantemente nas mesmas unidades diagnósticas.

A análise não trata as famílias de evidência como estatisticamente independentes por definição e não utiliza a sobreposição para excluir automaticamente uma trilha. O fundamento substantivo de cada regra permanece necessário.

## Unidades diagnósticas

São utilizadas as duas unidades congeladas:

- `UG × fornecedor × ano`, com T01–T06 no núcleo;
- `UG × ano`, com T01–T07 no núcleo.

T08 e T09 permanecem contextos. Eles são anexados às matrizes, mas não entram em `N_TRILHAS_ATIVAS`, `N_TRILHAS_NUCLEO`, `N_FAMILIAS_ATIVAS` ou `N_FAMILIAS_NUCLEO`.

A projeção das saídas primárias segue o contrato do notebook congelado. T06 usa o fornecedor Top-1 que originou o sinal estrutural. T07 e T08 não possuem `CHAVE_ENTIDADE` e, portanto, só participam diretamente da unidade `UG × ano`. T09 pode ser observado tanto no contexto `UG × fornecedor × ano` quanto agregado em `UG × ano`.

## Famílias na matriz

No nível `UG × fornecedor × ano`:

- `F1 = T01 OR T02`;
- `F2 = T03 OR T04 OR T05`;
- `F3 = T06`.

No nível `UG × ano`, acrescenta-se:

- `F4 = T07`.

Essas flags indicam presença de pelo menos uma trilha da família na unidade. Elas não são probabilidades e não formam score de risco.

## Elegibilidade estatística

A avaliação usada para PCA/VIF e para qualificar a interpretação de pares preserva os limiares congelados:

- pelo menos 30 unidades positivas;
- pelo menos 30 unidades negativas.

Os estados são:

- `SUFICIENTE`;
- `DIAGNOSTICO_ESTATISTICO_INSUFICIENTE`;
- `SEM_VARIACAO`.

Uma flag insuficiente continua disponível no motor e nas tabelas descritivas.

## Sobreposição

Para cada par de flags binárias são calculados:

- interseção (`n11`);
- unidades exclusivas de A (`n10`);
- unidades exclusivas de B (`n01`);
- nenhuma das duas (`n00`);
- união;
- Jaccard;
- coeficiente Phi;
- `P(B|A)`;
- `P(A|B)`.

As fórmulas seguem o notebook congelado. Quando o denominador de uma métrica é zero, o resultado permanece ausente em vez de receber valor artificial.

Cada recorte recebe ainda avaliação local. O par é `SUFICIENTE` somente quando ambas as flags possuem pelo menos 30 positivos e 30 negativos naquele recorte; caso contrário, recebe `CAUTELA_RARIDADE_NO_RECORTE`.

## Controle de exposição

As métricas podem ser repetidas:

- ano a ano;
- por `BANDA_EXPOSICAO_FORNECEDOR` em `UG × fornecedor × ano`;
- por `DECIL_EXPOSICAO_ANUAL` em `UG × ano`.

As estratificações reduzem a confusão descritiva entre oportunidade de disparo e convergência observada, mas **não constituem ajuste causal**.

## Contribuição marginal

A contribuição marginal responde à pergunta operacional:

> se uma trilha fosse retirada, quantas unidades deixariam de aparecer na união do motor?

Para cada trilha ou família são calculados:

- unidades sinalizadas;
- unidades exclusivas;
- participação exclusiva entre as unidades da própria regra;
- união do motor;
- união sem a regra;
- perda de unidades se a regra fosse retirada.

Contribuição marginal igual a zero não implica exclusão automática. Uma trilha pode continuar substantivamente necessária por representar condição normativa ou padrão distinto, mesmo quando sua ocorrência empírica estiver contida em outras flags na base observada.

## Limites desta entrega

Este bloco não porta ainda VIF, índice de condição ou PCA. Também não executa automaticamente a regressão integral da camada de governança sobre o CSV canônico de 1.876.087 registros. A validação empírica das matrizes e dos resultados de sobreposição será tratada em gate separado, preservando a mesma lógica adotada para a regressão T01–T09.
