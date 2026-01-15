"""
关注列表监控 - Finance Agent Listener 插件

功能:
- 监听报告导入事件 (report_imported)
- 检测报告内容是否提到用户关注的标的
- 发送通知提醒用户
- 更新 UI State (watchlist_tracker)

使用场景:
用户添加"招商银行"到关注列表
→ 上传新报告
→ watchlist_monitor 自动检测
→ 发现报告提到"招商银行"
→ 发送通知: "您关注的招商银行出现在新报告中！"
"""

import re
from typing import Dict, List, Any, Optional
from datetime import datetime


# ============================================================================
# Listener 配置 (必需导出)
# ============================================================================

config = {
    "id": "watchlist_monitor",
    "name": "关注列表监控",
    "description": "自动检测报告是否提到用户关注的标的，并发送通知",
    "enabled": True,
    "event": "report_imported"  # 监听报告导入事件
}


# ============================================================================
# Handler 函数 (必需导出)
# ============================================================================

async def handler(event_data: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    监控关注列表的处理函数
    
    Args:
        event_data: 事件数据
            - report_id: 报告 ID
            - title: 报告标题
            - content: 报告内容
            - category: 报告分类
        context: ListenerContext 对象
            - database: 数据库管理器
            - notify(): 发送通知
            - ui_state: UI State 管理器
            - log(): 记录日志
    
    Returns:
        ListenerResult: {
            'executed': bool,
            'reason': str,
            'data': {...}
        }
    """
    
    # 1. 获取报告信息
    report_id = event_data.get('report_id', 'unknown')
    title = event_data.get('title', '未知标题')
    content = event_data.get('content', '')
    
    context.log(f"检测报告: {title}")
    
    # 2. 获取用户的关注列表
    try:
        watchlist = await context.database.watchlist.get_list(status="active")
        
        if not watchlist or len(watchlist) == 0:
            context.log("用户暂无关注项，跳过检测")
            return {
                'executed': False,
                'reason': '用户暂无关注项'
            }
        
        context.log(f"当前关注列表: {len(watchlist)} 个项目")
    
    except Exception as e:
        context.log(f"获取关注列表失败: {e}", "error")
        return {
            'executed': False,
            'reason': f'获取关注列表失败: {str(e)}'
        }
    
    # 3. 检测报告中是否提到关注的标的
    mentioned_items = []
    mention_details = []
    
    for item in watchlist:
        target_name = item['target_name']
        target_type = item['target_type']
        
        # 在报告内容中搜索标的名称（忽略空格和换行）
        # 处理 OCR 文本中可能的空格问题
        clean_content = re.sub(r'\s+', '', content)
        clean_target = re.sub(r'\s+', '', target_name)
        
        # 检查是否存在
        if clean_target in clean_content:
            mentioned_items.append(item)
            
            # 提取提到标的的上下文（前后各50字）
            context_snippet = _extract_context(content, target_name, context_length=50)
            
            mention_details.append({
                'id': item['id'],
                'name': target_name,
                'type': target_type,
                'context': context_snippet,
                'report_title': title
            })
            
            context.log(f"✓ 检测到关注标的: {target_name} ({target_type})")
    
    # 4. 如果没有匹配项，直接返回
    if not mentioned_items:
        context.log("未检测到关注标的")
        return {
            'executed': False,
            'reason': '未检测到关注标的'
        }
    
    # 5. 发送通知
    try:
        # 构建通知消息
        if len(mentioned_items) == 1:
            item = mentioned_items[0]
            type_text = _get_type_text(item['target_type'])
            message = f"您关注的{type_text} {item['target_name']} 出现在新报告《{title}》中！"
        else:
            names = [item['target_name'] for item in mentioned_items[:3]]
            names_text = '、'.join(names)
            if len(mentioned_items) > 3:
                names_text += f" 等 {len(mentioned_items)} 个标的"
            message = f"您关注的 {names_text} 出现在新报告《{title}》中！"
        
        await context.notify(
            message,
            {
                'priority': 'high',
                'type': 'watchlist_alert'
            }
        )
        
        context.log(f"✓ 已发送通知: {len(mentioned_items)} 个关注标的")
    
    except Exception as e:
        context.log(f"发送通知失败: {e}", "warn")
    
    # 6. 更新 UI State (watchlist_tracker)
    try:
        # 获取当前状态
        state = await context.ui_state.get('watchlist_tracker')
        
        # 如果不存在，初始化
        if not state:
            await context.ui_state.initialize_if_needed('watchlist_tracker')
            state = await context.ui_state.get('watchlist_tracker')
        
        # 如果仍然为空，创建默认结构
        if not state:
            state = {
                'alerts': [],
                'last_updated': None
            }
        
        # 确保 alerts 字段存在
        if 'alerts' not in state:
            state['alerts'] = []
        
        # 添加新的提醒记录
        state['alerts'].append({
            'date': datetime.now().isoformat(),
            'report_id': report_id,
            'report_title': title,
            'items': mention_details,
            'count': len(mentioned_items)
        })
        
        # 只保留最近 50 条提醒
        state['alerts'] = state['alerts'][-50:]
        state['last_updated'] = datetime.now().isoformat()
        
        # 保存状态
        await context.ui_state.set('watchlist_tracker', state)
        
        context.log(f"✓ 已更新 UI State: watchlist_tracker")
    
    except Exception as e:
        context.log(f"更新 UI State 失败: {e}", "warn")
    
    # 7. 返回执行结果
    return {
        'executed': True,
        'reason': f'检测到 {len(mentioned_items)} 个关注标的',
        'data': {
            'mentioned_count': len(mentioned_items),
            'items': mention_details,
            'report_id': report_id,
            'report_title': title
        }
    }


# ============================================================================
# 辅助函数
# ============================================================================

def _extract_context(content: str, target: str, context_length: int = 50) -> str:
    """
    提取标的名称周围的上下文
    
    Args:
        content: 完整内容
        target: 目标标的名称
        context_length: 上下文长度（前后各多少字符）
    
    Returns:
        上下文片段
    """
    # 移除空格和换行
    clean_content = re.sub(r'\s+', '', content)
    clean_target = re.sub(r'\s+', '', target)
    
    # 查找位置
    index = clean_content.find(clean_target)
    
    if index == -1:
        return ""
    
    # 提取上下文
    start = max(0, index - context_length)
    end = min(len(clean_content), index + len(clean_target) + context_length)
    
    context_snippet = clean_content[start:end]
    
    # 如果不是从开头开始，添加省略号
    if start > 0:
        context_snippet = "..." + context_snippet
    
    # 如果不是到结尾，添加省略号
    if end < len(clean_content):
        context_snippet = context_snippet + "..."
    
    return context_snippet


def _get_type_text(target_type: str) -> str:
    """
    获取标的类型的中文描述
    
    Args:
        target_type: 标的类型 (stock/etf/index/industry)
    
    Returns:
        中文描述
    """
    type_map = {
        'stock': '股票',
        'etf': 'ETF',
        'index': '指数',
        'industry': '行业'
    }
    
    return type_map.get(target_type, '标的')
