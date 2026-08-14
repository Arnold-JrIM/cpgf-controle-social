from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
CONFIG_DIR = REPO_ROOT / "config"
DATA_DIR = REPO_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
INTERIM_DIR = DATA_DIR / "interim"
PROCESSED_DIR = DATA_DIR / "processed"
OUTPUT_DIR = DATA_DIR / "outputs"
REFERENCE_DIR = DATA_DIR / "reference"
MANIFEST_DIR = DATA_DIR / "manifests"
FIXTURE_DIR = DATA_DIR / "fixtures"
