from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

REPO_ROOT = Path(__file__).resolve().parents[1]
APP_FILES = (
    REPO_ROOT / "streamlit_app.py",
    REPO_ROOT / "pages/01_Visao_Geral.py",
    REPO_ROOT / "pages/02_Distribuicao_Territorial.py",
    REPO_ROOT / "pages/03_Trilhas_Analiticas.py",
    REPO_ROOT / "pages/04_Diagnostico_do_Motor.py",
    REPO_ROOT / "pages/05_Sinais_e_Validacao.py",
    REPO_ROOT / "pages/06_Metodologia.py",
    REPO_ROOT / "pages/07_Assistente_IA.py",
)


def main() -> None:
    failures: list[str] = []
    for path in APP_FILES:
        relative = path.relative_to(REPO_ROOT)
        print(f"[dashboard-smoke] executando {relative}")
        app = AppTest.from_file(str(path), default_timeout=45).run(timeout=45)
        if len(app.exception):
            details = "; ".join(str(item.value) for item in app.exception)
            failures.append(f"{relative}: {details}")
        else:
            print(f"[dashboard-smoke] PASS {relative}")

    if failures:
        raise RuntimeError("Falhas no smoke test do dashboard:\n" + "\n".join(failures))
    print(f"Dashboard smoke PASS: {len(APP_FILES)} scripts Streamlit executados sem exceção.")


if __name__ == "__main__":
    main()
