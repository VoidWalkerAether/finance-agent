"""
投资建议生成器
基于用户持仓 + 报告分析 + 投资原则，生成个性化投资建议
"""

import json
from typing import Dict, Any, List, Optional
from pathlib import Path
import sys

# 强制无缓冲输出（确保 print 日志立即显示）
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# 添加项目路径
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

# 导入 Schema
from database.schemas import (
    PortfolioSchemaV1,
    PrinciplesSchemaV1,
    principles_to_readable_text
)

# 导入 AIClient（正确的调用方式）
from ccsdk.ai_client import AIClient, AIQueryOptions


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

重要：JSON 格式要求：
1. 输出格式必须是有效的 JSON，不要使用 Markdown 代码块包裹
2. 字符串中如果包含双引号，必须转义为 \" （例如：\"十五五\"）
3. 避免使用行内注释（//）
4. 确保所有字符串正确闭合"""


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
    
    final_prompt = "\n".join(parts)
    
    # 打印最终发送给 LLM 的 Prompt
    print("\n" + "=" * 80, flush=True)
    print("📝 [最终 Prompt] 即将发送给 LLM 的完整内容：", flush=True)
    print("=" * 80, flush=True)
    print(final_prompt, flush=True)
    print("=" * 80, flush=True)
    print(f"📊 Prompt 统计：", flush=True)
    print(f"   - 总字符数: {len(final_prompt)}", flush=True)
    print(f"   - 总行数: {len(final_prompt.split(chr(10)))}", flush=True)
    print(f"   - 持仓数据：总资产 {portfolio['total_asset_value']:,.0f} 元，现金 {portfolio['cash_position']:,.0f} 元", flush=True)
    print(f"   - 持仓明细数: {len([h for h in portfolio['holdings'] if h['market_value'] > 0])} 个", flush=True)
    print("=" * 80 + "\n", flush=True)
    
    return final_prompt


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
    try:
        # 使用 AIClient.query_single() 方法（参考 ai_client.py:540-576）
        client = AIClient(
            options=AIQueryOptions(
                system_prompt=system_prompt,
                max_turns=10  # 投资建议生成不需要多轮对话
            )
        )
        
        # 调用 query_single
        result = await client.query_single(user_prompt)
        
        # 提取 assistant 消息的文本内容
        text_content = ""
        for message in result['messages']:
            if message.type == "assistant":
                # content 可能是字符串或列表
                if isinstance(message.content, str):
                    text_content += message.content
                elif isinstance(message.content, list):
                    for block in message.content:
                        if isinstance(block, dict) and block.get('type') == 'text':
                            text_content += block.get('text', '')
        
        if not text_content:
            return {
                'error': 'LLM 未返回有效内容',
                'raw_response': str(result)
            }
        
        # 打印完整的原始响应（调试用）
        print("\n" + "=" * 80, flush=True)
        print("📥 [LLM 原始响应] 完整内容：", flush=True)
        print("=" * 80, flush=True)
        print(text_content, flush=True)
        print("=" * 80, flush=True)
        print(f"📊 响应统计：", flush=True)
        print(f"   - 字符数: {len(text_content)}", flush=True)
        print(f"   - 行数: {len(text_content.split(chr(10)))}", flush=True)
        print("=" * 80 + "\n", flush=True)
        
        # 尝试解析 JSON
        # 如果模型返回了 markdown 代码块，先去除
        text_content = text_content.strip()
        if text_content.startswith('```'):
            # 去除开头的 ```json 或 ```
            lines = text_content.split('\n')
            text_content = '\n'.join(lines[1:-1]) if len(lines) > 2 else text_content
            # 去除结尾的 ```
            if text_content.endswith('```'):
                text_content = text_content[:-3].strip()
        
        # 保存原始 JSON 用于调试
        json_for_debug = text_content
        
        try:
            advice = json.loads(text_content)
            print("✅ JSON 解析成功", flush=True)
            return advice
        except json.JSONDecodeError as parse_error:
            # JSON 解析失败，尝试修复常见问题
            print(f"⚠️ 首次 JSON 解析失败: {parse_error}", flush=True)
            print(f"   错误位置: line {parse_error.lineno}, column {parse_error.colno}", flush=True)
            
            # 修复策略 1: 移除行尾注释
            lines = text_content.split('\n')
            cleaned_lines = []
            for line in lines:
                # 移除行尾注释（但保留字符串内的 //）
                if '//' in line and '"' not in line.split('//')[0]:
                    line = line.split('//')[0]
                cleaned_lines.append(line)
            text_content_v1 = '\n'.join(cleaned_lines)
            
            try:
                advice = json.loads(text_content_v1)
                print("✅ JSON 解析成功（移除注释后）", flush=True)
                return advice
            except json.JSONDecodeError:
                pass
            
            # 修复策略 2: 修复未转义的引号
            # 在 JSON 字符串内的引号应该转义为 \"
            import re
            
            # 找到所有 "key": "value" 的模式，修复 value 中未转义的引号
            def fix_quotes_in_json_string(text):
                # 匹配 JSON 字符串值（类似 "key": "value"）
                def replace_unescaped_quotes(match):
                    key = match.group(1)
                    value = match.group(2)
                    # 在 value 中查找未转义的引号
                    # 先保护已经转义的 \"
                    value = value.replace('\\"', '【ESCAPED_QUOTE】')
                    # 把未转义的 " 替换为 \"
                    value = value.replace('"', '\\"')
                    # 恢复已转义的
                    value = value.replace('【ESCAPED_QUOTE】', '\\"')
                    return f'"{key}": "{value}"'
                
                # 匹配模式："key": "value"
                pattern = r'"([^"]+)"\s*:\s*"([^"]*?)"'
                return re.sub(pattern, replace_unescaped_quotes, text)
            
            try:
                text_content_v2 = fix_quotes_in_json_string(text_content_v1)
                advice = json.loads(text_content_v2)
                print("✅ JSON 解析成功（修复引号后）", flush=True)
                return advice
            except Exception as e:
                print(f"❌ JSON 修复失败: {e}", flush=True)
                # 仍然失败，返回详细错误
                raise parse_error
    
    except json.JSONDecodeError as e:
        print(f"❌ JSON 解析失败: {e}")
        
        # 显示错误位置附近的内容
        if 'text_content' in locals() and e.lineno and e.colno:
            lines = text_content.split('\n')
            error_line_idx = e.lineno - 1
            
            print(f"\n❌ 错误位置周围的内容：")
            start_line = max(0, error_line_idx - 2)
            end_line = min(len(lines), error_line_idx + 3)
            
            for i in range(start_line, end_line):
                prefix = ">>> " if i == error_line_idx else "    "
                print(f"{prefix}Line {i+1}: {lines[i]}")
            
            if error_line_idx < len(lines):
                error_line = lines[error_line_idx]
                print(f"\n错误列指示: {' ' * (e.colno - 1)}^")
        
        # 保存完整响应到文件供分析
        if 'text_content' in locals():
            error_file = Path(__file__).parent.parent.parent / "data" / "llm_error_response.json"
            error_file.parent.mkdir(exist_ok=True)
            with open(error_file, 'w', encoding='utf-8') as f:
                f.write(text_content)
            print(f"\n💾 完整响应已保存到: {error_file}")
        
        return {
            'error': f'JSON 解析失败: {str(e)}',
            'error_line': e.lineno if hasattr(e, 'lineno') else None,
            'error_column': e.colno if hasattr(e, 'colno') else None,
            'raw_response': text_content if 'text_content' in locals() else 'N/A'
        }
    except Exception as e:
        print(f"❌ AI 调用失败: {e}")
        import traceback
        traceback.print_exc()
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
