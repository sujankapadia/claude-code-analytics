"""FastAPI dependency injection for shared services."""

import logging
from functools import lru_cache

from claude_code_analytics.services.analysis_service import AnalysisService
from claude_code_analytics.services.database_service import DatabaseService

logger = logging.getLogger(__name__)


@lru_cache
def get_db_service() -> DatabaseService:
    """Singleton DatabaseService instance."""
    return DatabaseService()


@lru_cache
def get_analysis_service() -> AnalysisService:
    """Singleton AnalysisService instance."""
    return AnalysisService()


@lru_cache
def get_embedding_service():
    """Singleton EmbeddingService instance. Returns None if ChromaDB unavailable."""
    try:
        from claude_code_analytics.services.embedding_service import EmbeddingService

        return EmbeddingService()
    except Exception:
        logger.warning("ChromaDB unavailable — semantic search disabled")
        return None
