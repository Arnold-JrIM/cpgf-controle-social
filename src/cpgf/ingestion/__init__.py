"""Aquisição e validação das fontes públicas do projeto CPGF."""

from .cpgf import CompetenceNotAvailable, PortalBlocked, PortalReturnedHTML
from .kaggle import download_snapshot
from .siafi import discover_latest_csv_resource

__all__ = [
    "CompetenceNotAvailable",
    "PortalBlocked",
    "PortalReturnedHTML",
    "discover_latest_csv_resource",
    "download_snapshot",
]
