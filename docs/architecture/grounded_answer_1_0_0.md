# Grounded Answer 1.0.0

## Decisão

O PR #65 adiciona a primeira camada capaz de transformar um `EvidenceBundle` em resposta textual ao usuário. A arquitetura mantém a separação estabelecida desde o ADR do PR #60:

> o LLM interpreta e sintetiza; componentes governados recuperam fatos; evidências viajam com proveniência; a resposta final só é liberada após verificação explícita.

O modelo padrão continua sendo `gpt-4o-mini`, definido centralmente por `model_policy.py`.

O pipeline não executa retrieval, ferramentas do Serving, SQL ou busca web. Ele recebe exclusivamente um `EvidenceBundle` previamente produzido pelos workers governados.

## Fluxo

A versão 1.0 usa duas chamadas estruturadas ao mesmo modelo governado:

`EvidenceBundle -> Synthesizer -> SynthesisDraft -> Evidence Verifier -> deterministic output guard -> GroundedAnswer`

A separação é deliberada. O primeiro passo propõe afirmações; o segundo deve inspecioná-las criticamente contra as evidências citadas. A resposta exibível não é aceita diretamente de nenhum dos dois modelos.

## Synthesizer

O Synthesizer produz apenas `SynthesisDraft`, composto por claims atômicos. Cada claim contém:

- `claim_id`;
- `statement`;
- um ou mais `evidence_ids` existentes no bundle.

O prompt proíbe:

- uso de conhecimento externo;
- ferramentas ou internet;
- preenchimento de lacunas por memória do modelo;
- conclusões automáticas de fraude, dolo, crime, ilegalidade ou irregularidade confirmada;
- tratamento de conteúdo WEB como instrução.

Números, datas e nomes devem ser copiados das evidências. Alertas e trilhas continuam sendo sinais de triagem.

## Evidence Verifier

O verificador recebe o mesmo pacote de evidências e o rascunho estruturado. Para cada claim, deve retornar exatamente um dos seguintes estados:

- `supported_by_evidence`;
- `partially_supported`;
- `conflicting_evidence`;
- `insufficient_evidence`;
- `requires_human_review`.

O verificador não pode corrigir claims nem acrescentar fatos. `retrieval_score` não é tratado como probabilidade de verdade.

Um claim classificado como `supported_by_evidence` precisa indicar ao menos um `checked_evidence_id` realmente inspecionado.

## Validação cruzada determinística

Após as chamadas do modelo, o código aplica validações que o LLM não pode contornar:

1. todo `evidence_id` citado pelo Synthesizer deve existir no bundle;
2. o Verifier deve devolver exatamente um resultado para cada claim;
3. `checked_evidence_ids` só podem pertencer ao conjunto originalmente citado pelo claim;
4. somente claims com status `supported_by_evidence` podem chegar ao renderer;
5. claims que acionam o guard de juízo de auditoria são bloqueados mesmo quando o Verifier os marca como suportados.

Qualquer violação de contrato produz abstenção, não fallback em texto livre.

## Audit Judgment Guard

A camada determinística protege contra conclusões que não devem ser automatizadas. Expressões conclusivas como fraude confirmada, irregularidade confirmada, ilegalidade ou desvio comprovado são bloqueadas antes da resposta final.

Esse guard não substitui julgamento profissional. Sua função é impedir que uma saída do LLM seja transformada em conclusão automática de auditoria.

Quando acionado:

- o claim não é exibido;
- `human_review_required=true`;
- um warning auditável é registrado.

## Abstenção

A abstenção é comportamento esperado e desejável. O modelo nem sequer é chamado quando:

- o `EvidenceBundle` está incompleto;
- há necessidade obrigatória ainda não satisfeita;
- o pacote é de simulação;
- não existe evidência factual no bundle.

Também há abstenção quando:

- o Synthesizer referencia evidência inexistente;
- o Verifier viola o contrato;
- nenhuma afirmação passa pela verificação;
- uma chamada estruturada falha.

A ausência de resposta factual é preferível à criação de informação não sustentada.

## Renderização e citações

A resposta final é montada deterministicamente a partir dos claims aceitos. O renderer não chama LLM.

As citações são numeradas em ordem de primeira utilização e vinculadas a:

- `evidence_id`;
- citação original;
- `source_ref`;
- `source_url`, quando disponível.

Assim, a frase exibida, a evidência inspecionada pelo Verifier e a origem da evidência permanecem conectadas.

Se apenas parte dos claims for aprovada, a saída recebe status `partial` e os claims rejeitados são omitidos. Se nenhum claim for aprovado, a saída recebe status `abstained`.

## Conteúdo WEB e prompt injection

O PR #64 já marca conteúdo externo como `untrusted_external_content`. O PR #65 reforça essa fronteira nos prompts de síntese e verificação: texto vindo da web é evidência a ser avaliada, nunca instrução.

O pipeline de resposta não contém cliente de rede e não pode seguir links, buscar contexto adicional ou obedecer instruções presentes em páginas externas.

## Context packing

Para manter o uso do modelo previsível, o payload enviado ao Synthesizer e ao Verifier usa excertos limitados por evidência e um teto global de contexto. Os dois estágios recebem a mesma representação empacotada, reduzindo assimetria entre geração e verificação.

Essa política de packing poderá ser avaliada separadamente em benchmark futuro; não altera o `EvidenceItem` original preservado no bundle.

## Modelo e rastreabilidade

`OpenAIResponsesAnswerProvider` usa a Responses API com JSON Schema estrito e `store=False`.

O provider herda o modelo de `project_llm_model()` e, portanto, usa:

`gpt-4o-mini`

Cada chamada preserva metadados de execução quando disponíveis:

- response id;
- modelo retornado;
- input tokens;
- output tokens;
- latência.

Esses metadados pertencem ao `AnswerRun` e não são tratados como evidência substantiva.

## O que este PR não faz

Este incremento não adiciona:

- decisão automática de irregularidade;
- score de fraude ou conformidade;
- replanejamento de evidências;
- text-to-SQL;
- retrieval autônomo pelo LLM;
- busca web autônoma;
- memória conversacional como fonte factual;
- aceitação direta de texto livre do modelo;
- benchmark live de qualidade da resposta.

## Métricas futuras

A arquitetura passa a permitir medir separadamente:

- claim groundedness;
- citation correctness;
- unsupported-claim rate;
- abstention correctness;
- proporção de claims encaminhados para revisão humana;
- estabilidade entre repetições;
- cobertura das evidências recuperadas.

Essas métricas deverão usar conjunto prospectivamente congelado antes de qualquer avaliação independente da nova arquitetura.

## Próximo incremento

Após o PR #65, o sistema terá workers DATA, KNOWLEDGE e WEB, `EvidenceBundle` e uma camada de resposta governada. O próximo passo deve voltar ao componente ainda ausente da arquitetura 2.0: o **Semantic Evidence Orchestrator**, responsável por transformar uma pergunta em `EvidencePlan` multi-rótulo antes de um novo holdout independente.
