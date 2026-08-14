# CPGF — Controle Social Orientado por Dados e IA

Projeto público de TCC para transformar dados abertos do **Cartão de Pagamento do Governo Federal (CPGF)** em uma aplicação reproduzível de exploração, visualização, sinais analíticos explicáveis e assistência conversacional.

## Estado metodológico

| Camada | Versão | Estado |
|---|---:|---|
| Preparação analítica | 1.0.0 | baseline |
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

Os arquivos brutos completos **não são versionados no Git**. Há dois caminhos previstos:

```bash
python scripts/bootstrap_data.py --source kaggle --dry-run
python scripts/bootstrap_data.py --source official --dry-run
```

Nesta versão inicial, os comandos formalizam a interface. A ingestão funcional será a próxima etapa.

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

Esses números são baseline de regressão sobre a mesma base, não metas para atualizações futuras.

## Gate técnico antes da migração das trilhas

T03/T04/T05/T07 permanecem bloqueadas até o fechamento do teste de identidade de `PORTADOR_ID`. A implementação deverá comparar a chave do notebook com uma chave composta baseada em `UG_ID + CPF normalizado + nome normalizado` e documentar o impacto.

Veja `docs/architecture/pre_src_gate_portador.md`.

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
