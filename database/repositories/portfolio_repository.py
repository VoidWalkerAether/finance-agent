"""
Portfolio Repository
负责用户持仓数据的数据库访问
"""

import json
import aiosqlite
from typing import Optional, Dict, Any
from pathlib import Path

# 导入 Schema 定义
from ..schemas import (
    PortfolioSchemaV1,
    DEFAULT_PORTFOLIO,
    validate_portfolio,
    fill_defaults
)


class PortfolioRepository:
    """用户持仓数据仓库"""
    
    def __init__(self, db_path: str):
        """
        初始化 Repository
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
    
    async def get_user_portfolio(self, user_id: str = 'default') -> Optional[PortfolioSchemaV1]:
        """
        获取用户持仓数据
        
        Args:
            user_id: 用户ID（默认 'default'）
            
        Returns:
            持仓数据，如果不存在返回 None
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT total_asset_value, cash_position, holdings_json
                FROM user_portfolios
                WHERE user_id = ?
                """,
                (user_id,)
            )
            row = await cursor.fetchone()
            
            if not row:
                return None
            
            # 解析 JSON
            try:
                holdings_data = json.loads(row['holdings_json'])
            except json.JSONDecodeError as e:
                print(f"[Portfolio Repository] JSON 解析失败: {e}")
                return None
            
            # 构造完整数据
            portfolio_data = {
                'total_asset_value': row['total_asset_value'],
                'cash_position': row['cash_position'],
                'holdings': holdings_data
            }
            
            # 填充默认值（容错）
            portfolio_data = fill_defaults(portfolio_data)
            
            return portfolio_data
    
    async def upsert_user_portfolio(
        self, 
        user_id: str, 
        portfolio_data: Dict[str, Any]
    ) -> None:
        """
        创建或更新用户持仓数据
        
        Args:
            user_id: 用户ID
            portfolio_data: 持仓数据（符合 PortfolioSchemaV1）
            
        Raises:
            ValueError: 如果数据验证失败
        """
        # 验证数据
        validated_data = validate_portfolio(portfolio_data)
        
        # 序列化 holdings
        holdings_json = json.dumps(
            validated_data['holdings'], 
            ensure_ascii=False
        )
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO user_portfolios (
                    user_id, 
                    total_asset_value, 
                    cash_position, 
                    holdings_json
                )
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    total_asset_value = excluded.total_asset_value,
                    cash_position = excluded.cash_position,
                    holdings_json = excluded.holdings_json,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    user_id,
                    validated_data['total_asset_value'],
                    validated_data['cash_position'],
                    holdings_json
                )
            )
            await db.commit()
            print(f"[Portfolio Repository] 用户 {user_id} 持仓已更新")
    
    async def delete_user_portfolio(self, user_id: str = 'default') -> bool:
        """
        删除用户持仓数据
        
        Args:
            user_id: 用户ID
            
        Returns:
            是否成功删除
        """
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "DELETE FROM user_portfolios WHERE user_id = ?",
                (user_id,)
            )
            await db.commit()
            deleted = cursor.rowcount > 0
            
            if deleted:
                print(f"[Portfolio Repository] 用户 {user_id} 持仓已删除")
            
            return deleted
    
    async def get_or_create_default_portfolio(
        self, 
        user_id: str = 'default'
    ) -> PortfolioSchemaV1:
        """
        获取用户持仓，如果不存在则返回默认值
        
        Args:
            user_id: 用户ID
            
        Returns:
            持仓数据
        """
        portfolio = await self.get_user_portfolio(user_id)
        
        if portfolio is None:
            return DEFAULT_PORTFOLIO.copy()
        
        return portfolio
