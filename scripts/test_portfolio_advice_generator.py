"""
测试投资建议生成器
端到端测试：持仓 + 报告 + 原则 → 生成建议
"""

import asyncio
import json
import sys
from pathlib import Path

# 添加项目路径
sys.path.append(str(Path(__file__).parent.parent))

from database.database_manager import DatabaseManager
from agent.custom_scripts.portfolio_advice_generator import generate_portfolio_advice


async def main():
    """端到端测试"""
    print("=" * 60)
    print("投资建议生成器 - 端到端测试")
    print("=" * 60)
    
    db = DatabaseManager("data/finance.db")
    
    # 1. 加载测试持仓
    print("\n【1/4】加载用户持仓...")
    portfolio = await db.portfolio.get_or_create_default_portfolio('default')
    
    # 如果没有持仓数据，创建测试数据
    if portfolio['total_asset_value'] == 0:
        print("   ⚠️ 未找到持仓数据，创建测试数据...")
        portfolio = {
            'total_asset_value': 1000000,
            'cash_position': 50000,
            'holdings': [
                {
                    'name': '沪深300 ETF',
                    'category': 'A股宽基',
                    'market_value': 500000,
                    'percentage': '50%'
                },
                {
                    'name': 'SGE黄金9999 ETF',
                    'category': '商品/黄金',
                    'market_value': 100000,
                    'percentage': '10%'
                },
                {
                    'name': '恒生互联网科技业ETF',
                    'category': '港股/跨境',
                    'market_value': 0,
                    'percentage': '0%',
                    'note': '关注但未买入'
                }
            ]
        }
    
    print(f"   ✅ 持仓加载完成")
    print(f"      总资产: {portfolio['total_asset_value']:,.0f} 元")
    print(f"      现金: {portfolio['cash_position']:,.0f} 元")
    print(f"      持仓数量: {len([h for h in portfolio['holdings'] if h['market_value'] > 0])} 个")
    
    # 2. 加载报告分析
    print("\n【2/4】加载报告分析...")
    
    # 方式1：从文件加载
    report_file = Path(__file__).parent.parent / "report" / "analysis_A股与黄金综合策略.json"
    if report_file.exists():
        with open(report_file, 'r', encoding='utf-8') as f:
            report_analysis = json.load(f)
        print(f"   ✅ 从文件加载报告: {report_analysis.get('report_info', {}).get('title', '未知')}")
    else:
        # 方式2：从数据库加载最新报告
        reports = await db.search_reports(limit=1, order_by='date_published DESC')
        if reports:
            report_analysis = json.loads(reports[0]['analysis_json'])
            print(f"   ✅ 从数据库加载报告: {reports[0]['title']}")
        else:
            print("   ❌ 未找到报告数据")
            return
    
    # 3. 加载投资原则
    print("\n【3/4】加载投资原则...")
    principles = await db.principles.get_active_principles('default')
    print(f"   ✅ 投资原则加载完成")
    print(f"      档案名称: {principles['profile_name']}")
    print(f"      单一品种上限: {principles['weight_management']['single_position_max_normal']*100:.0f}%")
    
    # 4. 生成投资建议
    print("\n【4/4】生成投资建议...")
    print("   🤖 正在调用 LLM...")
    
    advice = await generate_portfolio_advice(
        portfolio=portfolio,
        report_analysis=report_analysis,
        principles=principles
    )
    
    if 'error' in advice:
        print(f"   ❌ 生成失败: {advice['error']}")
        if 'raw_response' in advice:
            print(f"\n原始响应:\n{advice['raw_response']}")
        return
    
    print("   ✅ 建议生成完成\n")
    
    # 5. 输出结果
    print("=" * 60)
    print("📊 投资建议结果")
    print("=" * 60)
    
    # 整体仓位调整
    if 'rebalancing' in advice:
        print("\n【整体仓位调整】")
        print(f"当前偏差: {advice['rebalancing'].get('current_deviation', 'N/A')}")
        if advice['rebalancing'].get('suggestions'):
            print("\n调整建议:")
            for sug in advice['rebalancing']['suggestions']:
                print(f"  • {sug.get('asset_class', 'N/A')}: {sug.get('action', 'N/A')}")
                print(f"    从 {sug.get('from', 0)*100:.1f}% → {sug.get('to_range', [0,0])[0]*100:.0f}%-{sug.get('to_range', [0,0])[1]*100:.0f}%")
                print(f"    理由: {sug.get('reason', 'N/A')}")
    
    # 标的操作清单
    if 'actions' in advice:
        print("\n【标的操作清单】")
        for action in advice['actions']:
            priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(action.get('priority', 'medium'), "⚪")
            print(f"{priority_icon} {action.get('name', 'N/A')} - {action.get('advice', 'N/A').upper()}")
            print(f"   当前: {action.get('current_status', 'N/A')}")
            print(f"   理由: {action.get('reason', 'N/A')}")
    
    # 时机与风险
    if 'timing_and_risks' in advice:
        print("\n【时机与风险】")
        tar = advice['timing_and_risks']
        if tar.get('timing'):
            print("时机建议:")
            for t in tar['timing']:
                print(f"  • {t}")
        if tar.get('risks'):
            print("风险提示:")
            for r in tar['risks']:
                print(f"  ⚠️ {r}")
        if tar.get('liquidity'):
            print(f"流动性: {tar['liquidity']}")
    
    # 原则检查
    if 'constraints_check' in advice:
        print("\n【原则检查】")
        for check in advice['constraints_check']:
            status_icon = {
                'satisfied': '✅',
                'violated': '🔴',
                'warning': '🟡'
            }.get(check.get('status', 'satisfied'), '⚪')
            print(f"{status_icon} {check.get('rule', 'N/A')}: {check.get('details', 'N/A')}")
    
    # 保存完整 JSON
    output_file = Path(__file__).parent.parent / "data" / "latest_advice.json"
    output_file.parent.mkdir(exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(advice, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 完整建议已保存到: {output_file}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
