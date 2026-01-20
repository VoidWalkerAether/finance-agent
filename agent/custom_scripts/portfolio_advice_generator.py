"""
投资建议生成器
基于用户持仓 + 报告分析 + 投资原则，生成个性化投资建议
"""

import json
from typing import Dict, Any, List, Optional
from pathlib import Path
import sys

# 添加项目路径
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

# 导入 Schema
from database.schemas import (
    PortfolioSchemaV1,
    PrinciplesSchemaV1,
    principles_to_readable_text
)

# 导入 AI 客户端
try:
    from claude_agent_sdk import (
        AssistantMessage,
        TextBlock,
        query
    )
except ImportError:
    print("⚠️ 请先安装依赖: pip install claude-agent-sdk")
    raise


# ============================================================================
# 前置规则检查（不用 LLM，直接计算）
# ============================================================================

def check_principles_violations(
    portfolio: PortfolioSchemaV1,
    principles: PrinciplesSchemaV1
) -> List[Dict[str, Any]]:
    """
    检查当前持仓是否违反投资原则
    
    Args:
        portfolio: 用户持仓数据
        principles: 投资原则
        
    Returns:
        违规列表，每个元素包含 rule, status, details
    """
    violations = []
    wm = principles['weight_management']
    
    # 检查单一持仓权重
    for holding in portfolio['holdings']:
        if holding['market_value'] == 0:
            continue
        
        # 计算占比（字符串转浮点数）
        percentage_str = holding.get('percentage', '0%')
        percentage = float(percentage_str.strip('%')) / 100
        
        if percentage > wm['single_position_max_extreme']:
            violations.append({
                'rule': 'single_position_max_extreme',
                'status': 'violated',
                'details': f"{holding['name']} 占比 {percentage*100:.1f}% 超过极限 {wm['single_position_max_extreme']*100:.0f}%"
            })
        elif percentage > wm['single_position_max_normal']:
            violations.append({
                'rule': 'single_position_max_normal',
                'status': 'warning',
                'details': f"{holding['name']} 占比 {percentage*100:.1f}% 超过常规上限 {wm['single_position_max_normal']*100:.0f}%"
            })
    
    # 检查持仓数量
    non_zero_holdings = [h for h in portfolio['holdings'] if h['market_value'] > 0]
    holding_count = len(non_zero_holdings)
    
    if holding_count < wm['target_position_count_min']:
        violations.append({
            'rule': 'target_position_count_min',
            'status': 'violated',
            'details': f"当前持仓数量 {holding_count} 低于目标下限 {wm['target_position_count_min']}"
        })
    elif holding_count > wm['target_position_count_max']:
        violations.append({
            'rule': 'target_position_count_max',
            'status': 'warning',
            'details': f"当前持仓数量 {holding_count} 超过目标上限 {wm['target_position_count_max']}"
        })
    
    # 检查现金占比
    cash_ratio = portfolio['cash_position'] / portfolio['total_asset_value'] if portfolio['total_asset_value'] > 0 else 0
    
    if cash_ratio < 0.05:
        violations.append({
            'rule': 'liquidity',
            'status': 'warning',
            'details': f"现金占比 {cash_ratio*100:.1f}% 过低，流动性风险较高"
        })
    
    return violations


# ============================================================================
# Prompt 构造
# ============================================================================

def build_system_prompt() -> str:
    """构造系统 Prompt"""
    return """你是一位专业的私人财富管理顾问。你的任务是根据：
1. 最新的【市场策略报告】
2. 客户当前的【资产配置表】
3. 客户的【投资原则】

为客户生成个性化的操作建议。

你的建议必须：
- 具体、有逻辑支撑
- 严格基于报告内容和客户原则
- 不做过度发挥或主观臆测
- 当实际持仓与报告建议或客户原则冲突时，明确点出冲突并给出调整建议
- 所有仓位调整建议必须遵守客户的投资原则约束

输出格式必须是有效的 JSON，不要使用 Markdown 代码块包裹。"""


def build_user_prompt(
    report_analysis: Dict[str, Any],
    portfolio: PortfolioSchemaV1,
    principles: PrinciplesSchemaV1,
    pre_check_violations: List[Dict[str, Any]],
    history_reports: Optional[List[Dict[str, Any]]] = None
) -> str:
    """
    构造用户 Prompt
    
    Args:
        report_analysis: 报告分析 JSON
        portfolio: 用户持仓
        principles: 投资原则
        pre_check_violations: 前置规则检查结果
        history_reports: 历史报告（可选）
        
    Returns:
        完整的用户 Prompt
    """
    # 提取报告关键字段
    report_title = report_analysis.get('report_info', {}).get('title', '未知报告')
    investment_advice = report_analysis.get('investment_advice', {})
    investment_targets = report_analysis.get('investment_targets', {})
    risk_warnings = report_analysis.get('risk_warnings', [])
    
    # 转换投资原则为可读文本
    principles_text = principles_to_readable_text(principles)
    
    # 构造持仓摘要
    holdings_summary = []
    for h in portfolio['holdings']:
        if h['market_value'] > 0:
            holdings_summary.append(f"- {h['name']}（{h['category']}）：{h['percentage']}")
    
    cash_ratio = portfolio['cash_position'] / portfolio['total_asset_value'] if portfolio['total_asset_value'] > 0 else 0
    holdings_summary.append(f"- 现金：{cash_ratio*100:.1f}%")
    
    # 构造 Prompt
    parts = [
        "请分析以下数据并生成投资建议：",
        "",
        "=" * 60,
        "【1. 最新市场报告 - 关键数据】",
        f"报告标题: {report_title}",
        f"建议仓位: {investment_advice.get('target_allocation', 'N/A')}",
        f"操作建议: {investment_advice.get('action', 'N/A')}",
        f"时机建议: {investment_advice.get('timing', 'N/A')}",
        f"信心水平: {investment_advice.get('confidence_level', 'N/A')}",
        "",
        "推荐标的:",
    ]
    
    for target in investment_targets.get('recommended', [])[:5]:
        parts.append(f"  ✅ {target.get('name', 'N/A')}: {target.get('reason', '')}")
    
    parts.append("")
    parts.append("谨慎标的:")
    for target in investment_targets.get('cautious', [])[:3]:
        parts.append(f"  ⚠️ {target.get('name', 'N/A')}: {target.get('reason', '')}")
    
    parts.extend([
        "",
        "风险提示:",
    ])
    for risk in risk_warnings[:3]:
        if isinstance(risk, dict):
            parts.append(f"  🔸 {risk.get('risk_type', '风险')}: {risk.get('description', '')}")
    
    parts.extend([
        "",
        "=" * 60,
        "【2. 客户当前持仓】",
        f"总资产: {portfolio['total_asset_value']:,.0f} 元",
        f"现金: {portfolio['cash_position']:,.0f} 元 ({cash_ratio*100:.1f}%)",
        "",
        "持仓明细:",
        *holdings_summary,
        "",
        "=" * 60,
        "【3. 客户投资原则】",
        principles_text,
        "",
        "=" * 60,
        "【4. 前置规则检查结果】",
    ])
    
    if pre_check_violations:
        parts.append("⚠️ 检测到以下违规或预警：")
        for v in pre_check_violations:
            icon = "🔴" if v['status'] == 'violated' else "🟡"
            parts.append(f"{icon} {v['details']}")
    else:
        parts.append("✅ 当前持仓符合所有硬性约束")
    
    parts.extend([
        "",
        "=" * 60,
        "【请按以下 JSON 格式输出建议】：",
        "{",
        '  "rebalancing": {',
        '    "current_deviation": "描述当前配置与报告建议的偏差",',
        '    "suggestions": [',
        '      {',
        '        "asset_class": "资产类别（如：黄金/债券）",',
        '        "action": "increase/decrease/hold",',
        '        "from": 当前占比（小数，如 0.1）,',
        '        "to_range": [目标下限, 目标上限],',
        '        "reason": "调整理由"',
        '      }',
        '    ]',
        '  },',
        '  "actions": [',
        '    {',
        '      "name": "标的名称",',
        '      "current_status": "当前状态（如：持有10%、未持有）",',
        '      "advice": "buy/sell/hold/watch",',
        '      "priority": "high/medium/low",',
        '      "reason": "操作理由（基于报告和原则）"',
        '    }',
        '  ],',
        '  "timing_and_risks": {',
        '    "timing": ["时机建议1", "时机建议2"],',
        '    "risks": ["风险提示1", "风险提示2"],',
        '    "liquidity": "流动性建议"',
        '  },',
        '  "constraints_check": [',
        '    {',
        '      "rule": "原则名称",',
        '      "status": "satisfied/violated/warning",',
        '      "details": "检查结果说明"',
        '    }',
        '  ]',
        '}'
    ])
    
    return "\n".join(parts)


# ============================================================================
# AI 调用
# ============================================================================

async def call_ai_for_advice(system_prompt: str, user_prompt: str) -> Dict[str, Any]:
    """
    调用 LLM 生成投资建议
    
    Args:
        system_prompt: 系统提示词
        user_prompt: 用户提示词
        
    Returns:
        建议 JSON
    """
    messages = [
        AssistantMessage(role="user", content=[TextBlock(text=system_prompt + "\n\n" + user_prompt)])
    ]
    
    try:
        resp = await query(messages)
        
        # 提取文本内容
        if hasattr(resp, 'content') and len(resp.content) > 0:
            text_content = resp.content[0].text
        else:
            text_content = str(resp)
        
        # 尝试解析 JSON
        # 如果模型返回了 markdown 代码块，先去除
        text_content = text_content.strip()
        if text_content.startswith('```'):
            # 去除开头的 ```json 或 ```
            lines = text_content.split('\n')
            text_content = '\n'.join(lines[1:-1]) if len(lines) > 2 else text_content
        
        advice = json.loads(text_content)
        return advice
    
    except json.JSONDecodeError as e:
        print(f"❌ JSON 解析失败: {e}")
        print(f"原始响应: {text_content[:500]}...")
        return {
            'error': f'JSON 解析失败: {str(e)}',
            'raw_response': text_content[:1000]
        }
    except Exception as e:
        print(f"❌ AI 调用失败: {e}")
        return {
            'error': f'AI 调用失败: {str(e)}'
        }


# ============================================================================
# 核心函数
# ============================================================================

async def generate_portfolio_advice(
    portfolio: PortfolioSchemaV1,
    report_analysis: Dict[str, Any],
    principles: PrinciplesSchemaV1,
    history_reports: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    基于持仓、报告、原则生成个性化投资建议
    
    Args:
        portfolio: 用户持仓数据（PortfolioSchemaV1）
        report_analysis: 报告分析 JSON（dict）
        principles: 投资原则（PrinciplesSchemaV1）
        history_reports: 历史报告列表（可选）
        
    Returns:
        建议 JSON，结构：
        {
            'rebalancing': {...},
            'actions': [...],
            'timing_and_risks': {...},
            'constraints_check': [...]
        }
    """
    # 1. 前置规则检查
    pre_check_violations = check_principles_violations(portfolio, principles)
    
    # 2. 构造 Prompt
    system_prompt = build_system_prompt()
    user_prompt = build_user_prompt(
        report_analysis=report_analysis,
        portfolio=portfolio,
        principles=principles,
        pre_check_violations=pre_check_violations,
        history_reports=history_reports
    )
    
    # 3. 调用 LLM
    advice = await call_ai_for_advice(system_prompt, user_prompt)
    
    # 4. 附加前置检查结果（如果 LLM 没有返回或返回不完整）
    if 'constraints_check' not in advice or not advice['constraints_check']:
        advice['constraints_check'] = [
            {
                'rule': v['rule'],
                'status': v['status'],
                'details': v['details']
            }
            for v in pre_check_violations
        ]
    
    return advice


# ============================================================================
# 测试入口
# ============================================================================

async def main():
    """测试函数"""
    from database.schemas import DEFAULT_PORTFOLIO, DEFAULT_PRINCIPLES
    
    # 构造测试数据
    test_portfolio = DEFAULT_PORTFOLIO.copy()
    test_portfolio['total_asset_value'] = 1000000
    test_portfolio['cash_position'] = 50000
    test_portfolio['holdings'] = [
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
        }
    ]
    
    # 测试报告
    test_report = {
        'report_info': {
            'title': 'A股4000点拉锯与黄金见顶辨析'
        },
        'investment_advice': {
            'target_allocation': '黄金/债券20%-30%，港股跨境20%，A股高端制造与红利股30%-40%，现金<10%',
            'action': 'watch',
            'timing': '12月会议政策落地前逢低分批布局',
            'confidence_level': 'medium'
        },
        'investment_targets': {
            'recommended': [
                {'name': '恒生互联网科技业ETF', 'reason': '估值低、政策受益'}
            ],
            'cautious': [
                {'name': '中证A500 ETF', 'reason': '宽基承压'}
            ]
        },
        'risk_warnings': [
            {'risk_type': '流动性风险', 'description': '年末资金紧张'}
        ]
    }
    
    test_principles = DEFAULT_PRINCIPLES.copy()
    
    # 生成建议
    advice = await generate_portfolio_advice(
        portfolio=test_portfolio,
        report_analysis=test_report,
        principles=test_principles
    )
    
    print(json.dumps(advice, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
