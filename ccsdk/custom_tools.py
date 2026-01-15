#!/usr/bin/env python3
"""
Finance Agent Custom Tools - MCP Server

提供金融报告搜索和读取工具，供 Claude Agent SDK 使用

对应 TypeScript: email-agent/ccsdk/custom-tools.ts
"""

import asyncio
import json
import sys
import os
from pathlib import Path
from typing import Dict, Any, List
from functools import wraps

# 添加调试日志
print(f"🔧 [CustomTools] 启动 MCP 服务器", file=sys.stderr)
print(f"   - Python版本: {sys.version}", file=sys.stderr)
print(f"   - 当前工作目录: {os.getcwd()}", file=sys.stderr)
print(f"   - 脚本路径: {__file__}", file=sys.stderr)

# 强制无缓冲输出（确保 print 日志立即显示）
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

print(f"   - 项目根目录: {project_root}", file=sys.stderr)

# 加载环境变量
from dotenv import load_dotenv
env_path = project_root / '.env'
print(f"   - 环境变量文件路径: {env_path}", file=sys.stderr)
if env_path.exists():
    load_dotenv(env_path)
    print(f"   - 环境变量加载成功", file=sys.stderr)
else:
    print(f"   - 环境变量文件不存在", file=sys.stderr)

# 检查数据库路径
database_path = os.getenv('DATABASE_PATH', './data/finance.db')
print(f"   - DATABASE_PATH: {database_path}", file=sys.stderr)

# 导入 Claude Agent SDK
try:
    from claude_agent_sdk import tool, create_sdk_mcp_server
    from pydantic import BaseModel, Field
    print(f"✅ [CustomTools] Claude Agent SDK 导入成功", file=sys.stderr)
except ImportError as e:
    print(f"❌ [CustomTools] Claude Agent SDK 导入失败: {e}", file=sys.stderr)
    print("请安装: pip install claude-agent-sdk pydantic", file=sys.stderr)
    sys.exit(1)

# 导入数据库管理器
try:
    from database.database_manager import DatabaseManager
    print(f"✅ [CustomTools] DatabaseManager 导入成功", file=sys.stderr)
except ImportError as e:
    print(f"❌ [CustomTools] DatabaseManager 导入失败: {e}", file=sys.stderr)
    sys.exit(1)


class SearchReportsArgs(BaseModel):
    """搜索报告参数"""
    query: str = Field(
        ...,
        description="搜索关键词，支持全文搜索（如：'黄金 A股'）"
    )
    category: str = Field(
        None,
        description="报告分类（如：'市场分析'、'个股研报'）"
    )
    action: str = Field(
        None,
        description="投资建议（buy/sell/hold/watch）"
    )
    min_importance: int = Field(
        None,
        description="最小重要性评分（1-10）"
    )
    limit: int = Field(
        10,
        description="返回报告数量（默认 10，最大 50）"
    )


class ReadReportArgs(BaseModel):
    """读取报告参数"""
    report_id: str = Field(
        ...,
        description="报告唯一标识（report_id）"
    )


# 创建数据库管理器实例（延迟初始化）
_db_instance = None


def get_db():
    """获取数据库实例（单例模式）"""
    global _db_instance
    if _db_instance is None:
        _db_instance = DatabaseManager()
    return _db_instance


@tool("search_reports", "搜索金融报告", SearchReportsArgs)
async def search_reports_tool(args: SearchReportsArgs) -> Dict[str, Any]:
    """
    搜索金融报告工具函数 - 使用智能搜索
    """
    print(f"\n{'='*60}", flush=True)
    print(f"🔍 [search_reports] 工具被调用！", flush=True)
    print(f"📝 [search_reports] 参数: {args}", flush=True)
    print(f"{'='*60}\n", flush=True)
    print(args)
    
    try:
        db = get_db()
        print(f"✅ [search_reports] 数据库实例获取成功", flush=True)
        
        # 处理参数 - 确保我们正确访问参数值
        # 如果 args 是字典，则直接访问其键；如果是模型实例，则访问其属性
        query = args.get('query') if isinstance(args, dict) else args.query
        category = args.get('category') if isinstance(args, dict) else getattr(args, 'category', None)
        action = args.get('action') if isinstance(args, dict) else getattr(args, 'action', None)
        min_importance = args.get('min_importance') if isinstance(args, dict) else getattr(args, 'min_importance', None)
        limit = args.get('limit') if isinstance(args, dict) else getattr(args, 'limit', 10)
        
        # 确保 limit 是一个有效的整数
        if limit is None:
            limit = 10
        else:
            limit = int(limit)
        
        # 限制返回数量
        limit = min(limit, 50)
        
        print(f"🔍 [search_reports] 开始搜索数据库...", flush=True)
        # 使用智能搜索方法
        reports = await db.smart_search_reports(
            query=query,
            category=category,
            action=action,
            min_importance=min_importance,
            limit=limit
        )
        print(f"✅ [search_reports] 数据库搜索完成，找到 {len(reports)} 份报告", flush=True)
        
        if not reports:
            return {
                'content': [{
                    'type': 'text',
                    'text': '没有找到符合条件的报告。'
                }]
            }
        
        # 构建结果文本
        result_text = f"找到 {len(reports)} 份报告:\n\n"
        
        for i, report in enumerate(reports, 1):
            result_text += f"{i}. **{report.get('title', 'N/A')}**\n"
            result_text += f"   - 报告ID: {report.get('report_id', 'N/A')}\n"
            result_text += f"   - 分类: {report.get('category', 'N/A')}\n"
            result_text += f"   - 内容: {report.get('content', 'N/A')}/10\n"
            #result_text += f"   - 投资建议: {report.get('action', 'N/A')}\n"
            result_text += f"   - 一句话摘要: {report.get('summary_one_sentence', 'N/A')}\n"
            
            # 提取关键风险
            #if report.get('risks'):
            #    result_text += f"   - 主要风险: {report.get('risks', 'N/A')}\n"
            
            result_text += "\n"
        
        result_text += f"\n💡 使用 read_report 工具可以读取完整报告内容。"
        
        print(f"✅ [result_text] 返回报告 {result_text}")
        print(f"✅ [search_reports] 返回 {len(reports)} 份报告")
        
        return {
            'content': [{
                'type': 'text',
                'text': result_text
            }]
        }
    
    except Exception as e:
        error_msg = f"搜索报告失败: {str(e)}"
        print(f"❌ [search_reports] {error_msg}")
        import traceback
        traceback.print_exc()
        return {
            'content': [{
                'type': 'text',
                'text': error_msg
            }],
            'isError': True
        }


@tool("read_report", "读取完整报告内容", ReadReportArgs)
async def read_report_tool(args: ReadReportArgs) -> Dict[str, Any]:
    """
    读取完整报告内容工具函数
    """
    try:
        db = get_db()
        
        # 处理参数 - 确保我们正确访问参数值
        # 如果 args 是字典，则直接访问其键；如果是模型实例，则访问其属性
        report_id = args.get('report_id') if isinstance(args, dict) else args.report_id
        
        print(f"📖 [read_report] 读取报告: {report_id}")
        
        # 获取报告
        report = await db.get_report(report_id)
        
        if not report:
            return {
                'content': [{
                    'type': 'text',
                    'text': f'未找到报告 ID: {report_id}'
                }],
                'isError': True
            }
        
        # 构建完整报告内容
        content_parts = []
        
        # 标题和基本信息
        content_parts.append(f"# {report.get('title', 'N/A')}\n")
        content_parts.append(f"**报告ID**: {report.get('report_id', 'N/A')}\n")
        content_parts.append(f"**分类**: {report.get('category', 'N/A')}\n")
        content_parts.append(f"**发布日期**: {report.get('date_published', 'N/A')}\n")
        content_parts.append(f"**重要性**: {report.get('importance_score', 'N/A')}/10\n")
        content_parts.append(f"**投资建议**: {report.get('action', 'N/A')}\n\n")
        
        # 一句话摘要
        if report.get('summary_one_sentence'):
            content_parts.append(f"## 核心观点\n{report['summary_one_sentence']}\n\n")
        
        # 详细摘要
        if report.get('summary'):
            content_parts.append(f"## 详细摘要\n{report['summary']}\n\n")
        
        # 关键发现
        if report.get('key_findings'):
            content_parts.append(f"## 关键发现\n{report['key_findings']}\n\n")
        
        # 风险提示
        if report.get('risks'):
            content_parts.append(f"## 风险提示\n{report['risks']}\n\n")
        
        # 相关资产
        if report.get('related_assets'):
            content_parts.append(f"## 相关资产\n{report['related_assets']}\n\n")
        
        # 【核心添加】从 analysis_json 中提取关键信息
        analysis_json = report.get('analysis_json')
        if analysis_json:
            import json
            try:
                # 如果是字符串，解析为 JSON
                if isinstance(analysis_json, str):
                    analysis_data = json.loads(analysis_json)
                else:
                    analysis_data = analysis_json
                
                # 提取主要观点（最重要！）
                main_points = analysis_data.get('main_points', [])
                if main_points:
                    content_parts.append(f"## 主要观点\n")
                    for i, point in enumerate(main_points, 1):
                        content_parts.append(f"{i}. {point}\n")
                    content_parts.append("\n")
                
                # 提取核心观点
                core_views = analysis_data.get('text_summary', {}).get('core_views', [])
                if core_views:
                    content_parts.append(f"## 核心观点\n")
                    for i, view in enumerate(core_views, 1):
                        content_parts.append(f"{i}. {view}\n")
                    content_parts.append("\n")
                
                # 提取投资建议
                investment_advice = analysis_data.get('investment_advice', {})
                if investment_advice:
                    content_parts.append(f"## 投资建议\n")
                    if investment_advice.get('action'):
                        content_parts.append(f"**操作建议**: {investment_advice['action']}\n")
                    if investment_advice.get('target_allocation'):
                        content_parts.append(f"**目标配置**: {investment_advice['target_allocation']}\n")
                    if investment_advice.get('timing'):
                        content_parts.append(f"**时机选择**: {investment_advice['timing']}\n")
                    content_parts.append("\n")
                
            except Exception as e:
                print(f"⚠️  解析 analysis_json 失败: {e}")
                import traceback
                traceback.print_exc()
        
        # 完整内容（放在最后，避免太长）
        if report.get('content'):
            content_parts.append(f"## 完整内容\n{report['content']}\n")
        
        result_text = "".join(content_parts)
        
        print(f"✅ [read_report] 成功读取报告: {report_id}")
        
        return {
            'content': [{
                'type': 'text',
                'text': result_text
            }]
        }
    
    except Exception as e:
        error_msg = f"读取报告失败: {str(e)}"
        print(f"❌ [read_report] {error_msg}")
        import traceback
        traceback.print_exc()
        return {
            'content': [{
                'type': 'text',
                'text': error_msg
            }],
            'isError': True
        }


# 创建 MCP 服务器（使用装饰器定义的工具函数）
# 注意：这里直接返回服务器字典，而不是运行它
custom_server = create_sdk_mcp_server(
    name="reports",
    version="1.0.0",
    tools=[
        search_reports_tool,
        read_report_tool
    ],
)


# 作为独立进程运行时的入口（用于测试）
if __name__ == "__main__":
    print("\n" + "="*60, flush=True)
    print("🚀 Finance Agent Custom Tools Server 启动中...", flush=True)
    print(f"   提供工具: search_reports, read_report", flush=True)
    print(f"   数据库: {os.getenv('DATABASE_PATH', './data/finance.db')}", flush=True)
    print("="*60, flush=True)
    
    # 测试数据库连接
    try:
        db = get_db()
        print("✅ 数据库连接成功", flush=True)
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}", flush=True)
        import traceback
        traceback.print_exc()
    
    print("🌐 MCP 服务器已准备好，等待 Claude SDK 调用...\n", flush=True)
    
    # 注意：这里不直接运行服务器，而是保持进程运行等待 Claude SDK 调用
    # 服务器的实际运行由 Claude SDK 内部处理
    try:
        # 保持进程运行
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("👋 MCP 服务器已停止", flush=True)