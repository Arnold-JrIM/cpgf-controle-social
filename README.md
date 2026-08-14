# CPGF — Controle Social Orientado por Dados e IA

Projeto público de TCC para transformar dados abertos do **Cartão de Pagamento do Governo Federal (CPGF)** em uma aplicação reproduzível de exploração, visualização, sinais analíticos explicáveis e assistência conversacional.

## Estado metodológico

| Camada | Versão | Estado |
|---|---:|---|
| Preparação analítica — produção | 1.1.0 | atual |
| Preparação analítica — baseline | 1.0.0 | preservada para regressão |
| Regras T01–T09 | 1.2.0 | congeladas |
| Motor/Governança | 1.3.2 | congelado |
| Enriquecimento geográfico | 1.1.0 | congelado |
| Aplicação | 0.1.0-dev | em construção |

As trilhas produzem **sinais analíticos para triagem e controle social**. Elas não produzem automaticamente conclusões de fraude, irregularidade ou fracionamento.

## Arquitetura

```text
Fontes oficiais
    ├── Portal da Transparência — CPGF
    └── Tesouro Transparente / CKAN — Unidades Gestoras
             ↓
          ingestion/
             ↓
        preprocessing/
       ┌─────┼─────────┐
       ↓     ↓         ↓
    trails governance geography
       └─────┼─────────┘
             ↓
      Parquet + DuckDB
        ┌────┴────┐
        ↓         ↓
   Streamlit   LangGraph
```

## Dados

Os arquivos brutos completos **não são versionados no Git**. A camada de ingestão oferece dois caminhos: fontes oficiais e snapshot público do Kaggle. Os testes sem rede validam o contrato do código, e o workflow `ingestion-smoke` verifica periodicamente as superfícies externas sem contornar proteções do Portal.

### Fontes

- CPGF: Portal da Transparência, downloads mensais por competência.
- Cadastro de UGs: Tesouro Transparente / SIAFI, dataset CKAN.
- Snapshot de reprodução: Kaggle `arnoldjrim/dados-abertos-cpgf-2013-a-2026`.

## Baseline de regressão

`CPGF_201301_a_202607.csv`

- 1.876.087 registros
- 163 competências
- SHA-256 `300789f9bd866f313df4ca5ee5dfca7234050ef2452443b61b1e58425ca0997b`

| Trilha | Contagem |
|---|---:|
| T01 | 49.675 |
| T02 | 14 |
| T03 | 7.534 |
| T04 | 1.384 |
| T05 | 1.693 |
| T06 | 233 |
| T07 | 1.089 |
| T08 | 12 |
| T09 | 46.941 |

Esses números pertencem à baseline histórica com Preparação 1.0.0 e não são metas para bases futuras.

## Identidade do portador

O gate metodológico foi fechado. A produção utiliza `UG_ID + CPF normalizado + nome normalizado` como `PORTADOR_ID` na Preparação 1.1.0. A semântica 1.0.0 permanece disponível apenas para reprodução da baseline histórica.

Veja `docs/methodology/preparation_1_1_0.md`.

## Desenvolvimento

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
streamlit run streamlit_app.py
```

## Assistente IA

- LangChain + LangGraph;
- OpenAI API;
- modo demonstração com chave dedicada, autenticação e quota;
- modo BYOK com chave apenas em memória de sessão;
- SQL somente leitura contra views autorizadas;
- o LLM não recalcula nem altera T01–T09.

Hospedagem oficial da POC: **Streamlit Community Cloud**.
