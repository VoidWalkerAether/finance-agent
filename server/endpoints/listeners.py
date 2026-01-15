"""
Listeners API 端点

功能：
- 获取所有 Listeners
- 获取 Listener 日志
- 获取 Listener 统计信息
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api/listeners", tags=["listeners"])

# 依赖注入
listeners_manager = None


def set_dependencies(listeners):
    """设置依赖（从 server.py 注入）"""
    global listeners_manager
    listeners_manager = listeners


@router.get("")
async def list_listeners():
    """
    获取所有 Listeners
    
    返回:
        - listeners: Listener 列表
        - stats: 统计信息
    """
    try:
        listeners = listeners_manager.get_all_listeners()
        stats = listeners_manager.get_stats()
        
        return {
            "listeners": listeners,
            "stats": stats
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@router.get("/{listener_id}/logs")
async def get_listener_logs(listener_id: str, limit: int = 50):
    """
    获取 Listener 日志
    
    参数:
        - listener_id: Listener ID
        - limit: 返回数量（默认 50）
    
    返回:
        - logs: 日志列表
    """
    try:
        log_writer = listeners_manager.get_log_writer()
        logs = await log_writer.read_logs(listener_id, limit)
        
        return {"logs": logs}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@router.get("/stats/overview")
async def get_listeners_stats():
    """
    获取 Listeners 统计信息
    
    返回:
        - total_listeners: Listener 总数
        - active_listeners: 活跃 Listener 数量
        - event_types: 事件类型列表
    """
    try:
        stats = listeners_manager.get_stats()
        return stats
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )
