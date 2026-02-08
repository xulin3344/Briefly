from app.routes.sources import router as sources_router
from app.routes.articles import router as articles_router
from app.routes.keywords import router as keywords_router
from app.routes.system import router as system_router

__all__ = [
    "sources_router",
    "articles_router",
    "keywords_router",
    "system_router"
]
