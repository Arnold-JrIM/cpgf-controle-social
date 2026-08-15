# Fundação segura do Assistente IA — 0.4.0-dev

## Finalidade

O PR #25 cria a fronteira entre a futura camada conversacional e o sistema analítico determinístico. Nenhum modelo de linguagem é chamado nesta etapa. O objetivo é tornar as capacidades do agente explícitas, restritas, testáveis e auditáveis antes da introdução de RAG e LLM.

## Princípio arquitetural

O LLM não será o motor de auditoria. T01–T09, Preparação, Governança, Geo e Serving permanecem fora do modelo e conservam seus próprios contratos versionados.

A superfície inicial do agente contém sete ferramentas registradas, todas construídas sobre consultas que já existem no dashboard ou sobre metadados versionados:

- `overview`;
- `trail_prevalence`;
- `top_ugs`;
- `top_suppliers`;
- `territorial_metric`;
- `territorial_ug_context`;
- `methodology`.

Não existe ferramenta `sql`. Também não existe ferramenta RAG ativa neste PR.

## Contratos

Os argumentos são validados com Pydantic e `extra="forbid"`. Isso impede que uma futura chamada de ferramenta acrescente silenciosamente campos como SQL, nomes de tabela ou parâmetros não previstos pelo contrato.

Os resultados retornam estrutura comum com:

- nome da ferramenta;
- registros JSON-safe;
- resumo;
- avisos metodológicos;
- proveniência das versões Regras, Motor, Serving e Geo;
- marcação explícita `read_only=true`.

## Guardrails

Os controles implementados nesta etapa operam em camadas diferentes:

1. entrada: tamanho, caracteres de controle e pedidos explícitos de mutação/recomputação são rejeitados;
2. capacidade: apenas nomes registrados podem ser despachados;
3. SQL: qualquer tentativa de usar a função de SQL livre falha por definição;
4. saída: frases categóricas simples de fraude/irregularidade podem ser rejeitadas antes da apresentação;
5. estado: o objeto de estado é estruturado e não possui campo de credencial.

O guardrail lexical de entrada não é apresentado como solução completa contra prompt injection. A segurança principal decorre da ausência de capacidades mutáveis e do contrato fechado das ferramentas.

## Roteamento

O roteador do PR #25 é lexical e determinístico. Ele classifica de forma conservadora perguntas sobre visão geral, trilhas, território, fornecedores, UGs e metodologia, ou devolve `unsupported`. Ele não executa ferramenta automaticamente e não infere parâmetros analíticos ausentes.

A futura camada LLM poderá substituir ou complementar esse roteamento sem ampliar a superfície de ferramentas.

## Fora do escopo

- chamada OpenAI ou de outro provedor;
- LangGraph em execução;
- geração de SQL;
- RAG normativo;
- embeddings;
- armazenamento de chave de API;
- memória conversacional persistente;
- alteração/recalibração das trilhas;
- confirmação automática de fraude ou irregularidade.

## Gate de validação

O commit funcional `d9b9eb9657fcb1f316bc29fc2546665c11a9e53b` foi validado por duas superfícies independentes.

O workflow ordinário `tests`, run `31889983545`, concluiu com sucesso em Python 3.11 e 3.12, incluindo Ruff e 127 testes. O smoke `ai-foundation-smoke-release`, run `31889983585`, baixou e validou a release pública do Serving 1.5.0, reabriu o bundle em modo local/read-only e executou a fundação do agente contra o DuckDB real.

No smoke real:

- bootstrap remoto: `DOWNLOADED_VALID`, validação `PASS`;
- reutilização local: `LOCAL_VALID`;
- visão geral de 2025: 1.185 UGs;
- prevalência: nove linhas T01–T09;
- consulta territorial: 27 UFs;
- SQL livre: rejeitado por definição;
- `llm_called`: `false`;
- página `07_Assistente_IA.py`: PASS em `AppTest`.

A primeira execução de CI do commit inicial falhou exclusivamente porque o teste de versão ainda esperava `APP_VERSION = 0.3.0-dev`. A implementação e o primeiro smoke real já haviam passado. O contrato de versão foi atualizado para `0.4.0-dev`, e as execuções posteriores passaram integralmente. A ocorrência permanece documentada para preservar a trilha de validação.

Após o gate funcional, o workflow remoto volta a ser somente manual (`workflow_dispatch`). O CI ordinário permanece automático.
