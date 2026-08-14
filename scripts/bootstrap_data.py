from __future__ import annotations
import argparse

def main() -> None:
    parser=argparse.ArgumentParser(description="Bootstrap dos dados CPGF.")
    parser.add_argument("--source", choices=("kaggle","official"), required=True)
    parser.add_argument("--dry-run", action="store_true")
    args=parser.parse_args()
    print(f"Fonte selecionada: {args.source}")
    if args.source=="kaggle":
        print("Contrato: snapshot arnoldjrim/dados-abertos-cpgf-2013-a-2026")
    else:
        print("Contrato: Portal da Transparência + Tesouro Transparente/CKAN")
    if not args.dry_run:
        raise SystemExit("Bootstrap funcional será implementado na próxima etapa. Use --dry-run no esqueleto.")

if __name__=="__main__": main()
