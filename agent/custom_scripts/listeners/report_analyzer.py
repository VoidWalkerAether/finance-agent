"""
金融报告智能解析器 - Finance Agent Listener 插件
监听报告导入事件,自动提取关键信息并存储到数据库

功能:
- 自动分析新导入的金融报告
- 提取结构化信息(投资建议、风险评估、关键数据等)
- 存储到 SQLite 数据库(reports 表)
- 支持全文搜索(FTS5)
- 通知用户分析完成
"""

import json
import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from pathlib import Path

# Claude Agent SDK imports
try:
    from claude_agent_sdk import (
        AssistantMessage,
        TextBlock,
        query
    )
except ImportError:
    print("请先安装依赖: pip install claude-agent-sdk")
    raise

# 项目内部导入
import sys
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from database.database_manager import DatabaseManager


# ============================================================================
# Listener 配置 (必需导出)
# ============================================================================

config = {
    "id": "report_analyzer",
    "name": "金融报告智能分析器",
    "description": "自动分析新导入的金融报告,提取投资建议、风险评估、关键数据等结构化信息",
    "enabled": True,
    "event": "report_added"  # 监听报告添加事件（统一事件名）
}


def _extract_text_summary(report_text: str) -> Dict:
    """提取文本摘要、核心观点和分析框架"""
    import re
    
    # 先统一处理文本：去除所有空格和换行，然后按句号、问号、感叹号分句
    # 这样可以处理OCR文本中字与字之间有空格的情况
    cleaned_text = re.sub(r'\s+', '', report_text.strip())
    
    # 按句子分割（处理中文标点）
    sentences = re.split(r'[。！？;；]', cleaned_text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
    
    # 提取核心观点 - 寻找包含判断性词汇的完整句子
    core_views = []
    judgment_keywords = ['应当', '需要', '建议', '可以', '不会', '会', '将', '必然', '预期', '判断', '认为', '看好', '看空', '应该', '能够', '可能']
    
    for sentence in sentences:
        if len(sentence) > 20 and any(keyword in sentence for keyword in judgment_keywords):
            # 避免过长的句子，但保留足够的上下文
            if len(sentence) <= 150:
                core_views.append(sentence)
            else:
                # 对于超长句子，尝试从关键词附近提取
                for keyword in judgment_keywords:
                    if keyword in sentence:
                        # 找到关键词位置
                        idx = sentence.index(keyword)
                        # 提取关键词前后各75个字符
                        start = max(0, idx - 50)
                        end = min(len(sentence), idx + 100)
                        fragment = sentence[start:end]
                        if len(fragment) > 20:
                            core_views.append(fragment)
                            break
    
    # 提取关键数据 - 寻找包含数字的完整句子
    key_facts = []
    # 增强数字匹配模式
    number_pattern = r'\d+\.?\d*[%亿万元美元点盎司吨个家份月年日]|\d+[-~至]\d+|\d{4}年|\d+月|\d+日'
    
    for sentence in sentences:
        if re.search(number_pattern, sentence) and len(sentence) > 15:
            # 同样处理过长句子
            if len(sentence) <= 150:
                key_facts.append(sentence)
            else:
                # 提取包含数字的关键部分
                matches = list(re.finditer(number_pattern, sentence))
                if matches:
                    # 取第一个数字附近的内容
                    match = matches[0]
                    idx = match.start()
                    start = max(0, idx - 40)
                    end = min(len(sentence), idx + 110)
                    fragment = sentence[start:end]
                    if len(fragment) > 15:
                        key_facts.append(fragment)
    
    # 提取分析框架 - 寻找框架性描述的完整句子
    analysis_framework = []
    framework_keywords = ['因素', '框架', '方法', '逻辑', '模型', '维度', '特征', '原则', '策略', '机制', '驱动', '角度', '方面']
    
    for sentence in sentences:
        if len(sentence) > 20 and any(keyword in sentence for keyword in framework_keywords):
            if len(sentence) <= 150:
                analysis_framework.append(sentence)
            else:
                # 对于超长句子，提取关键词附近内容
                for keyword in framework_keywords:
                    if keyword in sentence:
                        idx = sentence.index(keyword)
                        start = max(0, idx - 50)
                        end = min(len(sentence), idx + 100)
                        fragment = sentence[start:end]
                        if len(fragment) > 20:
                            analysis_framework.append(fragment)
                            break
    
    # 去重（保持顺序）
    def deduplicate(items):
        seen = set()
        result = []
        for item in items:
            if item not in seen and len(item) > 10:
                seen.add(item)
                result.append(item)
        return result
    
    core_views = deduplicate(core_views)
    key_facts = deduplicate(key_facts)
    analysis_framework = deduplicate(analysis_framework)
    
    return {
        "core_views": core_views[:15],  # 最多15条核心观点
        "key_facts": key_facts[:20],    # 最多20条关键数据
        "analysis_framework": analysis_framework[:12]  # 最多12条分析框架
    }


def _build_analysis_prompt(report_text: str, depth: str) -> str:
    """根据分析深度构建提示词"""
    
    base_prompt = f"""你是一位专业的金融分析师,请分析以下报告:

{report_text}

请以JSON格式输出分析结果。"""

    if depth == "quick":
        base_prompt += """
只需要提供：
- 报告类型和日期
- 一句话总结
- 3个核心观点
- 简单的投资建议
"""
    elif depth == "deep":
        base_prompt += """
需要深度分析：
- 详细的因果关系分析
- 多维度的风险评估
- 量化的评分模型
- 具体的操作策略
- 关联资产分析
"""
    
    base_prompt += """
JSON格式要求（请尽可能详细提取所有信息）：
{
  "report_info": {
    "type": "报告类型",
    "category": "具体分类",
    "date": "日期",
    "title": "标题",
    "sources": ["信息来源1", "信息来源2"]  // 新增：标注报告引用的数据来源
  },
  "summary": {
    "one_sentence": "一句话总结",
    "sentiment": "bullish/bearish/neutral",
    "key_drivers": ["驱动因素1", "驱动因素2"]  // 新增：核心驱动因素
  },
  "key_data": {
    "关键指标": "数值"  // 尽可能提取所有数字、百分比、金额、时间节点等
  },
  "historical_context": {  // 新增：历史对比数据
    "对比项目": "历史数据对比",
    "趋势变化": "描述趋势转折点"
  },
  "main_points": ["观点1", "观点2", "观点3"],
  "investment_targets": {  // 新增：具体投资标的分析
    "recommended": [  // 推荐标的
      {
        "name": "公司/ETF名称",
        "type": "个股/ETF/板块",
        "reason": "推荐理由",
        "key_metrics": "关键财务/业绩数据",
        "price_action": "股价表现数据",
        "market_share": "市场份额等信息"
      }
    ],
    "cautious": [  // 需谨慎的标的
      {
        "name": "标的名称",
        "reason": "谨慎理由",
        "risk_factors": "风险因素"
      }
    ]
  },
  "investment_advice": {
    "action": "buy/sell/hold/watch",
    "target_allocation": "配置比例建议",
    "timing": "操作时机建议",  // 新增：时机建议
    "holding_period": "建议持有周期",  // 新增：持有期建议
    "confidence_level": "high/medium/low"
  },
  "risk_warnings": [  // 详细风险提示
    {
      "risk_type": "风险类型",
      "description": "具体风险描述",
      "impact_level": "high/medium/low",
      "affected_targets": ["受影响标的"]
    }
  ],
  "timeline_events": [  // 新增：关键时间节点
    {
      "date": "日期",
      "event": "事件描述",
      "impact": "影响分析"
    }
  ],
  "industry_structure": {  // 新增：产业结构分析
    "supply_chain": "产业链分析",
    "competitive_landscape": "竞争格局",
    "barriers_to_entry": "行业壁垒"
  },
  "quantitative_metrics": {  // 新增:量化指标
    "investment_scale": "投资规模数据",
    "growth_rates": "增长率数据",
    "market_size": "市场规模数据",
    "capacity_data": "产能/装机等数据"
  },
  "text_summary": {  // 新增:文本摘要(AI智能提取)
    "core_views": [  // 核心观点：高度概括的投资判断和策略建议（5-10条）
      "核心观点1：简洁陈述市场判断或投资策略",
      "核心观点2：..."
    ],
    "key_facts": [  // 关键数据事实：支撑观点的具体数字、比例、金额等（10-15条）
      "具体数据1：包含数字的关键事实",
      "具体数据2：..."
    ],
    "analysis_framework": [  // 分析框架：作者使用的分析方法、逻辑体系（3-8条）
      "分析框架1：如'四大因素驱动模型'",
      "分析框架2：..."
    ]
  },
  "key_metrics": {
    "importance_score": 8,
    "urgency_score": 7,
    "reliability_score": 9
  }
}

��别提示：
1. 请提取原文中所有具体的数字、百分比、金额、时间等数据
2. 对于提到的所有公司名称，尽可能提取其业绩、股价、市场份额等信息
3. 标注历史对比数据（如"十年前vs现在"、"去年vs今年"等）
4. 记录所有时间节点和关键事件
5. 区分短期、中期、长期的投资逻辑

**text_summary 字段填写要求**（重要）：
- core_views: 提炼报告的核心投资观点和判断，每条应是完整、独立、易理解的陈述（20-80字）
  示例："A股不大概率止步于4000点，当前围绕4000点的拉锯属年末上涨后的正常调整与流动性阶段性偏紧"
- key_facts: 提取支撑观点的具体数据和事实，保持原文准确性（15-60字）
  示例："上证指数涨幅约45%"、"A股三季报营收增长5%以上、净利润增长11%以上"
- analysis_framework: 总结作者使用的分析方法和逻辑框架（20-80字）
  示例："四大因子综合评估法：政策面、宏观面、资金面、上市公司基本面"
"""
    return base_prompt


def _parse_json_response(text: str) -> Dict:
    """解析Claude的响应"""
    import re
    
    # 尝试提取JSON
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except:
            pass
    
    return {"error": "无法解析响应", "raw_text": text}


# ============================================================================
# Listener 处理函数 (必需导出)
# ============================================================================

async def handler(event_data: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    报告分析 Listener 处理函数
    
    Args:
        event_data: {
            'file_path': '/path/to/report.txt',
            'filename': 'report.txt',
            'content': '报告原文...',
            'report_id': 'optional_custom_id',
            'skip_analysis': False  # 新增：如果为 True，跳过分析（避免重复）
        }
        context: ListenerContext {
            notify(message, options),
            callAgent(options),
            uiState.get/set(stateId, data)
        }
    
    Returns:
        {
            'executed': True/False,
            'reason': '执行原因',
            'actions': ['分析完成', '已存储'],
            'report_id': '生成的报告ID'
        }
    """
    # 检查是否跳过分析（避免 report_service 调用后重复分析）
    if event_data.get('skip_analysis'):
        return {
            'executed': False,
            'reason': '已由 API 分析，跳过 Listener 处理'
        }
    
    # 获取事件数据
    file_path = event_data.get('file_path')
    filename = event_data.get('filename', 'unknown')
    content = event_data.get('content')
    custom_report_id = event_data.get('report_id')
    
    # 验证输入
    if not content or len(content.strip()) < 50:
        return {
            'executed': False,
            'reason': '报告内容为空或过短'
        }
    
    try:
        # 步骤 1: 使用 AI 分析报告
        print(f"[报告分析器] 正在分析: {filename}")
        analysis_result = await _analyze_report_with_ai(content, depth="standard")
        
        if "error" in analysis_result:
            await context.notify(
                f"❌ 报告分析失败: {filename}\n原因: {analysis_result['error']}",
                {"priority": "normal"}
            )
            return {
                'executed': False,
                'reason': f"AI分析失败: {analysis_result['error']}"
            }
        
        # 步骤 2: 准备数据库存储格式
        report_data = _transform_to_db_format(analysis_result, filename, file_path, custom_report_id)
        
        # 步骤 3: 存储到数据库
        db = DatabaseManager()
        report_id = await db.upsert_report(report_data)
        
        # 步骤 4: 发送通知
        report_info = analysis_result.get('report_info', {})
        summary = analysis_result.get('summary', {})
        
        notification_msg = f"""✅ 报告分析完成

📋 {report_info.get('title', filename)}
分类: {report_info.get('category', 'N/A')}
情绪: {summary.get('sentiment', 'N/A')}
重要性: {analysis_result.get('key_metrics', {}).get('importance_score', 'N/A')}/10

💡 {summary.get('one_sentence', '')}
"""
        
        await context.notify(notification_msg, {"priority": "normal"})
        
        # 步骤 5: 更新 UI 状态 (可选)
        # 将最新报告添加到仪表板
        try:
            dashboard_state = await context.uiState.get("financial_dashboard")
            if dashboard_state and isinstance(dashboard_state, dict):
                recent_reports = dashboard_state.get('recent_reports', [])
                recent_reports.insert(0, {
                    'report_id': report_data['report_id'],
                    'title': report_data.get('title', filename),
                    'category': report_data.get('category'),
                    'date': report_data.get('date_published'),
                    'importance_score': report_data.get('importance_score')
                })
                dashboard_state['recent_reports'] = recent_reports[:10]  # 保留最近10条
                await context.uiState.set("financial_dashboard", dashboard_state)
        except Exception as e:
            print(f"[警告] 更新仪表板状态失败: {e}")
        
        # 步骤 6: 执行关联性分析
        print(f"[DEBUG] [报告分析器] [handler] 步骤6: 开始执行关联性分析, report_id={report_data['report_id']}")
        try:
            from database.relationship_analyzer import ReportRelationshipAnalyzer
            print(f"[DEBUG] [报告分析器] [handler] 初始化关联分析器")
            relationship_analyzer = ReportRelationshipAnalyzer(db)
            # 执行关联分析（报告已经存储到ChromaDB中）
            print(f"[DEBUG] [报告分析器] [handler] 调用关联分析方法")
            relationship_result = await relationship_analyzer.analyze_report_relationships(report_data['report_id'])
            print(f"[INFO] [报告分析器] [handler] 关联分析完成，找到 {len(relationship_result.get('relations', []))} 个关联关系")
        except Exception as e:
            print(f"[ERROR] [报告分析器] [handler] 关联分析失败: {e}")
            import traceback
            traceback.print_exc()
        
        return {
            'executed': True,
            'reason': f"成功分析并存储报告: {filename}",
            'actions': ['分析完成', '已存储到数据库', '已通知用户', '关联分析完成'],
            'report_id': report_data['report_id'],
            'importance_score': report_data.get('importance_score')
        }
        
    except Exception as e:
        print(f"[错误] 报告分析失败: {e}")
        await context.notify(
            f"❌ 报告分析失败: {filename}\n错误: {str(e)}",
            {"priority": "high"}
        )
        return {
            'executed': False,
            'reason': f"处理失败: {str(e)}"
        }


# ============================================================================
# 核心分析函数
# ============================================================================

async def _analyze_report_with_ai(report_text: str, depth: str = "standard") -> Dict[str, Any]:
    """
    使用 Claude AI 分析报告
    
    Args:
        report_text: 报告原文
        depth: 分析深度 (quick/standard/deep)
    
    Returns:
        Dict: 分析结果 JSON
    """
    prompt = _build_analysis_prompt(report_text, depth)
    
    result_text = ""
    try:
        async for message in query(prompt=prompt):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        result_text += block.text
    except Exception as e:
        return {"error": f"AI 调用失败: {str(e)}"}
    
    # 解析 JSON 响应
    analysis_result = _parse_json_response(result_text)
    
    # 如果 AI 没有返回有效的 text_summary，使用规则提取
    if "error" not in analysis_result:
        ai_summary = analysis_result.get("text_summary", {})
        has_valid_summary = (
            ai_summary and isinstance(ai_summary, dict) and
            (ai_summary.get("core_views") or ai_summary.get("key_facts"))
        )
        
        if not has_valid_summary:
            text_summary = _extract_text_summary(report_text)
            analysis_result["text_summary"] = text_summary
    
    return analysis_result


def _transform_to_db_format(
    analysis: Dict[str, Any],
    filename: str,
    file_path: Optional[str] = None,
    custom_report_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    将 AI 分析结果转换为数据库存储格式
    
    对应数据库表: reports (schema.sql)
    """
    report_info = analysis.get('report_info', {})
    summary = analysis.get('summary', {})
    investment = analysis.get('investment_advice', {})
    metrics = analysis.get('key_metrics', {})
    
    # 生成 report_id
    if custom_report_id:
        report_id = custom_report_id
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        category = report_info.get('category', 'unknown').replace(' ', '_')
        report_id = f"analysis_{category}_{timestamp}"
    
    # 提取原始内容 (从 text_summary 重建)
    text_summary = analysis.get('text_summary', {})
    content_parts = []
    if text_summary.get('core_views'):
        content_parts.append("\n".join(text_summary['core_views']))
    if text_summary.get('key_facts'):
        content_parts.append("\n".join(text_summary['key_facts']))
    # 如果从text_summary提取的内容为空，则使用完整的分析JSON作为内容
    content = "\n\n".join(content_parts) if content_parts else json.dumps(analysis, ensure_ascii=False, indent=2)
    
    return {
        'report_id': report_id,
        'title': report_info.get('title', filename),
        'report_type': report_info.get('type'),
        'category': report_info.get('category'),
        'date_published': report_info.get('date'),
        'sources': report_info.get('sources', []),
        'content': content,  # 确保content字段始终有内容用于FTS5搜索
        'summary_one_sentence': summary.get('one_sentence'),
        'sentiment': summary.get('sentiment'),
        'key_drivers': summary.get('key_drivers', []),
        'importance_score': metrics.get('importance_score'),
        'urgency_score': metrics.get('urgency_score'),
        'reliability_score': metrics.get('reliability_score'),
        'action': investment.get('action'),
        'target_allocation': investment.get('target_allocation'),
        'timing': investment.get('timing'),
        'holding_period': investment.get('holding_period'),
        'confidence_level': investment.get('confidence_level'),
        'analysis_json': analysis,  # 完整 JSON
        'original_file_path': file_path,
        'file_size': len(content) if content else 0
    }


# ============================================================================
# 工具函数 (供内部使用)
# ============================================================================


# 向后兼容: 保留独立使用的能力 (非 Listener 模式)
class FinancialReportAnalyzer:
    """金融报告分析器 - 独立使用版本"""
    
    def __init__(self, db_path: str = "data/finance.db"):
        self.db = DatabaseManager(db_path)
    
    async def analyze_and_store(self, report_text: str, filename: str = "report.txt", depth: str = "standard") -> Dict:
        """
        分析报告并存储到数据库
        
        Args:
            report_text: 报告文本内容
            filename: 文件名
            depth: 分析深度 (quick/standard/deep)
        
        Returns:
            {
                'report_id': str,
                'analysis': Dict,
                'db_id': int
            }
        """
        # 分析报告
        analysis = await _analyze_report_with_ai(report_text, depth)
        
        if "error" in analysis:
            return {'error': analysis['error']}
        
        # 转换为数据库格式
        report_data = _transform_to_db_format(analysis, filename)
        
        print("report_data:", report_data)
        # 存储到数据库
        db_id = await self.db.upsert_report(report_data)
        
        return {
            'report_id': report_data['report_id'],
            'analysis': analysis,
            'db_id': db_id
        }
    
    async def search_reports(self, query: str = None, **kwargs) -> List[Dict]:
        """搜索报告"""
        return await self.db.search_reports(query=query, **kwargs)
    
    async def get_report(self, report_id: str) -> Optional[Dict]:
        """获取单个报告"""
        return await self.db.get_report(report_id)
    
    def generate_readable_summary(self, analysis: Dict) -> str:
        """生成易读摘要"""
        summary = []
        summary.append("=" * 60)
        summary.append("📊 金融报告分析结果")
        summary.append("=" * 60)
        
        if "error" in analysis:
            summary.append(f"❌ 分析失败: {analysis['error']}")
            return "\n".join(summary)
        
        # 基本信息
        info = analysis.get("report_info", {})
        summary.append(f"\n📋 报告信息:")
        summary.append(f"  类型: {info.get('type', 'N/A')}")
        summary.append(f"  分类: {info.get('category', 'N/A')}")
        summary.append(f"  日期: {info.get('date', 'N/A')}")
        if info.get('sources'):
            summary.append(f"  来源: {', '.join(info['sources'][:3])}")
        
        # 核心摘要
        summ = analysis.get("summary", {})
        summary.append(f"\n💡 {summ.get('one_sentence', 'N/A')}")
        summary.append(f"   情绪: {summ.get('sentiment', 'N/A')}")
        if summ.get('key_drivers'):
            summary.append(f"   驱动: {', '.join(summ['key_drivers'][:3])}")
        
        # 关键数据亮点
        key_data = analysis.get("key_data", {})
        if key_data:
            summary.append(f"\n📈 关键数据:")
            for k, v in list(key_data.items())[:5]:  # 显示前5个
                summary.append(f"  • {k}: {v}")
        
        # 历史对比
        hist = analysis.get("historical_context", {})
        if hist:
            summary.append(f"\n📚 历史对比:")
            for k, v in hist.items():
                if v and v != 'N/A':
                    summary.append(f"  • {k}: {v}")
        
        # 核心观点
        points = analysis.get("main_points", [])
        if points:
            summary.append(f"\n🎯 核心观点:")
            for i, point in enumerate(points, 1):
                summary.append(f"  {i}. {point}")
        
        # 推荐标的
        targets = analysis.get("investment_targets", {})
        if targets.get("recommended"):
            summary.append(f"\n🎯 推荐标的:")
            for target in targets["recommended"][:5]:  # 显示前5个
                name = target.get('name', 'N/A')
                reason = target.get('reason', '')
                price_action = target.get('price_action', '')
                summary.append(f"  ✅ {name}")
                if reason:
                    summary.append(f"     理由: {reason[:100]}..." if len(reason) > 100 else f"     理由: {reason}")
                if price_action:
                    summary.append(f"     表现: {price_action}")
        
        if targets.get("cautious"):
            summary.append(f"\n⚠️  谨慎标的:")
            for target in targets["cautious"][:3]:  # 显示前3个
                name = target.get('name', 'N/A')
                reason = target.get('reason', '')
                summary.append(f"  🔸 {name}: {reason}")
        
        # 投资建议
        advice = analysis.get("investment_advice", {})
        summary.append(f"\n💼 投资建议:")
        summary.append(f"  操作: {advice.get('action', 'N/A').upper()}")
        summary.append(f"  配置: {advice.get('target_allocation', 'N/A')}")
        if advice.get('timing'):
            summary.append(f"  时机: {advice.get('timing')}")
        if advice.get('holding_period'):
            summary.append(f"  持有期: {advice.get('holding_period')}")
        summary.append(f"  信心: {advice.get('confidence_level', 'N/A').upper()}")
        
        # 风险提示
        risks = analysis.get("risk_warnings", [])
        if risks:
            summary.append(f"\n⚠️  风险提示:")
            for i, risk in enumerate(risks[:5], 1):  # 显示前5个
                if isinstance(risk, dict):
                    risk_type = risk.get('risk_type', '风险')
                    desc = risk.get('description', '')
                    impact = risk.get('impact_level', '')
                    impact_icon = "🔴" if impact == "high" else "🟡" if impact == "medium" else "🟢"
                    summary.append(f"  {i}. {impact_icon} {risk_type}: {desc}")
                else:
                    summary.append(f"  {i}. {risk}")
        
        # 关键时间节点
        timeline = analysis.get("timeline_events", [])
        if timeline:
            summary.append(f"\n📅 关键时间节点:")
            for event in timeline[:5]:  # 显示前5个
                date = event.get('date', '')
                evt = event.get('event', '')
                summary.append(f"  • {date}: {evt}")
        
        # 评分
        metrics = analysis.get("key_metrics", {})
        summary.append(f"\n⭐ 评分: 重要性{metrics.get('importance_score', 'N/A')}/10 "
                      f"紧急性{metrics.get('urgency_score', 'N/A')}/10 "
                      f"可靠性{metrics.get('reliability_score', 'N/A')}/10")
        
        # 文本摘要 (自动提取)
        text_summary = analysis.get("text_summary", {})
        if text_summary:
            summary.append(f"\n📝 文本摘要 (自动提取):")
            
            core_views = text_summary.get("core_views", [])
            if core_views:
                summary.append(f"\n  核心观点 ({len(core_views)}条):")
                for i, view in enumerate(core_views[:5], 1):  # 显示前5条
                    summary.append(f"    {i}. {view[:80]}..." if len(view) > 80 else f"    {i}. {view}")
            
            key_facts = text_summary.get("key_facts", [])
            if key_facts:
                summary.append(f"\n  关键数据 ({len(key_facts)}条):")
                for i, fact in enumerate(key_facts[:5], 1):  # 显示前5条
                    summary.append(f"    • {fact[:80]}..." if len(fact) > 80 else f"    • {fact}")
            
            framework = text_summary.get("analysis_framework", [])
            if framework:
                summary.append(f"\n  分析框架 ({len(framework)}条):")
                for i, method in enumerate(framework[:3], 1):  # 显示前3条
                    summary.append(f"    ◆ {method[:80]}..." if len(method) > 80 else f"    ◆ {method}")
        
        summary.append("=" * 60)
        return "\n".join(summary)
    
    def validate_analysis_completeness(self, analysis: Dict) -> Dict[str, Any]:
        """验证分析结果的完整性并提供详细报告"""
        validation_report = {
            "overall_score": 0,
            "completeness_percentage": 0,
            "missing_fields": [],
            "weak_fields": [],
            "strong_fields": [],
            "suggestions": []
        }
        
        # 定义必需字段和权重
        required_fields = {
            "report_info": 10,
            "summary": 10,
            "key_data": 15,
            "main_points": 10,
            "investment_advice": 15,
            "key_metrics": 5
        }
        
        # 推荐字段(加分项)
        recommended_fields = {
            "historical_context": 10,
            "investment_targets": 15,
            "risk_warnings": 10,
            "timeline_events": 5,
            "industry_structure": 5,
            "quantitative_metrics": 5,
            "text_summary": 5  # 新增: 文本摘要字段
        }
        
        total_score = 0
        max_score = sum(required_fields.values()) + sum(recommended_fields.values())
        
        # 检查必需字段
        for field, weight in required_fields.items():
            if field in analysis and analysis[field]:
                # 检查字段内容质量
                content = analysis[field]
                if isinstance(content, dict):
                    filled_ratio = sum(1 for v in content.values() if v and v != 'N/A') / max(len(content), 1)
                    score = weight * filled_ratio
                elif isinstance(content, list):
                    score = weight if len(content) > 0 else 0
                else:
                    score = weight
                
                total_score += score
                if score >= weight * 0.8:
                    validation_report["strong_fields"].append(field)
                elif score < weight * 0.5:
                    validation_report["weak_fields"].append(field)
                    validation_report["suggestions"].append(f"{field}字段信息不够完整，建议补充更多细节")
            else:
                validation_report["missing_fields"].append(field)
                validation_report["suggestions"].append(f"缺少必需字段：{field}")
        
        # 检查推荐字段
        for field, weight in recommended_fields.items():
            if field in analysis and analysis[field]:
                content = analysis[field]
                if isinstance(content, dict):
                    filled_ratio = sum(1 for v in content.values() if v and v != 'N/A') / max(len(content), 1)
                    score = weight * filled_ratio
                elif isinstance(content, list):
                    score = weight if len(content) > 0 else weight * 0.5
                else:
                    score = weight
                
                total_score += score
                if score >= weight * 0.8:
                    validation_report["strong_fields"].append(field)
        
        # 特别检查：investment_targets 是否有具体公司信息
        if "investment_targets" in analysis:
            targets = analysis["investment_targets"]
            if targets.get("recommended"):
                has_detailed_info = any(
                    t.get("key_metrics") or t.get("price_action") or t.get("market_share")
                    for t in targets["recommended"]
                )
                if not has_detailed_info:
                    validation_report["suggestions"].append(
                        "推荐标的缺少详细的财务数据、股价表现或市场份额信息"
                    )
        
        # 检查 key_data 是否有足够的数据点
        if "key_data" in analysis:
            if len(analysis["key_data"]) < 5:
                validation_report["suggestions"].append(
                    f"key_data仅有{len(analysis['key_data'])}个数据点，建议提取更多关键数字"
                )
        
        # 计算总分
        validation_report["overall_score"] = round(total_score, 2)
        validation_report["completeness_percentage"] = round((total_score / max_score) * 100, 2)
        
        # 总体评价
        if validation_report["completeness_percentage"] >= 80:
            validation_report["grade"] = "优秀"
            validation_report["summary"] = "分析非常全面详细，包含了绝大多数关键信息"
        elif validation_report["completeness_percentage"] >= 60:
            validation_report["grade"] = "良好"
            validation_report["summary"] = "分析质量较好，但还有改进空间"
        else:
            validation_report["grade"] = "需改进"
            validation_report["summary"] = "分析信息不够完整，建议重新分析或补充更多细节"
        
        return validation_report


# ============================================================================
# 独立使用接口 (命令行模式)
# ============================================================================

def load_report_from_file(file_path: Union[str, Path]) -> Optional[str]:
    """
    从文件读取报告内容
    
    Args:
        file_path: 文件路径
    
    Returns:
        str: 报告内容,失败返回 None
    """
    path_obj = Path(file_path)
    
    if not path_obj.exists() or not path_obj.is_file():
        print(f"❌ 文件不存在: {file_path}")
        return None
    
    if path_obj.suffix.lower() not in ['.txt', '.md', '.text']:
        print(f"⚠️ 不支持的文件格式: {path_obj.suffix}")
        return None
    
    try:
        with open(path_obj, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        if content:
            print(f"✅ 已加载文件: {path_obj.name} ({len(content)} 字符)")
            return content
        else:
            print(f"⚠️ 文件为空: {path_obj.name}")
            return None
    except Exception as e:
        print(f"❌ 读取文件失败: {e}")
        return None


# 命令行使用入口 (独立模式)
async def main_cli(input_file: Optional[str] = None):
    """
    命令行模式主函数
    
    Usage:
        python report_analyzer.py --input report.txt
    """
    print("🚀 金融报告智能分析器 (Finance Agent Listener)")
    print("=" * 60)
    
    # 创建分析器
    analyzer = FinancialReportAnalyzer()
    
    # 加载报告
    if input_file:
        content = load_report_from_file(input_file)
        filename = Path(input_file).name
    else:
        print("\n📝 使用示例报告...\n")
        filename = "示例报告.txt"
        content = """中国央行继续增持黄金，加上美国关税战出现新变数，国际金价维持在3350美元/盎司的高位。

7月7日数据显示，6月份继续增加了7万盎司的黄金储备，这是连续第8个月增持。

投资建议：
1. 继续保持一定比例的黄金投资，中长期看涨
2. 已有投资者不要过多加仓，建议不超过总资产的5-10%
3. 新投资者可在震荡时适度参与，通过定投方式降低风险"""
    
    if not content:
        print("❌ 无法加载报告内容")
        return
    
    # 分析并存储
    print(f"\n📖 正在分析: {filename}\n")
    result = await analyzer.analyze_and_store(content, filename)
    
    if 'error' in result:
        print(f"❌ 分析失败: {result['error']}")
        return
    
    print(f"✅ 分析完成!")
    print(f"   报告ID: {result['report_id']}")
    print(f"   数据库ID: {result['db_id']}")
    print(f"\n💾 已存储到数据库: data/finance.db")
    
    # 显示摘要
    analysis = result['analysis']
    summary = analysis.get('summary', {})
    print(f"\n📊 分析摘要:")
    print(f"   {summary.get('one_sentence', 'N/A')}")
    print(f"   情绪: {summary.get('sentiment', 'N/A')}")
    print(f"   重要性: {analysis.get('key_metrics', {}).get('importance_score', 'N/A')}/10")


# ============================================================================
# 命令行入口
# ============================================================================

if __name__ == "__main__":
    import asyncio
    import argparse
    
    parser = argparse.ArgumentParser(
        description="金融报告智能分析器 - Listener 插件",
        epilog="""
使用示例:
  # 作为 Listener 插件运行 (自动加载)
  # 由 ListenersManager 自动调用 handler() 函数
  
  # 独立命令行模式
  python report_analyzer.py --input report.txt
  
  # 使用示例文本
  python report_analyzer.py
        """
    )
    
    parser.add_argument(
        '--input', '-i',
        type=str,
        help='输入文件路径 (.txt, .md, .text)'
    )
    
    args = parser.parse_args()
    
    # 运行 CLI 模式
    asyncio.run(main_cli(input_file=args.input))
