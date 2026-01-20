"""
初始化默认投资原则
将默认的投资原则插入数据库
"""

import asyncio
import sys
from pathlib import Path

# 添加项目路径
sys.path.append(str(Path(__file__).parent.parent))

from database.database_manager import DatabaseManager
from database.schemas import DEFAULT_PRINCIPLES


async def main():
    """初始化默认投资原则"""
    db = DatabaseManager("data/finance.db")
    
    print("=" * 60)
    print("初始化默认投资原则")
    print("=" * 60)
    
    try:
        # 插入默认原则
        await db.principles.upsert_user_principles(
            user_id='default',
            principles_data=DEFAULT_PRINCIPLES,
            is_active=True
        )
        
        print(f"✅ 已为用户 'default' 初始化投资原则")
        print(f"   档案名称: {DEFAULT_PRINCIPLES['profile_name']}")
        print(f"   版本: {DEFAULT_PRINCIPLES['version']}")
        
        # 读取并验证
        loaded_principles = await db.principles.get_active_principles('default')
        print(f"\n✅ 验证成功，已从数据库读取投资原则")
        print(f"   单一品种常规上限: {loaded_principles['weight_management']['single_position_max_normal']*100:.0f}%")
        print(f"   单一品种极限上限: {loaded_principles['weight_management']['single_position_max_extreme']*100:.0f}%")
        print(f"   目标持仓数量: {loaded_principles['weight_management']['target_position_count_min']}-{loaded_principles['weight_management']['target_position_count_max']}")
        
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
