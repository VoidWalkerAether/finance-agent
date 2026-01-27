import asyncio
import json
import sys
import os
from pathlib import Path
import sqlite3
from typing import Dict, Any, List

# 更加稳健的项目根目录计算方式
CURRENT_FILE = Path(__file__).resolve()
ROOT_DIR = CURRENT_FILE.parents[4]

# 不再导入 server.services.portfolio_audit，直接在此实现简化版审计逻辑

def get_portfolio_from_db(db_path: str, user_id: str) -> Dict[str, Any]:
    """从数据库获取持仓数据"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 从 user_portfolios 表获取数据
    cursor.execute(
        "SELECT total_asset_value, cash_position, holdings_json FROM user_portfolios WHERE user_id = ?",
        (user_id,)
    )
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return {"holdings": [], "total_asset_value": 0, "cash_position": 0}
    
    # 解析 holdings_json
    try:
        holdings = json.loads(row["holdings_json"])
    except (json.JSONDecodeError, TypeError):
        holdings = []
    
    return {
        "holdings": holdings,
        "total_asset_value": row["total_asset_value"],
        "cash_position": row["cash_position"]
    }

def get_principles_from_db(db_path: str, user_id: str) -> Dict[str, Any]:
    """从数据库获取投资原则"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 从 user_investment_principles 表获取，按更新时间倒序取最新一条激活原则
    cursor.execute(
        """
        SELECT principles_json, version 
        FROM user_investment_principles 
        WHERE user_id = ? AND is_active = 1
        ORDER BY updated_at DESC
        LIMIT 1
        """,
        (user_id,)
    )
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return {}
    
    try:
        return json.loads(row["principles_json"])
    except (json.JSONDecodeError, TypeError):
        return {}

def check_violations(portfolio: Dict, principles: Dict) -> List[Dict[str, Any]]:
    """检查违规项"""
    violations = []
    
    holdings = portfolio.get("holdings", [])
    total_asset = portfolio.get("total_asset_value", 0)
    cash = portfolio.get("cash_position", 0)
    
    if total_asset == 0:
        return [{"rule": "no_data", "severity": "error", "message": "没有持仓数据"}]
    
    wm = principles.get("weight_management", {})
    
    # 检查单一标的权重
    single_max_normal = wm.get("single_position_max_normal", 0.2)
    single_max_extreme = wm.get("single_position_max_extreme", 0.3)
    
    for holding in holdings:
        weight = holding.get("market_value", 0) / total_asset
        name = holding.get("name", holding.get("symbol", "unknown"))
        
        if weight > single_max_extreme:
            violations.append({
                "rule": "single_position_max_extreme",
                "severity": "critical",
                "message": f"{name} 权重 {weight*100:.1f}% 超过极限上限 {single_max_extreme*100:.1f}%"
            })
        elif weight > single_max_normal:
            violations.append({
                "rule": "single_position_max_normal",
                "severity": "warning",
                "message": f"{name} 权重 {weight*100:.1f}% 超过常规上限 {single_max_normal*100:.1f}%"
            })
    
    # 检查持仓数量
    target_count_min = wm.get("target_position_count_min", 5)
    target_count_max = wm.get("target_position_count_max", 15)
    actual_count = len(holdings)
    
    if actual_count < target_count_min:
        violations.append({
            "rule": "position_count_too_low",
            "severity": "warning",
            "message": f"持仓数量 {actual_count} 低于目标下限 {target_count_min}"
        })
    elif actual_count > target_count_max:
        violations.append({
            "rule": "position_count_too_high",
            "severity": "info",
            "message": f"持仓数量 {actual_count} 高于目标上限 {target_count_max}"
        })
    
    # 检查现金占比
    cash_ratio = cash / total_asset
    target_cash_max = wm.get("target_cash_ratio_max", 0.2)
    
    if cash_ratio > target_cash_max:
        violations.append({
            "rule": "cash_ratio_too_high",
            "severity": "info",
            "message": f"现金占比 {cash_ratio*100:.1f}% 高于目标上限 {target_cash_max*100:.1f}%"
        })
    
    return violations

async def main():
    user_id = sys.argv[1] if len(sys.argv) > 1 else "default"
    db_path = os.environ.get("DB_PATH", str(ROOT_DIR / "finance_agent.db"))
    
    # 增加实时执行日志 (输出到 stderr 以免干扰 JSON 解析)
    print(f"🚀 [Audit Skill] 脚本启动 - 根目录: {ROOT_DIR}", file=sys.stderr)
    print(f"📁 [Audit Skill] 使用数据库: {db_path}", file=sys.stderr)
    
    if not os.path.exists(db_path):
        print(json.dumps({"error": f"Database not found at {db_path}"}, ensure_ascii=False))
        sys.exit(1)
        
    try:
        print(f"📊 [Audit Skill] 正在为用户 '{user_id}' 执行组合审计...", file=sys.stderr)
        
        # 直接使用本地函数，不再依赖外部模块
        portfolio = get_portfolio_from_db(db_path, user_id)
        principles = get_principles_from_db(db_path, user_id)
        
        if not principles:
            print(json.dumps({
                "error": "未找到投资原则",
                "user_id": user_id
            }, ensure_ascii=False))
            sys.exit(1)
        
        violations = check_violations(portfolio, principles)
        
        # 计算总体状态
        overall_status = "ok"
        if any(v["severity"] == "critical" for v in violations):
            overall_status = "critical"
        elif any(v["severity"] == "warning" for v in violations):
            overall_status = "warning"
        elif violations:
            overall_status = "info"
        
        result = {
            "user_id": user_id,
            "overall_status": overall_status,
            "violations": violations,
            "summary": f"共发现 {len(violations)} 个问题" if violations else "组合完全符合投资原则"
        }
        
        print(f"✅ [Audit Skill] 审计完成，返回结果。", file=sys.stderr)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
    except Exception as e:
        import traceback
        print(json.dumps({"error": str(e), "traceback": traceback.format_exc()}, ensure_ascii=False))
        sys.exit(1)

if __name__ == "__main__":
    try:
        # 在脚本最开始打印当前工作目录，这能解决 90% 的路径困惑
        print(f"📍 [Audit Skill] 当前工作目录 (CWD): {os.getcwd()}", file=sys.stderr)
        asyncio.run(main())
    except Exception as e:
        import traceback
        print(json.dumps({
            "error": str(e),
            "traceback": traceback.format_exc(),
            "cwd": os.getcwd(),
            "python_path": sys.path[:3]
        }, ensure_ascii=False))
        sys.exit(1)
