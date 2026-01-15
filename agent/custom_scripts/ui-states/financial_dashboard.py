"""
金融仪表盘 UI State 模板

用途:
- 显示最新报告列表
- 展示投资组合概览
- 显示关键指标统计
"""

# UI State 配置 (必需导出)
config = {
    'id': 'financial_dashboard',
    'name': '金融仪表盘',
    'description': '显示最新报告、投资组合概览和关键统计信息',
    'initialState': {
        # 最新报告列表 (最多 10 条)
        'recent_reports': [],
        
        # 投资组合概览
        'portfolio_summary': {
            'total_value': 0,
            'total_gain': 0,
            'gain_percentage': 0,
            'last_updated': None
        },
        
        # 关键统计
        'statistics': {
            'total_reports': 0,
            'avg_importance_score': 0,
            'bullish_reports': 0,
            'bearish_reports': 0,
            'neutral_reports': 0
        },
        
        # 关注列表摘要
        'watchlist_summary': {
            'total_items': 0,
            'active_alerts': 0
        }
    }
}
