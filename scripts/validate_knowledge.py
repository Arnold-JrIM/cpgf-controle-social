from __future__ import annotations

import argparse
from pathlib import Path

from cpgf.knowledge import validate_knowledge_bundle


def main() -> None:
    parser = argparse.ArgumentParser(description="Valida artefatos do Knowledge 1.0.0.")
    parser.add_argument("bundle_dir", type=Path)
    args = parser.parse_args()
    result = validate_knowledge_bundle(args.bundle_dir)
    print(result)
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
