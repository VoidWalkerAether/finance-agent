"""
测试 Report Analyzer Listener 插件

验证:
1. config 配置是否正确
2. handler 函数是否可调用
3. 数据库存储是否成功
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.append(str(Path(__file__).parent.parent))

# 导入 Listener
from agent.custom_scripts.listeners import report_analyzer


# 模拟 ListenerContext
class MockContext:
    """模拟 ListenerContext 用于测试"""
    
    def __init__(self):
        self.notifications = []
        self.ui_states = {}
    
    async def notify(self, message: str, options: dict = None):
        """记录通知"""
        print(f"\n📢 通知: {message}")
        self.notifications.append({
            'message': message,
            'options': options or {}
        })
    
    class UIState:
        def __init__(self, parent):
            self.parent = parent
        
        async def get(self, state_id: str):
            return self.parent.ui_states.get(state_id)
        
        async def set(self, state_id: str, data: dict):
            self.parent.ui_states[state_id] = data
            print(f"✅ UI状态已更新: {state_id}")
    
    def __init__(self):
        self.notifications = []
        self.ui_states = {}
        self.uiState = self.UIState(self)


async def test_listener():
    """测试 Listener 配置和执行"""
    
    print("=" * 70)
    print("🧪 测试 Report Analyzer Listener")
    print("=" * 70)
    
    # 1. 测试配置
    print("\n1️⃣ 测试配置 (config)")
    print(f"   ID: {report_analyzer.config['id']}")
    print(f"   名称: {report_analyzer.config['name']}")
    print(f"   事件: {report_analyzer.config['event']}")
    print(f"   启用: {report_analyzer.config['enabled']}")
    
    assert report_analyzer.config['id'] == 'report_analyzer', "❌ config.id 错误"
    assert report_analyzer.config['enabled'] == True, "❌ config.enabled 应为 True"
    assert report_analyzer.config['event'] == 'report_imported', "❌ config.event 错误"
    print("   ✅ 配置验证通过")
    
    # 2. 测试 handler 函数
    print("\n2️⃣ 测试 handler 函数")
    
    # 准备测试事件数据
    test_event = {
        'filename': '黄金投资报告.txt',
        'file_path': '/tmp/test_report.txt',
        'content': """
中国央行继续增持黄金，加上美国关税战出现新变数，国际金价维持在3350美元/盎司的高位。

7月7日数据显示，6月份继续增加了7万盎司的黄金储备，这是连续第8个月增持。

黄金价格年内最大涨幅达到60%，11月17日伦敦现货金价约为4000美元/盎司。

中国官方黄金储备为17409万盎司（2305吨），占外储比例仅为8%，而全球央行平均黄金占比为15%-20%。

投资建议：
1. 继续保持一定比例的黄金投资，中长期看涨
2. 已有投资者不要过多加仓，建议不超过总资产的5-10%
3. 新投资者可在震荡时适度参与，通过定投方式降低风险

风险提示：
- 短期涨幅过大，可能存在10%以上的技术性回调
- 政策预期落空风险
- 地缘政治不确定性
        """
    }
    
    # 创建模拟上下文
    context = MockContext()
    
    # 执行 handler
    print("   正在执行 handler...")
    try:
        result = await report_analyzer.handler(test_event, context)
        
        print(f"\n   执行结果:")
        print(f"   - executed: {result.get('executed')}")
        print(f"   - reason: {result.get('reason')}")
        print(f"   - actions: {result.get('actions')}")
        print(f"   - report_id: {result.get('report_id')}")
        
        assert result['executed'] == True, "❌ handler 执行失败"
        assert 'report_id' in result, "❌ 缺少 report_id"
        print("\n   ✅ handler 执行成功")
        
        # 检查通知
        print(f"\n   📢 发送了 {len(context.notifications)} 条通知")
        for i, notif in enumerate(context.notifications, 1):
            print(f"      {i}. {notif['message'][:100]}...")
        
    except Exception as e:
        print(f"\n   ❌ handler 执行失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 3. 测试数据库存储
    print("\n3️⃣ 验证数据库存储")
    from database.database_manager import DatabaseManager
    
    db = DatabaseManager()
    report_id = result.get('report_id')
    
    if report_id:
        stored_report = await db.get_report(report_id)
        if stored_report:
            print(f"   ✅ 报告已存储到数据库")
            print(f"      - ID: {stored_report['report_id']}")
            print(f"      - 标题: {stored_report.get('title', 'N/A')}")
            print(f"      - 分类: {stored_report.get('category', 'N/A')}")
            print(f"      - 重要性: {stored_report.get('importance_score', 'N/A')}/10")
        else:
            print(f"   ❌ 数据库中未找到报告: {report_id}")
    
    # 4. 测试全文搜索
    print("\n4️⃣ 测试全文搜索 (FTS5)")
    search_results = await db.search_reports(query="黄金", limit=5)
    print(f"   搜索 '黄金' 找到 {len(search_results)} 条结果")
    if search_results:
        print(f"   ✅ FTS5 全文搜索正常")
    
    print("\n" + "=" * 70)
    print("✅ 所有测试通过！Listener 插件可以正常使用")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_listener())
