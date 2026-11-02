from .verification import router as verification_router
from .news_search import router as search_router
from .history import router as history_router

__all__ = ["verification_router", "search_router", "history_router"]
