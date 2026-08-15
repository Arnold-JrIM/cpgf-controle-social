# Distribuição e consumo do Serving 1.4.0

## Finalidade

O PR #20 criou a camada materializada de serving em Parquet e DuckDB, mas os artefatos binários permanecem fora do Git. Esta etapa define como a aplicação pública obtém esse bundle de forma persistente, verificável e sem recomputar a preparação, as trilhas ou a governança estatística.

## Fonte de distribuição

O bundle oficial é publicado como GitHub Release versionada:

- tag: `serving-v1.4.0`;
- arquivo: `cpgf-serving-1.4.0.tar.gz`;
- checksum: `cpgf-serving-1.4.0.tar.gz.sha256`.

A publicação canônica inicial foi concluída com `PASS` no workflow `serving-publish-release`, run `31858520627`. A tag aponta para o merge do PR #20 na `main`, commit `b8066d72b87f5914cb8eb8cabc2cde6f0de990d8`. O arquivo publicado possui 12.221.316 bytes e SHA-256 `70f046a833ca76151a5d8298da395ffcae9a279c4dc25bd312e099de5014c3de`.

A proveniência completa foi congelada em `data/manifests/serving_distribution_1_4_0.json`.

A release é produzida por workflow manual a partir da `main`. O workflow baixa novamente o snapshot canônico, executa `scripts/build_serving.py`, valida o bundle, empacota o diretório íntegro e publica o arquivo acompanhado de seu SHA-256.

A release não substitui o contrato congelado no repositório. Ela é apenas o meio persistente de transportar os resultados já materializados e validados.

## Bootstrap da aplicação

`cpgf.serving.distribution.bootstrap_serving()` segue a sequência:

1. procura um bundle local;
2. se ele existir, executa `validate_serving_bundle()`;
3. se estiver íntegro, usa o catálogo local sem acesso à rede;
4. se estiver ausente ou inválido, baixa o checksum publicado;
5. baixa o arquivo compactado;
6. verifica o SHA-256 antes da extração;
7. rejeita links e caminhos de archive que possam escapar do diretório de destino;
8. extrai para um diretório temporário;
9. executa novamente a validação integral do manifesto, Parquets e DuckDB;
10. somente após `PASS` substitui atomicamente o bundle local.

Assim, um download parcial, adulterado ou estruturalmente inválido não se torna fonte de consulta da aplicação.

## Consumo read-only

Após o bootstrap, `cpgf.dashboard.data.load_dashboard_data()` cria um `ServingRepository` sobre `cpgf_serving.duckdb`.

O catálogo DuckDB já é aberto em `read_only=True`. O repositório aceita apenas nomes lógicos registrados em `serving_catalog`, não expõe SQL arbitrário e impõe limites de paginação.

A inicialização do dashboard não importa nem chama `build_serving_bundle()`, `run_all_trails()` ou funções de governança. O processamento pesado permanece fora do ciclo de requisição do Streamlit.

## Comportamento resiliente

A página inicial usa `serving_health()`. Se o bundle estiver indisponível, a aplicação não encerra com erro. Ela inicia em estado degradado e informa que as páginas analíticas ainda não possuem dados.

Esse comportamento é importante para implantação em Streamlit Community Cloud, em que o filesystem pode ser recriado. Quando isso ocorrer, o bundle será obtido novamente da release e validado antes do uso.

## Configuração

As seguintes variáveis são opcionais:

- `CPGF_SERVING_BUNDLE_DIR`: destino local do bundle;
- `CPGF_SERVING_CACHE_DIR`: diretório do arquivo baixado;
- `CPGF_SERVING_BUNDLE_URL`: substitui a URL padrão da release;
- `CPGF_SERVING_CHECKSUM_URL`: substitui a URL do checksum;
- `CPGF_SERVING_OFFLINE=1`: proíbe acesso à rede e exige bundle local válido.

Sem overrides, a aplicação usa a release oficial `serving-v1.4.0`.

## Execução local

```bash
python scripts/bootstrap_serving.py
```

Para validar um bundle já presente sem rede:

```bash
CPGF_SERVING_OFFLINE=1 python scripts/bootstrap_serving.py
```

## Publicação da release

O workflow `serving-publish-release` é deliberadamente manual depois da validação inicial. Ele deve ser executado quando uma nova versão do serving for congelada ou quando for necessário republicar exatamente a mesma versão materializada.

A publicação usa a `main` como alvo da tag e substitui os assets de mesmo nome de forma explícita, mantendo a URL de consumo estável para a aplicação.

A validação inicial incluiu dois smoke tests no próprio runner: download remoto da release recém-publicada com verificação de checksum e integridade, seguido de reutilização do bundle em modo offline. Ambos terminaram com `PASS`.

## Salvaguardas

Esta etapa não altera T01–T09, não modifica as matrizes ou diagnósticos do Motor 1.3.2, não cria score de risco e não implementa novas visualizações. Sua única função é transportar e disponibilizar de forma íntegra os resultados já validados.
