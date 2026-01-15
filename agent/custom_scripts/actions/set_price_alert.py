"""
Action: 设置价格提醒

功能: 当标的价格达到目标值时发送通知
"""

from ccsdk.action_context import ActionContext
from ccsdk.message_types import ActionResult


# Action 配置
config = {
    'id': 'set_price_alert',
    'name': '设置价格提醒',
    'description': '当标的价格达到目标值时发送通知',
    'icon': '🔔',
    'parameterSchema': {
        'type': 'object',
        'properties': {
            'symbol': {
                'type': 'string',
                'description': '标的名称（如: SGE黄金9999）'
            },
            'target_price': {
                'type': 'number',
                'description': '目标价格'
            },
            'condition': {
                'type': 'string',
                'enum': ['<=', '>='],
                'description': '触发条件（<= 表示低于，>= 表示高于）'
            }
        },
        'required': ['symbol', 'target_price', 'condition']
    }
}


async def handler(params: dict, context: ActionContext) -> ActionResult:
    """
    执行函数
    
    Args:
        params: 参数
            - symbol: 标的名称
            - target_price: 目标价格
            - condition: 触发条件
        context: Action 上下文
    
    Returns:
        ActionResult: 执行结果
    """
    symbol = params['symbol']
    target_price = params['target_price']
    condition = params['condition']
    
    try:
        # 1. 创建价格提醒
        alert_id = await context.alert_api.create_alert(
            symbol=symbol,
            target_price=target_price,
            condition=condition
        )
        
        # 2. 更新 UI State
        state = await context.ui_state.get('price_alerts')
        if not state:
            # 首次使用，初始化状态
            await context.ui_state.initialize_if_needed('price_alerts')
            state = await context.ui_state.get('price_alerts')
        
        # 添加新提醒到状态
        if state and 'alerts' in state:
            state['alerts'].append({
                'id': alert_id,
                'symbol': symbol,
                'target_price': target_price,
                'condition': condition,
                'status': 'active',
                'created_at': context.database.get_current_timestamp()
            })
            await context.ui_state.set('price_alerts', state)
        
        # 3. 发送确认通知
        condition_text = '低于' if condition == '<=' else '高于'
        await context.notify(
            f"已设置 {symbol} 价格提醒: {condition_text} {target_price}",
            priority="normal",
            type="success"
        )
        
        context.log(f"创建价格提醒成功: {symbol} {condition} {target_price}")
        
        return ActionResult(
            success=True,
            message=f'已设置 {symbol} 价格提醒',
            data={
                'alert_id': alert_id,
                'symbol': symbol,
                'target_price': target_price,
                'condition': condition
            }
        )
    
    except Exception as e:
        context.log(f"创建价格提醒失败: {e}", "error")
        return ActionResult(
            success=False,
            message=f'设置价格提醒失败: {str(e)}'
        )
