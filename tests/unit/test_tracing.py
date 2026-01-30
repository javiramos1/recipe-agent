"""Unit tests for tracing configuration and initialization.

Tests verify:
- Tracing configuration loading from environment
- Tracing initialization with database creation
- Graceful degradation if OpenTelemetry unavailable
- Configuration validation
"""

from unittest.mock import patch

import pytest

from src.utils.config import Config


class TestTracingConfig:
    """Test tracing configuration loading and validation."""

    def test_tracing_enabled_by_default(self, monkeypatch):
        """Test that tracing is enabled by default."""
        monkeypatch.delenv("ENABLE_TRACING", raising=False)
        config = Config()
        assert config.ENABLE_TRACING is True

    def test_tracing_disabled_via_env(self, monkeypatch):
        """Test that tracing can be disabled via environment variable."""
        monkeypatch.setenv("ENABLE_TRACING", "false")
        config = Config()
        assert config.ENABLE_TRACING is False

    def test_tracing_enabled_via_env(self, monkeypatch):
        """Test enabling tracing explicitly."""
        monkeypatch.setenv("ENABLE_TRACING", "true")
        config = Config()
        assert config.ENABLE_TRACING is True

    def test_tracing_db_type_default_sqlite(self, monkeypatch):
        """Test that SQLite is the default tracing database type."""
        monkeypatch.delenv("TRACING_DB_TYPE", raising=False)
        config = Config()
        assert config.TRACING_DB_TYPE == "sqlite"

    def test_tracing_db_type_postgres(self, monkeypatch):
        """Test setting PostgreSQL as tracing database type."""
        monkeypatch.setenv("TRACING_DB_TYPE", "postgres")
        config = Config()
        assert config.TRACING_DB_TYPE == "postgres"

    def test_tracing_db_file_default(self, monkeypatch):
        """Test that default tracing database file is agno_traces.db."""
        monkeypatch.delenv("TRACING_DB_FILE", raising=False)
        config = Config()
        assert config.TRACING_DB_FILE == "agno_traces.db"

    def test_tracing_db_file_custom_path(self, monkeypatch):
        """Test setting custom tracing database file path."""
        custom_path = "/tmp/custom_traces.db"
        monkeypatch.setenv("TRACING_DB_FILE", custom_path)
        config = Config()
        assert config.TRACING_DB_FILE == custom_path

    def test_tracing_db_type_validation_invalid(self):
        """Test that invalid tracing database type raises error."""
        with pytest.raises(ValueError) as exc_info:
            config = Config()
            config.TRACING_DB_TYPE = "invalid_db_type"
            config.validate()
        assert "TRACING_DB_TYPE must be 'sqlite' or 'postgres'" in str(exc_info.value)

    def test_tracing_config_environment_priority(self, monkeypatch):
        """Test that environment variables have highest priority."""
        monkeypatch.setenv("ENABLE_TRACING", "true")
        monkeypatch.setenv("TRACING_DB_TYPE", "sqlite")
        monkeypatch.setenv("TRACING_DB_FILE", "traces_custom.db")

        config = Config()
        assert config.ENABLE_TRACING is True
        assert config.TRACING_DB_TYPE == "sqlite"
        assert config.TRACING_DB_FILE == "traces_custom.db"


@pytest.mark.asyncio
async def test_initialize_tracing_disabled(monkeypatch):
    """Test that initialize_tracing returns None when disabled."""
    from src.utils.tracing import initialize_tracing
    from src.utils import config as config_module

    # Mock config.ENABLE_TRACING directly
    monkeypatch.setattr(config_module.config, "ENABLE_TRACING", False)

    result = await initialize_tracing()
    assert result is None


@pytest.mark.asyncio
async def test_initialize_tracing_creates_database(monkeypatch, tmp_path):
    """Test that initialize_tracing creates a database."""
    from src.utils.tracing import initialize_tracing
    from src.utils import config as config_module

    db_file = str(tmp_path / "test_traces.db")
    # Mock config directly
    monkeypatch.setattr(config_module.config, "ENABLE_TRACING", True)
    monkeypatch.setattr(config_module.config, "TRACING_DB_FILE", db_file)

    result = await initialize_tracing()

    # Should return a database instance
    assert result is not None
    assert hasattr(result, "db_file")


@pytest.mark.asyncio
async def test_initialize_tracing_graceful_degradation(monkeypatch):
    """Test that initialize_tracing handles missing OpenTelemetry gracefully."""
    from src.utils.tracing import initialize_tracing
    from src.utils import config as config_module

    # Mock config to enable tracing
    monkeypatch.setattr(config_module.config, "ENABLE_TRACING", True)

    # Mock setup_tracing to raise ImportError
    with patch("src.utils.tracing.setup_tracing") as mock_setup:
        mock_setup.side_effect = ImportError("opentelemetry not installed")

        result = await initialize_tracing()

        # Should return None but not crash
        assert result is None


@pytest.mark.asyncio
async def test_initialize_tracing_exception_handling(monkeypatch):
    """Test that initialize_tracing handles exceptions gracefully."""
    from src.utils.tracing import initialize_tracing
    from src.utils import config as config_module

    # Mock config to enable tracing
    monkeypatch.setattr(config_module.config, "ENABLE_TRACING", True)

    # Mock SqliteDb to raise an exception
    with patch("src.utils.tracing.SqliteDb") as mock_db:
        mock_db.side_effect = RuntimeError("Database connection failed")

        result = await initialize_tracing()

        # Should return None but not crash
        assert result is None
