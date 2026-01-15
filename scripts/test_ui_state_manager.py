"""
UIStateManager 测试脚本

测试功能:
1. 模板加载
2. 状态 CRUD 操作
3. 状态初始化
4. 订阅和广播
5. 日志记录
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from ccsdk.ui_state_manager import UIStateManager
from database.database_manager import DatabaseManager


async def test_ui_state_manager():
    """测试 UIStateManager 所有功能"""
    
    print("=" * 60)
    print("UIStateManager 测试")
    print("=" * 60)
    
    # 1. 初始化
    print("\n[1] 初始化 UIStateManager...")
    db = DatabaseManager("data/finance_test.db")
    
    # 定义更新回调 (模拟 WebSocket 广播)
    def on_state_update(state_id: str, data):
        print(f"   📡 广播更新: {state_id} -> {list(data.keys()) if isinstance(data, dict) else type(data)}")
    
    ui_manager = UIStateManager(db, update_callback=on_state_update)
    print("   ✓ UIStateManager 初始化成功")
    
    # 2. 加载模板
    print("\n[2] 加载 UI State 模板...")
    templates = await ui_manager.load_all_templates()
    print(f"   ✓ 加载了 {len(templates)} 个模板:")
    for template in templates:
        print(f"     - {template.id}: {template.name}")
    
    # 3. 测试状态初始化
    print("\n[3] 测试状态初始化...")
    initialized = await ui_manager.initialize_state_if_needed('financial_dashboard')
    if initialized:
        print("   ✓ 首次初始化成功")
    else:
        print("   ✓ 状态已存在,无需初始化")
    
    # 4. 获取状态
    print("\n[4] 获取状态...")
    dashboard_state = await ui_manager.get_state('financial_dashboard')
    if dashboard_state:
        print(f"   ✓ 获取成功: {list(dashboard_state.keys())}")
        print(f"     - recent_reports: {len(dashboard_state.get('recent_reports', []))} 条")
        print(f"     - statistics: {dashboard_state.get('statistics', {})}")
    else:
        print("   ✗ 状态不存在")
    
    # 5. 更新状态
    print("\n[5] 更新状态...")
    if dashboard_state:
        # 添加一条报告到 recent_reports
        dashboard_state['recent_reports'].append({
            'report_id': 'test_report_001',
            'title': '测试报告 - A股与黄金策略',
            'category': '综合',
            'importance_score': 8,
            'date': '2025-01-06'
        })
        
        # 更新统计信息
        dashboard_state['statistics']['total_reports'] = 1
        dashboard_state['statistics']['bullish_reports'] = 1
        
        await ui_manager.set_state('financial_dashboard', dashboard_state)
        print("   ✓ 状态更新成功")
    
    # 6. 验证更新
    print("\n[6] 验证更新...")
    updated_state = await ui_manager.get_state('financial_dashboard')
    if updated_state:
        recent_count = len(updated_state.get('recent_reports', []))
        total_reports = updated_state.get('statistics', {}).get('total_reports', 0)
        print(f"   ✓ 验证成功:")
        print(f"     - recent_reports: {recent_count} 条")
        print(f"     - total_reports: {total_reports}")
    
    # 7. 测试 price_alerts 状态
    print("\n[7] 测试 price_alerts 状态...")
    alerts_state = await ui_manager.get_state('price_alerts')
    if alerts_state is None:
        await ui_manager.initialize_state_if_needed('price_alerts')
        alerts_state = await ui_manager.get_state('price_alerts')
    
    if alerts_state:
        # 添加价格提醒
        alerts_state['alerts'].append({
            'id': 'alert_001',
            'symbol': 'SGE黄金9999',
            'target_price': 3850,
            'condition': '<=',
            'status': 'active',
            'created_at': '2025-01-06T10:30:00Z'
        })
        alerts_state['stats']['total_active'] = 1
        
        await ui_manager.set_state('price_alerts', alerts_state)
        print(f"   ✓ 价格提醒状态更新成功")
    
    # 8. 列出所有状态
    print("\n[8] 列出所有状态...")
    all_states = await ui_manager.list_states()
    print(f"   ✓ 共 {len(all_states)} 个状态:")
    for state_info in all_states:
        print(f"     - {state_info['stateId']}: {state_info['updatedAt']}")
    
    # 9. 订阅测试
    print("\n[9] 测试订阅机制...")
    
    update_received = []
    
    def custom_callback(state_id: str, data):
        update_received.append(state_id)
        print(f"   📢 自定义回调收到更新: {state_id}")
    
    unsubscribe = ui_manager.on_state_update(custom_callback)
    
    # 触发更新
    test_state = {'test': 'data'}
    await ui_manager.set_state('test_state', test_state)
    
    if 'test_state' in update_received:
        print("   ✓ 订阅机制正常工作")
    
    # 取消订阅
    unsubscribe()
    print("   ✓ 取消订阅成功")
    
    # 10. 获取统计信息
    print("\n[10] 获取统计信息...")
    stats = ui_manager.get_stats()
    print(f"   ✓ 统计信息:")
    print(f"     - total_templates: {stats['total_templates']}")
    print(f"     - template_ids: {stats['template_ids']}")
    print(f"     - watching: {stats['watching']}")
    
    # 11. 清理测试状态
    print("\n[11] 清理测试状态...")
    await ui_manager.delete_state('test_state')
    print("   ✓ 清理完成")
    
    print("\n" + "=" * 60)
    print("✅ 所有测试通过!")
    print("=" * 60)


async def test_hot_reload():
    """测试热重载功能"""
    print("\n" + "=" * 60)
    print("热重载测试 (手动测试)")
    print("=" * 60)
    print("\n提示:")
    print("1. 修改 agent/custom_scripts/ui-states/ 下的任意 .py 文件")
    print("2. 观察控制台输出,查看是否自动重新加载")
    print("3. 按 Ctrl+C 停止监听\n")
    
    db = DatabaseManager("data/finance_test.db")
    ui_manager = UIStateManager(db)
    
    await ui_manager.load_all_templates()
    
    async def on_templates_changed(templates):
        print(f"\n🔄 模板已重新加载! 共 {len(templates)} 个:")
        for t in templates:
            print(f"   - {t.id}: {t.name}")
    
    await ui_manager.watch_templates(on_templates_changed)
    
    try:
        # 保持运行,等待文件变化
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\n\n停止监听...")
        ui_manager.stop_watching()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="UIStateManager 测试")
    parser.add_argument(
        '--hot-reload',
        action='store_true',
        help='测试热重载功能 (需手动修改文件)'
    )
    
    args = parser.parse_args()
    
    if args.hot_reload:
        asyncio.run(test_hot_reload())
    else:
        asyncio.run(test_ui_state_manager())
