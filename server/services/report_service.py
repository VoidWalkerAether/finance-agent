"""
报告分析服务

功能：
- 调用 report_analyzer 的核心分析逻辑（避免代码重复）
- 保存到数据库
- 触发 Listeners
"""

import uuid
import json
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
import sys

# 导入 report_analyzer 的核心函数
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from agent.custom_scripts.listeners.report_analyzer import (
    _analyze_report_with_ai,
    _transform_to_db_format
)


class ReportAnalysisService:
    """报告分析服务"""
    
    def __init__(self, database_manager, listeners_manager=None):
        """
        初始化服务
        
        Args:
            database_manager: 数据库管理器
            listeners_manager: Listeners 管理器（可选）
        """
        self.db = database_manager
        self.listeners_manager = listeners_manager
        # 不再需要 AgentTools，直接调用 report_analyzer 的函数
    
    async def analyze_and_save_report(
        self,
        title: str,
        content: str,
        category: Optional[str] = None,
        file_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        分析报告并保存
        
        Args:
            title: 报告标题
            content: 报告内容
            category: 分类（可选）
            file_path: 原始文件路径（可选）
        
        Returns:
            Dict: 包含 report_id 和分析结果的字典
        """
        
        # 1. 调用 report_analyzer 的核心分析逻辑
        print(f"[ReportService] 开始分析报告: {title}")
        analysis_result = await _analyze_report_with_ai(content, depth="standard")
        
        if "error" in analysis_result:
            print(f"[ReportService] ⚠️ AI 分析失败: {analysis_result['error']}")
            return {
                'success': False,
                'error': analysis_result['error']
            }
        
        # 2. 转换为数据库格式（复用 report_analyzer 的函数）
        report_data = _transform_to_db_format(
            analysis=analysis_result,
            filename=title,
            file_path=file_path,
            custom_report_id=None  # 让它自动生成
        )
        
        # 3. 如果用户指定了 category，覆盖 AI 分析结果
        if category:
            report_data['category'] = category
        
        # 4. 保存到数据库
        print(f"[ReportService] 保存报告到数据库: {report_data['report_id']}")
        await self.db.upsert_report(report_data)
        
        # 5. 触发 Listeners（带 skip_analysis 标记，避免重复分析）
        if self.listeners_manager:
            await self._trigger_listeners(report_data, skip_analysis=True)
        
        print(f"[ReportService] ✅ 报告分析完成: {report_data['report_id']}")
        
        return {
            'report_id': report_data['report_id'],
            'title': report_data['title'],
            'sentiment': report_data['sentiment'],
            'action': report_data['action'],
            'importance_score': report_data['importance_score'],
            'summary_one_sentence': report_data['summary_one_sentence'],
            'category': report_data['category']
        }
    

    
    async def _trigger_listeners(self, report_data: Dict[str, Any], skip_analysis: bool = False):
        """
        触发 Listeners
        
        Args:
            report_data: 报告数据
            skip_analysis: 是否跳过 Listener 的分析（避免重复）
        """
        try:
            # 触发 "report_added" 事件
            await self.listeners_manager.check_event(
                event="report_added",
                data={
                    "report": report_data,
                    "report_id": report_data['report_id'],
                    "title": report_data['title'],
                    "action": report_data['action'],
                    "importance_score": report_data['importance_score'],
                    "skip_analysis": skip_analysis  # 新增：告诉 Listener 跳过分析
                }
            )
            print(f"[ReportService] ✅ 已触发 Listeners: report_added (skip_analysis={skip_analysis})")
        
        except Exception as e:
            print(f"[ReportService] ⚠️ 触发 Listeners 失败: {e}")
