# 插件加载机制详解

> **文档目的**：详细记录 Email Agent 中插件系统的实际实现，包括 Listeners、Actions、UI States、Components 的加载、执行、热重载机制。
> **原则**：基于实际代码，展示完整的插件生命周期。

---

## 📋 目录

1. [插件系统概览](#插件系统概览)
2. [Listeners 管理器](#listeners-管理器)
3. [Actions 管理器](#actions-管理器)
4. [热重载机制](#热重载机制)
5. [日志系统](#日志系统)
6. [上下文注入](#上下文注入)
7. [Python 实现要点](#python-实现要点)

---

## 🧩 插件系统概览

### **插件类型**

| 插件类型 | 触发方式 | 用途 | 文件位置 |
|---------|---------|------|----------|
| **Listeners** | 事件驱动（自动） | 监听邮件事件并自动执行 | `agent/custom_scripts/listeners/` |
| **Actions** | 用户触发（按钮） | 用户点击按钮执行操作 | `agent/custom_scripts/actions/` |
| **UI States** | 数据模板 | 定义持久化的 UI 状态结构 | `agent/custom_scripts/ui-states/` |
| **Components** | 视图模板 | 定义如何渲染 UI 状态 | `agent/custom_scripts/components/` |

### **目录结构**

```
agent/custom_scripts/
├── listeners/
│   ├── finance-email-tracker.ts
│   ├── todo-extractor.ts
│   └── .logs/
│       └── {listener-id}.jsonl
├── actions/
│   ├── create-task.ts
│   └── .logs/
│       └── {date}.jsonl
├── ui-states/
│   ├── financial-dashboard.ts
│   └── task-board.ts
└── types.ts
```

---

## 🎧 Listeners 管理器

### **加载流程**

```typescript
async loadAllListeners(): Promise<ListenerConfig[]> {
  this.listeners.clear();
  const files = await readdir(this.listenersDir);

  for (const file of files) {
    if (file.endsWith(".ts") && !file.startsWith("_") && !file.startsWith(".")) {
      await this.loadListener(file);
    }
  }
  return Array.from(this.listeners.values()).map(l => l.config);
}

private async loadListener(filename: string): Promise<void> {
  const filePath = join(this.listenersDir, filename);
  const module = await import(`${filePath}?t=${Date.now()}`);  // 缓存破坏

  if (!module.config || !module.handler) {
    console.error(`Invalid listener ${filename}`);
    return;
  }

  if (module.config.enabled) {
    this.listeners.set(module.config.id, { config: module.config, handler: module.handler });
  }
}
```

### **监听器文件结构**

```typescript
// listeners/finance-email-tracker.ts
export const config: ListenerConfig = {
  id: 'finance_email_tracker',
  name: 'Finance Email Tracker',
  enabled: true,
  event: 'email_received'
};

export async function handler(email: Email, context: ListenerContext): Promise<ListenerResult> {
  const classification = await context.callAgent({
    prompt: `Analyze email: ${email.subject}`,
    schema: { /* ... */ },
    model: 'haiku'
  });

  if (classification.isFinancial) {
    await context.uiState.set('financial_dashboard', data);
    await context.addLabel(email.messageId, 'Finance');
    return { executed: true, reason: 'Tracked expense' };
  }

  return { executed: false, reason: 'Not financial' };
}
```

---

## 🎬 Actions 管理器

### **加载流程**

```typescript
async loadAllTemplates(): Promise<ActionTemplate[]> {
  this.templates.clear();
  const files = await readdir(this.actionsDir);

  for (const file of files) {
    if (file.endsWith(".ts") && !file.startsWith("_")) {
      await this.loadTemplate(file);
    }
  }
  return Array.from(this.templates.values()).map(t => t.config);
}
```

### **动作文件结构**

```typescript
// actions/create-task.ts
export const config: ActionTemplate = {
  id: 'create_task',
  name: 'Create Task',
  icon: '📝',
  parameterSchema: {
    type: 'object',
    properties: {
      title: { type: 'string' },
      priority: { type: 'string', enum: ['low', 'medium', 'high'] }
    },
    required: ['title']
  }
};

export async function handler(params, context: ActionContext): Promise<ActionResult> {
  const task = { id: generateId(), title: params.title, status: 'todo' };
  await context.uiState.set('task_board', { tasks: [task] });
  
  return {
    success: true,
    message: `Created task: "${params.title}"`,
    components: [{ instanceId: 'comp_1', componentId: 'task_board', stateId: 'task_board' }]
  };
}
```

---

## 🔥 热重载机制

### **文件监听**

```typescript
async watchListeners(onChange: (listeners: ListenerConfig[]) => void): Promise<void> {
  const watcher = watch(this.listenersDir);

  for await (const event of watcher) {
    if (event.filename?.endsWith(".ts")) {
      const listeners = await this.loadAllListeners();
      onChange(listeners);
    }
  }
}
```

### **缓存破坏**

```typescript
// 使用时间戳破坏缓存
const module = await import(`${filePath}?t=${Date.now()}`);
```

---

## 📝 日志系统

### **JSONL 格式**

```typescript
async appendLog(listenerId: string, entry: ListenerLogEntry): Promise<void> {
  const logFile = path.join(this.logsDir, `${listenerId}.jsonl`);
  const logLine = JSON.stringify(entry) + "\n";
  await fs.appendFile(logFile, logLine, "utf-8");
}
```

### **日志示例**

```jsonl
{"timestamp":"2024-01-15T10:30:15.234Z","emailId":"<abc@example.com>","executed":true,"reason":"Tracked expense $49.99","executionTimeMs":1234}
```

---

## 🔌 上下文注入

### **ListenerContext**

```typescript
private createContext(listenerConfig: ListenerConfig): ListenerContext {
  return {
    notify: async (message, options) => { /* ... */ },
    archiveEmail: async (emailId) => {
      const email = await this.databaseManager.getEmailByMessageId(emailId);
      await this.imapManager.archiveEmail(email.imapUid, email.folder);
    },
    callAgent: async (options) => {
      const anthropic = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
      const response = await anthropic.messages.create({ /* ... */ });
      return response;
    },
    uiState: {
      get: async (stateId) => await this.uiStateManager?.getState(stateId),
      set: async (stateId, data) => await this.uiStateManager?.setState(stateId, data)
    }
  };
}
```

---

## 🐍 Python 实现要点

### **1. 动态导入**

```python
import importlib.util

async def load_listener(self, filename: str):
    file_path = self.listeners_dir / filename
    spec = importlib.util.spec_from_file_location(f"listener_{filename[:-3]}", file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    
    if hasattr(module, 'config') and module.config.get('enabled'):
        self.listeners[module.config['id']] = {'config': module.config, 'handler': module.handler}
```

### **2. 文件监听**

```python
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class ListenerFileHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith('.py'):
            asyncio.create_task(self.manager.load_all_listeners())

observer = Observer()
observer.schedule(event_handler, str(listeners_dir), recursive=False)
observer.start()
```

### **3. 缓存清除**

```python
import sys

# 清除模块缓存
module_name = f"listener_{filename[:-3]}"
if module_name in sys.modules:
    del sys.modules[module_name]
```

### **4. 上下文注入**

```python
class ListenerContext:
    async def archive_email(self, email_id: str):
        email = await self.database_manager.get_email_by_message_id(email_id)
        await self.imap_manager.archive_email(email.imap_uid, email.folder)

    async def call_agent(self, options: dict):
        anthropic = Anthropic(api_key=os.environ['ANTHROPIC_API_KEY'])
        response = await anthropic.messages.create(
            model='claude-3-5-haiku-20241022',
            messages=[{'role': 'user', 'content': options['prompt']}],
            tools=[{'name': 'respond', 'input_schema': options['schema']}]
        )
        return response.content[0].input
```

---

## ✅ 复刻检查清单

### **核心功能**
- [ ] 动态加载插件（Listeners、Actions）
- [ ] 文件过滤（跳过 `_` 开头）
- [ ] 缓存破坏（热重载）
- [ ] 事件匹配与执行
- [ ] 上下文注入（ListenerContext、ActionContext）
- [ ] JSONL 日志记录
- [ ] 文件监听（热重载）

### **Python 特定**
- [ ] `importlib` 动态导入
- [ ] `watchdog` 文件监听
- [ ] 模块缓存清除
- [ ] `asyncio` 异步执行
- [ ] `aiofiles` 异步文件操作

---

## 📚 相关文档

- **ARCHITECTURE_ACTUAL.md** - 整体架构
- **SESSION_FLOW.md** - 会话流程
- **DATABASE_SCHEMA.md** - 数据库结构
- **LISTENER_TEMPLATE.md** - 监听器开发模板
