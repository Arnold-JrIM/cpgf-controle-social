# Arquitetura do repositório

A UI não implementa regra analítica. O LLM não implementa regra analítica. `src/cpgf/` concentra domínio e serviços reutilizáveis.

```text
UI / LangGraph
      ↓
serving/
      ↓
dados curados
      ↓
trails/ governance/ geography/
      ↓
preprocessing/
      ↓
ingestion/
```

## Fronteiras
- `ingestion/`: aquisição, versão, download, hash, schema e manifests.
- `preprocessing/`: normalização única para datas, valores, identificadores e tipos de transação.
- `trails/`: T01–T09 versão 1.2.0.
- `governance/`: Motor 1.3.2.
- `geography/`: Geo 1.1.0.
- `serving/`: fronteira estável para Streamlit e IA.
- `ai/`: LangChain + LangGraph consumindo ferramentas seguras.

Antes de T03/T04/T05/T07, executar `pre_src_gate_portador.md`.
