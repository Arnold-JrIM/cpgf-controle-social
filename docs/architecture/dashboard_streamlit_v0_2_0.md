# Dashboard Streamlit 0.2.0-dev

## Finalidade

O PR #22 substitui os placeholders de interface por um dashboard funcional conectado ao
Serving 1.4.0. A aplicação consulta o catálogo DuckDB em modo read-only e não executa
preparação, trilhas ou diagnósticos de governança durante a navegação.

## Identidade visual

A interface adota linguagem institucional moderna:

- fundo claro;
- azul-marinho e cinza como base;
- laranja reservado a sinais e destaques analíticos;
- ausência de fotografias decorativas;
- gráficos e tabelas com densidade moderada;
- aviso persistente de que sinal analítico não equivale a fraude ou irregularidade.

## Páginas

1. **Visão Geral** — materialidade, volume, recorrência e evolução anual;
2. **Distribuição Territorial** — cobertura por UG e exposição anual;
3. **Trilhas Analíticas** — T01–T09, prevalência e recorrência;
4. **Diagnóstico do Motor** — Jaccard, contribuição marginal, VIF, índices de condição e PCA;
5. **Sinais e Validação** — unidades priorizadas para verificação;
6. **Metodologia** — versões, cobertura temporal e cadeia de processamento;
7. **Assistente IA** — página preparatória, sem integração do LLM nesta etapa.

## Consultas

As consultas agregadas são SQL fixo definido em `cpgf.dashboard.data`. Entradas do usuário
são apenas valores parametrizados de ano e código de UG. Não há caixa de SQL livre nem
interpolação de identificadores fornecidos pelo usuário.

Os diagnósticos pequenos são lidos por `ServingRepository`, que continua limitado aos nomes
lógicos registrados no catálogo.

## Cache e bootstrap

`cpgf.dashboard.runtime` usa `st.cache_resource` para evitar revalidar e reabrir o bundle em
cada rerun da mesma sessão. O primeiro acesso pode baixar a release oficial do Serving 1.4.0;
acessos subsequentes reutilizam o bundle local íntegro.

## Limitação geográfica

O Serving 1.4.0 não materializa a dimensão oficial `UG → UF/município`. Embora a versão
geográfica 1.1.0 esteja registrada no projeto, seus módulos ainda não compõem o bundle de
serving. O dashboard não tenta inferir território a partir do código da UG.

Por isso, a página territorial apresenta cobertura por Unidade Gestora e informa a limitação.
Um mapa por UF/município deverá ser habilitado somente após uma dimensão oficial curada ser
materializada e validada.

## Salvaguardas

O dashboard:

- não altera T01–T09;
- não cria score de risco;
- não classifica fraude;
- não remove trilhas por sobreposição estatística;
- não expõe SQL arbitrário;
- não modifica o bundle materializado;
- mantém T08/T09 como contexto na leitura do núcleo de governança.
