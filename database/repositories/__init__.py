"""
Repositories 模块

业务数据访问层，负责特定领域的数据库操作

架构说明:
- DatabaseManager: 核心数据库管理（连接、初始化、通用查询）
- Repository: 业务数据访问（关注列表、价格提醒、投资组合等）
"""

from .watchlist_repo import WatchlistRepository
from .portfolio_repository import PortfolioRepository

__all__ = ['WatchlistRepository', 'PortfolioRepository']
