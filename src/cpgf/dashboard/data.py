from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from cpgf.serving.distribution import (
    ServingBootstrapResult,
    ServingDistributionConfig,
    ServingUnavailableError,
    bootstrap_serving,
)
from cpgf.serving.repository import ServingRepository


@dataclass(frozen=True)
class DashboardDataContext:
    repository: ServingRepository
    bootstrap: ServingBootstrapResult


def load_dashboard_data(
    *,
    bundle_dir: Path | None = None,
    offline: bool | None = None,
    force_download: bool = False,
) -> DashboardDataContext:
    """Inicializa a camada de leitura sem executar preparação, trilhas ou governança."""
    config = ServingDistributionConfig.from_env()
    if bundle_dir is not None or offline is not None:
        config = ServingDistributionConfig(
            bundle_dir=Path(bundle_dir) if bundle_dir is not None else config.bundle_dir,
            cache_dir=config.cache_dir,
            source_url=config.source_url,
            checksum_url=config.checksum_url,
            offline=config.offline if offline is None else bool(offline),
        )

    bootstrap = bootstrap_serving(config, force_download=force_download)
    repository = ServingRepository(bootstrap.catalog_path)
    return DashboardDataContext(repository=repository, bootstrap=bootstrap)


def serving_health(
    *,
    bundle_dir: Path | None = None,
    offline: bool | None = None,
) -> dict[str, object]:
    """Retorna estado simples para a interface sem propagar falha de distribuição."""
    try:
        context = load_dashboard_data(bundle_dir=bundle_dir, offline=offline)
    except ServingUnavailableError as exc:
        return {
            "status": "UNAVAILABLE",
            "message": str(exc),
            "tables": 0,
            "source": None,
        }

    views = context.repository.list_views()
    return {
        "status": "READY",
        "message": "Serving 1.4.0 íntegro e disponível para consulta read-only.",
        "tables": len(views),
        "source": context.bootstrap.status,
        "catalog": str(context.bootstrap.catalog_path),
    }
