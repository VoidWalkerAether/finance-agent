# Session 会话流程详解

> **文档目的**：详细记录 Email Agent 中 Session 类的实际工作流程，包括会话创建、消息处理、多轮对话、并发控制等核心机制。
> **原则**：基于实际代码，详细展示每个步骤的执行逻辑。

---

## 📋 目录

1. [Session 类结构](#session-类结构)
2. [会话生命周期](#会话生命周期)
3. [消息处理流程](#消息处理流程)
4. [多轮对话机制](#多轮对话机制)
5. [并发控制机制](#并发控制机制)
6. [订阅者管理](#订阅者管理)
7. [消息广播机制](#消息广播机制)
8. [AI 客户端集成](#ai-客户端集成)
9. [Python 实现要点](#python-实现要点)

---

## 🏗️ Session 类结构

### **完整类定义** (`ccsdk/session.ts`)

```typescript
import { Database } from "bun:sqlite";
import { MessageQueue } from "./message-queue";
import type { WSClient, SDKUserMessage, SDKMessage } from "./types";
import { AIClient } from "./ai-client";

export class Session {
  // 公共属性
  public readonly id: string;

  // 私有属性
  private messageQueue: MessageQueue<SDKUserMessage>;
  private queryPromise: Promise<void> | null = null;  // 并发控制锁
  private subscribers: Set<WSClient> = new Set();     // 订阅者集合
  private db: Database;
  private messageCount = 0;                            // 消息计数器
  private aiClient: AIClient;
  private sdkSessionId: string | null = null;          // Claude SDK 会话 ID

  constructor(id: string, db: Database) {
    this.id = id;
    this.db = db;
    this.messageQueue = new MessageQueue();
    this.aiClient = new AIClient();
  }

  // 核心方法
  async addUserMessage(content: string): Promise<void> { /* ... */ }
  subscribe(client: WSClient): void { /* ... */ }
  unsubscribe(client: WSClient): void { /* ... */ }
  private broadcastToSubscribers(message: SDKMessage): void { /* ... */ }
  private broadcast(message: any): void { /* ... */ }
  private broadcastError(error: string): void { /* ... */ }
  hasSubscribers(): boolean { /* ... */ }
  async cleanup(): Promise<void> { /* ... */ }
  endConversation(): void { /* ... */ }
}
```

### **属性详解**

| 属性 | 类型 | 用途 | Python 对应 |
|------|------|------|-------------|
| `id` | `string` | 会话唯一标识符 | `str` |
| `messageQueue` | `MessageQueue<SDKUserMessage>` | 消息队列（当前未实际使用） | `asyncio.Queue` |
| `queryPromise` | `Promise<void> \| null` | **并发控制锁**，确保消息串行处理 | `asyncio.Lock` |
| `subscribers` | `Set<WSClient>` | **订阅者集合**（发布-订阅模式） | `set[WebSocket]` |
| `db` | `Database` | SQLite 数据库实例 | `aiosqlite.Connection` |
| `messageCount` | `number` | 会话中处理的消息数 | `int` |
| `aiClient` | `AIClient` | AI 客户端封装 | `AIClient` (自定义类) |
| `sdkSessionId` | `string \| null` | **Claude SDK 会话 ID**（多轮对话关键） | `str \| None` |

---

## 🔄 会话生命周期

### **1. 创建会话**

```typescript
// WebSocketHandler.ts
private getOrCreateSession(sessionId?: string): Session {
  if (sessionId && this.sessions.has(sessionId)) {
    return this.sessions.get(sessionId)!;
  }

  const newSessionId = sessionId || this.generateSessionId();
  const session = new Session(newSessionId, this.db);
  this.sessions.set(newSessionId, session);
  return session;
}

private generateSessionId(): string {
  return 'session-' + Date.now() + '-' + Math.random().toString(36).substring(7);
}
```

**创建时机**：
- 用户首次发送消息时
- 客户端主动指定 `sessionId` 时

**会话 ID 格式**：
```
session-1737123456789-a4k9m2x
         ↑             ↑
      时间戳       随机字符串
```

---

### **2. 订阅会话**

```typescript
// Session.ts
subscribe(client: WSClient) {
  this.subscribers.add(client);
  client.data.sessionId = this.id;

  // 发送会话信息给新订阅者
  client.send(JSON.stringify({
    type: 'session_info',
    sessionId: this.id,
    messageCount: this.messageCount,
    isActive: this.queryPromise !== null
  }));
}
```

**订阅流程**：
1. 将 WebSocket 客户端添加到 `subscribers` 集合
2. 在客户端的 `data.sessionId` 中标记订阅的会话
3. 发送会话元信息（ID、消息数、活跃状态）

---

### **3. 取消订阅**

```typescript
unsubscribe(client: WSClient) {
  this.subscribers.delete(client);
}
```

**触发时机**：
- WebSocket 连接关闭
- 客户端切换到其他会话

---

### **4. 清理会话**

```typescript
async cleanup() {
  this.messageQueue.close();
  this.subscribers.clear();
}

// WebSocketHandler.ts 中的自动清理
private cleanupEmptySessions() {
  for (const [id, session] of this.sessions) {
    if (!session.hasSubscribers()) {
      // 1 分钟宽限期
      setTimeout(() => {
        if (!session.hasSubscribers()) {
          session.cleanup();
          this.sessions.delete(id);
          console.log('Cleaned up empty session:', id);
        }
      }, 60000);
    }
  }
}
```

**清理策略**：
- 无订阅者的会话等待 60 秒后清理
- 清理时关闭消息队列并清空订阅者

---

## 📨 消息处理流程

### **完整流程图**

```
用户发送消息
  ↓
WebSocketHandler.onMessage({ type: 'chat', content: '...' })
  ↓
getOrCreateSession(sessionId)
  ↓
session.subscribe(ws)  // 自动订阅
  ↓
session.addUserMessage(content)
  ↓
┌─────────────────────────────────────────┐
│ 并发控制检查                             │
│ if (this.queryPromise) {                │
│   await this.queryPromise;  // 等待上一个 │
│ }                                       │
└─────────────────────────────────────────┘
  ↓
this.messageCount++
  ↓
┌─────────────────────────────────────────┐
│ 创建查询 Promise                         │
│ this.queryPromise = (async () => {      │
│   try {                                 │
│     // 多轮对话支持                      │
│     const options = this.sdkSessionId   │
│       ? { resume: this.sdkSessionId }   │
│       : {};                             │
│                                         │
│     // 流式调用 AI                       │
│     for await (const message of         │
│       this.aiClient.queryStream(        │
│         content, options)) {            │
│                                         │
│       // 广播消息                        │
│       this.broadcastToSubscribers(      │
│         message);                       │
│                                         │
│       // 捕获 SDK 会话 ID                │
│       if (message.type === 'system' &&  │
│           message.subtype === 'init') { │
│         this.sdkSessionId =             │
│           message.session_id;           │
│       }                                 │
│                                         │
│       // 检查是否完成                    │
│       if (message.type === 'result') {  │
│         console.log('Result received'); │
│       }                                 │
│     }                                   │
│   } catch (error) {                     │
│     this.broadcastError(error.message); │
│   } finally {                           │
│     this.queryPromise = null;  // 释放锁 │
│   }                                     │
│ })();                                   │
└─────────────────────────────────────────┘
  ↓
await this.queryPromise  // 等待完成
```

### **实际代码** (`ccsdk/session.ts`)

```typescript
async addUserMessage(content: string): Promise<void> {
  // ===== 步骤 1: 并发控制检查 =====
  if (this.queryPromise) {
    // 等待上一个查询完成
    await this.queryPromise;
  }

  // ===== 步骤 2: 消息计数 =====
  this.messageCount++;
  console.log(`Processing message ${this.messageCount} in session ${this.id}`);

  // ===== 步骤 3: 创建并执行查询 =====
  this.queryPromise = (async () => {
    try {
      // ===== 步骤 3.1: 准备多轮对话选项 =====
      const options = this.sdkSessionId
        ? { resume: this.sdkSessionId }  // 恢复上一轮对话
        : {};  // 新对话

      // ===== 步骤 3.2: 流式调用 AI =====
      for await (const message of this.aiClient.queryStream(content, options)) {
        // 实时广播每条消息
        this.broadcastToSubscribers(message);

        // ===== 步骤 3.3: 捕获 SDK 会话 ID =====
        if (message.type === 'system' && message.subtype === 'init') {
          this.sdkSessionId = message.session_id;
          console.log(`Captured SDK session ID: ${this.sdkSessionId}`);
        }

        // ===== 步骤 3.4: 检查结果 =====
        if (message.type === 'result') {
          console.log('Result received, ready for next user message');
        }
      }
    } catch (error) {
      console.error(`Error in session ${this.id}:`, error);
      this.broadcastError("Query failed: " + (error as Error).message);
    } finally {
      // ===== 步骤 3.5: 释放并发锁 =====
      this.queryPromise = null;
    }
  })();

  // ===== 步骤 4: 等待查询完成 =====
  await this.queryPromise;
}
```

---

## 🔁 多轮对话机制

### **关键：`sdkSessionId` 的捕获与使用**

#### **1. 首次对话（无 `sdkSessionId`）**

```typescript
// 用户消息 1
const options = this.sdkSessionId
  ? { resume: this.sdkSessionId }
  : {};  // {} - 新对话

for await (const message of this.aiClient.queryStream("查询收件箱", options)) {
  if (message.type === 'system' && message.subtype === 'init') {
    // 捕获 SDK 会话 ID
    this.sdkSessionId = "sdk-session-xyz-123";  
    console.log('Captured SDK session ID: sdk-session-xyz-123');
  }
}
```

**SDK 返回的 `system/init` 消息示例**：
```json
{
  "type": "system",
  "subtype": "init",
  "session_id": "sdk-session-xyz-123",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

---

#### **2. 后续对话（有 `sdkSessionId`）**

```typescript
// 用户消息 2
const options = this.sdkSessionId
  ? { resume: this.sdkSessionId }  // { resume: "sdk-session-xyz-123" }
  : {};

for await (const message of this.aiClient.queryStream("显示第一封邮件", options)) {
  // AI 会基于上一轮对话的上下文回答
}
```

**效果**：
- AI 记住了上一轮对话中的"收件箱"查询
- 可以直接回答"第一封邮件"而不需要重新查询

---

#### **3. 结束对话（重置会话）**

```typescript
endConversation() {
  this.sdkSessionId = null;
  this.queryPromise = null;
}
```

**触发时机**：
- 用户主动发送带 `newConversation: true` 的消息
- WebSocket 消息处理：

```typescript
// WebSocketHandler.onMessage()
case 'chat': {
  const session = this.getOrCreateSession(data.sessionId);
  
  if (data.newConversation) {
    session.endConversation();  // 重置多轮对话
  }

  await session.addUserMessage(data.content);
  break;
}
```

---

### **多轮对话示例对话**

```
用户消息 1: "查询未读邮件"
  ↓ options = {}
  ↓ AI 响应: "找到 5 封未读邮件..."
  ↓ 捕获 sdkSessionId = "sdk-abc-123"

用户消息 2: "显示第一封"
  ↓ options = { resume: "sdk-abc-123" }
  ↓ AI 响应: "第一封邮件主题是..." (基于上下文)

用户消息 3: "归档这封邮件"
  ↓ options = { resume: "sdk-abc-123" }
  ↓ AI 响应: "已归档邮件..." (知道"这封"指的是第一封)

用户: 点击 "New Conversation" 按钮
  ↓ session.endConversation()
  ↓ sdkSessionId = null

用户消息 4: "查询发件箱"
  ↓ options = {}  (全新对话)
  ↓ AI 响应: "找到 10 封已发送邮件..."
```

---

## 🔒 并发控制机制

### **问题：为什么需要并发控制？**

如果用户快速发送多条消息：
```
用户消息 1: "查询收件箱" (耗时 2 秒)
用户消息 2: "显示第一封" (耗时 1 秒)
用户消息 3: "归档这封邮件" (耗时 0.5 秒)
```

**不控制并发会导致**：
- 消息 1、2、3 同时调用 AI → 上下文混乱
- 消息 3 可能在消息 1 完成前就返回 → "这封邮件"指向错误

---

### **解决方案：使用 `queryPromise` 作为锁**

```typescript
async addUserMessage(content: string): Promise<void> {
  // ===== 等待上一个查询完成 =====
  if (this.queryPromise) {
    console.log('Previous query in progress, waiting...');
    await this.queryPromise;
  }

  // ===== 设置新的查询 Promise =====
  this.queryPromise = (async () => {
    try {
      // 执行 AI 查询...
    } finally {
      this.queryPromise = null;  // 释放锁
    }
  })();

  await this.queryPromise;
}
```

**执行时序**：

```
时间轴: 0s ──────────► 1s ──────────► 2s ──────────► 3s ──────────► 4s

消息 1: "查询收件箱"
  ↓ queryPromise = Promise1
  0s ━━━━━━━━━━━━━━━━━► 2s (完成)
  ↓ queryPromise = null

消息 2: "显示第一封"
  ↓ if (queryPromise) await ... (等待消息 1 完成)
  2s (开始) ━━━━━━━► 3s (完成)
  ↓ queryPromise = null

消息 3: "归档这封邮件"
  ↓ if (queryPromise) await ... (等待消息 2 完成)
  3s (开始) ━━► 3.5s (完成)
  ↓ queryPromise = null
```

**保证**：
- ✅ 消息严格按顺序处理
- ✅ 上下文连续性
- ✅ 不会出现竞态条件

---

### **Python 实现**

```python
import asyncio

class Session:
    def __init__(self, id: str, db):
        self.id = id
        self.db = db
        self.processing_lock = asyncio.Lock()  # 替代 queryPromise
        self.subscribers = set()
        self.message_count = 0
        self.ai_client = AIClient()
        self.sdk_session_id: str | None = None

    async def add_user_message(self, content: str):
        # 获取锁（自动等待上一个消息完成）
        async with self.processing_lock:
            self.message_count += 1
            print(f"Processing message {self.message_count} in session {self.id}")

            try:
                # 准备多轮对话选项
                options = {"resume": self.sdk_session_id} if self.sdk_session_id else {}

                # 流式调用 AI
                async for message in self.ai_client.query_stream(content, options):
                    # 广播消息
                    await self.broadcast_to_subscribers(message)

                    # 捕获 SDK 会话 ID
                    if message.get("type") == "system" and message.get("subtype") == "init":
                        self.sdk_session_id = message.get("session_id")
                        print(f"Captured SDK session ID: {self.sdk_session_id}")

            except Exception as error:
                await self.broadcast_error(str(error))
```

**关键差异**：
- TypeScript: `if (queryPromise) await queryPromise` + `queryPromise = (async () => { ... })()`
- Python: `async with self.processing_lock:` (更简洁)

---

## 👥 订阅者管理

### **发布-订阅模式**

```typescript
export class Session {
  private subscribers: Set<WSClient> = new Set();

  // 添加订阅者
  subscribe(client: WSClient) {
    this.subscribers.add(client);
    client.data.sessionId = this.id;

    // 发送会话信息
    client.send(JSON.stringify({
      type: 'session_info',
      sessionId: this.id,
      messageCount: this.messageCount,
      isActive: this.queryPromise !== null
    }));
  }

  // 移除订阅者
  unsubscribe(client: WSClient) {
    this.subscribers.delete(client);
  }

  // 检查是否有订阅者
  hasSubscribers(): boolean {
    return this.subscribers.size > 0;
  }

  // 广播消息给所有订阅者
  private broadcast(message: any) {
    const messageStr = JSON.stringify(message);
    for (const client of this.subscribers) {
      try {
        client.send(messageStr);
      } catch (error) {
        console.error('Error broadcasting to client:', error);
        this.subscribers.delete(client);  // 自动移除断开的客户端
      }
    }
  }
}
```

---

### **订阅场景**

#### **场景 1: 单客户端订阅**

```
客户端 A 连接
  ↓ onOpen(wsA)
  ↓ 发送 { type: 'chat', content: '查询邮件', sessionId: 'session-1' }
  ↓ getOrCreateSession('session-1')
  ↓ session.subscribe(wsA)
  ↓ subscribers = { wsA }

AI 响应
  ↓ broadcastToSubscribers(message)
  ↓ wsA 接收消息
```

---

#### **场景 2: 多客户端订阅同一会话**

```
客户端 A 连接
  ↓ subscribe(wsA) → subscribers = { wsA }

客户端 B 连接
  ↓ 发送 { type: 'subscribe', sessionId: 'session-1' }
  ↓ session.subscribe(wsB)
  ↓ subscribers = { wsA, wsB }

AI 响应
  ↓ broadcast(message)
  ↓ wsA 和 wsB 同时接收消息
```

**用途**：
- 多设备同步（手机 + 电脑）
- 团队协作（多人查看同一会话）

---

#### **场景 3: 客户端切换会话**

```
客户端 A 订阅 session-1
  ↓ subscribers(session-1) = { wsA }

客户端 A 发送 { type: 'subscribe', sessionId: 'session-2' }
  ↓ WebSocketHandler 检测到 wsA.data.sessionId !== 'session-2'
  ↓ session-1.unsubscribe(wsA)
  ↓ subscribers(session-1) = {}
  ↓ session-2.subscribe(wsA)
  ↓ subscribers(session-2) = { wsA }
```

---

## 📡 消息广播机制

### **核心方法：`broadcastToSubscribers()`**

```typescript
private broadcastToSubscribers(message: SDKMessage) {
  let wsMessage: any = null;

  // ===== 消息类型 1: Assistant 消息 =====
  if (message.type === "assistant") {
    const content = message.message.content;
    
    // 字符串内容
    if (typeof content === 'string') {
      wsMessage = {
        type: 'assistant_message',
        content: content,
        sessionId: this.id
      };
    } 
    // 内容块数组
    else if (Array.isArray(content)) {
      for (const block of content) {
        // 文本块
        if (block.type === 'text') {
          wsMessage = {
            type: 'assistant_message',
            content: block.text,
            sessionId: this.id
          };
        } 
        // 工具使用块
        else if (block.type === 'tool_use') {
          wsMessage = {
            type: 'tool_use',
            toolName: block.name,
            toolId: block.id,
            toolInput: block.input,
            sessionId: this.id
          };
        } 
        // 工具结果块
        else if (block.type === 'tool_result') {
          wsMessage = {
            type: 'tool_result',
            toolUseId: block.tool_use_id,
            content: block.content,
            isError: block.is_error,
            sessionId: this.id
          };
        }
        
        if (wsMessage) {
          this.broadcast(wsMessage);
        }
      }
      return;  // 已逐块广播
    }
  } 
  
  // ===== 消息类型 2: Result 消息 =====
  else if (message.type === "result") {
    if (message.subtype === "success") {
      wsMessage = {
        type: 'result',
        success: true,
        result: message.result,
        cost: message.total_cost_usd,
        duration: message.duration_ms,
        sessionId: this.id
      };
    } else {
      wsMessage = {
        type: 'result',
        success: false,
        error: message.subtype,
        sessionId: this.id
      };
    }
  } 
  
  // ===== 消息类型 3: System 消息 =====
  else if (message.type === "system") {
    wsMessage = {
      type: 'system',
      subtype: message.subtype,
      sessionId: this.id,
      data: message
    };
  } 
  
  // ===== 消息类型 4: User 消息（回显） =====
  else if (message.type === "user") {
    wsMessage = {
      type: 'user_message',
      content: message.message.content,
      sessionId: this.id
    };
  }

  // 广播转换后的消息
  if (wsMessage) {
    this.broadcast(wsMessage);
  }
}
```

---

### **消息转换示例**

#### **SDK 消息 → WebSocket 消息**

**示例 1: Assistant 文本消息**

```typescript
// SDK 消息
{
  type: "assistant",
  message: {
    content: "找到 3 封未读邮件"
  }
}

// 转换为 WebSocket 消息
{
  type: "assistant_message",
  content: "找到 3 封未读邮件",
  sessionId: "session-xyz"
}
```

---

**示例 2: Tool Use 消息**

```typescript
// SDK 消息
{
  type: "assistant",
  message: {
    content: [
      {
        type: "tool_use",
        name: "mcp__email__search_inbox",
        id: "toolu_01234",
        input: { limit: 10, includeRead: false }
      }
    ]
  }
}

// 转换为 WebSocket 消息
{
  type: "tool_use",
  toolName: "mcp__email__search_inbox",
  toolId: "toolu_01234",
  toolInput: { limit: 10, includeRead: false },
  sessionId: "session-xyz"
}
```

---

**示例 3: Result 消息**

```typescript
// SDK 消息
{
  type: "result",
  subtype: "success",
  result: "查询完成",
  total_cost_usd: 0.0012,
  duration_ms: 1500
}

// 转换为 WebSocket 消息
{
  type: "result",
  success: true,
  result: "查询完成",
  cost: 0.0012,
  duration: 1500,
  sessionId: "session-xyz"
}
```

---

## 🤖 AI 客户端集成

### **AIClient 类结构** (`ccsdk/ai-client.ts`)

```typescript
export class AIClient {
  private defaultOptions: AIQueryOptions;

  constructor(options?: Partial<AIQueryOptions>) {
    this.defaultOptions = {
      maxTurns: 100,
      cwd: path.join(process.cwd(), 'agent'),
      model: "opus",  // claude-opus-4-20250514
      allowedTools: [
        "Task", "Bash", "Glob", "Grep", "LS", "Read", "Edit", "Write",
        "WebFetch", "TodoWrite", "WebSearch", 
        "mcp__email__search_inbox", 
        "mcp__email__read_emails", 
        "Skill"
      ],
      appendSystemPrompt: EMAIL_AGENT_PROMPT,
      settingSources: ['local', 'project'],
      mcpServers: {
        "email": customServer  // 自定义邮件工具服务器
      },
      hooks: {
        // 文件写入钩子（限制脚本文件只能写入 custom_scripts 目录）
        PreToolUse: [
          {
            matcher: "Write|Edit|MultiEdit",
            hooks: [
              async (input: any): Promise<HookJSONOutput> => {
                const toolName = input.tool_name;
                const toolInput = input.tool_input;

                if (!['Write', 'Edit', 'MultiEdit'].includes(toolName)) {
                  return { continue: true };
                }

                let filePath = toolInput.file_path || '';
                const ext = path.extname(filePath).toLowerCase();
                
                if (ext === '.js' || ext === '.ts') {
                  const customScriptsPath = path.join(process.cwd(), 'agent', 'custom_scripts');

                  if (!filePath.startsWith(customScriptsPath)) {
                    return {
                      decision: 'block',
                      stopReason: `Script files must be written to ${customScriptsPath}`,
                      continue: false
                    };
                  }
                }

                return { continue: true };
              }
            ]
          }
        ]
      },
      ...options
    };
  }

  // 流式查询（Session 使用）
  async *queryStream(
    prompt: string | AsyncIterable<SDKUserMessage>,
    options?: Partial<AIQueryOptions>
  ): AsyncIterable<SDKMessage> {
    const mergedOptions = { ...this.defaultOptions, ...options };

    for await (const message of query({
      prompt,
      options: mergedOptions
    })) {
      yield message;
    }
  }

  // 单次查询（返回所有消息）
  async querySingle(prompt: string, options?: Partial<AIQueryOptions>): Promise<{
    messages: SDKMessage[];
    cost: number;
    duration: number;
  }> {
    const messages: SDKMessage[] = [];
    let totalCost = 0;
    let duration = 0;

    for await (const message of this.queryStream(prompt, options)) {
      messages.push(message);

      if (message.type === "result" && message.subtype === "success") {
        totalCost = message.total_cost_usd;
        duration = message.duration_ms;
      }
    }

    return { messages, cost: totalCost, duration };
  }
}
```

---

### **关键配置项**

| 配置项 | 值 | 用途 |
|--------|----|----|
| `maxTurns` | `100` | 最大对话轮数 |
| `model` | `"opus"` | Claude Opus 4 模型 |
| `cwd` | `agent/` | 工作目录（技能文件查找路径） |
| `appendSystemPrompt` | `EMAIL_AGENT_PROMPT` | 系统提示词 |
| `mcpServers.email` | `customServer` | 自定义邮件工具服务器 |
| `hooks.PreToolUse` | 文件写入钩子 | 限制脚本只能写入 `custom_scripts/` |

---

### **系统提示词** (`ccsdk/email-agent-prompt.ts`)

```typescript
export const EMAIL_AGENT_PROMPT = `You are a helpful email search assistant with access to the user's email database.

You can help users:
- Search for emails by sender, subject, date, or content
- Find emails with attachments
- Filter by read/unread status
- Search for specific types of emails (invoices, receipts, confirmations, etc.)
- Analyze email patterns and communication history
- Sync and retrieve new emails when needed

# IMPORTANT: Creating Email Listeners

When the user wants to set up **automated** email monitoring, notifications, or actions,
use the **listener-creator** skill using the Skill Tool to do this.
When referencing created listeners, use the format [listener:filename.ts].

# IMPORTANT: Creating One-Click Action Templates

When the user wants to create **reusable, user-triggered** actions,
use the **action-creator** skill using the Skill Tool to do this.

**Key difference**:
- **Listeners** = Automatic/event-triggered (run when emails arrive)
- **Actions** = User-triggered/on-demand (run when user clicks button)

When presenting email results:
- Use markdown formatting for readability
- Reference emails using [email:MESSAGE_ID] format for clickable links
- Show key details like subject, sender, and date
- Keep responses concise and relevant to the user's query

Your goal is to be a helpful assistant that makes it easy for users to find and manage their emails efficiently.`;
```

---

### **流式查询调用示例**

```typescript
// Session.ts 中的使用
const options = this.sdkSessionId
  ? { resume: this.sdkSessionId }
  : {};

for await (const message of this.aiClient.queryStream(content, options)) {
  // message 类型: SDKMessage
  // 可能的值:
  // - { type: "system", subtype: "init", session_id: "..." }
  // - { type: "user", message: { content: "..." } }
  // - { type: "assistant", message: { content: [...] } }
  // - { type: "result", subtype: "success", total_cost_usd: 0.001, ... }

  this.broadcastToSubscribers(message);
}
```

---

## 🐍 Python 实现要点

### **1. Session 类完整实现**

```python
import asyncio
import json
from typing import Set, Optional, AsyncIterator
from datetime import datetime

class Session:
    def __init__(self, id: str, db):
        self.id: str = id
        self.db = db
        self.processing_lock = asyncio.Lock()  # 并发控制锁
        self.subscribers: Set[WebSocket] = set()  # 订阅者集合
        self.message_count: int = 0
        self.ai_client = AIClient()
        self.sdk_session_id: Optional[str] = None  # 多轮对话 ID

    async def add_user_message(self, content: str) -> None:
        """处理用户消息"""
        # 获取锁（串行处理）
        async with self.processing_lock:
            self.message_count += 1
            print(f"Processing message {self.message_count} in session {self.id}")

            try:
                # 准备多轮对话选项
                options = {}
                if self.sdk_session_id:
                    options["resume"] = self.sdk_session_id

                # 流式调用 AI
                async for message in self.ai_client.query_stream(content, options):
                    # 广播消息
                    await self.broadcast_to_subscribers(message)

                    # 捕获 SDK 会话 ID
                    if message.get("type") == "system" and message.get("subtype") == "init":
                        self.sdk_session_id = message.get("session_id")
                        print(f"Captured SDK session ID: {self.sdk_session_id}")

                    # 检查结果
                    if message.get("type") == "result":
                        print("Result received, ready for next user message")

            except Exception as error:
                print(f"Error in session {self.id}: {error}")
                await self.broadcast_error(str(error))

    def subscribe(self, client: WebSocket) -> None:
        """添加订阅者"""
        self.subscribers.add(client)
        client.session_id = self.id

        # 发送会话信息
        asyncio.create_task(client.send_json({
            "type": "session_info",
            "sessionId": self.id,
            "messageCount": self.message_count,
            "isActive": self.processing_lock.locked()
        }))

    def unsubscribe(self, client: WebSocket) -> None:
        """移除订阅者"""
        self.subscribers.discard(client)

    async def broadcast_to_subscribers(self, message: dict) -> None:
        """广播消息给所有订阅者"""
        ws_message = None

        # 转换 SDK 消息为 WebSocket 消息
        if message.get("type") == "assistant":
            content = message.get("message", {}).get("content")
            
            if isinstance(content, str):
                ws_message = {
                    "type": "assistant_message",
                    "content": content,
                    "sessionId": self.id
                }
            elif isinstance(content, list):
                for block in content:
                    if block.get("type") == "text":
                        ws_message = {
                            "type": "assistant_message",
                            "content": block.get("text"),
                            "sessionId": self.id
                        }
                    elif block.get("type") == "tool_use":
                        ws_message = {
                            "type": "tool_use",
                            "toolName": block.get("name"),
                            "toolId": block.get("id"),
                            "toolInput": block.get("input"),
                            "sessionId": self.id
                        }
                    elif block.get("type") == "tool_result":
                        ws_message = {
                            "type": "tool_result",
                            "toolUseId": block.get("tool_use_id"),
                            "content": block.get("content"),
                            "isError": block.get("is_error"),
                            "sessionId": self.id
                        }
                    
                    if ws_message:
                        await self.broadcast(ws_message)
                return

        elif message.get("type") == "result":
            if message.get("subtype") == "success":
                ws_message = {
                    "type": "result",
                    "success": True,
                    "result": message.get("result"),
                    "cost": message.get("total_cost_usd"),
                    "duration": message.get("duration_ms"),
                    "sessionId": self.id
                }
            else:
                ws_message = {
                    "type": "result",
                    "success": False,
                    "error": message.get("subtype"),
                    "sessionId": self.id
                }

        elif message.get("type") == "system":
            ws_message = {
                "type": "system",
                "subtype": message.get("subtype"),
                "sessionId": self.id,
                "data": message
            }

        elif message.get("type") == "user":
            ws_message = {
                "type": "user_message",
                "content": message.get("message", {}).get("content"),
                "sessionId": self.id
            }

        if ws_message:
            await self.broadcast(ws_message)

    async def broadcast(self, message: dict) -> None:
        """广播消息"""
        message_str = json.dumps(message)
        disconnected = set()

        for client in self.subscribers:
            try:
                await client.send_text(message_str)
            except Exception as error:
                print(f"Error broadcasting to client: {error}")
                disconnected.add(client)

        # 移除断开的客户端
        self.subscribers -= disconnected

    async def broadcast_error(self, error: str) -> None:
        """广播错误消息"""
        await self.broadcast({
            "type": "error",
            "error": error,
            "sessionId": self.id
        })

    def has_subscribers(self) -> bool:
        """检查是否有订阅者"""
        return len(self.subscribers) > 0

    async def cleanup(self) -> None:
        """清理会话"""
        self.subscribers.clear()

    def end_conversation(self) -> None:
        """结束对话"""
        self.sdk_session_id = None
```

---

### **2. 并发控制对比**

| 特性 | TypeScript | Python |
|------|-----------|--------|
| **锁机制** | `queryPromise: Promise<void> \| null` | `asyncio.Lock()` |
| **获取锁** | `if (queryPromise) await queryPromise` | `async with self.processing_lock:` |
| **释放锁** | `finally { queryPromise = null }` | 自动释放（离开 `with` 块） |
| **锁状态检查** | `queryPromise !== null` | `lock.locked()` |

---

### **3. 类型定义**

```python
from typing import TypedDict, Literal, Optional, Union, List

class SDKMessage(TypedDict, total=False):
    type: Literal["assistant", "user", "system", "result"]
    subtype: Optional[str]
    message: Optional[dict]
    session_id: Optional[str]
    result: Optional[str]
    total_cost_usd: Optional[float]
    duration_ms: Optional[int]

class WSMessage(TypedDict):
    type: str
    sessionId: str
    content: Optional[str]
    success: Optional[bool]
    error: Optional[str]
```

---

### **4. WebSocket 集成（FastAPI）**

```python
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import Dict

app = FastAPI()

class WebSocketHandler:
    def __init__(self, db_manager):
        self.db = db_manager
        self.sessions: Dict[str, Session] = {}
        self.clients: Dict[str, WebSocket] = {}

    async def handle_connection(self, websocket: WebSocket):
        await websocket.accept()
        client_id = f"{datetime.now().timestamp()}-{id(websocket)}"
        self.clients[client_id] = websocket

        try:
            # 发送连接确认
            await websocket.send_json({
                "type": "connected",
                "message": "Connected to email assistant",
                "availableSessions": list(self.sessions.keys())
            })

            # 接收消息
            while True:
                data = await websocket.receive_json()
                await self.handle_message(websocket, data)

        except WebSocketDisconnect:
            # 清理订阅
            if hasattr(websocket, 'session_id') and websocket.session_id:
                session = self.sessions.get(websocket.session_id)
                if session:
                    session.unsubscribe(websocket)

            # 移除客户端
            del self.clients[client_id]

    async def handle_message(self, websocket: WebSocket, data: dict):
        msg_type = data.get("type")

        if msg_type == "chat":
            session = self.get_or_create_session(data.get("sessionId"))

            # 自动订阅
            if not hasattr(websocket, 'session_id') or websocket.session_id != session.id:
                session.subscribe(websocket)

            # 检查是否开始新对话
            if data.get("newConversation"):
                session.end_conversation()

            # 处理消息
            await session.add_user_message(data.get("content"))

        elif msg_type == "subscribe":
            session = self.sessions.get(data.get("sessionId"))
            if session:
                session.subscribe(websocket)
                await websocket.send_json({
                    "type": "subscribed",
                    "sessionId": data.get("sessionId")
                })

    def get_or_create_session(self, session_id: Optional[str] = None) -> Session:
        if session_id and session_id in self.sessions:
            return self.sessions[session_id]

        new_session_id = session_id or self.generate_session_id()
        session = Session(new_session_id, self.db)
        self.sessions[new_session_id] = session
        return session

    def generate_session_id(self) -> str:
        import random
        import string
        timestamp = int(datetime.now().timestamp() * 1000)
        random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=7))
        return f"session-{timestamp}-{random_str}"

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    handler = WebSocketHandler(db_manager)
    await handler.handle_connection(websocket)
```

---

## 📊 性能考虑

### **1. 内存管理**

- **订阅者集合**：使用 `Set` 而非 `Array`，O(1) 添加/删除
- **会话清理**：60 秒宽限期后自动清理无订阅者的会话
- **消息队列**：目前未实际使用，可移除以减少内存

---

### **2. 错误处理**

```typescript
// 广播时自动移除断开的客户端
private broadcast(message: any) {
  const messageStr = JSON.stringify(message);
  for (const client of this.subscribers) {
    try {
      client.send(messageStr);
    } catch (error) {
      console.error('Error broadcasting to client:', error);
      this.subscribers.delete(client);  // 自动清理
    }
  }
}
```

---

### **3. 并发性能**

- **串行处理**：确保上下文连续性
- **异步流式**：实时推送 AI 响应，减少等待时间
- **批量广播**：一次广播给所有订阅者

---

## ✅ 复刻检查清单

### **核心功能**
- [ ] Session 类（id、属性、方法）
- [ ] 并发控制（锁机制）
- [ ] 多轮对话（sdkSessionId 捕获与使用）
- [ ] 订阅者管理（发布-订阅模式）
- [ ] 消息广播（SDK 消息 → WebSocket 消息转换）
- [ ] AI 客户端集成（流式查询）

### **边界情况**
- [ ] 快速连续消息（并发控制测试）
- [ ] 多客户端订阅同一会话
- [ ] 客户端断开时自动清理
- [ ] 会话超时清理（60 秒宽限期）
- [ ] 新对话重置（endConversation）

### **Python 特定**
- [ ] `asyncio.Lock` 替代 `queryPromise`
- [ ] `set` 替代 `Set<WSClient>`
- [ ] FastAPI WebSocket 集成
- [ ] 类型提示（TypedDict / Pydantic）

---

## 📚 相关文档

继续阅读：
1. **PLUGIN_LOADING.md** - 插件加载与热重载机制
2. **WEBSOCKET_MESSAGES.md** - WebSocket 消息格式详解
3. **DATABASE_SCHEMA.md** - 数据库表结构
4. **TS_TO_PYTHON_MAP.md** - TypeScript → Python 完整映射
