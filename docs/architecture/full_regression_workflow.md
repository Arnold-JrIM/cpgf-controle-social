# Workflow de regressão integral canônica

O workflow `.github/workflows/full_regression_canonical.yml` permite repetir manualmente, pelo GitHub Actions, a regressão integral T01–T09 contra o snapshot canônico publicado no Kaggle.

A execução é deliberadamente manual (`workflow_dispatch`) porque baixa aproximadamente 500 MB e reprocessa as nove trilhas. O workflow valida o SHA-256 do arquivo no próprio gate, executa os modos baseline e produção e publica o relatório JSON como artifact.

Esse workflow complementa o CI ordinário com fixtures pequenas. Ele não deve ser acionado a cada commit e não substitui os testes unitários e de integração.
