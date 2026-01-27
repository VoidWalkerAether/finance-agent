"""
Portfolio API 端点

功能：
- 获取持仓数据
- 更新持仓数据
- 删除持仓数据
- 生成投资建议
"""

import json
import sys
from pathlib import Path
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

# 添加项目路径
sys.path.append(str(Path(__file__).parent.parent.parent))

# 导入投资建议生成器
from agent.custom_scripts.portfolio_advice_generator import generate_portfolio_advice
# 导入投资审计服务
from server.services.portfolio_audit import audit_portfolio_against_principles

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


@router.post("/advice")
async def generate_advice(request: Request):
    """
    生成投资建议（基于持仓 + 报告 + 原则）
    
    请求体:
        - user_id: 用户ID（可选，默认 'default'）
        - report_id: 报告 ID（必需）
        - principles_override: 临时覆盖的投资原则（可选）
    
    返回:
        - success: 是否成功
        - data: 投资建议数据
            - rebalancing: 整体仓位调整建议
            - actions: 标的操作清单
            - timing_and_risks: 时机与风险
            - constraints_check: 原则检查结果
    """
    try:
        data = await request.json()
        
        user_id = data.get('user_id', 'default')
        report_id = data.get('report_id')
        principles_override = data.get('principles_override')
        
        if not report_id:
            return JSONResponse(
                status_code=400,
                content={"error": "Missing required field: report_id"}
            )
        
        # 1. 获取报告数据
        report = await db_manager.get_report(report_id)
        if not report:
            return JSONResponse(
                status_code=404,
                content={"error": f"Report '{report_id}' not found"}
            )
        
        # 解析报告分析 JSON
        try:
            report_analysis = json.loads(report['analysis_json'])
        except (json.JSONDecodeError, KeyError) as e:
            return JSONResponse(
                status_code=500,
                content={"error": f"Failed to parse report analysis: {str(e)}"}
            )
        
        # 2. 获取用户持仓
        portfolio = await db_manager.portfolio.get_or_create_default_portfolio(user_id)
        
        # 检查持仓是否为空
        if portfolio['total_asset_value'] == 0:
            return JSONResponse(
                status_code=400,
                content={
                    "error": "Portfolio is empty. Please update your portfolio first.",
                    "hint": "Use PUT /api/portfolio to set your portfolio data"
                }
            )
        
        # 3. 获取投资原则（优先使用 override）
        if principles_override:
            from database.schemas import validate_principles
            try:
                principles = validate_principles(principles_override)
            except ValueError as e:
                return JSONResponse(
                    status_code=400,
                    content={"error": f"Invalid principles_override: {str(e)}"}
                )
        else:
            principles = await db_manager.principles.get_active_principles(user_id)
        
        # 4. 生成投资建议
        advice = await generate_portfolio_advice(
            portfolio=portfolio,
            report_analysis=report_analysis,
            principles=principles,
            history_reports=None  # TODO: 后续可增加历史报告
        )
        
        # 5. 检查是否有错误
        if 'error' in advice:
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Failed to generate advice",
                    "details": advice.get('error'),
                    "raw_response": advice.get('raw_response', '')[:500]
                }
            )
        
        return {
            "success": True,
            "data": advice
        }
        
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={"error": str(e)}
        )
    except Exception as e:
        import traceback
        return JSONResponse(
            status_code=500,
            content={
                "error": str(e),
                "traceback": traceback.format_exc()
            }
        )


@router.get("/audit")
async def audit_portfolio(user_id: str = 'default'):
    """
    审计投资组合与原则的一致性
    
    Skill: audit_portfolio_against_principles
    功能：检查投资组合是否符合投资原则约束
    
    参数:
        - user_id: 用户ID（可选，默认 'default'）
    
    返回:
        - success: 是否成功
        - data: 审计结果
            - overall_status: 总体状态 (ok/warning/violated)
            - violation_count: 违规数量
            - warning_count: 警告数量
            - violations: 违规详情列表
    """
    try:
        # 调用 Skill
        audit_result = await audit_portfolio_against_principles(
            db_path=db_manager.db_path,
            user_id=user_id
        )
        
        return {
            "success": True,
            "data": audit_result
        }
        
    except Exception as e:
        import traceback
        return JSONResponse(
            status_code=500,
            content={
                "error": str(e),
                "traceback": traceback.format_exc()
            }
        )
