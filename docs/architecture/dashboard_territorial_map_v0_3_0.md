# Dashboard territorial 0.3.0-dev

## Objetivo

O PR #24 habilita a visualização territorial estadual no Streamlit sem alterar a Geo 1.1.0 nem o Serving 1.5.0. A página consulta exclusivamente os objetos materializados no DuckDB read-only.

## Controles

A navegação territorial segue a hierarquia:

1. referência temporal (`TRANSACAO` ou `EXTRATO`);
2. ano;
3. métrica prevista em `geo_metric_catalog`;
4. UF para contextualização das UGs.

A referência `TRANSACAO` usa o ano da data de transação observável. A referência `EXTRATO` usa o ano de referência do ciclo. As duas referências permanecem separadas.

## Mapa

O mapa usa pontos proporcionais posicionados por uma âncora cartográfica para cada uma das 27 UFs. A coordenada é apenas um recurso de renderização e não participa de qualquer cálculo, ranking, filtro, trilha ou sinal.

As âncoras foram adaptadas do arquivo público `csv/estados.csv` do repositório `kelvins/Municipios-Brasileiros`. Os valores territoriais, por sua vez, vêm exclusivamente da Geo 1.1.0 materializada no Serving 1.5.0.

A escolha por pontos proporcionais evita uma dependência externa de malha GeoJSON durante a execução e preserva o funcionamento offline do bundle.

## Interpretação

`UF_UG` significa localização cadastral da Unidade Gestora. Portanto, o painel deve ser lido como **transações/registros do CPGF por UF da UG**, e não como local físico do gasto.

O drill-down por UG é uma contextualização baseada na matriz `matrix_ug_year`. Ele não é apresentado como decomposição direta das métricas de extrato, pois essa granularidade não foi materializada no Serving 1.5.0.

## Validação

O commit funcional `aa1eb6abc8d037cb36c5a68ca590be7dcbe0bec9` foi validado em dois gates independentes:

- `tests`, run `31862734841`: Ruff e pytest em Python 3.11 e 3.12, todos com PASS;
- `dashboard-smoke-release`, run `31862734860`: bootstrap e validação da release publicada do Serving 1.5.0 seguidos da execução headless da home e das sete páginas Streamlit, incluindo a página territorial, com PASS.

Após esse gate, o smoke remoto volta a ser exclusivamente manual por `workflow_dispatch`.

## Salvaguardas

- nenhuma alteração em T01–T09;
- nenhuma alteração no Motor/Governança 1.3.2;
- nenhuma alteração na Geo 1.1.0;
- nenhuma alteração no Serving 1.5.0;
- nenhuma reconstrução do enriquecimento no Streamlit;
- nenhuma leitura do fato CPGF bruto durante a navegação;
- sinais continuam sendo apresentados como elementos de triagem, nunca como conclusão automática de fraude ou irregularidade.
