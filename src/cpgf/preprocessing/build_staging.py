from __future__ import annotations

from pathlib import Path

import pandas as pd

from cpgf.ingestion.validators import read_csv_header

from .amounts import cents_to_reais_series, parse_amount_series_to_cents
from .dates import (
    build_extract_competence,
    parse_extract_month,
    parse_extract_year,
    parse_transaction_dates,
    transaction_year,
)
from .identifiers import (
    build_favorecido_id_series,
    build_portador_id_baseline_series,
    build_portador_id_series,
    normalize_name_series,
    normalize_ug_series,
)
from .schema import validate_raw_frame
from .transaction_types import sigilo_flags, transaction_flags


def build_staging_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Constrói a camada de staging compartilhada pela aplicação.

    As colunas originais são preservadas. As derivadas são adicionadas sem
    inferir data de transação a partir da referência de extrato.
    """
    validate_raw_frame(frame)
    staged = frame.copy()

    staged["UG_ID"] = normalize_ug_series(staged["CÓDIGO UNIDADE GESTORA"])
    staged["NOME_PORTADOR_NORMALIZADO"] = normalize_name_series(staged["NOME PORTADOR"])
    staged["PORTADOR_ID_BASELINE"] = build_portador_id_baseline_series(
        staged["CPF PORTADOR"], staged["NOME PORTADOR"]
    )
    staged["PORTADOR_ID"] = build_portador_id_series(
        staged["CÓDIGO UNIDADE GESTORA"], staged["CPF PORTADOR"], staged["NOME PORTADOR"]
    )
    staged["FAVORECIDO_ID"] = build_favorecido_id_series(
        staged["CNPJ OU CPF FAVORECIDO"], staged["NOME FAVORECIDO"]
    )
    staged["FAVORECIDO_IDENTIFICADO"] = staged["FAVORECIDO_ID"].notna()

    staged["DATA_DT"] = parse_transaction_dates(staged["DATA TRANSAÇÃO"])
    staged["ANO_TRANSACAO"] = transaction_year(staged["DATA_DT"])
    staged["ANO_EXTRATO_REF"] = parse_extract_year(staged["ANO EXTRATO"])
    staged["MES_EXTRATO_REF"] = parse_extract_month(staged["MÊS EXTRATO"])
    staged["COMPETENCIA_EXTRATO_REF"] = build_extract_competence(
        staged["ANO_EXTRATO_REF"], staged["MES_EXTRATO_REF"]
    )

    staged["VALOR_CENTAVOS"] = parse_amount_series_to_cents(staged["VALOR TRANSAÇÃO"])
    staged["VALOR_NUM"] = cents_to_reais_series(staged["VALOR_CENTAVOS"])

    flags = transaction_flags(staged["TRANSAÇÃO"])
    for column in flags.columns:
        staged[column] = flags[column]

    staged["EH_SIGILOSO"] = sigilo_flags(
        staged["TRANSAÇÃO"], staged["NOME PORTADOR"], staged["NOME FAVORECIDO"]
    )
    staged["EH_OPERACAO_EFETIVA"] = staged["EH_COMPRA_EFETIVA"] | staged["EH_SAQUE_EFETIVO"]
    staged["EH_OPERACAO_POSITIVA_NAO_AJUSTE"] = (
        staged["VALOR_CENTAVOS"].gt(0).fillna(False)
        & ~staged["EH_AJUSTE_CONTESTACAO"]
        & staged["EH_OPERACAO_EFETIVA"]
    )
    return staged


def read_cpgf_csv(path: Path) -> pd.DataFrame:
    encoding, delimiter, _ = read_csv_header(path)
    return pd.read_csv(
        path,
        sep=delimiter,
        encoding=encoding,
        dtype="string",
        keep_default_na=False,
    )


def build_staging_from_csv(input_path: Path, output_path: Path | None = None) -> pd.DataFrame:
    staged = build_staging_frame(read_cpgf_csv(input_path))
    if output_path is not None:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        staged.to_parquet(output_path, index=False)
    return staged
