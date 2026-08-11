"""Parallel Life Deep Reading / Production v1.0.1 (patch over frozen v1.0)."""

from app.parallel_life_deep_reading.production_models import (
    PRODUCTION_MODELS,
    PRODUCTION_MODELS_VERSION,
)
from app.parallel_life_deep_reading.prompts import PROMPT_VERSIONS
from app.parallel_life_deep_reading.service import DeepReadingService, get_deep_reading_service

SCHEMA_VERSION = "parallel-life-runtime-v1.0.6"
FIXTURE_VERSION = "deep-reading-fixtures-v1.0.2"
PRODUCT_CANDIDATE = "Parallel Life Deep Reading Production v1.0.2"
PRODUCTION_STATUS = "PRODUCTION V1.0.2 / CALL1-v1.0.3 + RUNTIME-v1.0.6"

__all__ = [
    "DeepReadingService",
    "get_deep_reading_service",
    "PROMPT_VERSIONS",
    "SCHEMA_VERSION",
    "FIXTURE_VERSION",
    "PRODUCT_CANDIDATE",
    "PRODUCTION_STATUS",
    "PRODUCTION_MODELS",
    "PRODUCTION_MODELS_VERSION",
]
