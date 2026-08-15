# Router do Assistente 1.0.0

## Finalidade

O Router 1.0.0 transforma a pergunta do usuário em uma decisão determinística de intenção e em um plano explícito de camadas de evidência. Ele não responde à pergunta, não executa ferramentas e não chama modelo de linguagem.

A separação entre **rota** e **evidência** evita duas simplificações inadequadas: tratar toda pergunta difícil como `composite` e assumir que uma única rota corresponde necessariamente a uma única fonte. Uma explicação de uma trilha T01–T09, por exemplo, permanece uma intenção metodológica, embora possa exigir apoio documental do Knowledge.

## Rotas autorizadas

- `overview`: consultas agregadas de visão geral no Serving;
- `trails`: consultas quantitativas de trilhas e sinais no Serving;
- `territorial`: consultas territoriais materializadas no Serving;
- `suppliers`: consultas agregadas por fornecedor;
- `ugs`: consultas agregadas por Unidade Gestora;
- `methodology`: explicações do método, das trilhas T01–T09 e de seus limites inferenciais;
- `knowledge`: conceitos, normas e literatura do corpus governado;
- `composite`: perguntas que exigem combinar camadas distintas de evidência;
- `unsupported`: intenção não reconhecida com segurança dentro do domínio autorizado.

## Camadas de evidência

O `RouteDecision` registra separadamente `evidence_layers`, atualmente limitadas a:

- `serving`: dados e sinais materializados, somente leitura;
- `knowledge`: corpus documental governado;
- `methodology`: contratos, definições e limites interpretativos do método do projeto.

A presença de uma camada não implica sua execução automática. Ela é um plano para a futura orquestração do agente.

Exemplos:

- “O que é suprimento de fundos?” → `knowledge` + `knowledge`;
- “Quantas ocorrências da T01 houve em 2024?” → `trails` + `serving`;
- “Como funciona a T08?” → `methodology` + `methodology, knowledge`;
- “A divergência de Benford prova fraude?” → `composite` + `methodology, knowledge`;
- pergunta de ranking seguida de acusação categórica → `composite` + `serving, methodology`.

## Segurança inferencial

O roteamento composto não cria autorização para afirmar fraude, irregularidade ou desconformidade. Ele apenas reconhece que uma pergunta mistura tipos de evidência e deve ser tratada com mais de uma camada.

Em especial:

- T01–T09 são sinais ou condições para verificação, conforme o contrato de cada trilha;
- T08 e T09 permanecem trilhas contextuais;
- divergência de Benford não constitui prova de fraude;
- proximidade a limites financeiros não demonstra, por si só, fracionamento ou intenção de evasão;
- ranking de fornecedores ou UGs não autoriza imputação de conduta.

## Benchmark congelado

O Router 1.0.0 foi desenvolvido contra o Benchmark 1.0.0 introduzido anteriormente e **o arquivo de 50 perguntas não foi alterado neste incremento**.

Baseline anterior ao novo roteador:

- 22/50 rotas exatas = 44%;
- apenas 29/50 alvos eram representáveis pela taxonomia então existente.

Validação funcional do Router 1.0.0 no mesmo benchmark:

- 50/50 rotas exatas = 100%;
- 50/50 alvos representáveis;
- distribuição esperada e observada idêntica entre `knowledge`, `overview`, `ugs`, `suppliers`, `territorial`, `trails`, `methodology` e `composite`.

Esse resultado é **in-sample e orientado pelo benchmark**. Ele demonstra que a nova taxonomia representa os casos de referência e que o algoritmo implementa o contrato congelado, mas não estima acurácia de produção nem capacidade de generalização para perguntas arbitrárias. Por isso, testes unitários incluem paráfrases adicionais fora dos 50 casos e uma etapa posterior deve acrescentar conjunto externo/holdout sem reutilização no ajuste.

O SHA-256 do benchmark usado na validação é `be1a0245f597f9b2456aacdc6485187d6fdb9c52230f0072519d6387148b5820`.

## Evidência funcional

Smoke validado no commit `d6f67255607ef803216cb58ce901ea79a3168c42`:

- workflow run `31906776202`;
- conclusão `success`;
- Router `1.0.0`;
- 50/50 rotas exatas;
- artifact ID `9252564762`;
- digest SHA-256 do artifact ZIP `ab1a79e9d12c2324b2a53dac546d693af0a21f8f3128cc5c587bb2a274a35972`.

O CI comum no mesmo commit também passou em Python 3.11 e 3.12, com Ruff e pytest, no run `31906776216`.

## Limites da versão

O Router 1.0.0 não:

- seleciona ou executa `ToolRequest` automaticamente;
- consulta o Serving;
- recupera chunks do Knowledge;
- faz busca web;
- chama embeddings por conta própria;
- chama LLM;
- modifica estado de validação analítica;
- substitui avaliação humana de casos ambíguos.

A próxima evolução deverá medir generalização fora do conjunto de desenvolvimento e, separadamente, avaliar a qualidade da recuperação documental lexical, semântica e híbrida antes da geração de respostas por LLM.
