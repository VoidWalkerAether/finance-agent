# Email Agent 实际架构文档

> **文档目的**：忠实记录 Email Agent (TypeScript/Bun) 的实际实现，为 Python 复刻提供精确参考。
> **原则**：只记录已有代码，不添加设计。代码片段为主，理论描述为辅。

---

## 📁 目录结构（实际）

```
email-agent/
├── ccsdk/                    # 核心 SDK 层（Agent 引擎）
│   ├── session.ts           # 会话管理（单会话，多轮对话）
│   ├── websocket-handler.ts # WebSocket 连接管理与消息分发
│   ├── listeners-manager.ts # 监听器加载、执行、热重载
│   ├── actions-manager.ts   # 动作模板加载、实例注册、执行
│   ├── ui-state-manager.ts  # UI 状态持久化、广播
│   ├── component-manager.ts # 组件模板管理
│   ├── ai-client.ts         # Claude API 封装
│   ├── message-queue.ts     # 消息队列实现
│   ├── custom-tools.ts      # 自定义工具定义
│   └── types.ts             # TypeScript 类型定义
│
├── agent/                    # 自定义脚本层（用户可扩展）
│   ├── custom_scripts/
│   │   ├── listeners/       # 监听器脚本（事件驱动）
│   │   ├── actions/         # 动作脚本（按钮触发）
│   │   ├── ui-states/       # UI 状态模板
│   │   └── types.ts         # 插件类型定义
│   ├── data/
│   │   └── PROFILE.MD       # 用户个人资料（AI 上下文）
│   └── email-api.ts         # 邮件 API 封装
│
├── database/                 # 数据库层
│   ├── database-manager.ts  # SQLite 操作、FTS5 全文搜索
│   ├── imap-manager.ts      # IMAP 协议、IDLE 监听
│   ├── email-sync.ts        # 邮件同步服务
│   ├── email-search.ts      # 邮件搜索逻辑
│   ├── email-db.ts          # 数据库查询封装
│   ├── config.ts            # 数据库配置
│   └── schema.sql           # 数据库表结构定义
│
├── server/                   # 服务端
│   ├── endpoints/           # REST API 端点
│   │   ├── emails.ts        # 邮件相关 API
│   │   ├── listeners.ts     # 监听器相关 API
│   │   ├── sync.ts          # 同步相关 API
│   │   ├── ui-states.ts     # UI 状态相关 API
│   │   └── index.ts         # 端点导出
│   ├── server.ts            # Bun HTTP Server + WebSocket
│   └── index.ts             # 服务入口
│
└── client/                   # 前端（React）
    ├── components/          # React 组件
    ├── hooks/               # React Hooks
    ├── store/               # 状态管理（Jotai）
    └── App.tsx              # 主应用组件
```

---

## 🏗️ 架构层次（实际）

### **Layer 1: CCSDK 层（核心引擎）**

#### **职责**
- 会话生命周期管理
- WebSocket 连接与消息分发
- 插件系统（Listeners、Actions、UI States）
- AI 调用与流式响应
- 数据持久化协调

#### **核心类实现**

##### **1. Session 类** (`ccsdk/session.ts`)

```typescript
export class Session {
  public readonly id: string;
  private messageQueue: MessageQueue<SDKUserMessage>;
  private queryPromise: Promise<void> | null = null;  // 并发控制锁
  private subscribers: Set<WSClient> = new Set();
  private db: Database;
  private messageCount = 0;
  private aiClient: AIClient;
  private sdkSessionId: string | null = null;  // Claude 会话 ID

  constructor(id: string, db: Database) {
    this.id = id;
    this.db = db;
    this.messageQueue = new MessageQueue();
    this.aiClient = new AIClient();
  }

  // 处理单条用户消息
  async addUserMessage(content: string): Promise<void> {
    if (this.queryPromise) {
      await this.queryPromise;  // 等待上一个查询完成
    }

    this.messageCount++;
    this.queryPromise = (async () => {
      try {
        // 使用 resume 实现多轮对话
        const options = this.sdkSessionId
          ? { resume: this.sdkSessionId }
          : {};

        // 流式调用 AI
        for await (const message of this.aiClient.queryStream(content, options)) {
          this.broadcastToSubscribers(message);

          // 捕获 SDK 会话 ID 用于多轮对话
          if (message.type === 'system' && message.subtype === 'init') {
            this.sdkSessionId = message.session_id;
          }
        }
      } catch (error) {
        this.broadcastError(error.message);
      } finally {
        this.queryPromise = null;
      }
    })();

    await this.queryPromise;
  }

  // 订阅管理（发布-订阅模式）
  subscribe(client: WSClient) {
    this.subscribers.add(client);
    client.data.sessionId = this.id;
  }

  unsubscribe(client: WSClient) {
    this.subscribers.delete(client);
  }

  // 广播消息给所有订阅者
  private broadcastToSubscribers(message: SDKMessage) {
    let wsMessage: any = null;

    if (message.type === "assistant") {
      // 处理助手消息
      const content = message.message.content;
      if (typeof content === 'string') {
        wsMessage = { type: 'assistant_message', content, sessionId: this.id };
      } else if (Array.isArray(content)) {
        // 处理内容块（text、tool_use、tool_result）
        for (const block of content) {
          if (block.type === 'text') {
            wsMessage = { type: 'assistant_message', content: block.text, sessionId: this.id };
          } else if (block.type === 'tool_use') {
            wsMessage = { type: 'tool_use', toolName: block.name, toolId: block.id, toolInput: block.input, sessionId: this.id };
          } else if (block.type === 'tool_result') {
            wsMessage = { type: 'tool_result', toolUseId: block.tool_use_id, content: block.content, isError: block.is_error, sessionId: this.id };
          }
          if (wsMessage) this.broadcast(wsMessage);
        }
        return;
      }
    } else if (message.type === "result") {
      // 处理结果消息
      if (message.subtype === "success") {
        wsMessage = { type: 'result', success: true, result: message.result, cost: message.total_cost_usd, duration: message.duration_ms, sessionId: this.id };
      } else {
        wsMessage = { type: 'result', success: false, error: message.subtype, sessionId: this.id };
      }
    } else if (message.type === "user") {
      // 回显用户消息
      wsMessage = { type: 'user_message', content: message.message.content, sessionId: this.id };
    }

    if (wsMessage) this.broadcast(wsMessage);
  }

  private broadcast(message: any) {
    const messageStr = JSON.stringify(message);
    for (const client of this.subscribers) {
      try {
        client.send(messageStr);
      } catch (error) {
        this.subscribers.delete(client);
      }
    }
  }

  endConversation() {
    this.sdkSessionId = null;
    this.queryPromise = null;
  }
}
```

**关键机制**：
- **并发控制**：使用 `queryPromise` 作为锁，确保消息串行处理
- **多轮对话**：通过 `sdkSessionId` 维持对话上下文
- **发布-订阅**：通过 `subscribers` 实现消息广播

---

##### **2. WebSocketHandler 类** (`ccsdk/websocket-handler.ts`)

```typescript
export class WebSocketHandler {
  private db: Database;
  private sessions: Map<string, Session> = new Map();
  private clients: Map<string, WSClient> = new Map();
  private actionsManager?: ActionsManager;
  private uiStateManager?: UIStateManager;
  private componentManager?: ComponentManager;

  constructor(dbPath: string, actionsManager?, uiStateManager?, componentManager?) {
    this.db = new Database(dbPath);
    this.actionsManager = actionsManager;
    this.uiStateManager = uiStateManager;
    this.componentManager = componentManager;
    this.initEmailWatcher();      // 定期推送收件箱更新
    this.initUIStateWatcher();    // 监听 UI 状态更新
  }

  // WebSocket 生命周期
  public async onOpen(ws: WSClient) {
    const clientId = Date.now() + '-' + Math.random().toString(36).substring(7);
    this.clients.set(clientId, ws);

    // 发送初始数据
    ws.send(JSON.stringify({ type: 'connected', availableSessions: Array.from(this.sessions.keys()) }));
    
    const emails = await this.getRecentEmails();
    ws.send(JSON.stringify({ type: 'inbox_update', emails }));

    // 发送模板信息
    if (this.actionsManager) {
      const templates = this.actionsManager.getAllTemplates();
      ws.send(JSON.stringify({ type: 'action_templates', templates }));
    }
  }

  public async onMessage(ws: WSClient, message: string) {
    const data = JSON.parse(message) as IncomingMessage;

    switch (data.type) {
      case 'chat': {
        const session = this.getOrCreateSession(data.sessionId);
        
        // 自动订阅
        if (!ws.data.sessionId || ws.data.sessionId !== session.id) {
          session.subscribe(ws);
        }

        // 新对话标记
        if (data.newConversation) {
          session.endConversation();
        }

        await session.addUserMessage(data.content);
        break;
      }

      case 'subscribe': {
        const session = this.sessions.get(data.sessionId);
        if (session) {
          // 取消之前的订阅
          if (ws.data.sessionId && ws.data.sessionId !== data.sessionId) {
            const currentSession = this.sessions.get(ws.data.sessionId);
            currentSession?.unsubscribe(ws);
          }
          session.subscribe(ws);
        }
        break;
      }

      case 'execute_action': {
        const { instanceId, sessionId } = data;
        const session = this.sessions.get(sessionId);
        if (!session) break;

        // 创建 ActionContext
        const context = this.createActionContext(sessionId, session);

        // 执行动作
        const result = await this.actionsManager.executeAction(instanceId, context);

        // 发送结果
        ws.send(JSON.stringify({ type: 'action_result', instanceId, result, sessionId }));

        // 处理组件实例
        if (result.components && this.componentManager) {
          for (const component of result.components) {
            this.componentManager.registerInstance({ ...component, sessionId, createdAt: new Date().toISOString() });
            this.broadcastComponentInstance(component, sessionId);
          }
        }

        if (result.refreshInbox) {
          this.broadcastInboxUpdate();
        }
        break;
      }
    }
  }

  public onClose(ws: WSClient) {
    // 取消订阅
    if (ws.data.sessionId) {
      const session = this.sessions.get(ws.data.sessionId);
      session?.unsubscribe(ws);
    }

    // 从客户端列表移除
    const clientsArray = Array.from(this.clients.entries());
    for (const [id, client] of clientsArray) {
      if (client === ws) {
        this.clients.delete(id);
        break;
      }
    }

    this.cleanupEmptySessions();
  }

  // 定期推送收件箱更新
  private async initEmailWatcher() {
    setInterval(() => {
      this.broadcastInboxUpdate();
    }, 5000);  // 每 5 秒推送一次
  }

  private async broadcastInboxUpdate() {
    const emails = await this.getRecentEmails();
    const message = JSON.stringify({ type: 'inbox_update', emails });
    for (const client of this.clients.values()) {
      try { client.send(message); } catch {}
    }
  }

  // 创建 ActionContext（给动作执行使用）
  private createActionContext(sessionId: string, session: any): ActionContext {
    return {
      sessionId,
      emailAPI: { /* 邮件 API 方法 */ },
      archiveEmail: async (emailId) => { /* IMAP 操作 */ },
      starEmail: async (emailId) => { /* ... */ },
      callAgent: async (options) => { /* 调用 Claude API */ },
      notify: (message, options) => { /* 广播通知 */ },
      uiState: {
        get: async (stateId) => await this.uiStateManager?.getState(stateId),
        set: async (stateId, data) => await this.uiStateManager?.setState(stateId, data)
      }
    };
  }
}
```

**关键机制**：
- **会话管理**：通过 `sessions` Map 管理多个会话
- **客户端管理**：通过 `clients` Map 管理 WebSocket 连接
- **消息路由**：根据 `type` 字段分发消息到不同处理器
- **定时推送**：每 5 秒推送收件箱更新

---

##### **3. ListenersManager 类** (`ccsdk/listeners-manager.ts`)

```typescript
export class ListenersManager {
  private listenersDir = join(process.cwd(), "agent/custom_scripts/listeners");
  private listeners: Map<string, ListenerModule> = new Map();
  private notificationCallback?: (notification: any) => void;
  private logBroadcastCallback?: (log: ListenerLogEntry & { listenerId: string; listenerName: string }) => void;
  private watcherActive = false;
  private imapManager: ImapManager;
  private databaseManager: DatabaseManager;
  private uiStateManager?: UIStateManager;
  private logWriter: LogWriter;

  constructor(notificationCallback, imapManager, databaseManager, logBroadcastCallback?, uiStateManager?) {
    this.notificationCallback = notificationCallback;
    this.imapManager = imapManager;
    this.databaseManager = databaseManager;
    this.logBroadcastCallback = logBroadcastCallback;
    this.uiStateManager = uiStateManager;
    this.logWriter = new LogWriter(this.listenersDir);
  }

  // 加载所有监听器
  async loadAllListeners(): Promise<ListenerConfig[]> {
    this.listeners.clear();

    const files = await readdir(this.listenersDir);

    for (const file of files) {
      // 跳过非 TS 文件和 _ 开头的文件
      if (file.endsWith(".ts") && !file.startsWith("_") && !file.startsWith(".")) {
        await this.loadListener(file);
      }
    }

    return Array.from(this.listeners.values()).map(l => l.config);
  }

  // 加载单个监听器
  private async loadListener(filename: string): Promise<void> {
    try {
      const filePath = join(this.listenersDir, filename);
      // 使用缓存破坏实现热重载
      const module = await import(`${filePath}?t=${Date.now()}`);

      if (!module.config || !module.handler) {
        console.error(`Invalid listener ${filename}: missing config or handler`);
        return;
      }

      if (module.config.enabled) {
        this.listeners.set(module.config.id, {
          config: module.config,
          handler: module.handler
        });
        console.log(`✓ Loaded listener: ${module.config.id} (${module.config.name})`);
      }
    } catch (error) {
      console.error(`Error loading listener ${filename}:`, error);
    }
  }

  // 创建 ListenerContext
  private createContext(listenerConfig: ListenerConfig): ListenerContext {
    return {
      notify: async (message: string, options?: NotifyOptions) => {
        if (this.notificationCallback) {
          this.notificationCallback({
            type: "listener_notification",
            listenerId: listenerConfig.id,
            listenerName: listenerConfig.name,
            priority: options?.priority || "normal",
            message,
            timestamp: new Date().toISOString()
          });
        }
      },

      archiveEmail: async (emailId: string) => {
        const email = await this.databaseManager.getEmailByMessageId(emailId);
        if (!email?.imapUid) throw new Error(`Email not found: ${emailId}`);
        
        await this.imapManager.archiveEmail(email.imapUid, email.folder);
        this.databaseManager.updateEmailFlags(emailId, { folder: '[Gmail]/All Mail' });
      },

      starEmail: async (emailId: string) => {
        const email = await this.databaseManager.getEmailByMessageId(emailId);
        await this.imapManager.starEmail(email.imapUid, email.folder);
        this.databaseManager.updateEmailFlags(emailId, { isStarred: true });
      },

      markAsRead: async (emailId: string) => { /* 类似实现 */ },
      addLabel: async (emailId: string, label: string) => { /* 类似实现 */ },

      callAgent: async <T = any>(options: SubagentOptions<T>): Promise<T> => {
        const anthropic = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });

        const modelMap = {
          opus: "claude-opus-4-20250514",
          sonnet: "claude-sonnet-4-20250514",
          haiku: "claude-3-5-haiku-20241022"
        };

        const response = await anthropic.messages.create({
          model: modelMap[options.model || "haiku"],
          max_tokens: 4096,
          messages: [{ role: "user", content: options.prompt }],
          tools: [{
            name: "respond",
            description: "Respond with structured data matching the schema",
            input_schema: options.schema
          }],
          tool_choice: { type: "tool", name: "respond" }
        });

        const toolUse = response.content.find((block) => block.type === "tool_use");
        if (!toolUse) throw new Error("Agent did not return structured response");

        return toolUse.input as T;
      },

      uiState: {
        get: async <T = any>(stateId: string): Promise<T | null> => {
          return await this.uiStateManager?.getState<T>(stateId);
        },
        set: async <T = any>(stateId: string, data: T): Promise<void> => {
          await this.uiStateManager?.setState<T>(stateId, data);
        }
      }
    };
  }

  // 检查事件并执行匹配的监听器
  async checkEvent(event: EventType, data: any): Promise<void> {
    const matchingListeners = Array.from(this.listeners.values())
      .filter(listener => listener.config.event === event);

    if (matchingListeners.length === 0) return;

    for (const listener of matchingListeners) {
      const startTime = Date.now();
      let result: ListenerResult | undefined;
      let error: Error | undefined;

      try {
        const context = this.createContext(listener.config);
        const handlerResult = await listener.handler(data, context);

        result = handlerResult || { executed: true, reason: "Listener completed successfully" };
      } catch (err) {
        error = err as Error;
        result = { executed: false, reason: `Error: ${error.message}` };
      }

      const executionTimeMs = Date.now() - startTime;

      // 创建日志条目
      const logEntry: ListenerLogEntry = {
        timestamp: new Date().toISOString(),
        emailId: data.messageId || data.id || "unknown",
        emailSubject: data.subject || "No subject",
        emailFrom: data.from || "Unknown sender",
        executed: result.executed,
        reason: result.reason,
        actions: result.actions,
        executionTimeMs,
        error: error ? error.message : undefined
      };

      // 写入 JSONL 文件
      this.logWriter.appendLog(listener.config.id, logEntry);

      // 广播日志
      if (this.logBroadcastCallback) {
        this.logBroadcastCallback({
          ...logEntry,
          listenerId: listener.config.id,
          listenerName: listener.config.name
        });
      }
    }
  }

  // 监听文件变化并热重载
  async watchListeners(onChange: (listeners: ListenerConfig[]) => void): Promise<void> {
    if (this.watcherActive) return;

    this.watcherActive = true;
    const watcher = watch(this.listenersDir);

    for await (const event of watcher) {
      if (event.filename?.endsWith(".ts")) {
        console.log("[ListenersManager] Reloading listeners...");
        const listeners = await this.loadAllListeners();
        onChange(listeners);
      }
    }
  }
}
```

**关键机制**：
- **动态加载**：使用 `import()` 和缓存破坏 (`?t=${Date.now()}`) 实现热重载
- **事件匹配**：通过 `config.event` 过滤匹配的监听器
- **上下文注入**：为每个监听器创建独立的 `ListenerContext`
- **JSONL 日志**：使用 `LogWriter` 记录执行日志

---

### **Layer 2: Database 层**

#### **职责**
- SQLite 数据库操作
- IMAP 协议通信
- 邮件同步与搜索
- UI 状态持久化

#### **核心类实现**

##### **DatabaseManager 类** (`database/database-manager.ts`)

```typescript
export class DatabaseManager {
  private static instance: DatabaseManager;
  private db: Database;
  private dbPath: string;

  private constructor(dbPath: string = DATABASE_PATH) {
    this.dbPath = dbPath;
    this.db = new Database(dbPath);
    this.db.exec("PRAGMA journal_mode = WAL");  // Write-Ahead Logging
    this.db.exec("PRAGMA foreign_keys = ON");
    this.initializeDatabase();
  }

  public static getInstance(dbPath?: string): DatabaseManager {
    if (!DatabaseManager.instance) {
      DatabaseManager.instance = new DatabaseManager(dbPath);
    }
    return DatabaseManager.instance;
  }

  private initializeDatabase(): void {
    // 创建 emails 表
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS emails (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        message_id TEXT UNIQUE NOT NULL,
        imap_uid INTEGER,
        thread_id TEXT,
        in_reply_to TEXT,
        email_references TEXT,
        date_sent DATETIME NOT NULL,
        subject TEXT,
        from_address TEXT NOT NULL,
        from_name TEXT,
        to_addresses TEXT,
        cc_addresses TEXT,
        body_text TEXT,
        body_html TEXT,
        snippet TEXT,
        is_read BOOLEAN DEFAULT 0,
        is_starred BOOLEAN DEFAULT 0,
        has_attachments BOOLEAN DEFAULT 0,
        folder TEXT DEFAULT 'INBOX',
        labels TEXT,  -- JSON 数组
        raw_headers TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
      )
    `);

    // 创建 FTS5 全文搜索表
    this.db.exec(`
      CREATE VIRTUAL TABLE IF NOT EXISTS emails_fts USING fts5(
        messageId UNINDEXED,
        subject,
        fromAddress,
        fromName,
        bodyText,
        toAddresses,
        ccAddresses,
        attachment_names,
        tokenize = 'porter unicode61'
      )
    `);

    // 创建 UI State 表
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS ui_states (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        state_id TEXT UNIQUE NOT NULL,
        data_json TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
      )
    `);

    // 创建索引
    this.db.exec("CREATE INDEX IF NOT EXISTS idx_emails_date_sent ON emails(date_sent DESC)");
    this.db.exec("CREATE INDEX IF NOT EXISTS idx_emails_from_address ON emails(from_address)");
    // ...更多索引
  }

  // Upsert 邮件（带附件）
  public upsertEmail(email: EmailRecord, attachments: Attachment[] = []): number {
    const upsertEmail = this.db.prepare(`
      INSERT INTO emails (message_id, subject, from_address, ...)
      VALUES ($messageId, $subject, $fromAddress, ...)
      ON CONFLICT(message_id) DO UPDATE SET
        subject = excluded.subject,
        from_address = excluded.from_address,
        ...
        updated_at = CURRENT_TIMESTAMP
      RETURNING id
    `);

    const insertAttachment = this.db.prepare(`
      INSERT INTO attachments (email_id, filename, content_type, ...)
      VALUES ($emailId, $filename, $contentType, ...)
    `);

    // 使用事务确保一致性
    const upsertTransaction = this.db.transaction(() => {
      const result = upsertEmail.get({ $messageId: email.messageId, ... });
      const emailId = result.id;

      // 插入附件
      for (const attachment of attachments) {
        insertAttachment.run({ $emailId: emailId, ... });
      }

      return emailId;
    });

    return upsertTransaction();
  }

  // 搜索邮件（支持全文搜索）
  public searchEmails(criteria: SearchCriteria): EmailRecord[] {
    let whereClauses: string[] = [];
    let params: any = {};

    // 全文搜索
    if (criteria.query) {
      whereClauses.push(`
        e.id IN (
          SELECT e2.id FROM emails e2
          JOIN emails_fts fts ON e2.message_id = fts.message_id
          WHERE emails_fts MATCH $query
        )
      `);
      params.$query = criteria.query;
    }

    // From 过滤（支持数组）
    if (criteria.from) {
      const fromAddresses = Array.isArray(criteria.from) ? criteria.from : [criteria.from];
      if (fromAddresses.length === 1) {
        whereClauses.push("e.from_address LIKE $from");
        params.$from = `%${fromAddresses[0]}%`;
      } else {
        const fromClauses = fromAddresses.map((_, i) => `e.from_address LIKE $from${i}`);
        whereClauses.push(`(${fromClauses.join(' OR ')})`);
        fromAddresses.forEach((addr, i) => { params[`$from${i}`] = `%${addr}%`; });
      }
    }

    // ... 其他过滤条件

    const whereClause = whereClauses.length > 0 ? "WHERE " + whereClauses.join(" AND ") : "";
    const limit = criteria.limit || 30;

    const sql = `
      SELECT e.* FROM emails e
      ${whereClause}
      ORDER BY e.date_sent DESC
      LIMIT ${limit}
    `;

    const query = this.db.prepare(sql);
    const results = query.all(params);

    return results.map(row => this.mapRowToEmailRecord(row));
  }

  // UI State 操作
  public getUIState(stateId: string): any | null {
    const query = this.db.prepare(`
      SELECT data_json FROM ui_states WHERE state_id = $stateId
    `);
    const result = query.get({ $stateId: stateId });
    return result ? JSON.parse(result.data_json) : null;
  }

  public setUIState(stateId: string, data: any): void {
    const dataJson = JSON.stringify(data);
    const query = this.db.prepare(`
      INSERT INTO ui_states (state_id, data_json, created_at, updated_at)
      VALUES ($stateId, $dataJson, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
      ON CONFLICT(state_id) DO UPDATE SET
        data_json = $dataJson,
        updated_at = CURRENT_TIMESTAMP
    `);
    query.run({ $stateId: stateId, $dataJson: dataJson });
  }
}
```

**关键技术**：
- **SQLite WAL 模式**：提升并发性能
- **FTS5 全文搜索**：支持中英文分词
- **事务保证**：确保邮件和附件一致性
- **单例模式**：全局唯一数据库实例

---

##### **ImapManager 类** (`database/imap-manager.ts`)

```typescript
export class ImapManager {
  private static instance: ImapManager;
  private imapConfig: ImapConfig;
  private imap: any;  // node-imap 实例
  private isConnected: boolean = false;
  private connectionPromise: Promise<void> | null = null;
  private isIdling: boolean = false;
  private currentFolder: string = "INBOX";
  private onNewEmailCallback: ((count: number) => void) | null = null;

  private constructor(config?: Partial<ImapConfig>) {
    const EMAIL = config?.user || process.env.EMAIL_ADDRESS;
    const PASSWORD = config?.password || process.env.EMAIL_APP_PASSWORD;

    if (!EMAIL || !PASSWORD) {
      throw new Error("Email credentials not found!");
    }

    this.imapConfig = {
      user: EMAIL,
      password: PASSWORD,
      host: config?.host || "imap.gmail.com",
      port: config?.port || 993,
      tls: true,
      connTimeout: 30000,
      authTimeout: 30000,
      keepalive: {
        interval: 10000,
        idleInterval: 300000,
        forceNoop: true
      }
    };

    this.imap = new Imap(this.imapConfig);
  }

  public static getInstance(config?: Partial<ImapConfig>): ImapManager {
    if (!ImapManager.instance) {
      ImapManager.instance = new ImapManager(config);
    }
    return ImapManager.instance;
  }

  private async connect(): Promise<void> {
    if (this.isConnected) return;
    if (this.connectionPromise) return this.connectionPromise;

    this.connectionPromise = new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        this.imap.end();
        reject(new Error('IMAP connection timeout after 30 seconds'));
      }, 30000);

      this.imap.once("ready", () => {
        clearTimeout(timeout);
        this.isConnected = true;
        this.connectionPromise = null;
        resolve();
      });

      this.imap.once("error", (err: Error) => {
        clearTimeout(timeout);
        this.isConnected = false;
        this.connectionPromise = null;
        reject(err);
      });

      this.imap.connect();
    });

    return this.connectionPromise;
  }

  // 搜索邮件（使用 IMAP 搜索）
  public async searchEmails(criteria: SearchCriteria): Promise<Array<{ email: EmailRecord; attachments: Attachment[] }>> {
    await this.ensureConnection();

    const folders = criteria.folders || [criteria.folder || "INBOX"];
    const allEmails: Array<{ email: EmailRecord; attachments: Attachment[] }> = [];
    const limit = criteria.limit || 30;

    for (const folder of folders) {
      await this.openMailbox(folder);

      const imapCriteria = this.buildImapSearchCriteria(criteria);
      const uids = await this.searchMailbox(imapCriteria);

      if (uids.length === 0) continue;

      // 限制 UIDs（倒序取最新）
      const limitedUids = uids.slice(-Math.min(limit, uids.length)).reverse();

      // 并行批量拉取
      const parsedEmails = await this.fetchEmailsBatch(limitedUids, false, 10);

      for (const uid of limitedUids) {
        const parsed = parsedEmails.get(uid);
        if (!parsed) continue;

        const email = this.parseEmailToRecord(parsed, uid, folder);
        const attachments = /* 提取附件 */;

        allEmails.push({ email, attachments });

        if (allEmails.length >= limit) break;
      }

      if (allEmails.length >= limit) break;
    }

    return allEmails;
  }

  // 并行批量拉取邮件
  private async fetchEmailsBatch(uids: number[], headersOnly: boolean, batchSize: number): Promise<Map<number, any>> {
    const results = new Map<number, any>();

    for (let i = 0; i < uids.length; i += batchSize) {
      const batch = uids.slice(i, i + batchSize);
      const promises = batch.map(async (uid) => {
        try {
          const parsed = await this.fetchEmail(uid, headersOnly);
          return { uid, parsed };
        } catch (err) {
          return { uid, parsed: null };
        }
      });

      const batchResults = await Promise.all(promises);
      for (const { uid, parsed } of batchResults) {
        if (parsed) results.set(uid, parsed);
      }
    }

    return results;
  }

  // 启动 IDLE 监听
  public async startIdleMonitoring(folder: string = "INBOX", onNewEmail: (count: number) => void): Promise<void> {
    await this.ensureConnection();

    this.currentFolder = folder;
    this.onNewEmailCallback = onNewEmail;

    await this.openMailbox(folder);

    this.isIdling = true;

    // 监听新邮件事件
    this.imap.on("mail", (numNewMsgs: number) => {
      console.log(`📬 New email(s) detected: ${numNewMsgs}`);
      if (this.onNewEmailCallback) {
        this.onNewEmailCallback(numNewMsgs);
      }
    });

    // 错误处理与自动重连
    this.imap.on("error", (err: Error) => {
      console.error("❌ IMAP IDLE error:", err.message);
      this.isIdling = false;
      setTimeout(() => {
        this.reconnect().then(() => {
          this.startIdleMonitoring(folder, onNewEmail);
        });
      }, 5000);
    });
  }

  // 邮件操作方法
  public async markAsRead(uid: number, folder: string = "INBOX"): Promise<void> {
    await this.ensureConnection();
    await this.openMailbox(folder, false);  // 读写模式

    return new Promise((resolve, reject) => {
      this.imap.addFlags(uid, ['\\Seen'], (err: Error | null) => {
        if (err) reject(err);
        else resolve();
      });
    });
  }

  public async starEmail(uid: number, folder: string = "INBOX"): Promise<void> {
    await this.openMailbox(folder, false);
    return new Promise((resolve, reject) => {
      this.imap.addFlags(uid, ['\\Flagged'], (err: Error | null) => {
        if (err) reject(err);
        else resolve();
      });
    });
  }

  public async archiveEmail(uid: number, folder: string = "INBOX"): Promise<void> {
    await this.openMailbox(folder, false);
    return new Promise((resolve, reject) => {
      this.imap.move(uid, '[Gmail]/All Mail', (err: Error | null) => {
        if (err) reject(err);
        else resolve();
      });
    });
  }
}
```

**关键技术**：
- **IDLE 协议**：实时监听新邮件（通过 `node-imap` 的 `mail` 事件）
- **并行拉取**：使用 `Promise.all` 批量拉取邮件
- **自动重连**：错误时自动重连并恢复 IDLE
- **单例模式**：全局唯一 IMAP 连接

---

### **Layer 3: Server 层**

#### **职责**
- Bun HTTP Server
- WebSocket 服务
- REST API 端点
- 前端资源服务（Transpile TSX）

#### **核心实现** (`server/server.ts`)

```typescript
// 初始化管理器
const dbManager = DatabaseManager.getInstance();
const imapManager = ImapManager.getInstance();
const actionsManager = new ActionsManager();
const uiStateManager = new UIStateManager(dbManager);
const componentManager = new ComponentManager(dbManager);

const wsHandler = new WebSocketHandler(
  DATABASE_PATH,
  actionsManager,
  uiStateManager,
  componentManager
);

const listenersManager = new ListenersManager(
  (notification) => { /* 通知回调 */ },
  imapManager,
  dbManager,
  (log) => { wsHandler.broadcastListenerLog(log); },
  uiStateManager
);

const syncService = new EmailSyncService(DATABASE_PATH, listenersManager);

// 异步初始化
(async () => {
  // 加载所有监听器
  await listenersManager.loadAllListeners();

  // 启动文件监听（热重载）
  listenersManager.watchListeners((listeners) => {
    console.log(`Listeners reloaded: ${listeners.length} active`);
  });

  // 加载动作模板
  await actionsManager.loadAllTemplates();
  actionsManager.watchTemplates((templates) => {
    console.log(`Action templates reloaded: ${templates.length}`);
  });

  // 加载 UI 状态模板
  await uiStateManager.loadAllTemplates();
  uiStateManager.watchTemplates((templates) => {
    console.log(`UI state templates reloaded: ${templates.length}`);
  });

  // 启动 IDLE 监听
  await imapManager.startIdleMonitoring("INBOX", async (count: number) => {
    console.log(`IDLE: ${count} new email(s) detected`);
    await syncService.handleIdleNewEmails(count, "INBOX");
  });
})();

const server = Bun.serve({
  port: 3000,
  idleTimeout: 120,

  websocket: {
    open(ws: WSClient) { wsHandler.onOpen(ws); },
    message(ws: WSClient, message: string) { wsHandler.onMessage(ws, message); },
    close(ws: WSClient) { wsHandler.onClose(ws); }
  },

  async fetch(req: Request, server: any) {
    const url = new URL(req.url);

    // CORS 预检
    if (req.method === 'OPTIONS') {
      return new Response(null, { headers: corsHeaders });
    }

    // WebSocket 升级
    if (url.pathname === '/ws') {
      const upgraded = server.upgrade(req, { data: { sessionId: '' } });
      if (!upgraded) {
        return new Response('WebSocket upgrade failed', { status: 400 });
      }
      return;
    }

    // 前端页面
    if (url.pathname === '/') {
      const file = Bun.file('./client/index.html');
      return new Response(file, { headers: { 'Content-Type': 'text/html' } });
    }

    // CSS 处理（Tailwind + PostCSS）
    if (url.pathname.endsWith('.css')) {
      const file = Bun.file(`.${url.pathname}`);
      if (await file.exists()) {
        const cssContent = await file.text();
        const postcss = require('postcss');
        const tailwindcss = require('@tailwindcss/postcss');

        const result = await postcss([tailwindcss()]).process(cssContent, { from: undefined });
        return new Response(result.css, { headers: { 'Content-Type': 'text/css' } });
      }
    }

    // TypeScript/TSX 转译
    if (url.pathname.endsWith('.tsx') || url.pathname.endsWith('.ts')) {
      const filePath = `.${url.pathname}`;
      const file = Bun.file(filePath);
      if (await file.exists()) {
        const transpiled = await Bun.build({
          entrypoints: [filePath],
          target: 'browser',
          format: 'esm',
        });
        if (transpiled.success) {
          const jsCode = await transpiled.outputs[0].text();
          return new Response(jsCode, { headers: { 'Content-Type': 'application/javascript' } });
        }
      }
    }

    // REST API 端点
    if (url.pathname === '/api/sync' && req.method === 'POST') {
      return handleSyncEndpoint(req);
    }

    if (url.pathname === '/api/emails/inbox' && req.method === 'GET') {
      return handleInboxEndpoint(req);
    }

    if (url.pathname === '/api/listeners' && req.method === 'GET') {
      const listeners = listenersManager.getAllListeners();
      return new Response(JSON.stringify({ listeners }), {
        headers: { 'Content-Type': 'application/json', ...corsHeaders }
      });
    }

    // ... 更多端点

    return new Response('Not Found', { status: 404 });
  },
});

console.log(`Server running at http://localhost:${server.port}`);
console.log('WebSocket endpoint available at ws://localhost:3000/ws');
```

**关键技术**：
- **Bun Native WebSocket**：无需额外库即可处理 WebSocket
- **Bun Transpiler**：实时转译 TSX 文件
- **PostCSS + Tailwind**：实时处理 CSS
- **异步初始化**：启动时加载所有插件和监听器

---

## 🧩 技术栈（实际使用）

### **运行时与工具**
```json
{
  "runtime": "Bun 1.x",
  "database": "SQLite (bun:sqlite)",
  "imap": "node-imap",
  "email_parser": "mailparser",
  "ai_sdk": "@anthropic-ai/claude-agent-sdk",
  "ai_client": "@anthropic-ai/sdk"
}
```

### **前端**
```json
{
  "framework": "React 18.3",
  "state": "Jotai",
  "styling": "Tailwind CSS 4.x + PostCSS",
  "icons": "lucide-react",
  "markdown": "react-markdown + remark-gfm"
}
```

### **依赖包** (`package.json`)
```json
{
  "dependencies": {
    "@anthropic-ai/claude-agent-sdk": "^0.1.28",
    "@anthropic-ai/sdk": "^0.68.0",
    "@tailwindcss/postcss": "^4.1.11",
    "dotenv": "^17.2.1",
    "jotai": "^2.14.0",
    "lucide-react": "^0.539.0",
    "mailparser": "^3.7.4",
    "node-imap": "^0.9.6",
    "react": "^18.3.1",
    "react-dom": "^18.3.1"
  }
}
```

---

## 🔄 数据流（实际）

### **1. 用户发送消息**
```
Client (WebSocket)
  ↓ { type: 'chat', content: 'Show me unread emails' }
WebSocketHandler.onMessage()
  ↓ 路由到 Session
Session.addUserMessage()
  ↓ 调用 AIClient.queryStream()
AIClient
  ↓ 流式调用 Claude API
  ↓ 返回 SDKMessage (assistant/tool_use/result)
Session.broadcastToSubscribers()
  ↓ 广播给所有订阅者
Client (接收 assistant_message)
```

### **2. 监听器触发**
```
IMAP IDLE 检测到新邮件
  ↓ onNewEmailCallback(count)
EmailSyncService.handleIdleNewEmails()
  ↓ ImapManager.searchEmails()
  ↓ DatabaseManager.upsertEmail()
  ↓ ListenersManager.checkEvent('email_received', email)
ListenersManager
  ↓ 过滤匹配的监听器
  ↓ 创建 ListenerContext
  ↓ 调用 handler(email, context)
Listener Handler
  ↓ context.callAgent() → 调用 Claude API
  ↓ context.uiState.set() → 更新 UI 状态
  ↓ 返回 ListenerResult
ListenersManager
  ↓ 写入 JSONL 日志
  ↓ 广播日志到 WebSocket
Client (接收 listener_log)
```

### **3. UI 状态更新**
```
Listener/Action
  ↓ context.uiState.set('financial_dashboard', data)
UIStateManager.setState()
  ↓ DatabaseManager.setUIState()
  ↓ 写入 JSONL 日志
  ↓ notifyStateUpdate()
WebSocketHandler
  ↓ broadcastUIStateUpdate(stateId, data)
Client (接收 ui_state_update)
  ↓ React 组件重新渲染
```

---

## 🐍 Python 对应技术栈

| TypeScript/Bun | Python 替代方案 |
|----------------|----------------|
| `Bun Server` | `FastAPI` + `Uvicorn` |
| `bun:sqlite` | `SQLAlchemy` + `aiosqlite` / `PostgreSQL` |
| `Bun WebSocket` | `FastAPI WebSocket` / `starlette.websockets` |
| `node-imap` | `aioimaplib` / `imapclient` |
| `mailparser` | `email` (标准库) / `mail-parser` |
| `fs/promises watch()` | `watchdog.observers.Observer` |
| `import()` (动态导入) | `importlib.util.spec_from_file_location()` |
| `async/await` | `async/await` (asyncio) |
| `Promise.all()` | `asyncio.gather()` |
| `Map<K, V>` | `dict[K, V]` |
| `Set<T>` | `set[T]` |
| `JSON.stringify/parse` | `json.dumps/loads` |
| `TypeScript interface` | `Pydantic BaseModel` |
| `React` | `React` (Vite 构建) |

---

## 📝 关键设计模式

### **1. 单例模式**
- `DatabaseManager.getInstance()`
- `ImapManager.getInstance()`

### **2. 发布-订阅模式**
- `Session.subscribers` (WebSocket 客户端订阅)
- `UIStateManager.updateCallbacks` (UI 状态更新订阅)

### **3. 插件系统**
- 动态加载：`import()` + 缓存破坏
- 热重载：`fs/promises watch()`
- 上下文注入：`ListenerContext` / `ActionContext`

### **4. 事务管理**
- `db.transaction(() => { ... })`
- 确保邮件和附件原子性

### **5. 并发控制**
- `Session.queryPromise`（锁机制）
- 串行处理用户消息

---

## 📊 性能优化

### **1. 数据库优化**
- **WAL 模式**：提升并发写入性能
- **FTS5 索引**：快速全文搜索
- **批量操作**：`batchUpsertEmails()`

### **2. IMAP 优化**
- **并行拉取**：`fetchEmailsBatch()` 使用 `Promise.all()`
- **批次大小**：每批 10-20 封邮件
- **只拉取头部**：`headersOnly` 模式加速

### **3. WebSocket 优化**
- **定时推送**：每 5 秒推送收件箱（而非每封邮件）
- **错误处理**：自动移除断开连接的客户端

---

## 🚀 启动流程

```bash
# 1. 安装依赖
bun install

# 2. 配置环境变量
export EMAIL_ADDRESS="your-email@gmail.com"
export EMAIL_APP_PASSWORD="your-app-password"
export ANTHROPIC_API_KEY="sk-ant-..."

# 3. 启动服务
bun run dev

# 4. 访问
# - WebSocket: ws://localhost:3000/ws
# - HTTP: http://localhost:3000
```

---

## ✅ 复刻检查清单

### **核心功能**
- [ ] Session 管理（多轮对话、订阅者）
- [ ] WebSocket 处理（连接、消息分发）
- [ ] Listeners 管理（加载、执行、热重载）
- [ ] Actions 管理（模板、实例、执行）
- [ ] UI State 管理（持久化、广播）
- [ ] AI Client（流式调用、工具使用）

### **数据库层**
- [ ] Email 存储（SQLite + FTS5）
- [ ] IMAP 操作（连接、同步、IDLE）
- [ ] Email Sync（解析、存储、触发 listener）
- [ ] UI State 存储

### **插件系统**
- [ ] 动态加载（热重载）
- [ ] 上下文注入（ListenerContext、ActionContext）
- [ ] JSONL 日志记录

---

## 📚 下一步

阅读以下文档：
1. **SESSION_FLOW.md** - 会话流程详解
2. **PLUGIN_LOADING.md** - 插件加载机制详解
3. **DATABASE_SCHEMA.md** - 数据库表结构
4. **WEBSOCKET_MESSAGES.md** - WebSocket 消息格式
5. **LISTENER_TEMPLATE.md** - 监听器开发模板
6. **TS_TO_PYTHON_MAP.md** - TypeScript → Python 映射表
