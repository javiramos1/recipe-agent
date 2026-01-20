"""Tracing initialization and configuration for AgentOS.

This module provides a factory function to initialize distributed tracing
with OpenTelemetry and Agno's built-in tracing infrastructure.
"""

from typing import Optional

from agno.db.sqlite import SqliteDb
from agno.tracing import setup_tracing

from src.utils.config import config
from src.utils.logger import logger


async def initialize_tracing() -> Optional[SqliteDb]:
    """Initialize tracing with dedicated database.

    Creates a dedicated tracing database separate from the agent session database
    for cleaner data separation and independent scaling. Enables batch processing
    and OpenTelemetry instrumentation for comprehensive observability.

    Returns:
        SqliteDb: Configured tracing database instance, or None if tracing disabled.

    Raises:
        Exception: If tracing initialization fails (logged as warning, non-fatal).
    """
    if not config.ENABLE_TRACING:
        logger.info("Tracing disabled via ENABLE_TRACING=false")
        return None

    try:
        logger.info("Initializing tracing...")

        # Create dedicated tracing database (separate from agent session db)
        tracing_db = SqliteDb(
            db_file=config.TRACING_DB_FILE,
            id="tracing_db",
        )

        # Set up tracing with OpenTelemetry and batch processing
        setup_tracing(
            db=tracing_db,
            batch_processing=True,
            max_queue_size=2048,
            schedule_delay_millis=3000,
            max_export_batch_size=256,
        )

        logger.info(
            f"Tracing enabled successfully. Database: {config.TRACING_DB_FILE}, "
            f"batch_size: 256, queue_size: 2048"
        )
        return tracing_db

    except ImportError as e:
        logger.warning(
            f"OpenTelemetry packages not installed (optional): {e}. "
            "Install with: pip install opentelemetry-api opentelemetry-sdk openinference-instrumentation-agno"
        )
        return None
    except Exception as e:
        logger.warning(f"Tracing initialization failed (non-fatal): {e}")
        return None
