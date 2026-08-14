# Especificação Metodológica, Governança, Enriquecimento Geográfico e Contrato de Produção — CPGF

**Status documental:** CONGELADO PARA IMPLEMENTAÇÃO DE PRODUÇÃO  
**Versão das regras:** 1.2.0  
**Versão do motor/governança:** 1.3.2  
**Versão do enriquecimento geográfico:** 1.1.0  
**Versão da preparação:** 1.0.0  
**Data do congelamento:** 13 de agosto de 2026  
**Base de validação:** `CPGF_201301_a_202607.csv`  
**SHA-256:** `300789f9bd866f313df4ca5ee5dfca7234050ef2452443b61b1e58425ca0997b`  
**Fingerprint das regras:** `fc82b5c4e19f2d1d91a8086e4f2a75f7677038bce4b25896e98c7323577668d9`  
**Fingerprint do motor:** `8d03a9c13d6dbe79289cb696fdeb7e09a6e8c7fafc49d9944e046ed6b7d20acf`

## 1. Decisão formal de congelamento

Ficam formalmente congeladas, para a etapa de implementação em `src/`, três camadas versionadas e independentes:

- **Metodologia das trilhas T01–T09: versão 1.2.0.**
- **Motor/governança analítica: versão 1.3.2.**
- **Enriquecimento geográfico: versão 1.1.0.**

A decisão é sustentada pela reprodução integral da baseline das nove trilhas na execução V1.3.2, pela cobertura de 100% do universo elegível pelas bandas de exposição do fornecedor, pela ausência de multicolinearidade relevante, pela contribuição marginal positiva das famílias de evidência, pela estabilização dos contratos de sensibilidade e validação e pela validação da dimensão territorial UG→UF com cobertura integral das UGs da base atual.

A partir deste ponto, alterações nas regras ou na governança deixam de ser ajustes informais de notebook e passam a exigir controle de versão, testes e nova evidência metodológica quando aplicável.

## 2. Finalidade e hierarquia documental

Este documento é a **fonte canônica humana** do contrato metodológico. O YAML `contrato_cpgf_regras_1.2.0_motor_1.3.2.yaml` é o contrato legível pelo código. O DOCX é a cópia formal controlada. O arquivo `REGISTRO_CONGELAMENTO_CPGF.md` registra a decisão e seus critérios.

Hierarquia recomendada:

```text
docs/
  ESPECIFICACAO_METODOLOGICA_GOVERNANCA_CPGF_Regras1.2.0_Motor1.3.2.md
  REGISTRO_CONGELAMENTO_CPGF.md
config/
  contrato_cpgf.yaml
  contrato_territorial_geo.json
  catalogo_metricas_territoriais.csv
notebooks/
  Diagnostico_e_Calibracao_Trilhas_CPGF_v1_3_2.ipynb
src/
tests/
```

## 3. Princípios obrigatórios

1. Um **sinal analítico não equivale a fraude, irregularidade ou fracionamento**.
2. `DATA_TRANSACAO` é a referência temporal comportamental/normativa; competência do extrato é metadado de origem.
3. Comparações monetárias exatas usam **centavos inteiros**.
4. Cada sinal deve ser rastreável às transações que o originaram.
5. `NIVEL_TRIAGEM` é um rótulo **intra-trilha**, não uma escala de risco comparável entre T01–T09.
6. T08 e T09 são **contextos** e não aumentam a contagem de convergência núcleo.
7. A natureza da evidência é separada do status de validação.
8. Não se cria score opaco obrigatório.
9. Parâmetros legais e definições determinísticas permanecem bloqueados.
10. Correlação, VIF ou PCA **não excluem regra automaticamente**.
11. Assertividade somente pode ser estimada após validação humana.
12. 2012 e 2026 são períodos parciais na visão por DATA TRANSAÇÃO; 2013–2025 são os exercícios completos da baseline atual.
13. `UF_UG` representa a localização cadastral da Unidade Gestora, não o local físico presumido da transação.
14. `ANO_TRANSACAO` e `ANO_EXTRATO_REF` são referências temporais distintas e não podem ser combinadas em um ano híbrido.

## 4. Baseline de regressão das regras

Base: **1,876,087 registros** e **163 competências**. A tabela abaixo é baseline de regressão para o mesmo hash de entrada, e não uma meta de produção.

| Trilha | V1.2 | V1.3.2 | Diferença | Controle |
|---|---:|---:|---:|---|
| T01 | 49.675 | 49.675 | 0 | OK |
| T02 | 14 | 14 | 0 | OK |
| T03 | 7.534 | 7.534 | 0 | OK |
| T04 | 1.384 | 1.384 | 0 | OK |
| T05 | 1.693 | 1.693 | 0 | OK |
| T06 | 233 | 233 | 0 | OK |
| T07 | 1.089 | 1.089 | 0 | OK |
| T08 | 12 | 12 | 0 | OK |
| T09 | 46.941 | 46.941 | 0 | OK |

Todas as trilhas reproduziram a baseline com diferença zero.

## 5. Matriz resumida T01–T09

| Trilha | Nome | Papel | Unidade |
|---|---|---|---|
| T01 | Despesa realizada em final de semana | Núcleo — transação; recorrência contextual | Transação; contexto UG × portador × ano |
| T02 | Transação classificada como compra parcelada | Núcleo — transação | Transação |
| T03 | Repetição exata de transações | Núcleo — grupo; T03-B apenas diagnóstico | Grupo de transações; ponte até linhas originais |
| T04 | Repetição multiportador | Núcleo — fornecedor | UG × fornecedor × data × valor |
| T05 | Recorrência de aquisições | Núcleo — fornecedor | Episódio UG × fornecedor × ano |
| T06 | Concentração em fornecedor | Núcleo — estrutura do fornecedor/UG | UG × ano; fornecedor principal |
| T07 | Recorrência de múltiplos saques | Núcleo — portador/UG; episódio diário como diagnóstico | T07-A: UG × portador × dia; T07-B: UG × portador × ano |
| T08 | Lei de Newcomb-Benford | Contexto estatístico — não aumenta convergência núcleo | População; ano; UG × ano; valor/dígito; persistência |
| T09 | Referências financeiras aplicáveis | Contexto normativo-financeiro — não aumenta convergência núcleo | Transação; agregado descritivo UG × fornecedor × ano |

## 6. Famílias de evidência

As famílias são **agrupamentos substantivos**, não declarações de independência estatística.

| Família | Denominação | Trilhas |
|---|---|---|
| F1 | Conformidade operacional observável | T01 | T02 |
| F2 | Repetição e recorrência de aquisições | T03 | T04 | T05 |
| F3 | Estrutura e concentração de fornecedor | T06 |
| F4 | Comportamento de saque | T07 |
| F5 | Contexto estatístico forense | T08 |
| F6 | Contexto normativo-financeiro | T09 |

A análise V1.3.2 confirmou que as famílias acrescentam informação própria. Em `UG × fornecedor × ano`, as participações exclusivas foram aproximadamente 96,0% para F1, 79,2% para F2 e 62,8% para F3. Em `UG × ano`, todas as famílias núcleo também apresentaram contribuição marginal positiva.

## 7. Regras congeladas em detalhe

### T01 — Despesa realizada em final de semana

**Papel no motor:** Núcleo — transação; recorrência contextual  
**Unidade:** Transação; contexto UG × portador × ano  
**Regra congelada:** Sinalizar compra efetiva em sábado ou domingo pela DATA TRANSAÇÃO. A recorrência anual por UG × portador é contexto descritivo e não cria nova trilha.  
**Parâmetros congelados/controle:** Sábado/domingo. Sem limiar de recorrência congelado para novo alerta.  
**Triagem:** ATENCAO no sinal individual.  
**Fundamento normativo:** Guias e manuais de suprimento de fundos: necessidade de examinar justificativa de despesas realizadas em final de semana.  
**Fundamento científico/metodológico:** Fundamento científico predominantemente arquitetural em auditoria contínua; a condição material é normativa.  
**Limitação central:** A justificativa documental não está na base pública.  
**Baseline validada:** 49.675 sinais.
### T02 — Transação classificada como compra parcelada

**Papel no motor:** Núcleo — transação  
**Unidade:** Transação  
**Regra congelada:** TRANSAÇÃO = 'CPP LOJISTA TRF P/FATURA - REAL', por correspondência exata.  
**Parâmetros congelados/controle:** Código operacional bloqueado.  
**Triagem:** ATENCAO.  
**Fundamento normativo:** Guias/manuais de suprimento: conferência de pagamentos à vista, totais e em uma única parcela.  
**Fundamento científico/metodológico:** Fundamento científico predominantemente arquitetural em auditoria contínua; a condição material é normativa.  
**Limitação central:** O código operacional isolado não demonstra descumprimento.  
**Baseline validada:** 14 sinais.
### T03 — Repetição exata de transações

**Papel no motor:** Núcleo — grupo; T03-B apenas diagnóstico  
**Unidade:** Grupo de transações; ponte até linhas originais  
**Regra congelada:** T03-A: UG + portador + favorecido + data + valor em centavos + tipo de transação. T03-B: repetição integral apenas em registros observáveis; não entra na convergência.  
**Parâmetros congelados/controle:** N≥2; REFORCADO quando N≥3. Comparações monetárias em centavos inteiros.  
**Triagem:** ATENCAO para N=2; REFORCADO para N≥3.  
**Fundamento normativo:** Monitoramento do uso do suprimento; sem presunção normativa de duplicidade.  
**Fundamento científico/metodológico:** Auditoria analítica e drill-down de duplicações; interpretação condicionada ao contexto.  
**Limitação central:** Transações legítimas podem compartilhar atributos idênticos. Não chamar automaticamente de pagamento duplicado.  
**Baseline validada:** 7.534 grupos T03-A; T03-B: 7.523 grupos integralmente observáveis.
### T04 — Repetição multiportador

**Papel no motor:** Núcleo — fornecedor  
**Unidade:** UG × fornecedor × data × valor  
**Regra congelada:** Agrupar UG + fornecedor + data + valor e sinalizar quando houver pelo menos 2 portadores distintos.  
**Parâmetros congelados/controle:** ATENCAO=2 portadores; REFORCADO=3–4; MUITO_ELEVADO≥5.  
**Triagem:** Faixas analíticas por número de portadores; não representam gradação jurídica.  
**Fundamento normativo:** Monitoramento conjunto dos supridos da mesma UG para padrões de aquisições.  
**Fundamento científico/metodológico:** Análise relacional de padrões de compras; evidência não conclusiva.  
**Limitação central:** O objeto adquirido não é observável.  
**Baseline validada:** 1.384 grupos.
### T05 — Recorrência de aquisições

**Papel no motor:** Núcleo — fornecedor  
**Unidade:** Episódio UG × fornecedor × ano  
**Regra congelada:** Janela de 30 dias, ≥5 transações, ≥2 portadores e CV≤20%; janelas sobrepostas são deduplicadas mantendo o episódio mais forte.  
**Parâmetros congelados/controle:** Baseline: 30 dias; N≥5; portadores≥2; CV≤0,20. REFORCADO quando CV≤0,10. Similaridade robusta em ±20% da mediana como atributo.  
**Triagem:** ATENCAO / REFORCADO.  
**Fundamento normativo:** Monitoramento de aquisições recorrentes e possível fracionamento no âmbito da UG.  
**Fundamento científico/metodológico:** Detecção de padrões e auditoria analítica; parâmetros calibrados empiricamente.  
**Limitação central:** Sem objeto da despesa, não é possível confirmar fracionamento.  
**Baseline validada:** 1.693 episódios finais.
### T06 — Concentração em fornecedor

**Papel no motor:** Núcleo — estrutura do fornecedor/UG  
**Unidade:** UG × ano; fornecedor principal  
**Regra congelada:** Elegível com ≥20 compras identificadas, ≥3 fornecedores e cobertura de valor identificado ≥80%; sinal quando Top-1 por valor ≥50%.  
**Parâmetros congelados/controle:** ATENCAO 50–<70%; REFORCADO 70–<80%; MUITO_ELEVADO ≥80%. Calcular Top-1 por valor/quantidade, Top-5 e HHI.  
**Triagem:** ATENCAO / REFORCADO / MUITO_ELEVADO.  
**Fundamento normativo:** Boas práticas de razoabilidade e exame da estrutura de fornecedores.  
**Fundamento científico/metodológico:** Métricas de concentração, inclusive Top-1 e HHI, utilizadas como indicadores estruturais.  
**Limitação central:** Concentração não equivale a favorecimento ou direcionamento.  
**Baseline validada:** 233 UG-anos.
### T07 — Recorrência de múltiplos saques

**Papel no motor:** Núcleo — portador/UG; episódio diário como diagnóstico  
**Unidade:** T07-A: UG × portador × dia; T07-B: UG × portador × ano  
**Regra congelada:** T07-A identifica ≥2 saques no mesmo dia. T07-B prioriza portadores com ≥3 dias de múltiplos saques e N_DIAS_MULTISAQUE ≥ P90 do ano, desde que existam ≥10 comparáveis.  
**Parâmetros congelados/controle:** ≥3 dias; quantil anual 90%; mínimo 10 comparáveis.  
**Triagem:** T07-B é a saída prioritária da tabela-mestre.  
**Fundamento normativo:** Saques devem estar relacionados às ações autorizadas no ato de concessão.  
**Fundamento científico/metodológico:** Monitoramento longitudinal de comportamento e priorização relativa.  
**Limitação central:** A base pública não contém a autorização do saque.  
**Baseline validada:** 22.609 episódios diários diagnósticos; 1.089 portador-anos prioritários.
### T08 — Lei de Newcomb-Benford

**Papel no motor:** Contexto estatístico — não aumenta convergência núcleo  
**Unidade:** População; ano; UG × ano; valor/dígito; persistência  
**Regra congelada:** Elegibilidade → D1 → D12 → MAD → Z/χ² auxiliares → Summation → Number Duplication → drill-down → ranking relativo UG-ano → persistência relativa.  
**Parâmetros congelados/controle:** D12≥R$10; N<300 não aplicar; 300–999 exploratório; ≥1000 formal; ≥3000 maior robustez. Ranking relativo: 2013–2025, ≥10 UGs comparáveis, extremo ≥P90 do MAD D12.  
**Triagem:** Contexto; 12 extremos relativos na baseline.  
**Fundamento normativo:** Não é regra jurídica; funciona como técnica analítica auxiliar.  
**Fundamento científico/metodológico:** Nigrini (2012) e literatura de Benford aplicada à auditoria.  
**Limitação central:** Não conformidade não prova erro ou fraude; arredondamento e pontos de preço afetam a distribuição.  
**Baseline validada:** MAD D1=0,006939; MAD D12=0,002583; 12 extremos UG-ano; 3 UGs com persistência elevada.
### T09 — Referências financeiras aplicáveis

**Papel no motor:** Contexto normativo-financeiro — não aumenta convergência núcleo  
**Unidade:** Transação; agregado descritivo UG × fornecedor × ano  
**Regra congelada:** Aplicar dimensão normativa pela data e comparar em centavos inteiros em dois cenários: compras/serviços e obras/engenharia. Status por cenário: ABAIXO_FAIXA, PROXIMO_LIMITE, NO_LIMITE e ACIMA_LIMITE.  
**Parâmetros congelados/controle:** Faixa de proximidade baseline=90%; limites normativos bloqueados; categoria real não escolhida automaticamente.  
**Triagem:** INFORMATIVO para próximo/no limite; ATENCAO acima de pelo menos um cenário; REFORCADO acima de ambos.  
**Fundamento normativo:** Portaria MF 95/2002 e Portaria Normativa MF 1.344/2023, conforme vigência, com valores legais atualizados.  
**Fundamento científico/metodológico:** Uso de benchmarks normativos como contexto de triagem; não substitui enquadramento jurídico.  
**Limitação central:** Objeto/categoria e ato de concessão não estão disponíveis; não declarar fracionamento.  
**Baseline validada:** 46.941 sinais/contextos.


## 8. Governança: unidades comparáveis

### 8.1 `UG × fornecedor × ano`

- Universo completo 2013–2025: **522.053** unidades.
- Trilhas núcleo comparáveis: T01–T06.
- T08: contexto da respectiva UG-ano.
- T09: contexto do mesmo UG-fornecedor-ano.
- Flags elegíveis para PCA/VIF: **T01, T03, T04, T05 e T06**.
- T02 permanece no motor, mas é rara demais para PCA/VIF.

### 8.2 `UG × ano`

- Universo completo 2013–2025: **13.785** unidades.
- Trilhas núcleo: T01–T07.
- T08/T09: contextos.
- Flags elegíveis para PCA/VIF: **T01, T03, T04, T05, T06 e T07**.
- T02 permanece descritiva e fora de PCA/VIF.

## 9. Controle de exposição

### 9.1 Fornecedor — bandas fixas de contagem

A distribuição de `N_COMPRAS_FORNECEDOR` é discreta e concentrada em empates. Por isso, não se usam decis no nível fornecedor.

| Ordem | Banda | Unidades | T01 | T03 | T04 | T05 |
|---:|---|---:|---:|---:|---:|---:|
| 1 | 1 compra | 332.344 | 4.38% | 0.00% | 0.00% | 0.00% |
| 2 | 2 compras | 88.882 | 5.98% | 0.79% | 0.30% | 0.00% |
| 3 | 3–4 compras | 55.968 | 7.85% | 1.77% | 0.39% | 0.00% |
| 4 | 5–9 compras | 31.672 | 11.07% | 3.53% | 0.82% | 0.99% |
| 5 | 10–19 compras | 9.964 | 17.45% | 6.63% | 1.55% | 4.61% |
| 6 | 20+ compras | 3.223 | 28.76% | 15.54% | 5.21% | 18.21% |

As seis bandas recompõem **100% das 522.053 unidades** dos exercícios completos.

### 9.2 UG — decis anuais

Em `UG × ano`, a exposição é medida por `N_OPERACOES_EFETIVAS` e dividida em dez decis dentro de cada exercício.

A incidência de diversas trilhas cresce com a exposição. Por exemplo, T01 passa de aproximadamente 7,5% no primeiro decil para 80,2% no décimo; T03, de 0,8% para 52,4%. Esse resultado demonstra que convergência bruta deve ser interpretada junto ao volume operacional.

T06 não segue o mesmo padrão monotônico, reforçando que exposição não explica mecanicamente todas as trilhas.

## 10. Elegibilidade estatística e análise de redundância

### 10.1 Regra de elegibilidade

Para PCA/VIF, uma flag precisa de:

- pelo menos **30 unidades positivas**;
- pelo menos **30 unidades negativas**.

| Trilha | Positivos fornecedor-ano | Elegibilidade | PCA/VIF |
|---|---:|---|---|
| T01 | 30.456 | SUFICIENTE | Sim |
| T02 | 1 | DIAGNOSTICO_ESTATISTICO_INSUFICIENTE | Não |
| T03 | 3.973 | SUFICIENTE | Sim |
| T04 | 1.071 | SUFICIENTE | Sim |
| T05 | 1.358 | SUFICIENTE | Sim |
| T06 | 218 | SUFICIENTE | Sim |

T02 possui apenas 1 positivo em fornecedor-ano e 7 positivos em UG-ano; por isso recebe `DIAGNOSTICO_ESTATISTICO_INSUFICIENTE`, sem ser removida do motor.

### 10.2 Diagnósticos congelados

- VIF máximo fornecedor: **1.024**.
- Índice de condição fornecedor: **1.179**.
- VIF máximo UG: **1.209**.
- Índice de condição UG: **1.702**.
- CP1 fornecedor: **24.26%** da variância.
- CP1 UG: **30.64%** da variância.

Não há evidência de multicolinearidade relevante ou de componente único dominante.

### 10.3 Interpretação de F2

T03, T04 e T05 permanecem separadas. Mesmo controlando exposição, T04×T05 apresenta associação, sobretudo em fornecedores muito recorrentes, mas longe de redundância. T03×T05 torna-se praticamente independente nas bandas mais comparáveis.

Consequência: **F2 é uma família de evidência composta por manifestações distintas de repetição/recorrência, e não uma única regra fragmentada em três.**

## 11. Contrato de sensibilidade

Toda saída de cenário deve declarar:

`TRILHA`, `PARAMETRO`, `VALOR_CENARIO`, `METRICA`, `UNIDADE_CONTAGEM`, `VALOR_METRICA`, `N_SINAIS_TOTAL_CENARIO`, `N_SINAIS_BASELINE`, `COMPARAVEL_COM_BASELINE`, `TIPO_CONTROLE`, `BASELINE`, `OBSERVACAO`.

### Parâmetros bloqueados

- T01: definição de sábado/domingo.
- T02: código oficial da transação.
- T08: fórmulas/probabilidades da Lei de Benford.
- T09: valores dos limites normativos.

### Parâmetros experimentais

- T03: mínimo de ocorrências.
- T04: mínimo de portadores.
- T05: janela, N, portadores e CV.
- T06: Top-1 e filtros analíticos.
- T07: mínimo de dias e percentil.
- T09: faixa de proximidade, sem alterar o limite legal.

### Semânticas especiais

**T05.** A grade de 160 combinações é grade de calibração de grupos representativos. Não deve ser comparada diretamente aos **1.693 episódios finais**. O simulador de produção deve reexecutar a lógica completa de episódios/deduplicação.

**T08.** `N` representa tamanho da população analisada; MAD e classificação são métricas do cenário. Não representa quantidade de sinais T08.

**T09.** Alterar a proximidade modifica somente o subconjunto `PROXIMO_LIMITE`. Na baseline de 90%, são 22.954 próximos + 23.987 no limite/acima = **46.941 sinais totais**.

Toda interface deve rotular mudanças como:

> **CENÁRIO EXPERIMENTAL — não altera a baseline metodológica.**

## 12. Protocolo de validação humana

### 12.1 Status

- `NAO_VALIDADO`
- `EM_ANALISE`
- `CONFIRMADO`
- `JUSTIFICADO`
- `FALSO_POSITIVO`
- `ERRO_DADO`
- `INCONCLUSIVO`

`CONFIRMADO` nunca é atribuído automaticamente apenas porque uma condição determinística foi observada.

### 12.2 Amostragem

- Estratificação: `TRILHA × NIVEL_TRIAGEM`.
- Meta: até 30 sinais por trilha, redistribuídos entre níveis quando necessário.
- Seleção: hash determinístico dentro do estrato.
- Amostra baseline: **236 sinais**.
- Peso: `PESO_AMOSTRAL = N_POP_ESTRATO / N_AMOSTRA_ESTRATO`.

Exemplos da baseline:

- T03: 15 ATENCAO + 15 REFORCADO.
- T04: 14 ATENCAO + 13 REFORCADO + 3 MUITO_ELEVADO.
- T06: 10 em cada nível.
- T09: 10 INFORMATIVO + 10 ATENCAO + 10 REFORCADO.
- T02 e T08: todos os casos disponíveis por raridade.

### 12.3 Feedback

- `CONFIRMADO`: preservar evidência e monitorar estabilidade.
- `JUSTIFICADO`: verificar se exceção legítima deve entrar na elegibilidade.
- `FALSO_POSITIVO`: reexaminar um parâmetro por vez e medir novamente volume, sobreposição e contribuição marginal.
- `ERRO_DADO`: corrigir a camada de dados, sem recalibrar limiar por erro de origem.
- `INCONCLUSIVO`: rever evidência mínima antes de alterar regra.

## 13. Convergência e contrato do dashboard

### 13.1 Convergência

**UG × ano:** T01–T07 formam o núcleo. T08/T09 são contextos.  
**UG × fornecedor × ano:** T01–T06 formam o núcleo. T08 contextualiza a UG-ano; T09 contextualiza o mesmo fornecedor-ano.

A convergência não representa probabilidade de fraude.

### 13.2 Abas

1. Visão geral
2. Motor de Trilhas
3. Diagnóstico do Motor
4. Sinais e Validação
5. Metodologia
6. Assistente IA

### 13.3 Exposição no dashboard

**Fornecedor:** bandas fixas `1`, `2`, `3–4`, `5–9`, `10–19`, `20+`.  
**UG:** decis anuais 1–10.

A interface não deve chamar as bandas do fornecedor de decis ou percentis.

### 13.4 Assistente IA

Pode explicar evidência estruturada, parâmetros, fundamentos e limitações. Não pode declarar fraude automaticamente, declarar fracionamento sem objeto/documentação, alterar limites legais, tratar correlação como causalidade ou ocultar versão de regra.


## 14. Enriquecimento geográfico congelado — versão 1.1.0

A dimensão territorial é uma **camada de enriquecimento e navegação**, não uma nova trilha de irregularidade. Ela associa `CÓDIGO UNIDADE GESTORA` à UF cadastral da respectiva UG e prepara agregados leves para mapa e drill-down.

### 14.1 Chave, fonte e proveniência

A chave canônica é:

```text
UG_ID = string de 6 dígitos
```

Exemplos: `133 → 000133` e `110161 → 110161`.

A dimensão de referência possui **49.552 UGs únicas**: 49.547 provenientes do cadastro SIAFI versão 2025 e 5 complementos manuais explicitamente identificados. No universo CPGF, 2.148 das 2.153 UGs foram associadas diretamente ao SIAFI e as cinco restantes por complemento documentado, resultando em **100% de cobertura das UGs e dos registros da base atual**.

Os complementos são: `511328→SP`, `511341→SP`, `510356→ES`, `110703→DF` e `110745→DF`. Eles preservam `TIPO_FONTE_UF=COMPLEMENTO_MANUAL` e `VERSAO_FONTE_UF=2026-08-13`.

A interpretação congelada é:

> **UF da Unidade Gestora = localização cadastral da UG; não representa necessariamente o local físico da transação.**

### 14.2 Duas referências temporais independentes

A V1.1 proíbe um ano híbrido. O dashboard deve exigir a escolha explícita da referência temporal.

| Referência | Campo | Cobertura | Métrica principal | Uso |
|---|---|---|---|---|
| TRANSACAO | `ANO_TRANSACAO` | somente registros com `DATA TRANSAÇÃO` observável | `VALOR_TRANSACIONADO_OBSERVAVEL` | comportamento temporal, compras, saques e integração com trilhas |
| EXTRATO | `ANO_EXTRATO_REF` | registros atribuíveis ao ano do extrato, inclusive sem data da transação observável | `VALOR_TOTAL_REGISTRADO` | cobertura do extrato, sigilo e observabilidade |

A visão `TRANSACAO` possui 405 linhas `UF×ano` para 2012–2026 e recompõe **R$ 506.719.563,42** em 1.506.714 operações com data observável. A visão `EXTRATO` possui 378 linhas para 2013–2026 e recompõe **R$ 976.936.749,90** em 1.876.065 registros positivos sem os ajustes/contestações definidos pelo pipeline.

### 14.3 Sigilo e observabilidade

Na referência `EXTRATO`, **R$ 506.719.563,42 (51,87%)** do valor possui `DATA TRANSAÇÃO` observável. O valor classificado como sigiloso soma **R$ 470.219.284,18 (48,13%)**. Em quantidade, 80,31% dos registros possuem data observável e 19,69% são sigilosos.

Sigilo e observabilidade são dimensões relacionadas, porém **não são classes mutuamente exclusivas**. Na baseline, 4 registros, somando R$ 2.097,70, são classificados como sigilosos e ainda possuem data da transação observável. Por isso, `TAXA_OBSERVABILIDADE` e `PCT_SIGILO` não devem ser forçados a somar exatamente 100%.

As métricas `TAXA_OBSERVABILIDADE_VALOR` e `TAXA_OBSERVABILIDADE_REGISTROS` descrevem a **observabilidade da base pública** e não constituem avaliação de irregularidade ou de desempenho institucional.

### 14.4 Contrato para mapa e dashboard

O artefato semântico recomendado é `agg_cpgf_uf_ano_dashboard_long.parquet`, com 6.615 linhas na baseline e 17 combinações referência–métrica catalogadas. Os controles mínimos da interface são:

```text
REFERENCIA_TEMPORAL
ANO
METRICA
```

A POC utiliza Folium e geometrias estaduais do `geobr`. O drill-down previsto é:

```text
Brasil → UF da UG → UG → fornecedor/portador → T01–T09
```

A geografia serve como porta de entrada para exploração e investigação, sem alterar a metodologia das trilhas ou a contagem de convergência.

### 14.5 Salvaguardas de produção

- não interpretar `UF_UG` como local físico da compra ou saque;
- não combinar `ANO_TRANSACAO` e `ANO_EXTRATO_REF` em uma única métrica temporal;
- apresentar sigilo e observabilidade na referência `EXTRATO`;
- tratar "cobertura integral" como cobertura do universo analítico positivo sem os ajustes/contestações definidos pelo pipeline, e não como sinônimo de todas as linhas brutas;
- preservar `FONTE_UF`, `TIPO_FONTE_UF` e `VERSAO_FONTE_UF`;
- não transformar o enriquecimento territorial em T10.

## 15. Controle de mudança

### 15.1 Regras

- **PATCH:** correção de implementação sem alterar semântica da regra.
- **MINOR:** mudança de parâmetro, população, classificação ou regra que altere sinais/interpretação.
- **MAJOR:** mudança da arquitetura analítica ou constructo metodológico/normativo central.

### 15.2 Motor/governança

- **PATCH:** correção de governança/contrato sem alterar T01–T09.
- **MINOR:** mudança da técnica de governança com efeito material na interpretação/diagnóstico.
- **MAJOR:** mudança da arquitetura de governança ou do constructo de validação.

Toda alteração em item congelado exige, no mesmo change set: contrato, testes, evidência de calibração quando aplicável, atualização documental e nova versão.

## 16. Critérios de aceite para `src/`

1. Semântica T01–T09 idêntica à versão 1.2.0.
2. Testes unitários positivos, negativos e de fronteira.
3. Centavos inteiros em comparações exatas.
4. Rastreabilidade `ID_SINAL → ID_TRANSACAO`.
5. T03-B fora da convergência.
6. T07-A como drill-down; T07-B como saída prioritária.
7. T08/T09 fora da contagem núcleo.
8. Exposição fornecedor por bandas fixas e exposição UG por decis anuais.
9. PCA/VIF somente para flags elegíveis.
10. Sensibilidade com métrica/unidade explícitas.
11. Validação preservando estrato e peso amostral.
12. Regressão compatível com a baseline quando executada sobre o mesmo SHA-256.

13. `UG_ID` como string canônica de seis dígitos e dimensão UG→UF com proveniência.
14. `ANO_TRANSACAO` e `ANO_EXTRATO_REF` separados, sem fallback semântico entre as referências.
15. Sigilo e observabilidade calculados na referência `EXTRATO`.
16. Agregados territoriais consumidos pelo dashboard sem leitura do fato bruto em tempo real.
17. Camada geográfica fora de T01–T09 e da contagem de convergência.

## 17. Dívida técnica conhecida sem efeito metodológico

Dois resíduos de nomenclatura da etapa de notebook devem ser corrigidos na migração para produção, sem nova versão metodológica:

- `N_V131` no CSV de regressão → usar `N_MOTOR_ATUAL`.
- `catalogo_trilhas_v1_3.csv` → usar nome estável `catalogo_trilhas.csv`, mantendo versões em metadados internos.

## 18. Bases documentais e referências

A especificação consolida a Matriz Formal, a Matriz de Implementação, o notebook V1.3.2 e sua execução validada, o dicionário público do CPGF, os normativos de suprimento de fundos, os contratos de governança gerados pelo motor e as referências metodológicas utilizadas no projeto.

**BRASIL. Controladoria-Geral da União.** Guia de Boas Práticas em Suprimento de Fundos e Cartão de Pagamento. Brasília, DF, 2024.

**BRASIL. Ministério da Fazenda.** Portaria MF nº 95, de 19 de abril de 2002.

**BRASIL. Ministério da Fazenda.** Portaria Normativa MF nº 1.344, de 31 de outubro de 2023.

**NIGRINI, Mark J.** *Benford's Law: Applications for Forensic Accounting, Auditing, and Fraud Detection*. Hoboken: Wiley, 2012.

> O fundamento científico específico de cada trilha possui maturidade desigual. Onde não existe referência científica específica congelada, o contrato registra explicitamente fundamento arquitetural/metodológico ou normativo, evitando atribuir ao artigo científico um suporte que ele não fornece.


### Artefatos geográficos congelados incluídos neste pacote

- `contrato_territorial_geo_1.1.0.json` — contrato territorial produzido pela execução validada;
- `metadata_execucao_geo_1.1.0.json` — hashes, cobertura e referências temporais;
- `catalogo_metricas_territoriais.csv` — catálogo semântico das 17 combinações referência–métrica;
- `resumo_observabilidade_ano_extrato.csv` — série anual usada para validar sigilo e observabilidade.
