from __future__ import annotations

import pandas as pd

from cpgf.trails.t05_vendor_recurrence import enrich_t05_episodes


def test_t05_signal_id_matches_frozen_reference_example():
    episode = pd.DataFrame(
        [
            {
                "JANELA_DIAS": 30,
                "UG_ID": "110001",
                "FAVORECIDO_ID": "06239994000180",
                "ANO_TRANSACAO": 2024,
                "DT_INICIO": pd.Timestamp("2024-10-15"),
                "DT_FIM": pd.Timestamp("2024-11-14"),
                "N_TRANSACOES": 14,
                "N_PORTADORES": 2,
                "MEDIA_CENTAVOS": 21028.357143,
                "DP_CENTAVOS": 3569.077684,
                "CV": 0.169726891163037,
                "MEDIANA_CENTAVOS": 21376.5,
                "Q1_CENTAVOS": 19403.0,
                "Q3_CENTAVOS": 22495.75,
                "IQR_CENTAVOS": 3092.75,
                "SHARE_DENTRO_FAIXA_MEDIANA": 0.7857142857142857,
                "MIN_CENTAVOS": 14561,
                "MAX_CENTAVOS": 29922,
                "VALOR_TOTAL_CENTAVOS": 294397,
            }
        ]
    )

    enriched = enrich_t05_episodes(episode)

    assert enriched.loc[0, "ID_SINAL"] == "T05_fcda5cd9559cd9086ac157f5"
