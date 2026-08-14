from cpgf.version import GEO_VERSION, MOTOR_VERSION, RULES_VERSION


def main() -> None:
    print(f"Regras={RULES_VERSION} Motor={MOTOR_VERSION} Geo={GEO_VERSION}")
    print("Validação completa de release ainda será implementada.")


if __name__ == "__main__":
    main()
