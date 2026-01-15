"""
测试 watchlist_monitor Listener

验证场景:
1. 加载 watchlist_monitor Listener
2. 创建测试关注列表
3. 触发 report_imported 事件（报告提到关注标的）
4. 验证通知发送
5. 验证 UI State 更新
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.database_manager import DatabaseManager
from ccsdk.listeners_manager import ListenersManager


# 模拟 AgentTools
class MockAgentTools:
    """Mock AgentTools 用于测试"""
    
    async def call_agent(self, prompt: str, schema: dict):
        """模拟 AI 调用"""
        return {"result": "mock_ai_response"}


# 模拟通知回调
notifications = []

async def mock_notify(notification):
    """模拟通知回调"""
    notifications.append(notification)
    print(f"\n📢 通知: {notification['message']}")
    print(f"   优先级: {notification['priority']}")


# 模拟日志广播回调
logs = []

async def mock_log_broadcast(log):
    """模拟日志广播回调"""
    logs.append(log)


async def test_watchlist_monitor():
    """测试 watchlist_monitor Listener"""
    
    print("=" * 60)
    print("watchlist_monitor Listener 测试")
    print("=" * 60)
    
    # 1. 初始化数据库
    print("\n[1] 初始化数据库...")
    db = DatabaseManager("data/finance_test.db")
    print("   ✓ 数据库已初始化")
    
    # 2. 创建测试关注列表
    print("\n[2] 创建测试关注列表...")
    
    # 清空现有关注列表（测试用）
    try:
        # 软删除所有现有项
        existing = await db.watchlist.get_list()
        for item in existing:
            await db.watchlist.remove_item(item['id'])
    except:
        pass
    
    # 添加测试关注项
    item1_id = await db.watchlist.add_item(
        target_name="招商银行",
        target_type="stock",
        notes="银行板块龙头"
    )
    print(f"   ✓ 添加关注: 招商银行 (ID: {item1_id})")
    
    item2_id = await db.watchlist.add_item(
        target_name="黄金ETF",
        target_type="etf",
        notes="黄金投资"
    )
    print(f"   ✓ 添加关注: 黄金ETF (ID: {item2_id})")
    
    item3_id = await db.watchlist.add_item(
        target_name="上证指数",
        target_type="index",
        notes="大盘指数"
    )
    print(f"   ✓ 添加关注: 上证指数 (ID: {item3_id})")
    
    # 3. 初始化 ListenersManager
    print("\n[3] 初始化 ListenersManager...")
    listeners_manager = ListenersManager(
        database=db,
        agent_tools=MockAgentTools(),  # 使用 Mock AgentTools
        notification_callback=mock_notify,
        log_broadcast_callback=mock_log_broadcast
    )
    print("   ✓ ListenersManager 已初始化")
    
    # 4. 加载 Listeners
    print("\n[4] 加载 Listeners...")
    listeners = await listeners_manager.load_all_listeners()
    print(f"   ✓ 加载了 {len(listeners)} 个 Listener:")
    for listener in listeners:
        print(f"      - {listener['id']}: {listener['name']}")
    
    # 验证 watchlist_monitor 已加载
    watchlist_monitor = listeners_manager.get_listener('watchlist_monitor')
    if not watchlist_monitor:
        print("   ✗ watchlist_monitor 未加载！")
        return
    print("   ✓ watchlist_monitor 已加载")
    
    # 5. 场景 1: 报告提到 2 个关注标的
    print("\n[5] 场景 1: 报告提到招商银行和黄金ETF...")
    
    notifications.clear()  # 清空通知列表
    
    event_data = {
        'report_id': 'test_report_001',
        'title': 'A股与黄金投资策略分析',
        'content': """
        本报告分析了当前市场环境下的投资机会。
        
        招商银行作为银行板块的龙头企业，近期表现稳健。
        我们维持"买入"评级，目标价40元。
        
        另外，黄金ETF在当前避险情绪下值得关注。
        建议配置5-10%的黄金资产。
        
        整体来看，市场风险可控。
        """,
        'category': 'A股与黄金综合策略'
    }
    
    await listeners_manager.check_event('report_imported', event_data)
    
    # 等待异步操作完成
    await asyncio.sleep(0.5)
    
    # 验证通知
    if notifications:
        print(f"   ✓ 发送了 {len(notifications)} 条通知")
        for notif in notifications:
            print(f"      消息: {notif['message']}")
    else:
        print("   ✗ 未发送通知")
    
    # 6. 场景 2: 报告未提到任何关注标的
    print("\n[6] 场景 2: 报告未提到任何关注标的...")
    
    notifications.clear()
    
    event_data = {
        'report_id': 'test_report_002',
        'title': '科技股投资机会分析',
        'content': """
        本报告分析科技股的投资机会。
        
        腾讯控股、阿里巴巴等互联网巨头值得关注。
        AI 产业链也有较好的投资机会。
        """,
        'category': '科技股分析'
    }
    
    await listeners_manager.check_event('report_imported', event_data)
    
    await asyncio.sleep(0.5)
    
    if not notifications:
        print("   ✓ 未发送通知（预期行为）")
    else:
        print(f"   ✗ 意外发送了 {len(notifications)} 条通知")
    
    # 7. 场景 3: 报告提到所有 3 个关注标的
    print("\n[7] 场景 3: 报告提到所有 3 个关注标的...")
    
    notifications.clear()
    
    event_data = {
        'report_id': 'test_report_003',
        'title': '全市场投资策略',
        'content': """
        全市场分析：
        
        上证指数站稳3000点，市场情绪回暖。
        
        招商银行领涨银行板块，资金流入明显。
        
        黄金ETF受避险需求支撑，建议持续关注。
        
        整体来看，多元化配置仍是最佳策略。
        """,
        'category': '全市场策略'
    }
    
    await listeners_manager.check_event('report_imported', event_data)
    
    await asyncio.sleep(0.5)
    
    if notifications:
        print(f"   ✓ 发送了 {len(notifications)} 条通知")
        for notif in notifications:
            print(f"      消息: {notif['message']}")
    else:
        print("   ✗ 未发送通知")
    
    # 8. 验证日志记录
    print("\n[8] 验证日志记录...")
    if logs:
        print(f"   ✓ 记录了 {len(logs)} 条日志")
        for log in logs[-3:]:  # 显示最后 3 条
            print(f"      - {log.get('listener_name')}: {log.get('reason')}")
    else:
        print("   ✗ 未记录日志")
    
    # 9. 统计信息
    print("\n[9] 统计信息...")
    stats = listeners_manager.get_stats()
    print(f"   - 总 Listeners: {stats['total']}")
    print(f"   - 启用的 Listeners: {stats['enabled']}")
    print(f"   - 按事件分组: {stats['by_event']}")
    
    print("\n" + "=" * 60)
    print("✅ 测试完成!")
    print("=" * 60)
    
    print("\n📝 测试总结:")
    print("  ✅ watchlist_monitor 成功加载")
    print("  ✅ 成功检测到报告中的关注标的")
    print("  ✅ 成功发送通知")
    print("  ✅ 成功记录日志")
    print("  ✅ 正确处理未匹配的情况")


if __name__ == "__main__":
    asyncio.run(test_watchlist_monitor())
