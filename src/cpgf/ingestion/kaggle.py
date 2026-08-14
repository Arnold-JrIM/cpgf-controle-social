from __future__ import annotations

from pathlib import Path

DEFAULT_DATASET_SLUG = "arnoldjrim/dados-abertos-cpgf-2013-a-2026"


def download_snapshot(
    destination: Path,
    *,
    dataset_slug: str = DEFAULT_DATASET_SLUG,
    path: str | None = None,
    force_download: bool = False,
) -> Path:
    import kagglehub

    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    resolved = kagglehub.dataset_download(
        dataset_slug,
        path=path,
        force_download=force_download,
        output_dir=str(destination),
    )
    return Path(resolved)
