"""Production model split version pin."""

from app.parallel_life_deep_reading.production_models import (
    CALL_1_MODEL,
    CALL_2_MODEL,
    CALL_3_MODEL,
    PRODUCTION_MODELS,
    PRODUCTION_MODELS_VERSION,
)


def test_production_models_version():
    assert PRODUCTION_MODELS_VERSION == "parallel-life-production-models-v1.0"


def test_production_call23_are_terra():
    assert CALL_2_MODEL == "gpt-5.6-terra"
    assert CALL_3_MODEL == "gpt-5.6-terra"
    assert PRODUCTION_MODELS["call_2"] == "gpt-5.6-terra"
    assert PRODUCTION_MODELS["call_3"] == "gpt-5.6-terra"


def test_call1_remains_stable_default():
    # Call 1 keeps existing stable default unless OPENAI_MODEL overrides.
    assert CALL_1_MODEL
    assert PRODUCTION_MODELS["call_1"] == CALL_1_MODEL
