"""
Principles Schema 定义
定义用户投资原则的标准JSON结构和验证逻辑
"""

from typing import TypedDict, Optional


class ThreeLowPrincipleSchema(TypedDict, total=False):
    """三低原则"""
    low_leverage: bool          # 低杠杆
    low_correlation: bool       # 低相关性
    low_concentration: bool     # 低集中度


class WeightManagementSchema(TypedDict, total=False):
    """仓位权重管理规则"""
    single_position_initial: float                # 单一品种初始权重（如 0.02 表示 2%）
    single_position_max_normal: float             # 单一品种常规上限（如 0.06 表示 6%）
    single_position_max_extreme: float            # 单一品种极端上限（如 0.08 表示 8%）
    extreme_condition: str                        # 极端情况描述
    target_position_count_min: int                # 目标持仓品种下限
    target_position_count_max: int                # 目标持仓品种上限
    target_market_count_min: int                  # 跨市场数量下限
    target_market_count_max: int                  # 跨市场数量上限
    three_low_principle: ThreeLowPrincipleSchema  # 三低原则


class DrawdownControlSchema(TypedDict, total=False):
    """回撤止损纪律"""
    single_stock_stop_loss_avg: float      # 个股平均止损（如 -0.128 表示 -12.8%）
    portfolio_nav_step_trigger: float      # 组合 NAV 回调触发阈值（如 0.025 表示 2.5%）
    portfolio_reduce_ratio_per_step: float # 每次触发后减仓比例（如 0.2 表示 20%）
    annual_nav_adjustment_max: float       # 年度净值调整上限（如 0.1 表示 10%）


class PrinciplesSchemaV1(TypedDict):
    """完整投资原则数据结构 V1"""
    profile_name: str                           # 原则档案名称
    version: str                                # 版本号
    last_updated: str                           # 最后更新时间
    weight_management: WeightManagementSchema   # 仓位权重管理
    drawdown_control: DrawdownControlSchema     # 回撤止损纪律


# ============================================================================
# 默认值定义
# ============================================================================

DEFAULT_THREE_LOW: ThreeLowPrincipleSchema = {
    'low_leverage': True,
    'low_correlation': True,
    'low_concentration': True
}

DEFAULT_WEIGHT_MANAGEMENT: WeightManagementSchema = {
    'single_position_initial': 0.02,
    'single_position_max_normal': 0.1,
    'single_position_max_extreme': 0.2,
    'extreme_condition': '分析师命中率极高且回撤受控',
    'target_position_count_min': 5,
    'target_position_count_max': 10,
    'target_market_count_min': 6,
    'target_market_count_max': 9,
    'three_low_principle': DEFAULT_THREE_LOW
}

DEFAULT_DRAWDOWN_CONTROL: DrawdownControlSchema = {
    'single_stock_stop_loss_avg': -0.128,
    'portfolio_nav_step_trigger': 0.025,
    'portfolio_reduce_ratio_per_step': 0.2,
    'annual_nav_adjustment_max': 0.1
}

DEFAULT_PRINCIPLES: PrinciplesSchemaV1 = {
    'profile_name': 'default_investment_principles',
    'version': '1.0',
    'last_updated': '2026-01-20',
    'weight_management': DEFAULT_WEIGHT_MANAGEMENT,
    'drawdown_control': DEFAULT_DRAWDOWN_CONTROL
}


# ============================================================================
# Schema 验证与规范化
# ============================================================================

def validate_weight_management(wm: dict) -> WeightManagementSchema:
    """
    验证并规范化仓位权重管理数据
    
    Args:
        wm: 原始仓位权重数据
        
    Returns:
        规范化后的数据
    """
    result: WeightManagementSchema = {
        'single_position_initial': float(wm.get('single_position_initial', 0.02)),
        'single_position_max_normal': float(wm.get('single_position_max_normal', 0.06)),
        'single_position_max_extreme': float(wm.get('single_position_max_extreme', 0.08)),
        'extreme_condition': str(wm.get('extreme_condition', '分析师命中率极高且回撤受控')),
        'target_position_count_min': int(wm.get('target_position_count_min', 50)),
        'target_position_count_max': int(wm.get('target_position_count_max', 70)),
        'target_market_count_min': int(wm.get('target_market_count_min', 6)),
        'target_market_count_max': int(wm.get('target_market_count_max', 9)),
    }
    
    # 三低原则
    three_low = wm.get('three_low_principle', {})
    result['three_low_principle'] = {
        'low_leverage': bool(three_low.get('low_leverage', True)),
        'low_correlation': bool(three_low.get('low_correlation', True)),
        'low_concentration': bool(three_low.get('low_concentration', True))
    }
    
    return result


def validate_drawdown_control(dc: dict) -> DrawdownControlSchema:
    """
    验证并规范化回撤止损数据
    
    Args:
        dc: 原始回撤止损数据
        
    Returns:
        规范化后的数据
    """
    result: DrawdownControlSchema = {
        'single_stock_stop_loss_avg': float(dc.get('single_stock_stop_loss_avg', -0.128)),
        'portfolio_nav_step_trigger': float(dc.get('portfolio_nav_step_trigger', 0.025)),
        'portfolio_reduce_ratio_per_step': float(dc.get('portfolio_reduce_ratio_per_step', 0.2)),
        'annual_nav_adjustment_max': float(dc.get('annual_nav_adjustment_max', 0.1))
    }
    
    return result


def validate_principles(principles: dict) -> PrinciplesSchemaV1:
    """
    验证并规范化完整投资原则数据
    
    Args:
        principles: 原始投资原则数据
        
    Returns:
        规范化后的数据
        
    Raises:
        ValueError: 如果必填字段缺失或格式不正确
    """
    if 'profile_name' not in principles:
        raise ValueError("缺少必填字段: profile_name")
    
    if 'weight_management' not in principles:
        raise ValueError("缺少必填字段: weight_management")
    
    if 'drawdown_control' not in principles:
        raise ValueError("缺少必填字段: drawdown_control")
    
    result: PrinciplesSchemaV1 = {
        'profile_name': str(principles['profile_name']),
        'version': str(principles.get('version', '1.0')),
        'last_updated': str(principles.get('last_updated', '')),
        'weight_management': validate_weight_management(principles['weight_management']),
        'drawdown_control': validate_drawdown_control(principles['drawdown_control'])
    }
    
    return result


def fill_principles_defaults(principles: dict) -> PrinciplesSchemaV1:
    """
    填充缺失字段的默认值（容错处理）
    
    Args:
        principles: 部分投资原则数据
        
    Returns:
        补全后的数据
    """
    result: PrinciplesSchemaV1 = {
        'profile_name': str(principles.get('profile_name', 'default_investment_principles')),
        'version': str(principles.get('version', '1.0')),
        'last_updated': str(principles.get('last_updated', '2026-01-20')),
        'weight_management': DEFAULT_WEIGHT_MANAGEMENT.copy(),
        'drawdown_control': DEFAULT_DRAWDOWN_CONTROL.copy()
    }
    
    # 如果有 weight_management，尝试合并
    if 'weight_management' in principles:
        try:
            result['weight_management'] = validate_weight_management(principles['weight_management'])
        except Exception:
            pass  # 使用默认值
    
    # 如果有 drawdown_control，尝试合并
    if 'drawdown_control' in principles:
        try:
            result['drawdown_control'] = validate_drawdown_control(principles['drawdown_control'])
        except Exception:
            pass  # 使用默认值
    
    return result


def principles_to_readable_text(principles: PrinciplesSchemaV1) -> str:
    """
    将投资原则 JSON 转换为易读的文本摘要（用于 LLM Prompt）
    
    Args:
        principles: 投资原则数据
        
    Returns:
        文本摘要
    """
    wm = principles['weight_management']
    dc = principles['drawdown_control']
    
    text_parts = [
        f"【投资原则档案：{principles['profile_name']}】",
        "",
        "第一部分：仓位权重限制",
        f"- 单一品种初始权重：{wm['single_position_initial']*100:.1f}%",
        f"- 单一品种常规上限：{wm['single_position_max_normal']*100:.1f}%",
        f"- 单一品种极端上限：{wm['single_position_max_extreme']*100:.1f}%（条件：{wm['extreme_condition']}）",
        f"- 目标持仓数量：{wm['target_position_count_min']}-{wm['target_position_count_max']} 个品种",
        f"- 跨市场数量：{wm['target_market_count_min']}-{wm['target_market_count_max']} 个市场",
        f"- 三低原则：低杠杆={wm['three_low_principle']['low_leverage']}、低相关={wm['three_low_principle']['low_correlation']}、低集中度={wm['three_low_principle']['low_concentration']}",
        "",
        "第二部分：回撤止损纪律",
        f"- 个股平均止损：{dc['single_stock_stop_loss_avg']*100:.1f}%",
        f"- 组合 NAV 每回调 {dc['portfolio_nav_step_trigger']*100:.1f}%，必须砍掉 {dc['portfolio_reduce_ratio_per_step']*100:.0f}% 的总头寸",
        f"- 年度净值调整上限：{dc['annual_nav_adjustment_max']*100:.0f}%"
    ]
    
    return "\n".join(text_parts)
