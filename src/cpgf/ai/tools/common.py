from __future__ import annotations

from cpgf.ai.contracts import ToolProvenance
from cpgf.version import GEO_VERSION, MOTOR_VERSION, RULES_VERSION, SERVING_VERSION


def serving_provenance() -> ToolProvenance:
    return ToolProvenance(
        serving_version=SERVING_VERSION,
        rules_version=RULES_VERSION,
        motor_version=MOTOR_VERSION,
        geo_version=GEO_VERSION,
        read_only=True,
        source="serving_views",
    )
