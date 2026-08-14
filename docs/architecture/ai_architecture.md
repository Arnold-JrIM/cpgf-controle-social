# Arquitetura de IA

- LangChain + LangGraph;
- OpenAI API;
- três rotas iniciais: RAG, consulta de dados e explicação de sinais.

```text
pergunta → guardrail → router → RAG | Dados | Sinais → síntese → guardrail → resposta
```

## Credenciais
- Demo: chave dedicada do projeto em secrets do Streamlit; autenticação e quota antes da publicação.
- BYOK: chave somente em memória de sessão; nunca em arquivo, banco, log ou cache global.

## SQL
Somente `SELECT` contra views autorizadas, com limites de linhas, tempo e recursos.
