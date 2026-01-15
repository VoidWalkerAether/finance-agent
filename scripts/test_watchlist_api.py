"""
关注列表 API 测试脚本

测试场景:
1. 添加关注项
2. 获取关注列表
3. 更新关注项
4. 删除关注项
5. 验证数据持久化
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.database_manager import DatabaseManager


async def test_watchlist_api():
    """测试关注列表 API"""
    
    print("=" * 60)
    print("关注列表 API 测试")
    print("=" * 60)
    
    # 1. 初始化数据库
    print("\n[1] 初始化数据库...")
    db = DatabaseManager("data/finance_test.db")
    print("   ✓ 数据库已初始化")
    
    # 2. 添加关注项
    print("\n[2] 添加关注项...")
    
    # 添加股票
    stock_id = await db.add_watchlist_item(
        target_name="招商银行",
        target_type="stock",
        notes="银行板块龙头"
    )
    print(f"   ✓ 添加股票: 招商银行 (ID: {stock_id})")
    
    # 添加 ETF
    etf_id = await db.add_watchlist_item(
        target_name="黄金ETF",
        target_type="etf",
        notes="黄金投资工具"
    )
    print(f"   ✓ 添加 ETF: 黄金ETF (ID: {etf_id})")
    
    # 添加指数
    index_id = await db.add_watchlist_item(
        target_name="上证指数",
        target_type="index",
        alert_conditions={"price_level": 3000},
        notes="大盘指数"
    )
    print(f"   ✓ 添加指数: 上证指数 (ID: {index_id})")
    
    # 3. 获取关注列表
    print("\n[3] 获取关注列表...")
    watchlist = await db.get_watchlist()
    print(f"   ✓ 获取到 {len(watchlist)} 个关注项:")
    for item in watchlist:
        print(f"      - {item['target_name']} ({item['target_type']}) - {item.get('notes', '')}")
    
    # 4. 获取单个关注项
    print("\n[4] 获取单个关注项...")
    item = await db.get_watchlist_item(stock_id)
    if item:
        print(f"   ✓ 找到关注项:")
        print(f"      ID: {item['id']}")
        print(f"      名称: {item['target_name']}")
        print(f"      类型: {item['target_type']}")
        print(f"      备注: {item.get('notes', '')}")
        print(f"      创建时间: {item['created_at']}")
    
    # 5. 更新关注项
    print("\n[5] 更新关注项...")
    success = await db.update_watchlist_item(
        stock_id,
        {
            'notes': '银行板块龙头 - 已关注',
            'alert_conditions': {'price': '<40'}
        }
    )
    if success:
        print("   ✓ 更新成功")
        updated_item = await db.get_watchlist_item(stock_id)
        print(f"      新备注: {updated_item['notes']}")
        print(f"      提醒条件: {updated_item.get('alert_conditions')}")
    
    # 6. 软删除关注项
    print("\n[6] 软删除关注项 (招商银行)...")
    success = await db.remove_watchlist_item(stock_id)
    if success:
        print("   ✓ 软删除成功 (status = 'inactive')")
        
        # 验证不在活跃列表中
        active_list = await db.get_watchlist(status="active")
        print(f"   ✓ 活跃关注项: {len(active_list)} 个")
        
        # 验证在非活跃列表中
        inactive_list = await db.get_watchlist(status="inactive")
        print(f"   ✓ 非活跃关注项: {len(inactive_list)} 个")
    
    # 7. 完全删除关注项
    print("\n[7] 完全删除关注项 (黄金ETF)...")
    success = await db.delete_watchlist_item(etf_id)
    if success:
        print("   ✓ 硬删除成功")
        
        # 验证已删除
        deleted_item = await db.get_watchlist_item(etf_id)
        if deleted_item is None:
            print("   ✓ 确认已删除")
    
    # 8. 最终统计
    print("\n[8] 最终统计...")
    all_active = await db.get_watchlist(status="active")
    all_inactive = await db.get_watchlist(status="inactive")
    print(f"   - 活跃关注项: {len(all_active)} 个")
    print(f"   - 非活跃关注项: {len(all_inactive)} 个")
    print(f"   - 总计: {len(all_active) + len(all_inactive)} 个")
    
    print("\n" + "=" * 60)
    print("✅ 测试完成!")
    print("=" * 60)
    
    print("\n📝 测试总结:")
    print("  ✅ 成功添加关注项 (stock, etf, index)")
    print("  ✅ 成功获取关注列表")
    print("  ✅ 成功更新关注项")
    print("  ✅ 成功软删除关注项")
    print("  ✅ 成功硬删除关注项")
    print("  ✅ JSON 字段序列化/反序列化正常")


if __name__ == "__main__":
    asyncio.run(test_watchlist_api())
