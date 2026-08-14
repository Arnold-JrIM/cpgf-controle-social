import pandas as pd

from cpgf.ingestion.validators import CPGF_REFERENCE_COLUMNS
from cpgf.preprocessing.build_staging import build_staging_frame


def _row(**overrides):
    row = {column: "" for column in CPGF_REFERENCE_COLUMNS}
    row.update(
        {
            "CÓDIGO UNIDADE GESTORA": "133",
            "ANO EXTRATO": "2025",
            "MÊS EXTRATO": "01",
            "CPF PORTADOR": "***123***",
            "NOME PORTADOR": "João da Silva",
            "CNPJ OU CPF FAVORECIDO": "12345678000199",
            "NOME FAVORECIDO": "Fornecedor Teste",
            "TRANSAÇÃO": "COMPRA A/V - R$ - APRES",
            "DATA TRANSAÇÃO": "05/01/2025",
            "VALOR TRANSAÇÃO": "1.234,56",
        }
    )
    row.update(overrides)
    return row


def test_staging_builds_shared_contract_without_mutating_source():
    source = pd.DataFrame(
        [
            _row(),
            _row(**{"NOME PORTADOR": "Pessoa B"}),
            _row(
                **{
                    "NOME PORTADOR": "Pessoa C",
                    "CNPJ OU CPF FAVORECIDO": "-1",
                    "NOME FAVORECIDO": "Informações protegidas por sigilo",
                    "DATA TRANSAÇÃO": "",
                    "VALOR TRANSAÇÃO": "10,00",
                }
            ),
        ]
    )
    original_columns = list(source.columns)

    staged = build_staging_frame(source)

    assert list(source.columns) == original_columns
    assert staged.loc[0, "UG_ID"] == "000133"
    assert staged.loc[0, "PORTADOR_ID_BASELINE"] == staged.loc[1, "PORTADOR_ID_BASELINE"]
    assert staged.loc[0, "PORTADOR_ID"] != staged.loc[1, "PORTADOR_ID"]
    assert staged.loc[0, "VALOR_CENTAVOS"] == 123456
    assert staged.loc[0, "ANO_TRANSACAO"] == 2025
    assert staged.loc[0, "COMPETENCIA_EXTRATO_REF"] == "202501"
    assert staged.loc[0, "EH_COMPRA_NACIONAL"]
    assert staged.loc[0, "EH_OPERACAO_POSITIVA_NAO_AJUSTE"]
    assert pd.isna(staged.loc[2, "DATA_DT"])
    assert not staged.loc[2, "FAVORECIDO_IDENTIFICADO"]
    assert staged.loc[2, "EH_SIGILOSO"]
