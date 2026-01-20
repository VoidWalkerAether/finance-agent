"""
Principles API 端点

功能：
- 获取用户投资原则
- 更新用户投资原则
- 列出所有投资原则档案
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api/principles", tags=["principles"])

# 依赖注入
db_manager = None


def set_dependencies(db):
    """设置依赖（从 server.py 注入）"""
    global db_manager
    db_manager = db


@router.get("")
async def get_principles(user_id: str = 'default'):
    """
    获取用户当前激活的投资原则
    
    参数:
        - user_id: 用户ID（可选，默认 'default'）
    
    返回:
        - success: 是否成功
        - data: 投资原则数据
    """
    try:
        principles = await db_manager.principles.get_active_principles(user_id)
        
        return {
            "success": True,
            "data": principles
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@router.get("/list")
async def list_principles(user_id: str = 'default'):
    """
    列出用户的所有投资原则档案
    
    参数:
        - user_id: 用户ID（可选，默认 'default'）
    
    返回:
        - success: 是否成功
        - data: 投资原则档案列表
    """
    try:
        principles_list = await db_manager.principles.list_user_principles(user_id)
        
        return {
            "success": True,
            "data": principles_list
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@router.put("")
async def update_principles(request: Request):
    """
    创建或更新用户投资原则
    
    请求体:
        - user_id: 用户ID（可选，默认 'default'）
        - principles: 投资原则数据（必需）
            - profile_name: 档案名称
            - version: 版本号
            - weight_management: 仓位权重管理
            - drawdown_control: 回撤止损纪律
        - is_active: 是否激活（可选，默认 true）
    
    返回:
        - success: 是否成功
        - message: 提示消息
    """
    try:
        data = await request.json()
        
        user_id = data.get('user_id', 'default')
        principles_data = data.get('principles')
        is_active = data.get('is_active', True)
        
        if not principles_data:
            return JSONResponse(
                status_code=400,
                content={"error": "Missing required field: principles"}
            )
        
        # 验证并更新投资原则
        await db_manager.principles.upsert_user_principles(
            user_id=user_id,
            principles_data=principles_data,
            is_active=is_active
        )
        
        return {
            "success": True,
            "message": "Principles updated successfully"
        }
    except ValueError as e:
        # 数据验证错误
        return JSONResponse(
            status_code=400,
            content={"error": f"Principles validation failed: {str(e)}"}
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@router.post("/activate")
async def activate_principles(request: Request):
    """
    激活指定的投资原则档案
    
    请求体:
        - user_id: 用户ID（必需）
        - profile_name: 要激活的档案名称（必需）
    
    返回:
        - success: 是否成功
        - message: 提示消息
    """
    try:
        data = await request.json()
        
        user_id = data.get('user_id')
        profile_name = data.get('profile_name')
        
        if not user_id or not profile_name:
            return JSONResponse(
                status_code=400,
                content={"error": "Missing required fields: user_id, profile_name"}
            )
        
        success = await db_manager.principles.set_active_principles(user_id, profile_name)
        
        if success:
            return {
                "success": True,
                "message": f"Principles '{profile_name}' activated successfully"
            }
        else:
            return JSONResponse(
                status_code=404,
                content={"error": f"Principles '{profile_name}' not found"}
            )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@router.delete("")
async def delete_principles(user_id: str = 'default', profile_name: str = None):
    """
    删除用户投资原则
    
    参数:
        - user_id: 用户ID（可选，默认 'default'）
        - profile_name: 档案名称（可选，不指定则删除该用户所有原则）
    
    返回:
        - success: 是否成功
        - message: 提示消息
    """
    try:
        deleted = await db_manager.principles.delete_user_principles(user_id, profile_name)
        
        if deleted:
            return {
                "success": True,
                "message": "Principles deleted successfully"
            }
        else:
            return JSONResponse(
                status_code=404,
                content={"error": "Principles not found"}
            )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )
