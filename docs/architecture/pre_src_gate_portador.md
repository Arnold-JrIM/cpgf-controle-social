# Gate pré-`src/` — identidade do portador

**Status:** RESOLVIDO em 2026-08-14.

O diagnóstico comparou a identidade histórica baseada em CPF mascarado com a chave composta `UG_ID + CPF normalizado + nome normalizado` sobre a base congelada `CPGF_201301_a_202607.csv`.

O resultado confirmou colisões reais de identidade e alteração de uma unidade prioritária em T07-B, sem mudança nas contagens de T03, T04, T05 ou nos episódios diários de T07.

Decisão:

1. preservar Preparação 1.0.0 para reprodução/regressão histórica;
2. adotar Preparação 1.1.0 em produção;
3. manter Regras T01–T09 na versão 1.2.0;
4. implementar `PORTADOR_ID` composto antes da migração das trilhas dependentes de portador.

Detalhes em `docs/methodology/portador_identity_gate_result.md` e `docs/methodology/preparation_1_1_0.md`.
