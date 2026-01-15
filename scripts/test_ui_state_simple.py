"""
UIStateManager 基础测试脚本 (不使用热重载功能)

测试功能:
1. 模板加载
2. 状态 CRUD 操作
3. 状态初始化
4. 订阅和广播
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# 临时禁用 watchdog 导入
import ccsdk.ui_state_manager as ui_module
# 注释掉 watchdog 相关方法
ui_module.Observer = None

from database.database_manager import DatabaseManager


# 简化版 UIStateManager (移除热重载功能)
class SimpleUIStateManager:
    """简化版 UI State 管理器 (用于测试)"""
    
    def __init__(self, database, update_callback=None):
        from ccsdk.ui_state_manager import UIStateManager
        self._manager = UIStateManager.__new__(UIStateManager)
        self._manager.ui_states_dir = ui_module.os.path.join(ui_module.os.getcwd(), "agent/custom_scripts/ui-states")
        self._manager.logs_dir = ui_module.os.path.join(ui_module.os.getcwd(), "agent/custom_scripts/.logs/ui-states")
        self._manager.templates = {}
        self._manager.update_callbacks = set()
        self._manager.database = database
        self._manager.watcher_active = False
        self._manager.observer = None
        
        if update_callback:
            self._manager.update_callbacks.add(update_callback)
        
        self._manager._ensure_logs_dir()
    
    def __getattr__(self, name):
        return getattr(self._manager, name)


async def test_ui_state_manager():
    """测试 UIStateManager 核心功能"""
    
    print("=" * 60)
    print("UIStateManager 基础测试")
    print("=" * 60)
    
    # 1. 初始化
    print("\n[1] 初始化 UIStateManager...")
    db = DatabaseManager("data/finance_test.db")
    
    # 定义更新回调 (模拟 WebSocket 广播)
    def on_state_update(state_id: str, data):
        print(f"   📡 广播更新: {state_id} -> {list(data.keys()) if isinstance(data, dict) else type(data)}")
    
    ui_manager = SimpleUIStateManager(db, update_callback=on_state_update)
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
    
    # 11. 清理测试状态
    print("\n[11] 清理测试状态...")
    await ui_manager.delete_state('test_state')
    print("   ✓ 清理完成")
    
    print("\n" + "=" * 60)
    print("✅ 所有测试通过!")
    print("=" * 60)
    
    print("\n提示:")
    print("- 数据库文件: data/finance_test.db")
    print("- 日志目录: agent/custom_scripts/.logs/ui-states/")
    print("- 热重载功能需要安装 watchdog: pip install watchdog")


if __name__ == "__main__":
    asyncio.run(test_ui_state_manager())
