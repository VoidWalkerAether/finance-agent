"""
价格提醒 UI State 模板

用途:
- 显示所有活跃的价格提醒
- 追踪已触发的提醒历史
"""

# UI State 配置 (必需导出)
config = {
    'id': 'price_alerts',
    'name': '价格提醒',
    'description': '管理和显示价格提醒列表',
    'initialState': {
        # 活跃的提醒
        'alerts': [
            # {
            #     'id': 'alert_123',
            #     'symbol': 'SGE黄金9999',
            #     'target_price': 3850,
            #     'condition': '<=',  # '<=' 或 '>='
            #     'status': 'active',  # 'active' | 'triggered' | 'disabled'
            #     'created_at': '2025-01-06T10:30:00Z',
            #     'triggered_at': None
            # }
        ],
        
        # 已触发的提醒历史 (最多 20 条)
        'history': [],
        
        # 统计信息
        'stats': {
            'total_active': 0,
            'total_triggered': 0
        }
    }
}
