# WebSocket Handler 实现文档

## 概述

`WebSocketHandler` 是 Finance Agent 的核心组件，负责管理 WebSocket 连接、Session 生命周期和消息路由。

基于 Email Agent 的 `websocket-handler.ts` (666 行) 完整复刻到 Python (374 行)。

---

## 核心功能

### 1. WebSocket 连接管理

#### 连接事件 (on_open)
- **功能**: 客户端连接时触发
- **对应 TS**: `onOpen()` (websocket-handler.ts 第 145-189 行)
- **操作**:
  - 生成唯一客户端 ID
  - 发送连接确认消息
  - 发送初始报告列表

**示例消息**:
```json
{
  "type": "connected",
  "message": "Connected to Finance Agent",
  "availableSessions": ["session-1", "session-2"]
}
```

#### 断开事件 (on_close)
- **功能**: 客户端断开时触发
- **对应 TS**: `onClose()` (websocket-handler.ts 第 342-361 行)
- **操作**:
  - 从 Session 取消订阅
  - 从客户端列表移除
  - 清理空 Session (60 秒宽限期)

---

### 2. Session 管理

#### 创建 Session
- **触发**: 收到 `chat` 消息且未指定 sessionId
- **对应 TS**: `getOrCreateSession()` (websocket-handler.ts 第 134-143 行)
- **Session ID 格式**: `session-{timestamp}-{random}`

#### 订阅 Session
- **消息类型**: `subscribe`
- **功能**: 客户端订阅到指定 Session，接收该 Session 的所有消息
- **对应 TS**: case 'subscribe' (websocket-handler.ts 第 215-237 行)

**请求示例**:
```json
{
  "type": "subscribe",
  "sessionId": "session-123"
}
```

**响应示例**:
```json
{
  "type": "subscribed",
  "sessionId": "session-123"
}
```

#### 取消订阅
- **消息类型**: `unsubscribe`
- **功能**: 取消订阅 Session
- **对应 TS**: case 'unsubscribe' (websocket-handler.ts 第 239-251 行)

---

### 3. 消息路由

#### 聊天消息 (chat)
- **功能**: 处理用户对话消息
- **对应 TS**: case 'chat' (websocket-handler.ts 第 196-213 行)

**请求示例**:
```json
{
  "type": "chat",
  "content": "分析一下最近的市场趋势",
  "sessionId": "session-123",
  "newConversation": false
}
```

**流程**:
1. 获取或创建 Session
2. 自动订阅发送者到该 Session
3. 如果 `newConversation=true`，结束当前对话
4. 调用 `session.add_user_message()` 处理消息
5. 流式广播 AI 响应给所有订阅者

#### 请求报告列表 (request_reports)
- **功能**: 主动请求报告列表
- **对应 TS**: case 'request_inbox' (websocket-handler.ts 第 253-261 行)

**请求示例**:
```json
{
  "type": "request_reports"
}
```

**响应示例**:
```json
{
  "type": "reports_update",
  "reports": [
    {
      "id": 1,
      "report_id": "20251127_001",
      "title": "A股4000点拉锯与黄金见顶辨析",
      "category": "市场分析",
      "importance": 9,
      "snippet": "当前市场处于关键转折点..."
    }
  ]
}
```

---

### 4. 数据广播

#### 自动报告更新
- **频率**: 每 5 秒自动广播
- **对应 TS**: `initEmailWatcher()` (websocket-handler.ts 第 33-41 行)
- **消息类型**: `reports_update`

**实现**:
```python
async def _init_report_watcher(self):
    """定时广播报告列表"""
    await self._broadcast_reports_update()  # 初始推送
    
    while True:
        await asyncio.sleep(5)  # 每 5 秒
        await self._broadcast_reports_update()
```

#### UI State 更新
- **功能**: 广播 UI 状态变化
- **对应 TS**: `broadcastUIStateUpdate()` (websocket-handler.ts 第 96-111 行)
- **消息类型**: `ui_state_update`

---

### 5. 并发控制

#### Session 级并发控制
- **实现**: `asyncio.Lock` 在 Session 内部
- **保证**: 同一 Session 内消息按顺序处理
- **对应 TS**: `queryPromise` 链式等待 (session.ts)

#### 多 Session 并发
- **支持**: 多个 Session 可并行处理
- **隔离**: 不同 Session 之间互不影响

---

## 架构对比

### Email Agent (TypeScript)

```typescript
// websocket-handler.ts
export class WebSocketHandler {
  private db: Database;
  private sessions: Map<string, Session> = new Map();
  private clients: Map<string, WSClient> = new Map();
  
  async onMessage(ws: WSClient, message: string) {
    const data = JSON.parse(message);
    switch (data.type) {
      case 'chat': // 处理聊天
      case 'subscribe': // 订阅 Session
      case 'execute_action': // 执行动作 (Email 特有)
    }
  }
}
```

### Finance Agent (Python)

```python
# websocket_handler.py
class WebSocketHandler:
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager or DatabaseManager()
        self.sessions: Dict[str, Session] = {}
        self.clients: Dict[str, WSClient] = {}
    
    async def on_message(self, ws: WSClient, message: str):
        data: IncomingMessage = json.loads(message)
        msg_type = data.get('type')
        
        if msg_type == 'chat':  # 处理聊天
        elif msg_type == 'subscribe':  # 订阅 Session
        elif msg_type == 'request_reports':  # 请求报告列表
```

---

## 功能映射表

| Email Agent | Finance Agent | 说明 |
|------------|--------------|------|
| `inbox_update` | `reports_update` | 数据列表推送 |
| `getRecentEmails()` | `_get_recent_reports()` | 获取最近数据 |
| `broadcastInboxUpdate()` | `_broadcast_reports_update()` | 广播数据更新 |
| `execute_action` | _(未实现)_ | 动作系统 (Finance Agent 暂不需要) |
| `listener_log` | _(未实现)_ | 监听器日志 (Finance Agent 暂不需要) |
| `component_instance` | _(未实现)_ | 组件实例 (Finance Agent 暂不需要) |

---

## 错误处理

### 1. 未知消息类型
```json
{
  "type": "error",
  "error": "Unknown message type: xxx"
}
```

### 2. Session 不存在
```json
{
  "type": "error",
  "error": "Session not found"
}
```

### 3. 无效 JSON
```json
{
  "type": "error",
  "error": "Failed to process message"
}
```

---

## 测试覆盖

### 测试文件
`scripts/test_websocket_handler.py` (384 行)

### 测试场景

1. **基本连接** ✅
   - 连接/断开
   - 初始消息推送

2. **Session 管理** ✅
   - 创建 Session
   - 订阅/取消订阅
   - Session 清理

3. **消息路由** ✅
   - 未知消息类型处理
   - 请求报告列表

4. **数据广播** ✅
   - 自动推送 (5 秒轮询)
   - 多客户端广播

5. **并发处理** ✅
   - 多客户端订阅同一 Session
   - 并发聊天消息

6. **错误处理** ✅
   - 不存在的 Session
   - 无效 JSON

### 测试结果
```
✅ All tests passed!
- Test 1: Basic Connection ✅
- Test 2: Session Management ✅
- Test 3: Message Routing ✅
- Test 4: Data Broadcast ✅
- Test 5: Concurrent Chat Handling ✅
- Test 6: Error Handling ✅
```

---

## 使用示例

### Python 服务端

```python
from ccsdk import WebSocketHandler
from database import DatabaseManager

# 初始化
db = DatabaseManager()
handler = WebSocketHandler(db)
await handler.start()

# 连接事件
await handler.on_open(ws_client)

# 消息事件
await handler.on_message(ws_client, '{"type": "chat", "content": "Hello"}')

# 断开事件
await handler.on_close(ws_client)

# 清理
await handler.stop()
```

### 客户端 (JavaScript)

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

// 连接
ws.onopen = () => {
  console.log('Connected to Finance Agent');
};

// 发送聊天消息
ws.send(JSON.stringify({
  type: 'chat',
  content: '分析一下最近的市场趋势',
  newConversation: false
}));

// 接收消息
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  switch (data.type) {
    case 'reports_update':
      console.log('Reports:', data.reports);
      break;
    case 'assistant_message':
      console.log('AI:', data.content);
      break;
    case 'session_info':
      console.log('Session ID:', data.session_id);
      break;
  }
};

// 订阅 Session
ws.send(JSON.stringify({
  type: 'subscribe',
  sessionId: 'session-123'
}));
```

---

## 技术细节

### 1. WebSocket 客户端协议

```python
@dataclass
class WSClient(Protocol):
    """WebSocket 客户端协议"""
    session_id: Optional[str]
    async def send(self, message: str) -> None: ...
```

### 2. 消息类型

```python
IncomingMessage = Union[
    ChatMessage,        # 聊天消息
    SubscribeMessage,   # 订阅请求
    UnsubscribeMessage, # 取消订阅
    RequestReportsMessage  # 请求报告列表
]
```

### 3. 并发模型

```
┌─────────────────┐
│ WebSocketHandler │
└────────┬────────┘
         │
    ┌────┴────┐
    │ Session │ (Lock: 保证顺序处理)
    │  #1     │
    └─────────┘
         │
    ┌────┴──────────┐
    │ Subscribers   │
    │ - Client A    │
    │ - Client B    │
    └───────────────┘
```

---

## 下一步计划

1. **FastAPI 集成** - 创建 HTTP 服务器
2. **Actions Manager** - 动作系统 (如果需要)
3. **Listeners Manager** - 监听器系统 (如果需要)
4. **UI State Manager** - UI 状态管理
5. **Component Manager** - 组件管理

---

## 参考文档

- Email Agent: `/email-agent/ccsdk/websocket-handler.ts` (666 行)
- Session 实现: `/finance-agent/ccsdk/session.py` (344 行)
- 数据库管理: `/finance-agent/database/database_manager.py` (503 行)
