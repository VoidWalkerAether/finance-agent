# WebSocket + UIStateManager 集成说明

## ✅ 完成内容

已成功将 UIStateManager 集成到 WebSocketHandler，实现 UI State 更新的实时 WebSocket 广播功能。

## 📝 修改文件

### 1. WebSocketHandler (`ccsdk/websocket_handler.py`)

**新增功能：**
- ✅ 构造函数接受 `ui_state_manager` 参数
- ✅ `_init_ui_state_watcher()` - 初始化 UI State 监听器
- ✅ `_on_ui_state_update()` - UI State 更新回调
- ✅ `on_open()` - 客户端连接时发送 UI State 模板列表
- ✅ `_get_or_create_session()` - 将 UIStateManager 注入到 Session

**核心代码：**
```python
def __init__(
    self,
    db_manager: Optional[DatabaseManager] = None,
    ui_state_manager: Optional['UIStateManager'] = None
):
    self.ui_state_manager = ui_state_manager
    
    # 初始化 UI State 监听器
    if self.ui_state_manager:
        self._init_ui_state_watcher()

def _init_ui_state_watcher(self):
    """订阅 UI State 更新"""
    if not self.ui_state_manager:
        return
    
    self.ui_state_manager.on_state_update(self._on_ui_state_update)
    print("✅ UI State watcher initialized")

def _on_ui_state_update(self, state_id: str, data: Any):
    """创建异步任务广播更新"""
    asyncio.create_task(self._broadcast_ui_state_update(state_id, data))
```

### 2. Session (`ccsdk/session.py`)

**修改内容：**
- ✅ 构造函数接受 `ui_state_manager` 参数
- ✅ 存储 `self.ui_state_manager` 以便传递给 ListenerContext

**核心代码：**
```python
def __init__(
    self,
    session_id: str,
    db: Optional[DatabaseManager] = None,
    ui_state_manager: Optional[Any] = None
):
    self.ui_state_manager = ui_state_manager
```

### 3. 文档更新

**UI_STATE_MANAGER_README.md:**
- ✅ 添加 "🌐 WebSocket 集成" 章节
- ✅ 说明初始化集成方法
- ✅ 说明自动广播机制
- ✅ 添加集成测试说明
- ✅ 添加 Listener 中的使用示例

### 4. 集成测试 (`scripts/test_websocket_integration.py`)

**测试覆盖：**
- ✅ WebSocketHandler 成功集成 UIStateManager
- ✅ 客户端连接时收到 UI State 模板
- ✅ UI State 更新自动广播到所有客户端
- ✅ 多客户端广播正常工作

## 🎯 功能验证

运行集成测试验证所有功能：

```bash
cd /Users/caiwei/workbench/claude-agent-sdk-demos/finance-agent
python scripts/test_websocket_integration.py
```

**测试结果：**
```
✅ 所有测试通过!
  ✅ WebSocketHandler 成功集成 UIStateManager
  ✅ 客户端连接时收到 UI State 模板
  ✅ UI State 更新自动广播到所有客户端
  ✅ 多客户端广播正常工作
```

## 🌐 WebSocket 消息格式

### 1. 客户端连接时 - UI State 模板列表

```json
{
  "type": "ui_state_templates",
  "templates": [
    {
      "id": "financial_dashboard",
      "name": "金融仪表盘",
      "description": "显示最新报告、投资组合概览和关键统计信息"
    },
    {
      "id": "price_alerts",
      "name": "价格提醒",
      "description": "管理股票价格提醒"
    }
  ]
}
```

### 2. UI State 更新广播

```json
{
  "type": "ui_state_update",
  "stateId": "financial_dashboard",
  "data": {
    "recent_reports": [...],
    "portfolio_summary": {...},
    "statistics": {...},
    "watchlist_summary": {...}
  }
}
```

## 🔄 数据流

```
Listener 更新 UI State
    ↓
UIStateManager.set_state()
    ↓
1. 保存到数据库
2. 记录 JSONL 日志
3. 调用所有 update_callbacks
    ↓
WebSocketHandler._on_ui_state_update()
    ↓
WebSocketHandler._broadcast_ui_state_update()
    ↓
所有连接的 WebSocket 客户端收到更新
```

## 📋 使用示例

### 服务器端初始化

```python
from ccsdk.websocket_handler import WebSocketHandler
from ccsdk.ui_state_manager import UIStateManager
from database.database_manager import DatabaseManager

# 1. 初始化组件
db = DatabaseManager()
ui_manager = UIStateManager(db)
await ui_manager.load_all_templates()

# 2. 创建 WebSocketHandler (注入 UIStateManager)
ws_handler = WebSocketHandler(
    db_manager=db,
    ui_state_manager=ui_manager
)

# 3. 启动
await ws_handler.start()
```

### Listener 中使用

```python
# agent/custom_scripts/listeners/report_analyzer.py

async def handler(event_data, context):
    # 获取 UI State
    dashboard = await context.ui_state.get('financial_dashboard')
    
    # 修改数据
    dashboard['statistics']['total_reports'] += 1
    dashboard['recent_reports'].insert(0, {
        'title': event_data['title'],
        'importance': 8
    })
    
    # 保存 (自动触发 WebSocket 广播)
    await context.ui_state.set('financial_dashboard', dashboard)
    # ↑ 所有已连接的前端客户端将实时收到更新
    
    return {'executed': True}
```

## 🎉 集成完成

UIStateManager 已成功集成到 WebSocketHandler，实现了：
- ✅ 客户端连接时自动发送 UI State 模板
- ✅ UI State 更新自动广播到所有客户端
- ✅ 多客户端实时同步
- ✅ Listener 可以通过 context.ui_state 操作状态
- ✅ 完整的集成测试覆盖

下一步可以考虑：
- 实现 ComponentManager（Phase 1 Week 2 的另一个任务）
- 或进入 ActionsManager（Phase 1 Week 3）
