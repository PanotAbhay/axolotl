"""Settings tests - owner: Dev 2.

The case that matters: `.env.example` ships blank placeholders and the README tells
you to copy it verbatim. If a blank value crashes `Settings()`, the app refuses to
boot for every teammate on their first run, with a pydantic error that looks nothing
like "you need to fill in .env".
"""

import pytest
from pydantic import ValidationError

from app.config import Settings


def test_a_blank_optional_int_falls_back_to_its_default():
    """EMBEDDING_DIMENSIONS= straight out of .env.example."""
    settings = Settings(EMBEDDING_DIMENSIONS="", _env_file=None)
    assert settings.embedding_dimensions is None


def test_a_blank_string_falls_back_to_its_default():
    settings = Settings(GEMINI_MODEL="", _env_file=None)
    assert settings.gemini_model == "gemini-4-argon"


def test_a_blank_numeric_falls_back_rather_than_exploding():
    settings = Settings(MAX_PATCH_ATTEMPTS="", _env_file=None)
    assert settings.max_patch_attempts == 3


def test_whitespace_counts_as_blank():
    settings = Settings(EMBEDDING_DIMENSIONS="   ", _env_file=None)
    assert settings.embedding_dimensions is None


def test_the_whole_env_example_shape_loads():
    """Every blank in .env.example at once - the real first-run scenario."""
    settings = Settings(
        GEMINI_API_KEY="",
        GEMINI_MODEL="gemini-4-argon",
        GEMINI_THINKING_LEVEL="medium",
        GEMINI_EMBEDDING_MODEL="",
        EMBEDDING_DIMENSIONS="",
        MONGODB_URI="",
        MONGODB_DATABASE="axolotl",
        RUNNER_MODE="trusted_docker",
        ALLOW_ARBITRARY_CODE_EXECUTION="false",
        _env_file=None,
    )
    assert settings.embedding_dimensions is None
    assert settings.mongodb_uri == ""
    assert settings.runner_mode == "trusted_docker"
    assert settings.allow_arbitrary_code_execution is False


def test_real_values_still_parse():
    settings = Settings(EMBEDDING_DIMENSIONS="768", MAX_PATCH_ATTEMPTS="5",
                        _env_file=None)
    assert settings.embedding_dimensions == 768
    assert settings.max_patch_attempts == 5


def test_a_genuinely_invalid_value_is_still_rejected():
    """Blank means "default". "banana" still means "you typed it wrong"."""
    with pytest.raises(ValidationError):
        Settings(EMBEDDING_DIMENSIONS="banana", _env_file=None)


def test_an_invalid_runner_mode_is_rejected():
    with pytest.raises(ValidationError):
        Settings(RUNNER_MODE="yolo", _env_file=None)


def test_secret_values_only_reports_things_worth_redacting():
    settings = Settings(
        MONGODB_URI="mongodb+srv://EXAMPLE-LONG-ENOUGH-TO-REDACT/db",
        GEMINI_API_KEY="",
        _env_file=None,
    )
    secrets = settings.secret_values()
    assert any("EXAMPLE-LONG-ENOUGH" in s for s in secrets)
    assert "" not in secrets
