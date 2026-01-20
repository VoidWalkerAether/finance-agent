"""
Portfolio Schema 定义
定义持仓数据的标准JSON结构和默认值
"""

from typing import TypedDict, List, Optional


class HoldingSchema(TypedDict, total=False):
    """单个持仓的数据结构"""
    name: str                    # 必填：标的名称
    category: str                # 必填：资产类别（如：A股宽基、商品/黄金、港股/跨境）
    market_value: float          # 必填：市值金额
    percentage: str              # 必填：占总资产百分比（如："50%"）
    cost_price: Optional[float]  # 可选：成本价
    current_price: Optional[float]  # 可选：当前价格
    quantity: Optional[float]    # 可选：持仓数量
    status: Optional[str]        # 可选：状态描述（如："盈利中"）
    note: Optional[str]          # 可选：备注信息


class PortfolioSchemaV1(TypedDict):
    """完整持仓数据结构 V1"""
    total_asset_value: float     # 总资产价值
    cash_position: float         # 现金头寸
    holdings: List[HoldingSchema]  # 持仓明细列表


# ============================================================================
# 默认值定义
# ============================================================================

DEFAULT_HOLDING: HoldingSchema = {
    'name': '',
    'category': '',
    'market_value': 0.0,
    'percentage': '0%',
    'cost_price': None,
    'current_price': None,
    'quantity': None,
    'status': '',
    'note': ''
}

DEFAULT_PORTFOLIO: PortfolioSchemaV1 = {
    'total_asset_value': 0.0,
    'cash_position': 0.0,
    'holdings': []
}


# ============================================================================
# Schema 验证与规范化
# ============================================================================

def validate_holding(holding: dict) -> HoldingSchema:
    """
    验证并规范化单个持仓数据
    
    Args:
        holding: 原始持仓数据
        
    Returns:
        规范化后的持仓数据（缺失字段补默认值）
    """
    result: HoldingSchema = {
        'name': holding.get('name', ''),
        'category': holding.get('category', ''),
        'market_value': float(holding.get('market_value', 0.0)),
        'percentage': holding.get('percentage', '0%'),
    }
    
    # 可选字段
    if 'cost_price' in holding and holding['cost_price'] is not None:
        result['cost_price'] = float(holding['cost_price'])
    
    if 'current_price' in holding and holding['current_price'] is not None:
        result['current_price'] = float(holding['current_price'])
    
    if 'quantity' in holding and holding['quantity'] is not None:
        result['quantity'] = float(holding['quantity'])
    
    if 'status' in holding:
        result['status'] = str(holding['status'])
    
    if 'note' in holding:
        result['note'] = str(holding['note'])
    
    return result


def validate_portfolio(portfolio: dict) -> PortfolioSchemaV1:
    """
    验证并规范化完整持仓数据
    
    Args:
        portfolio: 原始持仓数据
        
    Returns:
        规范化后的持仓数据
        
    Raises:
        ValueError: 如果必填字段缺失
    """
    if 'total_asset_value' not in portfolio:
        raise ValueError("缺少必填字段: total_asset_value")
    
    if 'cash_position' not in portfolio:
        raise ValueError("缺少必填字段: cash_position")
    
    if 'holdings' not in portfolio:
        raise ValueError("缺少必填字段: holdings")
    
    result: PortfolioSchemaV1 = {
        'total_asset_value': float(portfolio['total_asset_value']),
        'cash_position': float(portfolio['cash_position']),
        'holdings': []
    }
    
    # 验证每个持仓
    for holding in portfolio['holdings']:
        result['holdings'].append(validate_holding(holding))
    
    return result


def fill_defaults(portfolio: dict) -> PortfolioSchemaV1:
    """
    填充缺失字段的默认值（容错处理）
    
    Args:
        portfolio: 部分持仓数据
        
    Returns:
        补全后的持仓数据
    """
    result: PortfolioSchemaV1 = {
        'total_asset_value': float(portfolio.get('total_asset_value', 0.0)),
        'cash_position': float(portfolio.get('cash_position', 0.0)),
        'holdings': []
    }
    
    if 'holdings' in portfolio and isinstance(portfolio['holdings'], list):
        for holding in portfolio['holdings']:
            result['holdings'].append(validate_holding(holding))
    
    return result
