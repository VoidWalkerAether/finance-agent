"""
Actions API 端点

功能：
- 获取 Action 模板列表
- 执行 Action
- 获取 Action 执行历史
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api/actions", tags=["actions"])

# 依赖注入
actions_manager = None


def set_dependencies(actions):
    """设置依赖（从 server.py 注入）"""
    global actions_manager
    actions_manager = actions


@router.get("/templates")
async def list_action_templates():
    """
    获取 Action 模板列表
    
    返回:
        - templates: Action 模板数组
    """
    try:
        templates = actions_manager.get_all_templates()
        return {"templates": templates}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@router.post("/execute")
async def execute_action(request: Request):
    """
    执行 Action
    
    请求体:
        - instance_id: 组件实例 ID（必需）
        - session_id: 会话 ID（可选）
    
    返回:
        - Action 执行结果
    """
    try:
        data = await request.json()
        instance_id = data.get("instance_id")
        session_id = data.get("session_id")
        
        if not instance_id:
            return JSONResponse(
                status_code=400,
                content={"error": "instance_id is required"}
            )
        
        # 执行 Action（通过 ActionsManager）
        result = await actions_manager.execute_action(
            instance_id=instance_id,
            session_id=session_id
        )
        
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@router.get("/stats")
async def get_action_stats():
    """
    获取 Action 统计信息
    
    返回:
        - total_templates: 模板总数
        - template_list: 模板列表
    """
    try:
        templates = actions_manager.get_all_templates()
        return {
            "total_templates": len(templates),
            "template_list": [t.get('id') for t in templates]
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )
