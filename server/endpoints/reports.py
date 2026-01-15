"""
报告相关 API 端点

功能：
- 获取报告列表（分页）
- 获取报告详情
- 全文搜索（FTS5）
- 上传报告（新增）
"""

from fastapi import APIRouter, Request, UploadFile, File, Form
from fastapi.responses import JSONResponse
from typing import Optional
import uuid
from datetime import datetime

router = APIRouter(prefix="/api/reports", tags=["reports"])

# 依赖注入（将在 server.py 中设置）
db_manager = None
report_service = None


def set_dependencies(db, service):
    """设置依赖（从 server.py 注入）"""
    global db_manager, report_service
    db_manager = db
    report_service = service


@router.get("")
async def get_reports(limit: int = 20, offset: int = 0):
    """
    获取报告列表（分页）
    
    参数:
        - limit: 每页数量（默认 20）
        - offset: 偏移量（默认 0）
    
    返回:
        - reports: 报告列表
        - total: 总数量
        - limit: 每页数量
        - offset: 偏移量
    """
    try:
        # 使用 search_reports 代替 get_all_reports
        reports = await db_manager.search_reports(limit=limit, offset=offset)
        stats = await db_manager.get_report_stats()
        total = stats.get('total_reports', 0) if stats else 0
        
        return {
            "reports": reports,
            "total": total,
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@router.get("/{report_id}")
async def get_report_details(report_id: str):
    """
    获取报告详情
    
    参数:
        - report_id: 报告唯一标识
    
    返回:
        - report: 报告详情（包含完整 JSON 数据）
    """
    try:
        report = await db_manager.get_report(report_id)
        
        if not report:
            return JSONResponse(
                status_code=404,
                content={"error": f"Report {report_id} not found"}
            )
        
        return {"report": report}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@router.post("/search")
async def search_reports(request: Request):
    """
    搜索报告（智能选择搜索方式）
    
    请求体:
        - query: 搜索关键词
        - category: 分类筛选（可选）
        - action: 投资建议筛选（可选）
        - min_importance: 最小重要性评分（可选）
        - limit: 返回数量（默认 20）
    
    返回:
        - results: 搜索结果列表
        - query: 搜索关键词
        - count: 结果数量
    """
    try:
        data = await request.json()
        query = data.get("query", "")
        category = data.get("category")
        action = data.get("action")
        min_importance = data.get("min_importance")
        limit = data.get("limit", 20)
        
        # 使用智能搜索方法
        results = await db_manager.smart_search_reports(
            query=query,
            category=category,
            action=action,
            min_importance=min_importance,
            limit=limit
        )
        
        return {
            "results": results,
            "query": query,
            "count": len(results)
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@router.post("")
async def upload_report(
    title: str = Form(...),
    content: str = Form(...),
    category: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None)
):
    """
    上传新报告并进行 AI 分析
    
    参数:
        - title: 报告标题（必需）
        - content: 报告内容/原文（必需）
        - category: 分类（可选，如 A股/黄金/债券）
        - file: 文件上传（可选，支持 txt/md）
    
    流程:
        1. 接收报告文本
        2. 调用 AI 进行结构化分析
        3. 保存到数据库
        4. 触发 Listeners（如有）
    
    返回:
        - success: 是否成功
        - report_id: 报告 ID
        - analysis: AI 分析结果摘要
    """
    try:
        # 如果上传了文件，读取内容
        if file:
            file_content = await file.read()
            content = file_content.decode('utf-8')
            if not title:
                title = file.filename
        
        # 调用报告分析服务
        result = await report_service.analyze_and_save_report(
            title=title,
            content=content,
            category=category
        )
        
        return {
            "success": True,
            "report_id": result['report_id'],
            "title": result['title'],
            "analysis_summary": {
                "sentiment": result.get('sentiment'),
                "action": result.get('action'),
                "importance_score": result.get('importance_score'),
                "summary": result.get('summary_one_sentence')
            },
            "message": f"Report '{title}' analyzed and saved successfully"
        }
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "error": str(e),
                "detail": "Failed to analyze report"
            }
        )


@router.get("/stats/overview")
async def get_report_stats():
    """
    获取报告统计信息
    
    返回:
        - total_reports: 总报告数
        - by_category: 按分类统计
        - by_action: 按投资建议统计
        - avg_importance: 平均重要性评分
    """
    try:
        stats = await db_manager.get_report_stats()
        return stats
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )
