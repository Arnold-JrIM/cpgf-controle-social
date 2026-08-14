# Resultado do gate de identidade do portador

**Data do diagnóstico:** 2026-08-14  
**Base:** `CPGF_201301_a_202607.csv`  
**SHA-256:** `300789f9bd866f313df4ca5ee5dfca7234050ef2452443b61b1e58425ca0997b`  
**Registros:** 1.876.087  
**Regras congeladas:** 1.2.0  
**Motor/Governança:** 1.3.2  
**Preparação histórica:** 1.0.0

## Objetivo

Avaliar se o identificador histórico de portador, derivado apenas dos dígitos observáveis do CPF mascarado, poderia colapsar pessoas distintas e alterar as trilhas que dependem da noção de portador.

Foram comparadas duas chaves:

```text
A — baseline histórica
CPF_PORTADOR_NORMALIZADO

B — candidata de produção
UG_ID + CPF_PORTADOR_NORMALIZADO + NOME_PORTADOR_NORMALIZADO
```

O nome foi normalizado por trim, colapso de espaços, caixa alta e remoção de acentos. Registros protegidos por sigilo continuam sem `PORTADOR_ID` analítico.

## Universo de identidade

| Métrica | Resultado |
|---|---:|
| CPFs mascarados distintos na chave histórica | 26.273 |
| unidades distintas `UG + CPF mascarado` | 28.178 |
| identidades candidatas `UG + CPF + nome` | 28.186 |
| CPFs mascarados associados a mais de um nome | 410 |
| CPFs mascarados presentes em mais de uma UG | 1.749 |
| pares `UG + CPF` associados a mais de um nome | 8 |

O resultado mostra que o CPF mascarado não é uma chave global inequívoca. A maior parte da diferença decorre de reutilização do mesmo padrão mascarado entre UGs. Como T03, T04, T05 e T07 já incorporam a UG em suas unidades de análise, o ponto substantivo para essas trilhas são os **8 pares UG + CPF** em que o mesmo identificador mascarado está associado a nomes distintos dentro da própria UG.

## Impacto sobre as trilhas

| Trilha | Baseline | Chave candidata | Delta |
|---|---:|---:|---:|
| T03 — repetição exata | 7.534 | 7.534 | 0 |
| T04 — multiportador | 1.384 | 1.384 | 0 |
| T05 — recorrência | 1.693 | 1.693 | 0 |
| T07 — portador-anos prioritários | 1.089 | 1.088 | -1 |

T03 e T04 foram recalculadas integralmente. Para T05, somente grupos `UG × fornecedor × ano` que poderiam ser afetados pela mudança de identidade precisavam ser recalculados: 275 grupos foram examinados, e os episódios resultantes permaneceram idênticos. Como todos os demais grupos têm exatamente a mesma identidade sob A e B, o total projetado permanece em 1.693.

Em T07, os **22.609 episódios diários** permaneceram idênticos. A diferença aparece apenas na recorrência anual. Um portador-ano de 2022, formado historicamente pela agregação de um mesmo CPF mascarado associado a dois nomes distintos na mesma UG, reunia 6 dias de múltiplos saques e atingia o P90 anual. Com a chave composta, o registro se separa em duas identidades, com 2 e 4 dias, respectivamente; nenhuma alcança o limiar de 6 dias. O universo de comparáveis de 2022 passa de 952 para 953, sem mudança do P90.

O identificador mascarado afetado não é exposto neste relatório. Para auditoria técnica do diagnóstico, foi utilizado o hash truncado `541d32bfc1571277` do valor normalizado observado.

## Exposição do Motor 1.3.2

As variáveis principais de exposição permanecem inalteradas por construção:

- `N_COMPRAS_FORNECEDOR` é contagem de operações em `UG × fornecedor × ano`;
- `N_OPERACOES_EFETIVAS` é contagem de operações em `UG × ano`.

A troca de identidade do portador não altera essas contagens. A única alteração direta observada no motor decorre da perda de um sinal T07 no conjunto de flags.

## Checagem adicional de T03-A e sigilo

A T03-A não possui uma cláusula textual `NOT EH_SIGILOSO`, mas combina `EH_COMPRA_EFETIVA`, `PORTADOR_ID IS NOT NULL` e `FAVORECIDO_IDENTIFICADO`. Na baseline, havia **1.196.756 registros elegíveis para T03-A e nenhum deles estava marcado como sigiloso**. As 18.977 linhas envolvidas nos 7.534 grupos T03 também continham zero registros sigilosos.

Assim, a exclusão de sigilo da T03-A está empiricamente confirmada para a baseline, embora a futura implementação de produção deva tornar essa intenção explícita para legibilidade e defesa do contrato.

## Decisão metodológica pendente

O gate encontrou uma alteração real, ainda que mínima, em T07. Por isso, a chave não deve ser trocada silenciosamente dentro da preparação 1.0.0.

A recomendação técnica é:

1. preservar a baseline histórica **Preparação 1.0.0 + Regras 1.2.0 + Motor 1.3.2** para regressão e reprodutibilidade;
2. adotar a chave composta na produção sob **Preparação 1.1.0**;
3. manter as regras T01–T09 em 1.2.0, pois os critérios das trilhas não mudaram; mudou apenas a resolução da entidade `portador`;
4. criar uma nova baseline de produção registrando T07 = 1.088 para o mesmo SHA-256 e documentando a diferença de -1 como efeito da correção de identidade;
5. somente depois dessa decisão implementar `preprocessing/identifiers.py` e migrar T03/T04/T05/T07.

Este documento registra evidência e recomendação. Ele não altera por si só nenhuma versão de produção.
