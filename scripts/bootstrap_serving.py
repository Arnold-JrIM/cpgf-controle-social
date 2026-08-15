from __future__ import annotations

import argparse
from pathlib import Path

from cpgf.serving.distribution import (
    ServingDistributionConfig,
    bootstrap_serving,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Baixa, verifica e disponibiliza o bundle materializado do Serving 1.4.0."
    )
    parser.add_argument(
        "--bundle-dir",
        type=Path,
        help="Diretório local do bundle. O padrão vem de CPGF_SERVING_BUNDLE_DIR.",
    )
    parser.add_argument(
        "--force-download",
        action="store_true",
        help="Força novo download mesmo quando o bundle local é válido.",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Não acessa rede; exige bundle local já válido.",
    )
    args = parser.parse_args()

    config = ServingDistributionConfig.from_env()
    if args.bundle_dir is not None or args.offline:
        config = ServingDistributionConfig(
            bundle_dir=args.bundle_dir or config.bundle_dir,
            cache_dir=config.cache_dir,
            source_url=config.source_url,
            checksum_url=config.checksum_url,
            offline=args.offline or config.offline,
        )

    result = bootstrap_serving(config, force_download=args.force_download)
    print(f"Status: {result.status}")
    print(f"Bundle: {result.bundle_dir}")
    print(f"Catálogo: {result.catalog_path}")
    print(f"Validação: {result.validation['status']}")


if __name__ == "__main__":
    main()
