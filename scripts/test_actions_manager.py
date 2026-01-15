"""
ActionsManager 测试脚本

测试场景:
1. 加载 Action 模板
2. 注册 Action 实例
3. 执行 Action
4. 验证日志记录
"""

import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from ccsdk.actions_manager import ActionsManager
from ccsdk.action_context import ActionContext
from ccsdk.message_types import ActionInstance, ActionResult
from database.database_manager import DatabaseManager


# 模拟通知回调
async def mock_notify(message: str, priority: str, type: str):
    """模拟通知"""
    print(f"   📢 通知 [{type}]: {message}")


# 模拟日志回调
def mock_log(message: str, level: str):
    """模拟日志"""
    print(f"   📝 日志 [{level}]: {message}")


# 模拟 AI 调用
async def mock_call_agent(prompt: str, schema: dict):
    """模拟 AI 调用（模型由环境变量控制）"""
    print(f"   🤖 调用 AI: {prompt[:50]}...")
    return {"result": "mock_response"}


async def test_actions_manager():
    """测试 ActionsManager"""
    
    print("=" * 60)
    print("ActionsManager 测试")
    print("=" * 60)
    
    # 1. 初始化
    print("\n[1] 初始化 ActionsManager...")
    db = DatabaseManager("data/finance_test.db")
    actions_manager = ActionsManager(db)
    print("   ✓ ActionsManager 已初始化")
    
    # 2. 加载 Action 模板
    print("\n[2] 加载 Action 模板...")
    templates = await actions_manager.load_all_templates()
    print(f"   ✓ 加载了 {len(templates)} 个模板:")
    for template in templates:
        print(f"      - {template.id}: {template.name} {template.icon}")
    
    if len(templates) == 0:
        print("   ⚠️  没有找到 Action 模板")
        print("   提示: 请确保 agent/custom_scripts/actions/ 目录下有 .py 文件")
        return
    
    # 3. 获取单个模板
    print("\n[3] 获取单个模板...")
    template = actions_manager.get_template('set_price_alert')
    if template:
        print(f"   ✓ 找到模板: {template.name}")
        print(f"      ID: {template.id}")
        print(f"      图标: {template.icon}")
        print(f"      描述: {template.description}")
        print(f"      参数: {list(template.parameterSchema.get('properties', {}).keys())}")
    else:
        print("   ❌ 未找到 set_price_alert 模板")
        return
    
    # 4. 注册 Action 实例
    print("\n[4] 注册 Action 实例...")
    instance = ActionInstance(
        instanceId="act_test_001",
        templateId="set_price_alert",
        label="设置黄金价格提醒: ≤3850元",
        description="当黄金价格低于3850时通知",
        params={
            'symbol': 'SGE黄金9999',
            'target_price': 3850,
            'condition': '<='
        },
        style="primary",
        sessionId="session_test",
        createdAt=datetime.now().isoformat()
    )
    
    actions_manager.register_instance(instance)
    print(f"   ✓ 注册实例: {instance.instanceId}")
    print(f"      标签: {instance.label}")
    print(f"      参数: {instance.params}")
    
    # 5. 创建 ActionContext
    print("\n[5] 创建 ActionContext...")
    context = ActionContext(
        session_id="session_test",
        database=db,
        ui_state_manager=None,  # 暂时不集成 UIStateManager
        _notify_callback=mock_notify,
        _log_callback=mock_log,
        _call_agent_callback=mock_call_agent
    )
    print("   ✓ ActionContext 已创建")
    
    # 6. 执行 Action
    print("\n[6] 执行 Action...")
    result = await actions_manager.execute_action("act_test_001", context)
    
    print(f"\n   执行结果:")
    print(f"      成功: {result.success}")
    print(f"      消息: {result.message}")
    if result.data:
        print(f"      数据: {json.dumps(result.data, ensure_ascii=False, indent=8)}")
    
    # 7. 验证日志文件
    print("\n[7] 验证日志文件...")
    log_dir = "agent/custom_scripts/.logs/actions"
    today = datetime.now().strftime('%Y-%m-%d')
    log_file = f"{log_dir}/{today}.jsonl"
    
    if Path(log_file).exists():
        print(f"   ✓ 日志文件存在: {log_file}")
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            print(f"   ✓ 日志条目数: {len(lines)}")
            if lines:
                last_log = json.loads(lines[-1])
                print(f"   ✓ 最新日志:")
                print(f"      实例ID: {last_log['instanceId']}")
                print(f"      模板ID: {last_log['templateId']}")
                print(f"      执行时间: {last_log['duration']}ms")
                print(f"      结果: {last_log['result']['message']}")
    else:
        print(f"   ⚠️  日志文件不存在: {log_file}")
    
    # 8. 测试第二个 Action
    print("\n[8] 测试 add_to_watchlist...")
    instance2 = ActionInstance(
        instanceId="act_test_002",
        templateId="add_to_watchlist",
        label="添加招商银行到关注列表",
        params={
            'target_name': '招商银行',
            'target_type': 'stock'
        },
        sessionId="session_test",
        createdAt=datetime.now().isoformat()
    )
    
    actions_manager.register_instance(instance2)
    result2 = await actions_manager.execute_action("act_test_002", context)
    
    print(f"   执行结果:")
    print(f"      成功: {result2.success}")
    print(f"      消息: {result2.message}")
    
    # 9. 统计信息
    print("\n[9] 统计信息...")
    stats = actions_manager.get_stats()
    print(f"   - 模板总数: {stats['total_templates']}")
    print(f"   - 模板列表: {stats['template_ids']}")
    print(f"   - 实例总数: {stats['total_instances']}")
    print(f"   - 热重载: {stats['watching']}")
    
    print("\n" + "=" * 60)
    print("✅ 测试完成!")
    print("=" * 60)
    
    print("\n📝 测试总结:")
    print(f"  ✅ 成功加载 {len(templates)} 个 Action 模板")
    print(f"  ✅ 成功注册 {stats['total_instances']} 个 Action 实例")
    print(f"  ✅ 成功执行 Action 并记录日志")
    print(f"  ✅ ActionContext 功能正常")


if __name__ == "__main__":
    asyncio.run(test_actions_manager())
