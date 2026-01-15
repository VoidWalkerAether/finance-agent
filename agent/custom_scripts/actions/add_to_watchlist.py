"""  
Action: 添加到关注列表

功能: 将标的添加到用户的关注列表
"""

from datetime import datetime
from ccsdk.action_context import ActionContext
from ccsdk.message_types import ActionResult


# Action 配置
config = {
    'id': 'add_to_watchlist',
    'name': '添加到关注列表',
    'description': '将标的添加到用户的关注列表',
    'icon': '⭐',
    'parameterSchema': {
        'type': 'object',
        'properties': {
            'target_name': {
                'type': 'string',
                'description': '标的名称（如: 招商银行、上证指数）'
            },
            'target_type': {
                'type': 'string',
                'enum': ['stock', 'etf', 'index', 'industry'],
                'description': '标的类型',
                'default': 'stock'
            }
        },
        'required': ['target_name']
    }
}


async def handler(params: dict, context: ActionContext) -> ActionResult:
    """
    执行函数
    
    Args:
        params: 参数
            - target_name: 标的名称
            - target_type: 标的类型
        context: Action 上下文
    
    Returns:
        ActionResult: 执行结果
    """
    target_name = params['target_name']
    target_type = params.get('target_type', 'stock')
    
    try:
        # 1. 添加到关注列表
        item_id = await context.watchlist_api.add_to_watchlist(
            target_name=target_name,
            target_type=target_type,
            notes=f"通过 Action 添加: {target_type}"
        )
        
        context.log(f"添加关注成功: {target_name} (ID: {item_id})")
        
        # 2. 更新 UI State (刷新关注列表)
        current_state = await context.ui_state.get('watchlist_tracker')
        if not current_state:
            await context.ui_state.initialize_if_needed('watchlist_tracker')
            current_state = await context.ui_state.get('watchlist_tracker')
        
        # 获取最新的关注列表
        watchlist = await context.watchlist_api.get_watchlist()
        if current_state and 'items' in current_state:
            current_state['items'] = watchlist
            current_state['last_updated'] = datetime.now().isoformat()
            await context.ui_state.set('watchlist_tracker', current_state)
            context.log(f"UI State 已更新: {len(watchlist)} 个关注项")
        
        # 3. 发送通知
        type_text = {
            'stock': '股票',
            'etf': 'ETF',
            'index': '指数',
            'industry': '行业'
        }.get(target_type, '标的')
        
        await context.notify(
            f"已添加 {target_name} ({type_text}) 到关注列表",
            priority="normal",
            type="success"
        )
        
        # 4. 返回成功结果
        return ActionResult(
            success=True,
            message=f'已添加 {target_name} 到关注列表',
            data={
                'item_id': item_id,
                'target_name': target_name,
                'target_type': target_type,
                'total_items': len(watchlist) if watchlist else 0
            }
        )
    
    except Exception as e:
        context.log(f"添加关注失败: {e}", "error")
        return ActionResult(
            success=False,
            message=f'添加到关注列表失败: {str(e)}'
        )
