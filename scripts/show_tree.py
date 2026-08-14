from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    for path in sorted(ROOT.rglob("*")):
        if path.is_file() and ".git" not in path.parts:
            print(path.relative_to(ROOT))


if __name__ == "__main__":
    main()
