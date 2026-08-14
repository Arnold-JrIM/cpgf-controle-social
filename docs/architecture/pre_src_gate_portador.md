# Gate pré-`src/` — identidade do portador

**Status:** DIAGNÓSTICO EXECUTADO — decisão de versionamento pendente antes de T03/T04/T05/T07.

## Problema

A implementação de pesquisa constrói `PORTADOR_ID` a partir do CPF mascarado. Identificador mascarado não deve ser tratado automaticamente como identidade global inequívoca.

## Chaves comparadas

A — baseline do notebook:

```text
CPF_PORTADOR_NORMALIZADO
```

B — candidata de produção:

```text
UG_ID + CPF_PORTADOR_NORMALIZADO + NOME_PORTADOR_NORMALIZADO
```

## Resultado

O diagnóstico foi executado sobre a baseline de 1.876.087 registros, SHA-256 `300789f9bd866f313df4ca5ee5dfca7234050ef2452443b61b1e58425ca0997b`.

- 410 CPFs mascarados estão associados a mais de um nome no universo completo;
- 1.749 CPFs mascarados aparecem em mais de uma UG;
- 8 pares `UG + CPF mascarado` estão associados a mais de um nome dentro da mesma UG;
- T03: 7.534 → 7.534;
- T04: 1.384 → 1.384;
- T05: 1.693 → 1.693;
- T07: 1.089 → 1.088 portador-anos prioritários;
- episódios diários T07: 22.609 → 22.609.

A única alteração ocorre em T07-B, onde a chave histórica agrega duas identidades nominativas sob o mesmo CPF mascarado e produz um portador-ano prioritário que desaparece após a separação.

## Consequência

O gate confirma que a chave composta é tecnicamente mais apropriada para produção, mas também confirma que a mudança altera a baseline. Portanto, ela não deve ser incorporada silenciosamente à Preparação 1.0.0.

A recomendação é preservar a baseline histórica e, após decisão formal, adotar a chave composta em **Preparação 1.1.0**, mantendo Regras 1.2.0 e Motor 1.3.2.

O relatório completo está em `docs/methodology/portador_identity_gate_result.md`.
