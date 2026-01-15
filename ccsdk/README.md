# Finance Agent CCSDK 模块

> **Claude Code SDK 核心模块** - 基于 Email Agent 完整复刻

---

## 📁 文件结构

```
ccsdk/
├── __init__.py           # 模块导出
├── types.py              # 类型定义 (221 行)
├── ai_client.py          # AI 客户端 (223 行)
├── session.py            # Session 类 (344 行)
└── README.md             # 本文档
```

---

## ✅ 完成的功能

### 1. **types.py** - 类型定义系统

完全对应 Email Agent 的类型系统：

| Python 类型 | TypeScript 对应 | 说明 |
|------------|----------------|------|
| `WSClient` | `ServerWebSocket<{ sessionId: string }>` | WebSocket 客户端协议 |
| `ChatMessage` | `ChatMessage` | 聊天消息 |
| `SDKMessage` | `SDKMessage` | SDK 消息联合类型 |
| `OutgoingMessage` | - | 发送给客户端的消息 |

**核心消息类型**:
- ✅ `ChatMessage` - 用户聊天
- ✅ `SubscribeMessage` - 订阅会话
- ✅ `SDKUserMessage` / `SDKAssistantMessage` - SDK 消息
- ✅ `WSAssistantMessage` / `WSResultMessage` - WebSocket 消息

---

### 2. **ai_client.py** - AI 客户端

对应 `email-agent/ccsdk/ai-client.ts` (114 行)

**核心功能**:

```python
class AIClient:
    def __init__(self, options: Optional[AIQueryOptions] = None)
    
    async def query_stream(
        self, 
        prompt: Union[str, AsyncIterable[SDKUserMessage]],
        options: Optional[Dict[str, Any]] = None
    ) -> AsyncIterable[SDKMessage]
    
    async def query_single(
        self,
        prompt: str,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]
```

**与 Email Agent 对比**:

| 功能 | Email Agent | Finance Agent | 状态 |
|------|-------------|---------------|------|
| `queryStream()` | ✅ | `query_stream()` | ✅ 接口完成 |
| `querySingle()` | ✅ | `query_single()` | ✅ 接口完成 |
| 系统提示词 | `EMAIL_AGENT_PROMPT` | `FINANCE_AGENT_PROMPT` | ⚠️ 待创建 |
| MCP 服务器 | `customServer` (email) | `reports` | ⚠️ 待实现 |

**注意**: 当前使用模拟响应，实际部署需要集成 Claude Agent SDK for Python。

---

### 3. **session.py** - Session 核心类 ⭐

完全对应 `email-agent/ccsdk/session.ts` (207 行)

**核心功能对比**:

| 功能 | TypeScript 实现 | Python 实现 | 说明 |
|------|----------------|-------------|------|
| **并发控制** | `queryPromise: Promise<void>` | `asyncio.Lock` | ✅ 完全等价 |
| **多轮对话** | `sdkSessionId: string \| null` | `sdk_session_id: Optional[str]` | ✅ 完全一致 |
| **订阅管理** | `subscribers: Set<WSClient>` | `subscribers: Set[WSClient]` | ✅ 完全一致 |
| **消息广播** | `broadcastToSubscribers()` | `_broadcast_to_subscribers()` | ✅ 逻辑一致 |

**关键方法**:

```python
class Session:
    # 核心方法
    async def add_user_message(content: str) -> None  # 处理用户消息
    def subscribe(client: WSClient) -> None           # 订阅客户端
    def unsubscribe(client: WSClient) -> None         # 取消订阅
    
    # 辅助方法
    def has_subscribers() -> bool                     # 检查订阅者
    async def cleanup() -> None                       # 清理资源
    def end_conversation() -> None                    # 结束对话
```

**测试结果** ✅:

```bash
$ python scripts/test_session.py

✅ 基本功能测试通过
   - 会话创建 ✅
   - 客户端订阅 ✅
   - 用户消息处理 ✅
   - 多轮对话 ✅
   - 取消订阅 ✅
   - 会话清理 ✅

✅ 并发控制测试通过
   - 并发发送 3 条消息
   - 消息按顺序处理 ✅

✅ 错误处理测试通过
```

---

## 🔄 与 Email Agent 对应关系

### 架构对应

```
Email Agent (TypeScript)          Finance Agent (Python)
├── session.ts                    ├── session.py         ✅
├── ai-client.ts                  ├── ai_client.py       ✅
├── types.ts                      ├── types.py           ✅
├── message-queue.ts              ├── (未实现)           ⚠️
├── websocket-handler.ts          ├── (待实现)           📝
├── listeners-manager.ts          ├── (待实现)           📝
├── actions-manager.ts            ├── (待实现)           📝
└── custom-tools.ts               └── (待实现)           📝
```

### 并发控制对比

**TypeScript (Email Agent)**:
```typescript
private queryPromise: Promise<void> | null = null;

async addUserMessage(content: string): Promise<void> {
  if (this.queryPromise) {
    await this.queryPromise;  // 等待之前的查询
  }
  
  this.queryPromise = (async () => {
    // 处理查询
  })();
  
  await this.queryPromise;
}
```

**Python (Finance Agent)**:
```python
_query_lock = asyncio.Lock()

async def add_user_message(self, content: str) -> None:
    async with self._query_lock:  # 自动等待和释放
        # 处理查询
```

✅ **Python 的 `asyncio.Lock` 更简洁且安全**

---

## 📊 代码统计

| 文件 | 行数 | TypeScript 对应 | 完成度 |
|------|------|----------------|--------|
| `types.py` | 221 | `types.ts` (32行) | ✅ 100% (扩展完整) |
| `ai_client.py` | 223 | `ai-client.ts` (114行) | ✅ 90% (接口完成) |
| `session.py` | 344 | `session.ts` (207行) | ✅ 100% |
| **总计** | **788** | **353** | **✅ 核心功能完成** |

---

## 🚀 使用示例

### 基本用法

```python
from ccsdk.session import Session
from database.database_manager import DatabaseManager

# 1. 创建会话
db = DatabaseManager("data/finance.db")
session = Session("user_session_001", db)

# 2. 订阅客户端
session.subscribe(websocket_client)

# 3. 处理用户消息
await session.add_user_message("请分析最新的A股黄金报告")

# 4. 多轮对话
await session.add_user_message("那么投资建议是什么?")

# 5. 清理
await session.cleanup()
```

### 并发处理

```python
# Session 自动处理并发,消息按顺序处理
await asyncio.gather(
    session.add_user_message("消息1"),
    session.add_user_message("消息2"),
    session.add_user_message("消息3")
)
# 输出: 消息按顺序处理 1 → 2 → 3
```

---

## ⚠️ 待实现功能

1. **Claude Agent SDK 集成** (P0)
   - 当前使用模拟响应
   - 需要等待 Python 版本的 Claude Agent SDK

2. **Finance Agent Prompt** (P1)
   - 创建 `finance_agent_prompt.py`
   - 定义金融报告分析的系统提示词

3. **Custom Tools** (P1)
   - 实现 `custom_tools.py`
   - 提供 `search_reports`, `read_report` 等工具

4. **WebSocket Handler** (P1)
   - 实现 `websocket_handler.py`
   - 管理 WebSocket 连接

5. **Listeners/Actions Manager** (P2)
   - 实现监听器和动作管理系统

---

## ✅ 测试覆盖

| 测试项 | 状态 | 脚本 |
|--------|------|------|
| Session 基本功能 | ✅ | `scripts/test_session.py` |
| 并发控制 | ✅ | `scripts/test_session.py` |
| 错误处理 | ✅ | `scripts/test_session.py` |
| 多轮对话 | ✅ | `scripts/test_session.py` |
| 订阅管理 | ✅ | `scripts/test_session.py` |

---

## 📝 下一步

**Phase 2.1 完成 ✅** - Session 类已实现

**下一阶段 (Phase 2.2)**:
1. 实现 WebSocket Handler
2. 创建 Finance Agent Prompt
3. 实现 Custom Tools (MCP Server)

参考 `IMPLEMENTATION_CHECKLIST.md` 继续开发。
