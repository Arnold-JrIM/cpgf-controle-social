# Preparação 1.1.0 — identidade composta do portador

## Decisão

A Preparação 1.1.0 passa a utilizar, para produção, a chave:

```text
UG_ID + CPF_PORTADOR_NORMALIZADO + NOME_PORTADOR_NORMALIZADO
```

A alteração decorre do gate empírico documentado no PR metodológico de identidade do portador. A base congelada apresentou 410 CPFs mascarados associados a mais de um nome e oito pares `UG + CPF mascarado` com mais de um nome dentro da própria UG.

## Compatibilidade

A Preparação 1.0.0 não é reescrita. Ela permanece preservada como contrato de reprodução da baseline histórica das Regras 1.2.0 e do Motor 1.3.2 sobre o arquivo congelado.

A implementação expõe duas funções:

- `build_portador_id_baseline(...)`: reproduz a semântica 1.0.0;
- `build_portador_id(...)`: aplica a semântica 1.1.0 para produção.

## Impacto observado no gate

| Saída | Baseline | Chave composta |
|---|---:|---:|
| T03 | 7.534 | 7.534 |
| T04 | 1.384 | 1.384 |
| T05 | 1.693 | 1.693 |
| T07 episódios diários | 22.609 | 22.609 |
| T07 portador-anos prioritários | 1.089 | 1.088 |

A diferença em T07-B mostrou que a chave antiga podia agregar duas identidades nominativas distintas sob o mesmo CPF mascarado dentro da mesma UG. Por isso, a mudança é tratada como versionamento explícito de preparação, e não como correção silenciosa da baseline.

## Normalização

- UG numérica: seis dígitos;
- CPF: apenas dígitos observáveis; `-1`, vazio e portador marcado como sigilo são inválidos;
- nome: remoção de espaços excedentes, caixa alta e remoção de diacríticos.

## Efeito sobre as regras

As Regras 1.2.0 permanecem congeladas. A alteração afeta a entidade usada pelas trilhas dependentes de portador, mas não modifica os critérios substantivos de T03, T04, T05 ou T07.
