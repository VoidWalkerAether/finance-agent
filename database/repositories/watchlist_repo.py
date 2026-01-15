"""
Watchlist Repository

关注列表数据访问层

职责:
- 关注列表的 CRUD 操作
- JSON 序列化/反序列化
- 业务查询逻辑
"""

import aiosqlite
import json
from typing import Optional, Dict, Any, List


class WatchlistRepository:
    """关注列表 Repository"""
    
    def __init__(self, db_path: str):
        """
        初始化 Repository
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
    
    async def add_item(
        self,
        target_name: str,
        target_type: str = "stock",
        user_id: str = "default",
        alert_conditions: Optional[Dict[str, Any]] = None,
        notes: Optional[str] = None
    ) -> int:
        """
        添加关注项
        
        Args:
            target_name: 标的名称
            target_type: 标的类型 (stock/etf/index/industry)
            user_id: 用户 ID
            alert_conditions: 提醒条件 (JSON)
            notes: 备注
        
        Returns:
            int: 关注项 ID
        """
        # 序列化 JSON 字段
        conditions_json = None
        if alert_conditions:
            conditions_json = json.dumps(alert_conditions, ensure_ascii=False)
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO watchlist (user_id, target_name, target_type, alert_conditions, notes)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, target_name, target_type, conditions_json, notes))
            
            await db.commit()
            return cursor.lastrowid
    
    async def get_list(
        self,
        user_id: str = "default",
        status: str = "active"
    ) -> List[Dict[str, Any]]:
        """
        获取关注列表
        
        Args:
            user_id: 用户 ID
            status: 状态 (active/inactive)
        
        Returns:
            List[Dict]: 关注项列表
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM watchlist
                WHERE user_id = ? AND status = ?
                ORDER BY created_at DESC
            """, (user_id, status))
            
            rows = await cursor.fetchall()
            items = [dict(row) for row in rows]
            
            # 反序列化 JSON 字段
            for item in items:
                if item.get('alert_conditions'):
                    try:
                        item['alert_conditions'] = json.loads(item['alert_conditions'])
                    except json.JSONDecodeError:
                        item['alert_conditions'] = None
            
            return items
    
    async def get_item(self, item_id: int) -> Optional[Dict[str, Any]]:
        """
        获取单个关注项
        
        Args:
            item_id: 关注项 ID
        
        Returns:
            Dict: 关注项数据
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM watchlist WHERE id = ?",
                (item_id,)
            )
            row = await cursor.fetchone()
            
            if row:
                item = dict(row)
                if item.get('alert_conditions'):
                    try:
                        item['alert_conditions'] = json.loads(item['alert_conditions'])
                    except json.JSONDecodeError:
                        item['alert_conditions'] = None
                return item
            
            return None
    
    async def update_item(
        self,
        item_id: int,
        updates: Dict[str, Any]
    ) -> bool:
        """
        更新关注项
        
        Args:
            item_id: 关注项 ID
            updates: 要更新的字段
        
        Returns:
            bool: 是否成功
        """
        # 序列化 JSON 字段
        if 'alert_conditions' in updates and isinstance(updates['alert_conditions'], dict):
            updates['alert_conditions'] = json.dumps(updates['alert_conditions'], ensure_ascii=False)
        
        # 构建 UPDATE 语句
        fields = []
        values = []
        for key, value in updates.items():
            if key in ['target_name', 'target_type', 'alert_conditions', 'status', 'notes']:
                fields.append(f"{key} = ?")
                values.append(value)
        
        if not fields:
            return False
        
        values.append(item_id)
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                f"UPDATE watchlist SET {', '.join(fields)} WHERE id = ?",
                values
            )
            await db.commit()
            return True
    
    async def remove_item(self, item_id: int) -> bool:
        """
        删除关注项 (软删除，设置 status = 'inactive')
        
        Args:
            item_id: 关注项 ID
        
        Returns:
            bool: 是否成功
        """
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE watchlist SET status = 'inactive' WHERE id = ?",
                (item_id,)
            )
            await db.commit()
            return True
    
    async def delete_item(self, item_id: int) -> bool:
        """
        完全删除关注项 (硬删除)
        
        Args:
            item_id: 关注项 ID
        
        Returns:
            bool: 是否成功
        """
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "DELETE FROM watchlist WHERE id = ?",
                (item_id,)
            )
            await db.commit()
            return True
    
    async def get_by_type(
        self,
        target_type: str,
        user_id: str = "default",
        status: str = "active"
    ) -> List[Dict[str, Any]]:
        """
        按类型获取关注列表
        
        Args:
            target_type: 标的类型 (stock/etf/index/industry)
            user_id: 用户 ID
            status: 状态
        
        Returns:
            List[Dict]: 关注项列表
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM watchlist
                WHERE user_id = ? AND status = ? AND target_type = ?
                ORDER BY created_at DESC
            """, (user_id, status, target_type))
            
            rows = await cursor.fetchall()
            items = [dict(row) for row in rows]
            
            # 反序列化 JSON 字段
            for item in items:
                if item.get('alert_conditions'):
                    try:
                        item['alert_conditions'] = json.loads(item['alert_conditions'])
                    except json.JSONDecodeError:
                        item['alert_conditions'] = None
            
            return items
