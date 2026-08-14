# Port das trilhas T08 e T09 — Regras 1.2.0

Este documento registra o port para `src/` das duas famílias contextuais finais do motor congelado. O objetivo é transformar a especificação executada nos notebooks arquivados em funções testáveis, sem recalibrar critérios e sem atribuir conclusão jurídica automática aos resultados.

## T08 — Lei de Newcomb-Benford

A T08 mantém papel de **contexto estatístico**, e não de trilha núcleo. O universo principal é formado por compras nacionais positivas com ano efetivo da transação observável.

O port preserva os seguintes critérios da Regras 1.2.0:

- D1 usa todas as compras nacionais positivas;
- D12 principal usa valores de pelo menos R$ 10;
- `N < 300`: `NAO_APLICAR`;
- `300 <= N < 1000`: `EXPLORATORIO`;
- `1000 <= N < 3000`: `FORMAL`;
- `N >= 3000`: `FORMAL_ROBUSTEZ_MAIOR`;
- MAD é a medida principal; qui-quadrado permanece diagnóstico auxiliar;
- a priorização relativa usa apenas `UG × ano` com `N_D12 >= 1000`, exercícios completos de 2013 a 2025 e pelo menos 10 UGs comparáveis no ano;
- o limiar relativo é o P90 anual de `MAD_D12`, com empates preservados;
- a saída mestre T08 corresponde aos `UG × ano` no decil superior válido.

A persistência relativa por UG e o Summation Test D12 são mantidos como diagnósticos auxiliares. O Summation Test não recebe limiar arbitrário de anomalia. O port não interpreta divergência de Benford como erro, fraude ou irregularidade.

A baseline histórica da Preparação 1.0.0 permanece em **12 sinais T08**. A reprodução integral dessa contagem sobre o arquivo congelado será tratada no gate de regressão completa, separado do CI com fixtures.

## T09 — referências financeiras em cenários paralelos

A T09 mantém papel de **contexto normativo-financeiro**. Para cada compra nacional positiva com data efetiva observável, a aplicação compara o valor, em centavos inteiros, com dois cenários paralelos:

- `COMPRAS_SERVICOS`;
- `OBRAS_ENGENHARIA`.

A categoria real da despesa não é observável no CSV público. Por isso, o sistema não escolhe automaticamente um dos cenários e registra `APLICABILIDADE_JURIDICA = NAO_CONCLUSIVA_SEM_OBJETO_CATEGORIA`.

A dimensão temporal preserva as referências congeladas da Portaria MF 95/2002, dos valores da Lei 8.666/1993 e do Decreto 9.412/2018, e, a partir de dezembro de 2023, da Portaria Normativa MF 1.344/2023 combinada com os decretos anuais de atualização. Os valores são transformados em centavos antes da comparação.

Cada cenário recebe exatamente um dos estados:

- `ABAIXO_FAIXA`: abaixo de 90% da referência;
- `PROXIMO_LIMITE`: de 90% até menos de 100%;
- `NO_LIMITE`: igualdade exata em centavos;
- `ACIMA_LIMITE`: estritamente acima.

`STATUS_T09` combina os dois cenários apenas para triagem. `STATUS_COMPRAS` e `STATUS_ENGENHARIA` permanecem a evidência primária. A classificação agregada por `UG × fornecedor × ano` é exclusivamente descritiva e não soma transações para concluir fracionamento.

Para reduzir memória no runtime, `run_t09()` mantém uma linha classificada por transação com os dois cenários lado a lado. A tabela materializada com duas linhas por transação é opcional (`include_scenarios=True`), e sua função valida a cardinalidade `2 × N`.

A baseline histórica permanece em **46.941 registros contextuais T09**. Assim como T08, a regressão integral será executada em etapa própria sobre o arquivo congelado de SHA-256 `300789f9bd866f313df4ca5ee5dfca7234050ef2452443b61b1e58425ca0997b`.

## Estado após este port

Com T08 e T09, T01–T09 possuem implementação executável em `src/cpgf/trails`. O estado do catálogo passa a `PORTED_PENDING_FULL_REGRESSION`: o CI valida comportamento determinístico, limiares, cardinalidades e casos de borda com fixtures, mas não equivale à recomputação integral da baseline de 1.876.087 linhas.
