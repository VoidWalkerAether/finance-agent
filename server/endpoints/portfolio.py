"""
Portfolio API 端点

功能：
- 获取持仓数据
- 更新持仓数据
- 删除持仓数据
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])

# 依赖注入
db_manager = None


def set_dependencies(db):
    """设置依赖（从 server.py 注入）"""
    global db_manager
    db_manager = db


@router.get("")
async def get_portfolio(user_id: str = 'default'):
    """
    获取用户持仓数据
    
    参数:
        - user_id: 用户ID（可选，默认 'default'）
    
    返回:
        - success: 是否成功
        - data: 持仓数据
    """
    try:
        portfolio = await db_manager.portfolio.get_or_create_default_portfolio(user_id)
        
        return {
            "success": True,
            "data": portfolio
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@router.put("")
async def update_portfolio(request: Request):
    """
    更新用户持仓数据
    
    请求体:
        - user_id: 用户ID（可选，默认 'default'）
        - portfolio: 持仓数据（必需）
            - total_asset_value: 总资产价值
            - cash_position: 现金头寸
            - holdings: 持仓明细列表
    
    返回:
        - success: 是否成功
        - message: 提示消息
    """
    try:
        data = await request.json()
        
        user_id = data.get('user_id', 'default')
        portfolio_data = data.get('portfolio')
        
        if not portfolio_data:
            return JSONResponse(
                status_code=400,
                content={"error": "Missing required field: portfolio"}
            )
        
        # 验证并更新持仓
        await db_manager.portfolio.upsert_user_portfolio(user_id, portfolio_data)
        
        return {
            "success": True,
            "message": "Portfolio updated successfully"
        }
    except ValueError as e:
        # 数据验证错误
        return JSONResponse(
            status_code=400,
            content={"error": f"Portfolio validation failed: {str(e)}"}
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@router.delete("")
async def delete_portfolio(user_id: str = 'default'):
    """
    删除用户持仓数据
    
    参数:
        - user_id: 用户ID（可选，默认 'default'）
    
    返回:
        - success: 是否成功
        - message: 提示消息
    """
    try:
        deleted = await db_manager.portfolio.delete_user_portfolio(user_id)
        
        if deleted:
            return {
                "success": True,
                "message": "Portfolio deleted successfully"
            }
        else:
            return JSONResponse(
                status_code=404,
                content={"error": "Portfolio not found"}
            )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )
