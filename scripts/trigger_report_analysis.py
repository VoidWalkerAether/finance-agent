"""
触发报告分析 Listener 的示例脚本

演示如何通过事件触发 report_analyzer Listener
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.append(str(Path(__file__).parent.parent))

# 加载环境变量
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
    print(f"[DEBUG] 已加载环境变量文件: {env_path}")

from agent.custom_scripts.listeners import report_analyzer


# 模拟 ListenerContext
class SimpleContext:
    """简单的 ListenerContext 实现"""
    
    async def notify(self, message: str, options: dict = None):
        priority = options.get('priority', 'normal') if options else 'normal'
        icon = "🔴" if priority == "high" else "🟡" if priority == "medium" else "🟢"
        print(f"\n{icon} 【通知】 {message}\n")
    
    class UIState:
        async def get(self, state_id: str):
            return None  # 简化实现
        
        async def set(self, state_id: str, data: dict):
            print(f"✅ UI状态已更新: {state_id}")
    
    def __init__(self):
        self.uiState = self.UIState()


async def trigger_analysis(report_file: str = None):
    """
    触发报告分析
    
    Args:
        report_file: 报告文件路径（可选，如果未提供则使用示例）
    """
    print("=" * 70)
    print("🚀 触发金融报告分析 Listener")
    print("=" * 70)
    
    # 准备事件数据
    if report_file and Path(report_file).exists():
        with open(report_file, 'r', encoding='utf-8') as f:
            content = f.read()
        filename = Path(report_file).name
        file_path = str(Path(report_file).absolute())
    else:
        # 使用示例报告
        filename = "A股与黄金综合策略分析.txt"
        file_path = None
        content = """
A股4000点拉锯与黄金见顶辨析

【核心观点】
A股不大概率止步于4000点，当前围绕4000点的拉锯属年末上涨后的正常调整与流动性阶段性偏紧。四大关键因子（政策、宏观、资金、基本面）未转向利空，上市公司三季报营收、净利双升构成中长期支撑。

【市场数据】
- 上证指数自2024年9月24日起累计上涨约45%
- A股三季报营收增速5%以上，净利润增速11%以上
- 全市场ETF规模年内增幅56%，股票ETF占比从80%降至66%
- 黄金年内最高涨幅60%+，11月中旬回落至4000美元/盎司仍上涨45%左右
- 中国官方黄金储备2305吨，占外储仅8%，全球央行平均15%-20%

【资金流向分析】
ETF资金流向显示市场正构建"防御+跨境低估值"新均衡：
- 减配：沪深300、中证A500宽基指数
- 增配：黄金、债券、恒生科技、港股互联网
- 机器人产业指数ETF年净流入超500亿元
- 债券类ETF年内净流入超5000亿元
- 恒生科技、港股互联网近一月合计净流入540亿元

【黄金分析】
黄金短期过热存在技术回调，但四大逻辑未变：
1. 央行储备需求持续（中国储备占比仅8%，距全球均值有缺口）
2. 居民配置提升趋势
3. 地缘避险需求
4. 美元降息预期（2026年美联储进一步降息或驱动金价新一轮上涨）

【投资建议】
操作策略：watch
配置比例：防御与进攻平衡
- 黄金/债券：20%-30%
- 港股跨境：20%
- A股高端制造与红利股：30%-40%
- 现金：<10%

时机建议：12月中央经济工作会议政策落地前逢低分批布局，黄金回调至3800-3900美元区间再考虑加仓

持有期：中期（6-12个月）

信心水平：medium

【推荐标的】
1. 恒生互联网科技业ETF
   - 理由：估值低、政策受益、资金周度净流入>16亿元
   - 表现：随港股企稳反弹

2. SGE黄金9999 ETF
   - 理由：央行持续购金+居民配置提升，回调后布局
   - 表现：年内涨幅仍约45%

3. 机器人产业指数ETF
   - 理由："十五五"高端制造重点方向，年净流入>500亿元
   - 表现：前期涨幅高、近期回调

【风险提示】
1. 流动性风险（medium）
   - 年末市场资金季节性紧张，宽基指数波动放大
   - 影响标的：沪深300、中证A500、创业板

2. 政策预期落空（high）
   - 年底中央经济工作会议政策力度若低于预期，市场或二次探底
   - 影响标的：全市场

3. 黄金短期回调（medium）
   - 年内涨幅过大，投机资金获利了结可能引发10%以上调整
   - 影响标的：黄金ETF、黄金股

【关键时间节点】
- 2024-09-24：本轮A股牛市起点
- 2025-10-31：上证指数突破4000点
- 2025-11-14：全球市场情绪转谨慎
- 2025-12：中央经济工作会议（政策定调）
- 2026：美联储有望继续降息

【重要性评分】
重要性：9/10
紧急性：8/10
可靠性：9/10
        """
    
    print(f"\n📄 报告信息:")
    print(f"   文件名: {filename}")
    print(f"   内容长度: {len(content)} 字符")
    if file_path:
        print(f"   文件路径: {file_path}")
    
    # 构建事件数据
    event_data = {
        'filename': filename,
        'content': content,
        'file_path': file_path
    }
    
    # 创建上下文
    context = SimpleContext()
    
    # 执行 Listener handler
    print(f"\n⏳ 正在调用 Listener handler...")
    print(f"   Listener ID: {report_analyzer.config['id']}")
    print(f"   Listener 名称: {report_analyzer.config['name']}")
    
    try:
        result = await report_analyzer.handler(event_data, context)
        
        print(f"\n✅ 执行完成!")
        print(f"\n📊 执行结果:")
        print(f"   - 是否执行: {result.get('executed')}")
        print(f"   - 执行原因: {result.get('reason')}")
        print(f"   - 报告ID: {result.get('report_id')}")
        
        if result.get('actions'):
            print(f"   - 执行动作:")
            for action in result['actions']:
                print(f"      • {action}")
        
        if result.get('importance_score'):
            print(f"   - 重要性评分: {result['importance_score']}/10")
        
        # 查询数据库验证
        if result.get('report_id'):
            from database.database_manager import DatabaseManager
            db = DatabaseManager()
            
            print(f"\n🔍 数据库验证:")
            report = await db.get_report(result['report_id'])
            if report:
                print(f"   ✅ 报告已成功存储到数据库")
                print(f"      - 标题: {report.get('title', 'N/A')}")
                print(f"      - 分类: {report.get('category', 'N/A')}")
                print(f"      - 情绪: {report.get('sentiment', 'N/A')}")
                print(f"      - 投资建议: {report.get('action', 'N/A')}")
            else:
                print(f"   ❌ 数据库中未找到报告")
        
    except Exception as e:
        print(f"\n❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 70)


async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="触发报告分析 Listener")
    parser.add_argument('--file', '-f', help='报告文件路径')
    args = parser.parse_args()
    
    await trigger_analysis(args.file)


if __name__ == "__main__":
    asyncio.run(main())
