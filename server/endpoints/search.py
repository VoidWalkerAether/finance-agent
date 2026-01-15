"""
智能搜索相关 API 端点

功能：
- 基于意图识别的智能搜索接口
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api/search", tags=["search"])

# 依赖注入（将在 server.py 中设置）
search_service = None


def set_dependencies(service):
    """设置依赖（从 server.py 注入）"""
    global search_service
    search_service = service


@router.post("/smart")
async def smart_search(request: Request):
    """
    基于意图识别的智能搜索接口
    
    请求体:
        - query: 用户查询语句（必需）
        - limit: 返回数量限制（可选，默认 10）
    
    返回:
        - query: 原始查询
        - intent: 识别出的意图信息
          - intent: "FINANCE" 或 "GENERAL"
          - reason: 分类理由
          - confidence: 置信度 (0.0-1.0)
        - search_type: 搜索类型 ("local_database" 或 "web")
        - results: 搜索结果列表
    
    示例:
        请求:
        {
            "query": "现在黄金价格是多少？",
            "limit": 5
        }
        
        响应:
        {
            "query": "现在黄金价格是多少？",
            "intent": {
                "intent": "FINANCE",
                "reason": "查询黄金价格属于金融类问题",
                "confidence": 0.95
            },
            "search_type": "local_database",
            "results": [...]
        }
    """
    try:
        data = await request.json()
        query = data.get("query", "")
        limit = data.get("limit", 10)
        
        if not query:
            return JSONResponse(
                status_code=400,
                content={
                    "error": "Query is required",
                    "message": "请求体中必须包含 'query' 字段"
                }
            )
            
        # 调用搜索服务的智能搜索方法
        result = await search_service.smart_search(query=query, limit=limit)
        
        return result
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "error": str(e),
                "message": "智能搜索失败"
            }
        )


@router.post("/classify")
async def classify_intent(request: Request):
    """
    查询意图分类接口（独立调用）
    
    请求体:
        - query: 用户查询语句
    
    返回:
        - intent: "FINANCE" 或 "GENERAL"
        - reason: 分类理由
        - confidence: 置信度 (0.0-1.0)
    """
    try:
        data = await request.json()
        query = data.get("query", "")
        
        if not query:
            return JSONResponse(
                status_code=400,
                content={
                    "error": "Query is required",
                    "message": "请求体中必须包含 'query' 字段"
                }
            )
        
        # 调用意图识别服务
        result = await search_service.classify_intent(query)
        
        return result
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "error": str(e),
                "message": "意图识别失败"
            }
        )
