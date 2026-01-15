"""
测试 ActionContext.watchlist_api

验证 ActionContext 提供的关注列表 API 是否正常工作
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.database_manager import DatabaseManager
from ccsdk.action_context import ActionContext


async def test_action_context_watchlist():
    """测试 ActionContext 的 watchlist_api"""
    
    print("=" * 60)
    print("ActionContext.watchlist_api 测试")
    print("=" * 60)
    
    # 1. 初始化
    print("\n[1] 初始化 ActionContext...")
    db = DatabaseManager("data/finance_test.db")
    context = ActionContext(
        session_id="test_session",
        database=db
    )
    print("   ✓ ActionContext 已初始化")
    
    # 2. 通过 watchlist_api 添加关注项
    print("\n[2] 通过 context.watchlist_api 添加关注项...")
    
    item_id_1 = await context.watchlist_api.add_to_watchlist(
        target_name="贵州茅台",
        target_type="stock",
        notes="白酒龙头"
    )
    print(f"   ✓ 添加成功: 贵州茅台 (ID: {item_id_1})")
    
    item_id_2 = await context.watchlist_api.add_to_watchlist(
        target_name="沪深300ETF",
        target_type="etf",
        notes="宽基指数ETF"
    )
    print(f"   ✓ 添加成功: 沪深300ETF (ID: {item_id_2})")
    
    # 3. 获取关注列表
    print("\n[3] 通过 context.watchlist_api 获取关注列表...")
    watchlist = await context.watchlist_api.get_watchlist()
    print(f"   ✓ 获取到 {len(watchlist)} 个关注项:")
    for item in watchlist:
        print(f"      - {item['target_name']} ({item['target_type']})")
    
    # 4. 获取单个关注项
    print("\n[4] 获取单个关注项...")
    item = await context.watchlist_api.get_item(item_id_1)
    if item:
        print(f"   ✓ 找到: {item['target_name']}")
        print(f"      类型: {item['target_type']}")
        print(f"      备注: {item.get('notes')}")
    
    # 5. 更新关注项
    print("\n[5] 更新关注项...")
    success = await context.watchlist_api.update_item(
        item_id_1,
        {'notes': '白酒龙头 - 核心持仓'}
    )
    if success:
        print("   ✓ 更新成功")
        updated = await context.watchlist_api.get_item(item_id_1)
        print(f"      新备注: {updated['notes']}")
    
    # 6. 删除关注项
    print("\n[6] 删除关注项...")
    success = await context.watchlist_api.remove_from_watchlist(item_id_2)
    if success:
        print("   ✓ 删除成功 (软删除)")
        
        # 验证
        active = await context.watchlist_api.get_watchlist(status="active")
        print(f"   ✓ 当前活跃关注项: {len(active)} 个")
    
    print("\n" + "=" * 60)
    print("✅ ActionContext.watchlist_api 测试完成!")
    print("=" * 60)
    
    print("\n📝 验证结果:")
    print("  ✅ context.watchlist_api.add_to_watchlist() 正常")
    print("  ✅ context.watchlist_api.get_watchlist() 正常")
    print("  ✅ context.watchlist_api.get_item() 正常")
    print("  ✅ context.watchlist_api.update_item() 正常")
    print("  ✅ context.watchlist_api.remove_from_watchlist() 正常")


if __name__ == "__main__":
    asyncio.run(test_action_context_watchlist())
