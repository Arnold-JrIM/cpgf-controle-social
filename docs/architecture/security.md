# Segurança — baseline

1. Nunca versionar chaves.
2. Nunca persistir chave BYOK.
3. Não usar variável global para chave fornecida por usuário.
4. Não cachear cliente LLM com chave BYOK.
5. SQL gerado por LLM somente `SELECT`.
6. Consultas apenas contra views autorizadas.
7. Limitar linhas, tempo e recursos.
8. Não persistir conversas públicas por padrão.
9. Modo demo exige quota persistente antes da publicação.
10. Falhas em download oficial não alteram manifests/snapshots válidos.
