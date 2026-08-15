from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

APP_FILES = (
    Path("streamlit_app.py"),
    Path("pages/01_Visao_Geral.py"),
    Path("pages/02_Distribuicao_Territorial.py"),
    Path("pages/03_Trilhas_Analiticas.py"),
    Path("pages/04_Diagnostico_do_Motor.py"),
    Path("pages/05_Sinais_e_Validacao.py"),
    Path("pages/06_Metodologia.py"),
    Path("pages/07_Assistente_IA.py"),
)


def main() -> None:
    failures: list[str] = []
    for path in APP_FILES:
        print(f"[dashboard-smoke] executando {path}")
        app = AppTest.from_file(str(path), default_timeout=45).run(timeout=45)
        if len(app.exception):
            details = "; ".join(str(item.value) for item in app.exception)
            failures.append(f"{path}: {details}")
        else:
            print(f"[dashboard-smoke] PASS {path}")

    if failures:
        raise RuntimeError("Falhas no smoke test do dashboard:\n" + "\n".join(failures))
    print(f"Dashboard smoke PASS: {len(APP_FILES)} scripts Streamlit executados sem exceção.")


if __name__ == "__main__":
    main()
