"""
API 端点模块

遵守规范：API 代码模块化设计，不放在 database_manager.py 中
"""

from .reports import router as reports_router
from .watchlist import router as watchlist_router
from .portfolio import router as portfolio_router
from .principles import router as principles_router
from .ui_states import router as ui_states_router
from .actions import router as actions_router
from .listeners import router as listeners_router
from .search import router as search_router

__all__ = [
    'reports_router',
    'watchlist_router',
    'portfolio_router',
    'principles_router',
    'ui_states_router',
    'actions_router',
    'listeners_router',
    'search_router',
]
