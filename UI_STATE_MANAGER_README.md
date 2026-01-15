# UIStateManager 使用指南

## 📋 概述

UIStateManager 是 Finance Agent 的 UI 状态管理系统，负责：
- 📦 **模板管理** - 自动加载 UI State 模板定义
- 💾 **持久化存储** - 将状态数据保存到 SQLite 数据库
- 🔄 **实时广播** - 通过 WebSocket 推送状态更新
- 📝 **日志记录** - JSONL 格式的审计跟踪
- 🔥 **热重载** - 开发时自动重新加载模板 (需安装 watchdog)
- 🌐 **WebSocket 集成** - 与 WebSocketHandler 无缝集成，自动广播更新

## 🚀 快速开始

### 1. 安装依赖

```bash
# 基础依赖 (已包含在 requirements.txt)
pip install aiosqlite

# 可选：热重载功能
pip install watchdog
```

### 2. 创建 UI State 模板

在 `agent/custom_scripts/ui-states/` 目录下创建 `.py` 文件：

```python
# agent/custom_scripts/ui-states/my_dashboard.py

config = {
    'id': 'my_dashboard',
    'name': '我的仪表盘',
    'description': '显示自定义数据',
    'initialState': {
        'items': [],
        'total': 0
    }
}
```

### 3. 在代码中使用

```python
from ccsdk.ui_state_manager import UIStateManager
from database.database_manager import DatabaseManager

# 初始化
db = DatabaseManager()
ui_manager = UIStateManager(db)

# 加载模板
await ui_manager.load_all_templates()

# 获取状态 (自动使用 initialState)
state = await ui_manager.get_state('my_dashboard')

# 更新状态
state['items'].append({'name': 'Item 1'})
state['total'] = 1
await ui_manager.set_state('my_dashboard', state)
# ↑ 自动保存到数据库 + WebSocket 广播
```

## 📚 核心功能

### 1. 模板加载

```python
# 加载所有模板
templates = await ui_manager.load_all_templates()

# 获取单个模板
template = ui_manager.get_template('financial_dashboard')
print(template.id, template.name, template.initialState)
```

### 2. 状态 CRUD

```python
# 获取状态
state = await ui_manager.get_state('price_alerts')

# 设置/更新状态
await ui_manager.set_state('price_alerts', {
    'alerts': [...],
    'stats': {...}
})

# 列出所有状态
all_states = await ui_manager.list_states()

# 删除状态
await ui_manager.delete_state('old_state')
```

### 3. 状态初始化

```python
# 如果状态不存在,使用模板的 initialState 自动初始化
initialized = await ui_manager.initialize_state_if_needed('my_dashboard')

if initialized:
    print("状态已初始化")
else:
    print("状态已存在")
```

### 4. 订阅状态更新

```python
# 订阅所有状态更新 (用于 WebSocket 广播)
def on_state_update(state_id: str, data: Any):
    print(f"状态 {state_id} 已更新")
    # 广播到 WebSocket 客户端
    await websocket.send_json({
        'type': 'ui_state_update',
        'stateId': state_id,
        'data': data
    })

unsubscribe = ui_manager.on_state_update(on_state_update)

# 取消订阅
unsubscribe()
```

### 5. 热重载 (开发时)

```python
# 启动文件监听 (需要安装 watchdog)
async def on_templates_changed(templates):
    print(f"模板已重新加载: {len(templates)} 个")
    # 广播到前端
    await websocket.broadcast_templates_update(templates)

await ui_manager.watch_templates(on_templates_changed)

# 停止监听
ui_manager.stop_watching()
```

## 🎯 在 Listener 中使用

```python
# agent/custom_scripts/listeners/report_analyzer.py

async def handler(event_data, context):
    # 分析报告
    analysis = await analyze_report(event_data['content'])
    
    # 更新 UI State
    dashboard = await context.ui_state.get('financial_dashboard')
    
    if not dashboard:
        # 首次使用时初始化
        await context.ui_state.initialize_if_needed('financial_dashboard')
        dashboard = await context.ui_state.get('financial_dashboard')
    
    # 添加报告到列表
    dashboard['recent_reports'].insert(0, {
        'title': analysis['title'],
        'importance': analysis['importance_score']
    })
    
    # 保存 (自动触发 WebSocket 广播)
    await context.ui_state.set('financial_dashboard', dashboard)
    
    return {'executed': True}
```

## 📂 文件结构

```
finance-agent/
├── ccsdk/
│   ├── ui_state_manager.py          # UIStateManager 实现
│   └── types.py                     # UIStateTemplate 类型定义
├── database/
│   ├── database_manager.py          # UI State 数据库操作
│   └── schema.sql                   # ui_states 表定义
├── agent/custom_scripts/
│   ├── ui-states/                   # UI State 模板目录
│   │   ├── financial_dashboard.py  # 示例模板
│   │   └── price_alerts.py         # 示例模板
│   └── .logs/
│       └── ui-states/               # JSONL 日志
│           └── 2025-12-01.jsonl
└── scripts/
    ├── test_ui_state_manager.py       # 完整测试 (需要 watchdog)
    ├── test_ui_state_simple.py        # 基础测试 (不需要 watchdog)
    └── test_websocket_integration.py  # WebSocket 集成测试
```

## 🗄️ 数据库表结构

```sql
CREATE TABLE ui_states (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  state_id TEXT UNIQUE NOT NULL,
  data_json TEXT NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

## 📝 日志格式

```jsonl
{"timestamp":"2025-12-01T10:30:00Z","stateId":"financial_dashboard","action":"update","dataSize":1234}
{"timestamp":"2025-12-01T10:35:00Z","stateId":"price_alerts","action":"update","dataSize":567}
```

## 🔧 运行测试

```bash
# 基础测试 (不需要 watchdog)
python scripts/test_ui_state_simple.py

# 完整测试 (需要 watchdog)
python scripts/test_ui_state_manager.py

# 热重载测试 (需要 watchdog)
python scripts/test_ui_state_manager.py --hot-reload
```

## ⚠️ 注意事项

1. **热重载功能可选** - 如果未安装 `watchdog`，其他功能仍正常工作
2. **状态 ID 必须与模板 ID 一致** - `get_state('my_dashboard')` 会优先从数据库读取，不存在时返回模板的 `initialState`
3. **数据持久化** - 所有状态更新都会立即保存到数据库
4. **并发安全** - 使用 SQLite 的事务机制确保数据一致性

## 🌐 WebSocket 集成

UIStateManager 与 [`WebSocketHandler`](./ccsdk/websocket_handler.py) 集成，实现实时 UI 状态广播。

### 初始化集成

```python
from ccsdk.websocket_handler import WebSocketHandler
from ccsdk.ui_state_manager import UIStateManager
from database.database_manager import DatabaseManager

# 1. 初始化 UI State Manager
db = DatabaseManager()
ui_manager = UIStateManager(db)
await ui_manager.load_all_templates()

# 2. 注入到 WebSocketHandler
ws_handler = WebSocketHandler(
    db_manager=db,
    ui_state_manager=ui_manager  # ← 注入 UIStateManager
)

await ws_handler.start()
```

### 自动广播机制

当 UIStateManager 被注入到 WebSocketHandler 后：

1. **客户端连接时** - 自动发送所有 UI State 模板列表
   ```json
   {
     "type": "ui_state_templates",
     "templates": [
       {"id": "financial_dashboard", "name": "金融仪表盘", "description": "..."},
       {"id": "price_alerts", "name": "价格提醒", "description": "..."}
     ]
   }
   ```

2. **状态更新时** - 自动广播到所有连接的客户端
   ```python
   # 更新 UI State
   await ui_manager.set_state('financial_dashboard', new_state)
   
   # ↑ 自动触发 WebSocket 广播
   # {
   #   "type": "ui_state_update",
   #   "stateId": "financial_dashboard",
   #   "data": {...}
   # }
   ```

3. **多客户端同步** - 所有连接的客户端同时收到更新

### 集成测试

```bash
# 运行 WebSocket 集成测试
python scripts/test_websocket_integration.py
```

测试验证：
- ✅ WebSocketHandler 成功集成 UIStateManager
- ✅ 客户端连接时收到 UI State 模板
- ✅ UI State 更新自动广播到所有客户端
- ✅ 多客户端广播正常工作

### 在 Listener 中使用

当 WebSocketHandler 创建 Session 时，UIStateManager 会自动注入到 ListenerContext：

```python
# agent/custom_scripts/listeners/my_listener.py

async def handler(event_data, context):
    # 获取状态
    dashboard = await context.ui_state.get('financial_dashboard')
    
    # 修改数据
    dashboard['statistics']['total_reports'] += 1
    
    # 保存 (自动广播到 WebSocket)
    await context.ui_state.set('financial_dashboard', dashboard)
    # ↑ 所有已连接的前端客户端将实时收到更新
    
    return {'executed': True}
```

## ⚠️ 注意事项

1. **热重载功能可选** - 如果未安装 `watchdog`，其他功能仍正常工作
2. **状态 ID 必须与模板 ID 一致** - `get_state('my_dashboard')` 会优先从数据库读取，不存在时返回模板的 `initialState`
3. **数据持久化** - 所有状态更新都会立即保存到数据库
4. **并发安全** - 使用 SQLite 的事务机制确保数据一致性

## 📖 内置模板

### 1. financial_dashboard (金融仪表盘)

```python
{
    'recent_reports': [],           # 最新报告列表
    'portfolio_summary': {...},     # 投资组合概览
    'statistics': {...},            # 关键统计
    'watchlist_summary': {...}      # 关注列表摘要
}
```

### 2. price_alerts (价格提醒)

```python
{
    'alerts': [],                   # 活跃的提醒
    'history': [],                  # 已触发的历史
    'stats': {...}                  # 统计信息
}
```

## 🎨 最佳实践

1. **模板设计**
   - 使用清晰的 `initialState` 结构
   - 包含完整的类型注释 (TypedDict)
   - 提供详细的 description

2. **状态更新**
   - 先 `get_state()` 获取当前状态
   - 修改数据
   - 调用 `set_state()` 保存
   - 避免直接覆盖整个状态

3. **性能优化**
   - 合并多次更新为一次 `set_state()`
   - 避免频繁更新大数据
   - 使用增量更新而非全量替换

4. **错误处理**
   - 始终检查 `get_state()` 返回值
   - 使用 `initialize_if_needed()` 确保状态存在
   - 捕获数据库异常

## 🧪 运行测试

```bash
# 基础测试 (不需要 watchdog)
python scripts/test_ui_state_simple.py

# 完整测试 (需要 watchdog)
python scripts/test_ui_state_manager.py

# 热重载测试 (需要 watchdog)
python scripts/test_ui_state_manager.py --hot-reload

# WebSocket 集成测试
python scripts/test_websocket_integration.py
```

## 🔗 相关文档

- [FEATURES_ROADMAP.md](./FEATURES_ROADMAP.md) - 功能路线图
- [Email Agent UI_STATE_SYSTEM.md](../email-agent/UI_STATE_SYSTEM.md) - TypeScript 参考实现
- [DATABASE_SCHEMA.md](./DATABASE_SCHEMA.md) - 数据库设计

---

**创建日期**: 2025-12-01  
**版本**: 1.0.0  
**状态**: ✅ 已实现并测试通过
