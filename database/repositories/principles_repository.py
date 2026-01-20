"""
Principles Repository
负责用户投资原则数据的数据库访问
"""

import json
import aiosqlite
from typing import Optional, Dict, Any, List
from pathlib import Path

# 导入 Schema 定义
from ..schemas import (
    PrinciplesSchemaV1,
    DEFAULT_PRINCIPLES,
    validate_principles,
    fill_principles_defaults
)


class PrinciplesRepository:
    """用户投资原则数据仓库"""
    
    def __init__(self, db_path: str):
        """
        初始化 Repository
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
    
    async def get_user_principles(
        self, 
        user_id: str = 'default',
        profile_name: Optional[str] = None
    ) -> Optional[PrinciplesSchemaV1]:
        """
        获取用户投资原则数据
        
        Args:
            user_id: 用户ID（默认 'default'）
            profile_name: 原则档案名称（可选，如不指定则返回 is_active=1 的）
            
        Returns:
            投资原则数据，如果不存在返回 None
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            
            if profile_name:
                # 按 profile_name 查询
                cursor = await db.execute(
                    """
                    SELECT principles_json, version
                    FROM user_investment_principles
                    WHERE user_id = ? AND profile_name = ?
                    """,
                    (user_id, profile_name)
                )
            else:
                # 查询激活的原则
                cursor = await db.execute(
                    """
                    SELECT principles_json, version
                    FROM user_investment_principles
                    WHERE user_id = ? AND is_active = 1
                    ORDER BY updated_at DESC
                    LIMIT 1
                    """,
                    (user_id,)
                )
            
            row = await cursor.fetchone()
            
            if not row:
                return None
            
            # 解析 JSON
            try:
                principles_data = json.loads(row['principles_json'])
            except json.JSONDecodeError as e:
                print(f"[Principles Repository] JSON 解析失败: {e}")
                return None
            
            # 填充默认值（容错）
            principles_data = fill_principles_defaults(principles_data)
            
            return principles_data
    
    async def get_active_principles(
        self, 
        user_id: str = 'default'
    ) -> PrinciplesSchemaV1:
        """
        获取用户当前生效的投资原则，如果不存在则返回默认值
        
        Args:
            user_id: 用户ID
            
        Returns:
            投资原则数据（保证非空）
        """
        principles = await self.get_user_principles(user_id)
        
        if principles is None:
            return DEFAULT_PRINCIPLES.copy()
        
        return principles
    
    async def upsert_user_principles(
        self, 
        user_id: str, 
        principles_data: Dict[str, Any],
        is_active: bool = True
    ) -> None:
        """
        创建或更新用户投资原则数据
        
        Args:
            user_id: 用户ID
            principles_data: 投资原则数据（符合 PrinciplesSchemaV1）
            is_active: 是否激活（默认 True）
            
        Raises:
            ValueError: 如果数据验证失败
        """
        # 验证数据
        validated_data = validate_principles(principles_data)
        
        # 序列化 JSON
        principles_json = json.dumps(
            validated_data, 
            ensure_ascii=False
        )
        
        profile_name = validated_data['profile_name']
        version = validated_data['version']
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO user_investment_principles (
                    user_id, 
                    profile_name,
                    principles_json,
                    version,
                    is_active
                )
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(user_id, profile_name) DO UPDATE SET
                    principles_json = excluded.principles_json,
                    version = excluded.version,
                    is_active = excluded.is_active,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    user_id,
                    profile_name,
                    principles_json,
                    version,
                    1 if is_active else 0
                )
            )
            await db.commit()
            print(f"[Principles Repository] 用户 {user_id} 的投资原则 {profile_name} 已更新")
    
    async def delete_user_principles(
        self, 
        user_id: str = 'default',
        profile_name: Optional[str] = None
    ) -> bool:
        """
        删除用户投资原则数据
        
        Args:
            user_id: 用户ID
            profile_name: 原则档案名称（如不指定则删除该用户所有原则）
            
        Returns:
            是否成功删除
        """
        async with aiosqlite.connect(self.db_path) as db:
            if profile_name:
                cursor = await db.execute(
                    "DELETE FROM user_investment_principles WHERE user_id = ? AND profile_name = ?",
                    (user_id, profile_name)
                )
            else:
                cursor = await db.execute(
                    "DELETE FROM user_investment_principles WHERE user_id = ?",
                    (user_id,)
                )
            
            await db.commit()
            deleted = cursor.rowcount > 0
            
            if deleted:
                if profile_name:
                    print(f"[Principles Repository] 用户 {user_id} 的投资原则 {profile_name} 已删除")
                else:
                    print(f"[Principles Repository] 用户 {user_id} 的所有投资原则已删除")
            
            return deleted
    
    async def list_user_principles(
        self,
        user_id: str = 'default'
    ) -> List[Dict[str, Any]]:
        """
        列出用户的所有投资原则档案
        
        Args:
            user_id: 用户ID
            
        Returns:
            原则档案列表（每个元素包含 profile_name, version, is_active, updated_at）
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT profile_name, version, is_active, updated_at, principles_json
                FROM user_investment_principles
                WHERE user_id = ?
                ORDER BY updated_at DESC
                """,
                (user_id,)
            )
            rows = await cursor.fetchall()
            
            result = []
            for row in rows:
                try:
                    principles_data = json.loads(row['principles_json'])
                    result.append({
                        'profile_name': row['profile_name'],
                        'version': row['version'],
                        'is_active': bool(row['is_active']),
                        'updated_at': row['updated_at'],
                        'principles': principles_data
                    })
                except json.JSONDecodeError:
                    continue
            
            return result
    
    async def set_active_principles(
        self,
        user_id: str,
        profile_name: str
    ) -> bool:
        """
        设置指定档案为激活状态（其他档案自动设为非激活）
        
        Args:
            user_id: 用户ID
            profile_name: 要激活的档案名称
            
        Returns:
            是否成功设置
        """
        async with aiosqlite.connect(self.db_path) as db:
            # 先将该用户所有档案设为非激活
            await db.execute(
                "UPDATE user_investment_principles SET is_active = 0 WHERE user_id = ?",
                (user_id,)
            )
            
            # 再将指定档案设为激活
            cursor = await db.execute(
                """
                UPDATE user_investment_principles 
                SET is_active = 1, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND profile_name = ?
                """,
                (user_id, profile_name)
            )
            
            await db.commit()
            success = cursor.rowcount > 0
            
            if success:
                print(f"[Principles Repository] 已激活用户 {user_id} 的投资原则 {profile_name}")
            
            return success
