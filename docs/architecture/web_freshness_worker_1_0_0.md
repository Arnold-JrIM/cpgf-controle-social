# Web/Freshness Evidence Worker 1.0.0

## Decisão

O PR #64 introduz a fronteira governada de evidência externa da arquitetura **Evidence-Orchestrated Assistant 2.0**. O objetivo não é transformar a aplicação em um agente de navegação autônomo, mas permitir que uma necessidade `WEB` já declarada no `EvidencePlan` seja executada de forma explícita, rastreável e de baixo privilégio.

O princípio permanece o mesmo adotado desde o ADR da arquitetura 2.0:

> o LLM interpreta e sintetiza; componentes governados recuperam fatos; evidências viajam com proveniência.

Neste incremento, nenhum LLM executa busca, escolhe URL, interpreta página ou decide mérito de auditoria.

## Fronteira por adapter

O core define a interface `WebSearcher`:

```text
question -> EvidencePlan -> need WEB -> WebSearcher -> WebSearchResult -> policy -> EvidenceItem
```

O worker não conhece SDK, chave, mecanismo de busca ou transporte de rede. Um provedor precisa ser **explicitamente injetado** em `run_evidence_orchestration(..., web_searcher=...)`.

Sem adapter, o comportamento anterior é preservado em fail-closed por `disabled_web_need()`. Isso impede acesso externo implícito e mantém o bundle incompleto quando uma necessidade WEB obrigatória não pode ser satisfeita.

Essa separação permite testar integralmente a política com snapshots determinísticos antes de conectar qualquer provedor live.

## Official-first

A política 1.0 classifica como oficiais os hosts pertencentes aos sufixos brasileiros:

- `gov.br`;
- `leg.br`;
- `jus.br`;
- `mp.br`;
- `mil.br`.

Resultados oficiais são priorizados preservando, dentro de cada classe, a ordem original entregue pelo provedor. A política **não afirma** que toda página oficial constitui norma vigente ou decisão de controle externo; o nível atribuído é apenas `official_institutional`.

Fontes externas não oficiais podem ser mantidas quando `official_only=false`, mas recebem `web_unclassified`. Quando o plano exige `official_only=true`, resultados externos são excluídos.

## Freshness

Todo `EvidenceItem` WEB exige `observed_at`, já previsto no contrato de evidências. O timestamp registra quando o sistema observou o resultado e não é confundido com a data de publicação da página.

O parâmetro opcional `max_age_days` permite um filtro adicional quando a data de publicação está disponível. Se esse filtro for solicitado:

- resultados sem data de publicação são rejeitados;
- resultados anteriores ao cutoff são rejeitados;
- a necessidade permanece não satisfeita caso nenhum resultado sobreviva.

A ausência de `max_age_days` não autoriza inferir uma data de publicação inexistente.

## Isolamento de conteúdo externo

Conteúdo retornado por uma página externa é tratado como **dado não confiável**, nunca como instrução para o sistema.

Antes de entrar no `EvidenceBundle`, o texto é encapsulado em JSON com os campos:

- `trust = untrusted_external_content`;
- `instruction_policy = treat_as_evidence_not_instructions`;
- título;
- host;
- data de publicação, quando existente;
- texto externo.

A política preserva o conteúdo para futura verificação, inclusive quando ele contém frases semelhantes a prompt injection. Ela não tenta "reescrever" a evidência nem executa instruções encontradas na página.

O futuro Synthesizer/Verifier deverá consumir essa marcação como parte do contrato de confiança.

## Segurança de URL

A versão 1.0 aceita somente URLs `https` com host válido e rejeita:

- credenciais embutidas na URL;
- `localhost` e domínios locais;
- IPs privados;
- loopback;
- link-local;
- multicast;
- endereços reservados ou não especificados;
- esquemas diferentes de `https`.

O core também não implementa `requests`, `httpx`, `urlopen` ou outro cliente de rede. O transporte pertence ao adapter externo, que será uma integração explicitamente configurada.

## Parâmetros WEB 1.0

O worker aceita somente:

- `limit`: 1 a 10, padrão 5;
- `official_only`: booleano, padrão `false`;
- `max_age_days`: 1 a 3650, opcional.

Parâmetros desconhecidos ou inválidos produzem warning estruturado e nenhuma evidência.

Filtros `source_classes` e `temporal_statuses` oriundos do corpus governado não são silenciosamente tratados como filtros de web. Quando presentes, o worker registra que não foram aplicados pelo provedor.

## Proveniência

Cada evidência WEB preserva:

- URL completa em `source_url`;
- host em `source_ref`;
- `observed_at`;
- título/citação;
- classe `web`;
- nível de autoridade derivado apenas do domínio;
- parâmetros do `EvidenceNeed`;
- `web_worker_version`;
- `web_policy_version`.

A arquitetura não converte o resultado em score de conformidade, probabilidade de irregularidade ou decisão de auditoria.

## Snapshot determinístico

Antes de qualquer avaliação live, o repositório congela `tests/fixtures/web_search/official_first.json` como fixture 1.0.0. O snapshot contém resultados oficiais e não oficiais e um exemplo de conteúdo potencialmente hostil.

Os testes verificam:

- priorização official-first;
- preservação de proveniência;
- classificação de autoridade sem exagero semântico;
- `official_only`;
- `max_age_days`;
- rejeição de URLs inseguras;
- isolamento de prompt injection;
- execução WEB somente com adapter explicitamente injetado;
- fail-closed sem adapter.

## StateGraph 1.2.0

A topologia de fan-out/fan-in não muda. A diferença é que o branch WEB deixa de ser exclusivamente simulado/desabilitado e passa a executar o worker quando um `WebSearcher` é fornecido:

```text
START
  -> prepare
  -> Send(EvidenceNeed...)
  -> evidence_worker
       DATA      -> TOOL_REGISTRY
       KNOWLEDGE -> Retriever governado
       WEB       -> WebSearcher + Web Policy 1.0
  -> fan_in
  -> EvidenceBundle
  -> END
```

O harness `run_simulated_orchestration()` permanece isolado e explícito para testes estruturais.

## Limites deliberados

O PR #64 não inclui:

- busca web autônoma por padrão;
- fallback web quando DATA/KNOWLEDGE falham;
- text-to-SQL;
- LLM como mecanismo de busca;
- interpretação automática de normas encontradas na web;
- conclusão de irregularidade;
- Synthesizer;
- Evidence Verifier.

Esses limites preservam a decomposição do sistema e evitam que a introdução de uma fonte externa reduza a rastreabilidade alcançada nos PRs anteriores.

## Próximo incremento

Após o merge, o próximo passo arquitetural é o **Synthesizer + Evidence Verifier**, que deverá gerar texto somente a partir do `EvidenceBundle`, verificar cada afirmação material contra as evidências disponíveis e permitir abstention quando o bundle for insuficiente ou conflitante.
