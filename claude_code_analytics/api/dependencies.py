"""FastAPI dependency injection for shared services."""

from functools import lru_cache

from claude_code_analytics.streamlit_app.services.analysis_service import AnalysisService
from claude_code_analytics.streamlit_app.services.database_service import DatabaseService


@lru_cache
def get_db_service() -> DatabaseService:
    """Singleton DatabaseService instance."""
    return DatabaseService()


@lru_cache
def get_analysis_service() -> AnalysisService:
    """Singleton AnalysisService instance."""
    return AnalysisService()
