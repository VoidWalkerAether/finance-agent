"""
UI State API 端点

功能：
- 获取所有 UI State
- 获取单个 UI State
- 更新 UI State
- 获取 UI State 模板列表
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api/ui-states", tags=["ui-states"])

# 依赖注入
ui_state_manager = None


def set_dependencies(ui_manager):
    """设置依赖（从 server.py 注入）"""
    global ui_state_manager
    ui_state_manager = ui_manager


@router.get("")
async def list_ui_states():
    """
    获取所有 UI State
    
    返回:
        - states: UI State 列表
    """
    try:
        states = await ui_state_manager.list_all_states()
        return {"states": states}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@router.get("/{state_id}")
async def get_ui_state(state_id: str):
    """
    获取单个 UI State
    
    参数:
        - state_id: 状态 ID
    
    返回:
        - state_id: 状态 ID
        - data: 状态数据
    """
    try:
        state = await ui_state_manager.get_state(state_id)
        
        if state is None:
            return JSONResponse(
                status_code=404,
                content={"error": f"State {state_id} not found"}
            )
        
        return {"state_id": state_id, "data": state}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@router.put("/{state_id}")
async def update_ui_state(state_id: str, request: Request):
    """
    更新 UI State
    
    参数:
        - state_id: 状态 ID
    
    请求体:
        - 任意 JSON 数据
    
    返回:
        - success: 是否成功
        - state_id: 状态 ID
        - message: 提示消息
    """
    try:
        data = await request.json()
        
        await ui_state_manager.set_state(state_id, data)
        
        return {
            "success": True,
            "state_id": state_id,
            "message": f"Updated state {state_id}"
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@router.get("/templates/list")
async def list_ui_state_templates():
    """
    获取 UI State 模板列表
    
    返回:
        - templates: 模板列表
    """
    try:
        templates = ui_state_manager.get_all_templates()
        return {"templates": templates}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@router.delete("/{state_id}")
async def delete_ui_state(state_id: str):
    """
    删除 UI State
    
    参数:
        - state_id: 状态 ID
    
    返回:
        - success: 是否成功
        - message: 提示消息
    """
    try:
        await ui_state_manager.delete_state(state_id)
        
        return {
            "success": True,
            "message": f"Deleted state {state_id}"
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )
