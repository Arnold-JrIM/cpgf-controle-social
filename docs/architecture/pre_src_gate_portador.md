# Gate pré-`src/` — identidade do portador

**Status:** BLOQUEADOR para T03, T04, T05 e T07.

## Problema
A implementação de pesquisa constrói `PORTADOR_ID` a partir do CPF mascarado. Identificador mascarado não deve ser tratado automaticamente como identidade global inequívoca.

## Chaves a comparar

A — baseline do notebook:
```text
CPF_PORTADOR_NORMALIZADO
```

B — candidata de produção:
```text
UG_ID + CPF_PORTADOR_NORMALIZADO + NOME_PORTADOR_NORMALIZADO
```

## Teste obrigatório
Reprocessar universo de portadores, T03, T04, T05, T07, exposições relacionadas e regressão dos grupos afetados.

Se houver alteração material, não corrigir silenciosamente: produzir relatório de impacto e decidir se a baseline histórica é preservada ou se haverá nova versão metodológica.
