"""Unit tests for configuration management (Task 2)."""

import os
from unittest.mock import patch

import pytest

from src.utils.config import Config


class TestConfigInitialization:
    """Test Config class initialization and environment variable loading."""

    def test_config_loads_default_values(self, monkeypatch):
        """Test that Config uses default values when env vars not set."""
        # Clear environment variables for this test
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("SPOONACULAR_API_KEY", raising=False)
        monkeypatch.delenv("PORT", raising=False)
        monkeypatch.delenv("MAX_HISTORY", raising=False)
        monkeypatch.delenv("MAX_IMAGE_SIZE_MB", raising=False)
        monkeypatch.delenv("MIN_INGREDIENT_CONFIDENCE", raising=False)
        monkeypatch.delenv("GEMINI_MODEL", raising=False)
        monkeypatch.delenv("DATABASE_URL", raising=False)

        config = Config()

        assert config.PORT == 7777
        assert config.MAX_HISTORY == 3
        assert config.MAX_RECIPES == 10
        assert config.MAX_IMAGE_SIZE_MB == 5
        assert config.MIN_INGREDIENT_CONFIDENCE == 0.7
        assert config.GEMINI_MODEL == "gemini-3-flash-preview"
        assert config.IMAGE_DETECTION_MODEL == "gemini-3-flash-preview"
        assert config.DATABASE_URL is None

    def test_config_loads_from_environment(self, monkeypatch):
        """Test that Config loads values from environment variables."""
        monkeypatch.setenv("PORT", "8888")
        monkeypatch.setenv("MAX_HISTORY", "5")
        monkeypatch.setenv("MAX_IMAGE_SIZE_MB", "10")
        monkeypatch.setenv("MIN_INGREDIENT_CONFIDENCE", "0.85")
        monkeypatch.setenv("GEMINI_MODEL", "custom-model")
        monkeypatch.setenv("IMAGE_DETECTION_MODEL", "vision-model")
        monkeypatch.setenv("GEMINI_API_KEY", "test_gemini_key")
        monkeypatch.setenv("SPOONACULAR_API_KEY", "test_spoonacular_key")

        config = Config()

        assert config.PORT == 8888
        assert config.MAX_HISTORY == 5
        assert config.MAX_IMAGE_SIZE_MB == 10
        assert config.MIN_INGREDIENT_CONFIDENCE == 0.85
        assert config.GEMINI_MODEL == "custom-model"
        assert config.IMAGE_DETECTION_MODEL == "vision-model"
        assert config.GEMINI_API_KEY == "test_gemini_key"
        assert config.SPOONACULAR_API_KEY == "test_spoonacular_key"

    def test_config_converts_numeric_types(self, monkeypatch):
        """Test that Config properly converts numeric environment variables."""
        monkeypatch.setenv("PORT", "9000")
        monkeypatch.setenv("MAX_HISTORY", "10")
        monkeypatch.setenv("MAX_IMAGE_SIZE_MB", "20")
        monkeypatch.setenv("MIN_INGREDIENT_CONFIDENCE", "0.95")
        monkeypatch.setenv("GEMINI_API_KEY", "key1")
        monkeypatch.setenv("SPOONACULAR_API_KEY", "key2")

        config = Config()

        assert isinstance(config.PORT, int)
        assert isinstance(config.MAX_HISTORY, int)
        assert isinstance(config.MAX_IMAGE_SIZE_MB, int)
        assert isinstance(config.MIN_INGREDIENT_CONFIDENCE, float)


class TestConfigValidation:
    """Test Config validation logic."""

    def test_validate_raises_error_for_missing_gemini_key(self, monkeypatch):
        """Test that validate() raises ValueError if GEMINI_API_KEY missing."""
        monkeypatch.setenv("GEMINI_API_KEY", "")
        monkeypatch.setenv("SPOONACULAR_API_KEY", "key")

        config = Config()
        with pytest.raises(ValueError, match="GEMINI_API_KEY"):
            config.validate()

    def test_validate_raises_error_for_missing_spoonacular_key(self, monkeypatch):
        """Test that validate() raises ValueError if SPOONACULAR_API_KEY missing when USE_SPOONACULAR=true."""
        monkeypatch.setenv("GEMINI_API_KEY", "key")
        monkeypatch.setenv("USE_SPOONACULAR", "true")
        monkeypatch.setenv("SPOONACULAR_API_KEY", "")

        config = Config()
        with pytest.raises(ValueError, match="SPOONACULAR_API_KEY"):
            config.validate()
    
    def test_validate_allows_missing_spoonacular_key_when_disabled(self, monkeypatch):
        """Test that validate() succeeds without SPOONACULAR_API_KEY when USE_SPOONACULAR=false."""
        monkeypatch.setenv("GEMINI_API_KEY", "key")
        monkeypatch.setenv("USE_SPOONACULAR", "false")
        monkeypatch.setenv("SPOONACULAR_API_KEY", "")

        config = Config()
        config.validate()  # Should not raise

    def test_validate_succeeds_with_both_keys(self, monkeypatch):
        """Test that validate() succeeds when both required keys are present."""
        monkeypatch.setenv("GEMINI_API_KEY", "gemini_key")
        monkeypatch.setenv("SPOONACULAR_API_KEY", "spoonacular_key")

        config = Config()
        config.validate()  # Should not raise

    def test_validate_ignores_other_missing_variables(self, monkeypatch):
        """Test that validate() only checks required keys, not optional ones."""
        monkeypatch.setenv("GEMINI_API_KEY", "key")
        monkeypatch.setenv("SPOONACULAR_API_KEY", "key")
        monkeypatch.delenv("DATABASE_URL", raising=False)

        config = Config()
        config.validate()  # Should not raise even though DATABASE_URL missing


class TestConfigOptionalFields:
    """Test optional configuration fields."""

    def test_database_url_is_optional(self, monkeypatch):
        """Test that DATABASE_URL is optional with None default."""
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.setenv("GEMINI_API_KEY", "key")
        monkeypatch.setenv("SPOONACULAR_API_KEY", "key")

        config = Config()
        assert config.DATABASE_URL is None

    def test_database_url_loaded_when_set(self, monkeypatch):
        """Test that DATABASE_URL is loaded when provided."""
        monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/db")
        monkeypatch.setenv("GEMINI_API_KEY", "key")
        monkeypatch.setenv("SPOONACULAR_API_KEY", "key")

        config = Config()
        assert config.DATABASE_URL == "postgresql://localhost/db"


class TestConfigEnvironmentOverride:
    """Test that environment variables override other sources."""

    def test_system_env_overrides_defaults(self, monkeypatch):
        """Test that system env vars take precedence over defaults."""
        monkeypatch.setenv("PORT", "5555")
        monkeypatch.setenv("GEMINI_API_KEY", "key")
        monkeypatch.setenv("SPOONACULAR_API_KEY", "key")

        config = Config()
        assert config.PORT == 5555  # Not default 7777

    def test_all_configuration_sources_work(self, monkeypatch):
        """Test that configuration loads from environment variables."""
        test_values = {
            "GEMINI_API_KEY": "test_gemini",
            "SPOONACULAR_API_KEY": "test_spoon",
            "GEMINI_MODEL": "test-model",
            "PORT": "6666",
            "MAX_HISTORY": "7",
            "MAX_IMAGE_SIZE_MB": "15",
            "MIN_INGREDIENT_CONFIDENCE": "0.6",
            "DATABASE_URL": "postgresql://test/db",
            "IMAGE_DETECTION_MODE": "tool",
        }

        for key, value in test_values.items():
            monkeypatch.setenv(key, value)

        config = Config()

        assert config.GEMINI_API_KEY == "test_gemini"
        assert config.SPOONACULAR_API_KEY == "test_spoon"
        assert config.GEMINI_MODEL == "test-model"
        assert config.PORT == 6666
        assert config.MAX_HISTORY == 7
        assert config.MAX_IMAGE_SIZE_MB == 15
        assert config.MIN_INGREDIENT_CONFIDENCE == 0.6
        assert config.DATABASE_URL == "postgresql://test/db"
        assert config.IMAGE_DETECTION_MODE == "tool"


class TestImageDetectionMode:
    """Test IMAGE_DETECTION_MODE configuration."""

    def test_default_image_detection_mode(self, monkeypatch):
        """Test that IMAGE_DETECTION_MODE defaults to 'pre-hook'."""
        monkeypatch.delenv("IMAGE_DETECTION_MODE", raising=False)
        monkeypatch.setenv("GEMINI_API_KEY", "key")
        monkeypatch.setenv("SPOONACULAR_API_KEY", "key")

        config = Config()
        assert config.IMAGE_DETECTION_MODE == "pre-hook"

    def test_image_detection_mode_pre_hook(self, monkeypatch):
        """Test that 'pre-hook' mode is valid."""
        monkeypatch.setenv("IMAGE_DETECTION_MODE", "pre-hook")
        monkeypatch.setenv("GEMINI_API_KEY", "key")
        monkeypatch.setenv("SPOONACULAR_API_KEY", "key")

        config = Config()
        config.validate()  # Should not raise
        assert config.IMAGE_DETECTION_MODE == "pre-hook"

    def test_image_detection_mode_tool(self, monkeypatch):
        """Test that 'tool' mode is valid."""
        monkeypatch.setenv("IMAGE_DETECTION_MODE", "tool")
        monkeypatch.setenv("GEMINI_API_KEY", "key")
        monkeypatch.setenv("SPOONACULAR_API_KEY", "key")

        config = Config()
        config.validate()  # Should not raise
        assert config.IMAGE_DETECTION_MODE == "tool"

    def test_image_detection_mode_invalid(self, monkeypatch):
        """Test that invalid IMAGE_DETECTION_MODE raises ValueError."""
        monkeypatch.setenv("IMAGE_DETECTION_MODE", "invalid-mode")
        monkeypatch.setenv("GEMINI_API_KEY", "key")
        monkeypatch.setenv("SPOONACULAR_API_KEY", "key")

        config = Config()
        with pytest.raises(ValueError, match="IMAGE_DETECTION_MODE"):
            config.validate()


class TestImageDetectionModel:
    """Test IMAGE_DETECTION_MODEL configuration."""

    def test_default_image_detection_model(self, monkeypatch):
        """Test that IMAGE_DETECTION_MODEL defaults to 'gemini-3-flash-preview'."""
        monkeypatch.delenv("IMAGE_DETECTION_MODEL", raising=False)
        monkeypatch.setenv("GEMINI_API_KEY", "key")
        monkeypatch.setenv("SPOONACULAR_API_KEY", "key")

        config = Config()
        assert config.IMAGE_DETECTION_MODEL == "gemini-3-flash-preview"

    def test_custom_image_detection_model(self, monkeypatch):
        """Test that IMAGE_DETECTION_MODEL can be customized independently."""
        monkeypatch.setenv("GEMINI_MODEL", "gemini-3-flash-preview")
        monkeypatch.setenv("IMAGE_DETECTION_MODEL", "gemini-3-pro-preview")
        monkeypatch.setenv("GEMINI_API_KEY", "key")
        monkeypatch.setenv("SPOONACULAR_API_KEY", "key")

        config = Config()
        config.validate()  # Should not raise
        assert config.GEMINI_MODEL == "gemini-3-flash-preview"
        assert config.IMAGE_DETECTION_MODEL == "gemini-3-pro-preview"

    def test_image_detection_model_independent_from_main_model(self, monkeypatch):
        """Test that changing main model doesn't affect image detection model."""
        monkeypatch.setenv("GEMINI_MODEL", "custom-recipe-model")
        monkeypatch.setenv("IMAGE_DETECTION_MODEL", "custom-vision-model")
        monkeypatch.setenv("GEMINI_API_KEY", "key")
        monkeypatch.setenv("SPOONACULAR_API_KEY", "key")

        config = Config()
        assert config.GEMINI_MODEL == "custom-recipe-model"
        assert config.IMAGE_DETECTION_MODEL == "custom-vision-model"


class TestCompressImg:
    """Test COMPRESS_IMG configuration for image compression toggle."""

    def test_default_compress_img_enabled(self, monkeypatch):
        """Test that COMPRESS_IMG defaults to True (enabled)."""
        monkeypatch.delenv("COMPRESS_IMG", raising=False)
        monkeypatch.setenv("GEMINI_API_KEY", "key")
        monkeypatch.setenv("SPOONACULAR_API_KEY", "key")

        config = Config()
        assert config.COMPRESS_IMG is True

    def test_compress_img_enabled_explicit_true(self, monkeypatch):
        """Test COMPRESS_IMG=true enables compression."""
        monkeypatch.setenv("COMPRESS_IMG", "true")
        monkeypatch.setenv("GEMINI_API_KEY", "key")
        monkeypatch.setenv("SPOONACULAR_API_KEY", "key")

        config = Config()
        assert config.COMPRESS_IMG is True

    def test_compress_img_enabled_with_yes(self, monkeypatch):
        """Test COMPRESS_IMG=yes enables compression."""
        monkeypatch.setenv("COMPRESS_IMG", "yes")
        monkeypatch.setenv("GEMINI_API_KEY", "key")
        monkeypatch.setenv("SPOONACULAR_API_KEY", "key")

        config = Config()
        assert config.COMPRESS_IMG is True

    def test_compress_img_enabled_with_one(self, monkeypatch):
        """Test COMPRESS_IMG=1 enables compression."""
        monkeypatch.setenv("COMPRESS_IMG", "1")
        monkeypatch.setenv("GEMINI_API_KEY", "key")
        monkeypatch.setenv("SPOONACULAR_API_KEY", "key")

        config = Config()
        assert config.COMPRESS_IMG is True

    def test_compress_img_disabled_false(self, monkeypatch):
        """Test COMPRESS_IMG=false disables compression."""
        monkeypatch.setenv("COMPRESS_IMG", "false")
        monkeypatch.setenv("GEMINI_API_KEY", "key")
        monkeypatch.setenv("SPOONACULAR_API_KEY", "key")

        config = Config()
        assert config.COMPRESS_IMG is False

    def test_compress_img_disabled_no(self, monkeypatch):
        """Test COMPRESS_IMG=no disables compression."""
        monkeypatch.setenv("COMPRESS_IMG", "no")
        monkeypatch.setenv("GEMINI_API_KEY", "key")
        monkeypatch.setenv("SPOONACULAR_API_KEY", "key")

        config = Config()
        assert config.COMPRESS_IMG is False

    def test_compress_img_disabled_zero(self, monkeypatch):
        """Test COMPRESS_IMG=0 disables compression."""
        monkeypatch.setenv("COMPRESS_IMG", "0")
        monkeypatch.setenv("GEMINI_API_KEY", "key")
        monkeypatch.setenv("SPOONACULAR_API_KEY", "key")

        config = Config()
        assert config.COMPRESS_IMG is False

    def test_compress_img_case_insensitive(self, monkeypatch):
        """Test COMPRESS_IMG is case-insensitive."""
        monkeypatch.setenv("COMPRESS_IMG", "TRUE")
        monkeypatch.setenv("GEMINI_API_KEY", "key")
        monkeypatch.setenv("SPOONACULAR_API_KEY", "key")

        config = Config()
        assert config.COMPRESS_IMG is True

        monkeypatch.setenv("COMPRESS_IMG", "False")
        config2 = Config()
        assert config2.COMPRESS_IMG is False


