# Pipeline de dados

```text
Portal da Transparência          Tesouro Transparente CKAN
         │                                │
         ▼                                ▼
 ingestion/cpgf.py               ingestion/siafi.py
         └──────────────┬─────────────────┘
                        ▼
                 validação/manifests
                        ▼
                 preprocessing/
                        ▼
              stg_cpgf_transacoes
                 ┌──────┼───────┐
                 ▼      ▼       ▼
              trails governance geography
                 └──────┼───────┘
                        ▼
                 Parquets curados
                        ▼
                     DuckDB
                 ┌──────┴──────┐
                 ▼             ▼
             Streamlit       IA tools
```

Kaggle é snapshot de distribuição/reprodução, não fonte primária.
