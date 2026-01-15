"""
关注列表 API 端点

功能：
- 获取关注列表
- 添加关注项
- 删除关注项
- 更新关注项
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])

# 依赖注入
db_manager = None


def set_dependencies(db):
    """设置依赖（从 server.py 注入）"""
    global db_manager
    db_manager = db


@router.get("")
async def get_watchlist():
    """
    获取关注列表
    
    返回:
        - watchlist: 关注列表数组
    """
    try:
        watchlist = await db_manager.get_watchlist()
        return {"watchlist": watchlist}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@router.post("")
async def add_watchlist_item(request: Request):
    """
    添加关注项
    
    请求体:
        - target_name: 标的名称（必需）
        - target_type: 标的类型（必需，如 ETF/stock/index/industry）
        - alert_conditions: 提醒条件（可选，JSON 格式）
        - notes: 备注（可选）
    
    返回:
        - success: 是否成功
        - item_id: 关注项 ID
        - message: 提示消息
    """
    try:
        data = await request.json()
        
        item_id = await db_manager.add_watchlist_item(
            target_name=data.get("target_name"),
            target_type=data.get("target_type"),
            alert_conditions=data.get("alert_conditions"),
            notes=data.get("notes")
        )
        
        return {
            "success": True,
            "item_id": item_id,
            "message": f"Added {data.get('target_name')} to watchlist"
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@router.delete("/{item_id}")
async def delete_watchlist_item(item_id: int):
    """
    删除关注项
    
    参数:
        - item_id: 关注项 ID
    
    返回:
        - success: 是否成功
        - message: 提示消息
    """
    try:
        await db_manager.delete_watchlist_item(item_id)
        return {
            "success": True,
            "message": f"Deleted watchlist item {item_id}"
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@router.get("/{item_id}")
async def get_watchlist_item(item_id: int):
    """
    获取单个关注项详情
    
    参数:
        - item_id: 关注项 ID
    
    返回:
        - item: 关注项详情
    """
    try:
        item = await db_manager.get_watchlist_item(item_id)
        
        if not item:
            return JSONResponse(
                status_code=404,
                content={"error": f"Watchlist item {item_id} not found"}
            )
        
        return {"item": item}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@router.put("/{item_id}")
async def update_watchlist_item(item_id: int, request: Request):
    """
    更新关注项
    
    参数:
        - item_id: 关注项 ID
    
    请求体:
        - alert_conditions: 新的提醒条件（可选）
        - status: 状态（可选）
        - notes: 备注（可选）
    
    返回:
        - success: 是否成功
        - message: 提示消息
    """
    try:
        data = await request.json()
        
        success = await db_manager.update_watchlist_item(
            item_id=item_id,
            **data
        )
        
        if not success:
            return JSONResponse(
                status_code=404,
                content={"error": f"Watchlist item {item_id} not found"}
            )
        
        return {
            "success": True,
            "message": f"Updated watchlist item {item_id}"
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )
