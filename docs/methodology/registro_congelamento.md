# Registro Formal de Congelamento — CPGF

**Data:** 13 de agosto de 2026  
**Objeto:** motor de trilhas analíticas, governança e enriquecimento territorial para dados públicos do Cartão de Pagamento do Governo Federal  
**Decisão:** APROVADO PARA MIGRAÇÃO À IMPLEMENTAÇÃO DE PRODUÇÃO

## Camadas congeladas

- **Regras T01–T09:** `1.2.0`
- **Motor/Governança:** `1.3.2`
- **Enriquecimento Geográfico:** `1.1.0`
- **Preparação analítica das trilhas:** `1.0.0`

## Evidência das regras e governança

- Base CPGF: `CPGF_201301_a_202607.csv`
- SHA-256 CPGF: `300789f9bd866f313df4ca5ee5dfca7234050ef2452443b61b1e58425ca0997b`
- Registros: 1.876.087
- Competências: 163
- Fingerprint das regras: `fc82b5c4e19f2d1d91a8086e4f2a75f7677038bce4b25896e98c7323577668d9`
- Fingerprint do motor: `8d03a9c13d6dbe79289cb696fdeb7e09a6e8c7fafc49d9944e046ed6b7d20acf`
- Regressão: **T01–T09 com diferença zero**

## Evidência do enriquecimento geográfico

- Cadastro SIAFI de referência: versão `2025`
- SHA-256 SIAFI: `ee2064fb5e0ce5e729365e1a1f2d80f92a55a659da8160cddd10db7f438c0634`
- UGs do CPGF: 2.153
- Correspondência direta no SIAFI: 2.148
- Complementos manuais documentados: 5
- Cobertura final UG→UF: **100%**
- Cobertura final dos registros por UF: **100%**
- Visão por ano da transação: 405 linhas UF×ano; R$ 506.719.563,42; 1.506.714 operações observáveis
- Visão por ano do extrato: 378 linhas UF×ano; R$ 976.936.749,90; 1.876.065 registros
- Valor sob sigilo na visão do extrato: R$ 470.219.284,18 (48,13%)
- Valor com data da transação observável: R$ 506.719.563,42 (51,87%)

## Critérios atendidos

1. Regras 1.2.0 integralmente reproduzidas pela execução V1.3.2.
2. Governança 1.3.2 estabilizada com exposição, elegibilidade, redundância, sensibilidade e validação.
3. As seis bandas de exposição do fornecedor recompõem 100% do universo elegível.
4. T02 permanece no motor e é excluída de PCA/VIF apenas por insuficiência estatística.
5. Famílias de evidência preservam contribuição marginal positiva.
6. A dimensão geográfica normaliza `UG_ID` como string de seis dígitos e alcança 100% de cobertura na base atual.
7. As cinco UGs não encontradas no cadastro foram complementadas com proveniência explícita.
8. A V1.1 separa `ANO_TRANSACAO` de `ANO_EXTRATO_REF`, sem ano híbrido.
9. Sigilo e observabilidade são calculados na referência do extrato e reconhecidos como dimensões não necessariamente mutuamente exclusivas.
10. A tabela longa territorial e o contrato de métricas estão prontos para o dashboard.
11. A dimensão geográfica permanece fora das regras T01–T09 e da contagem de convergência.

## Salvaguarda

O congelamento significa que as três camadas estão suficientemente estabilizadas para implementação em código de produção. Não significa que sinais, padrões territoriais, concentração, sigilo ou baixa observabilidade provem fraude, irregularidade ou fracionamento.

`UF_UG` representa a localização cadastral da Unidade Gestora e não deve ser interpretada como local físico da transação.

## Próxima etapa autorizada

Desenho da arquitetura definitiva do repositório, extração para `src/`, testes automatizados e integração com dashboard/API/RAG, mantendo este pacote como contrato formal de referência.
