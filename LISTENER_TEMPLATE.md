# Listener 监听器开发模板

> **文档目的**：提供完整的 Listener 开发指南，包括文件结构、API 参考、最佳实践和实际示例。
> **适用场景**：需要**自动化处理事件**（如新交易到达时自动分类、标记）。

---

## 📋 目录

1. [Listener 是什么](#listener-是什么)
2. [文件结构](#文件结构)
3. [配置对象 (config)](#配置对象-config)
4. [处理函数 (handler)](#处理函数-handler)
5. [上下文 API (ListenerContext)](#上下文-api-listenercontext)
6. [返回值 (ListenerResult)](#返回值-listenerresult)
7. [完整示例](#完整示例)
8. [最佳实践](#最佳实践)
9. [常见模式](#常见模式)
10. [Python 实现参考](#python-实现参考)

---

## 🎧 Listener 是什么

### **定义**
Listener（监听器）是**事件驱动的自动化脚本**，当特定事件发生时（如新交易到达），自动执行预定义的逻辑。

### **与 Action 的区别**

| 特性 | Listener | Action |
|------|----------|--------|
| **触发方式** | 自动（事件驱动） | 手动（用户点击按钮） |
| **执行时机** | 事件发生时立即执行 | 用户主动触发 |
| **典型场景** | 新交易自动分类、自动标记 | 手动添加费用、生成报表 |
| **用户感知** | 后台静默执行 | 明确的用户操作 |

### **使用场景（Finance Agent）**
- ✅ 新交易到达时自动分类（食品、交通、娱乐等）
- ✅ 检测到重复交易时发送通知
- ✅ 检测到大额支出时标记为重要
- ✅ 自动提取发票信息并存储
- ✅ 定期汇总每月支出统计

---

## 📁 文件结构

### **文件位置**
```
agent/custom_scripts/listeners/
├── transaction-classifier.ts        # 交易分类器
├── duplicate-detector.ts            # 重复检测器
├── expense-tracker.ts               # 费用追踪器
└── _draft-listener.ts               # ❌ 以 _ 开头会被跳过
```

### **最小文件结构**

```typescript
// agent/custom_scripts/listeners/my-listener.ts
import type { ListenerConfig, ListenerContext, ListenerResult } from '../types';

// ===== 必需导出 1: config =====
export const config: ListenerConfig = {
  id: "my_listener",              // 唯一 ID（下划线命名）
  name: "My Listener",            // 显示名称
  description: "Description",     // 描述（可选）
  enabled: true,                  // 是否启用
  event: "email_received"         // 监听的事件类型
};

// ===== 必需导出 2: handler =====
export async function handler(
  data: any,                      // 事件数据（如交易对象）
  context: ListenerContext        // 上下文（提供 API）
): Promise<ListenerResult> {
  // 你的逻辑
  return {
    executed: true,
    reason: "处理成功"
  };
}
```

---

## ⚙️ 配置对象 (config)

### **TypeScript 接口**

```typescript
interface ListenerConfig {
  id: string;              // 唯一标识符
  name: string;            // 显示名称
  description?: string;    // 描述（可选）
  enabled: boolean;        // 是否启用
  event: EventType;        // 监听的事件类型
}

type EventType = 
  | "email_received"       // 新邮件到达（Email Agent）
  | "transaction_received" // 新交易到达（Finance Agent）
  | "email_sent"           
  | "email_starred"
  | "scheduled_time";      // 定时触发
```

### **字段说明**

| 字段 | 类型 | 必需 | 说明 | 示例 |
|------|------|------|------|------|
| `id` | `string` | ✅ | 唯一标识符（下划线命名） | `"transaction_classifier"` |
| `name` | `string` | ✅ | 显示名称（用于日志和 UI） | `"Transaction Classifier"` |
| `description` | `string` | ❌ | 功能描述 | `"Automatically categorizes transactions"` |
| `enabled` | `boolean` | ✅ | 是否启用（`false` 会跳过加载） | `true` |
| `event` | `EventType` | ✅ | 监听的事件类型 | `"transaction_received"` |

### **Finance Agent 事件类型**

```typescript
type FinanceEventType = 
  | "transaction_received"   // 新交易到达
  | "transaction_updated"    // 交易更新
  | "balance_changed"        // 余额变化
  | "scheduled_time";        // 定时触发（如每日汇总）
```

### **配置示例**

```typescript
export const config: ListenerConfig = {
  id: "expense_tracker",
  name: "Expense Tracker",
  description: "Tracks and categorizes expenses from transaction data",
  enabled: true,
  event: "transaction_received"
};
```

---

## 🔧 处理函数 (handler)

### **函数签名**

```typescript
async function handler(
  data: any,                    // 事件数据（Email Agent 是 Email 对象）
  context: ListenerContext      // 上下文对象（提供 API）
): Promise<ListenerResult>      // 返回执行结果
```

### **参数说明**

#### **1. data（事件数据）**

**Email Agent 的 data（Email 对象）：**
```typescript
interface Email {
  messageId: string;       // 邮件唯一 ID
  from: string;            // 发件人
  to: string;              // 收件人
  subject: string;         // 主题
  body: string;            // 正文
  date: string;            // 日期
  isRead: boolean;         // 是否已读
  hasAttachments: boolean; // 是否有附件
  labels?: string[];       // 标签
}
```

**Finance Agent 的 data（Transaction 对象，建议）：**
```typescript
interface Transaction {
  transaction_id: string;    // 交易唯一 ID
  transaction_date: string;  // 交易日期（ISO 格式）
  amount: number;            // 金额（正数=收入，负数=支出）
  type: 'income' | 'expense' | 'transfer';  // 交易类型
  merchant: string;          // 商户名称
  description: string;       // 交易描述
  account_name?: string;     // 账户名称
  category?: string;         // 分类（可能未分类）
  tags?: string[];           // 标签
  source: string;            // 数据来源（如 'bank_api', 'email'）
  source_id?: string;        // 原始来源 ID
}
```

#### **2. context（上下文对象）**

提供各种能力的 API，详见下一节。

---

## 🔌 上下文 API (ListenerContext)

### **完整接口**

```typescript
interface ListenerContext {
  // ===== 通知 =====
  notify(message: string, options?: NotifyOptions): Promise<void>;

  // ===== 邮件操作（Email Agent）=====
  archiveEmail(emailId: string): Promise<void>;
  starEmail(emailId: string): Promise<void>;
  unstarEmail(emailId: string): Promise<void>;
  markAsRead(emailId: string): Promise<void>;
  markAsUnread(emailId: string): Promise<void>;
  addLabel(emailId: string, label: string): Promise<void>;
  removeLabel(emailId: string, label: string): Promise<void>;

  // ===== 交易操作（Finance Agent）=====
  updateTransaction(transactionId: string, updates: Partial<Transaction>): Promise<void>;
  flagTransaction(transactionId: string): Promise<void>;
  addTag(transactionId: string, tag: string): Promise<void>;

  // ===== AI 调用 =====
  callAgent<T>(options: SubagentOptions<T>): Promise<T>;

  // ===== UI 状态操作 =====
  uiState: {
    get<T>(stateId: string): Promise<T | null>;
    set<T>(stateId: string, data: T): Promise<void>;
  };
}
```

---

### **API 详解**

#### **1. notify() - 发送通知**

```typescript
await context.notify(
  "检测到大额支出：$500 在 Amazon",
  { priority: "high" }
);
```

**参数：**
- `message: string` - 通知消息
- `options?: NotifyOptions` - 可选配置
  - `priority?: "low" | "normal" | "high"` - 优先级（默认 `"normal"`）

**用途：**
- 提醒用户重要事件
- 显示处理结果

---

#### **2. 交易操作（Finance Agent 专用）**

##### **updateTransaction() - 更新交易**

```typescript
await context.updateTransaction(transaction.transaction_id, {
  category: "Food",
  tags: ["lunch", "business"]
});
```

##### **flagTransaction() - 标记交易**

```typescript
await context.flagTransaction(transaction.transaction_id);
```

##### **addTag() - 添加标签**

```typescript
await context.addTag(transaction.transaction_id, "deductible");
```

---

#### **3. callAgent() - 调用 AI 子代理**

**用途：** 使用 AI 进行智能分析（如分类、提取信息）

```typescript
const result = await context.callAgent<{
  category: string;
  confidence: number;
}>({
  prompt: `Categorize this transaction:
Merchant: ${transaction.merchant}
Description: ${transaction.description}
Amount: $${transaction.amount}

Categories: Food, Transportation, Shopping, Entertainment, Utilities, Healthcare, Other`,
  schema: {
    type: "object",
    properties: {
      category: { type: "string" },
      confidence: { type: "number" }
    },
    required: ["category", "confidence"]
  },
  model: "haiku"  // 快速模型（推荐）
});

if (result.confidence > 0.7) {
  await context.updateTransaction(transaction.transaction_id, {
    category: result.category
  });
}
```

**参数：**
- `prompt: string` - 提示词
- `schema: JSONSchema` - 返回数据的 JSON Schema
- `model?: "opus" | "sonnet" | "haiku"` - 模型选择（默认 `"haiku"`）
  - `"haiku"` - 快速、便宜（推荐日常使用）
  - `"sonnet"` - 平衡
  - `"opus"` - 强大但慢

**返回：** 符合 schema 的结构化数据（类型安全）

---

#### **4. uiState - UI 状态操作**

##### **get() - 获取状态**

```typescript
const dashboard = await context.uiState.get<FinancialDashboardState>(
  "financial_dashboard"
);

if (!dashboard) {
  // 状态不存在，初始化
}
```

##### **set() - 设置状态**

```typescript
await context.uiState.set("financial_dashboard", {
  expenses: [...],
  income: [...],
  monthlyTotals: { ... }
});
```

**典型用法：**
```typescript
// 1. 获取现有状态
let state = await context.uiState.get<FinancialDashboardState>("financial_dashboard");

// 2. 如果不存在，初始化
if (!state) {
  state = { expenses: [], income: [], categories: {}, monthlyTotals: {} };
}

// 3. 修改状态
state.expenses.push(newExpense);
state.categories[category].total += amount;

// 4. 保存状态
await context.uiState.set("financial_dashboard", state);
```

---

## 📤 返回值 (ListenerResult)

### **接口定义**

```typescript
interface ListenerResult {
  executed: boolean;        // 是否执行了操作
  reason: string;           // 执行原因或跳过原因
  actions?: string[];       // 执行的操作列表（可选）
  components?: ComponentInstance[];  // 要渲染的组件（可选）
}
```

### **字段说明**

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `executed` | `boolean` | ✅ | 是否执行了操作（`true` 表示已处理，`false` 表示跳过） |
| `reason` | `string` | ✅ | 执行原因（会记录到日志） |
| `actions` | `string[]` | ❌ | 执行的操作列表（如 `["categorized", "flagged"]`） |
| `components` | `ComponentInstance[]` | ❌ | 要渲染的组件实例 |

### **返回值示例**

#### **成功执行**
```typescript
return {
  executed: true,
  reason: "Categorized as Food with 95% confidence",
  actions: ["categorized", "tagged:lunch"]
};
```

#### **跳过执行**
```typescript
return {
  executed: false,
  reason: "Transaction already categorized"
};
```

#### **带组件渲染**
```typescript
return {
  executed: true,
  reason: "Updated financial dashboard",
  actions: ["updated_dashboard"],
  components: [{
    instanceId: `comp_${Date.now()}`,
    componentId: "financial_dashboard",
    stateId: "financial_dashboard"
  }]
};
```

---

## 📝 完整示例

### **示例 1: 交易分类器（Finance Agent）**

```typescript
// agent/custom_scripts/listeners/transaction-classifier.ts
import type { ListenerConfig, ListenerContext, ListenerResult } from '../types';
import type { FinancialDashboardState } from '../ui-states/financial-dashboard';

export const config: ListenerConfig = {
  id: "transaction_classifier",
  name: "Transaction Classifier",
  description: "Automatically categorizes transactions using AI",
  enabled: true,
  event: "transaction_received"
};

interface Transaction {
  transaction_id: string;
  merchant: string;
  description: string;
  amount: number;
  category?: string;
}

export async function handler(
  transaction: Transaction,
  context: ListenerContext
): Promise<ListenerResult> {
  try {
    // 跳过已分类的交易
    if (transaction.category) {
      return {
        executed: false,
        reason: "Transaction already categorized"
      };
    }

    // 使用 AI 分类
    const classification = await context.callAgent<{
      category: string;
      confidence: number;
      reasoning: string;
    }>({
      prompt: `Categorize this transaction:

Merchant: ${transaction.merchant}
Description: ${transaction.description}
Amount: $${Math.abs(transaction.amount)}

Choose from: Food, Transportation, Shopping, Entertainment, Utilities, Healthcare, Travel, Other

Provide category, confidence (0-1), and brief reasoning.`,
      schema: {
        type: "object",
        properties: {
          category: {
            type: "string",
            enum: ["Food", "Transportation", "Shopping", "Entertainment", "Utilities", "Healthcare", "Travel", "Other"]
          },
          confidence: { type: "number" },
          reasoning: { type: "string" }
        },
        required: ["category", "confidence", "reasoning"]
      },
      model: "haiku"
    });

    // 只在高置信度时自动分类
    if (classification.confidence < 0.7) {
      return {
        executed: false,
        reason: `Low confidence (${(classification.confidence * 100).toFixed(0)}%): ${classification.reasoning}`
      };
    }

    // 更新交易分类
    await context.updateTransaction(transaction.transaction_id, {
      category: classification.category
    });

    // 更新 UI 状态
    let state = await context.uiState.get<FinancialDashboardState>("financial_dashboard");
    if (!state) {
      state = { expenses: [], income: [], categories: {}, monthlyTotals: {} };
    }

    // 更新分类统计
    if (!state.categories[classification.category]) {
      state.categories[classification.category] = { total: 0, count: 0 };
    }
    state.categories[classification.category].total += Math.abs(transaction.amount);
    state.categories[classification.category].count += 1;

    await context.uiState.set("financial_dashboard", state);

    return {
      executed: true,
      reason: `Categorized as ${classification.category} (${(classification.confidence * 100).toFixed(0)}% confidence)`,
      actions: ["categorized", `category:${classification.category}`]
    };
  } catch (error) {
    return {
      executed: false,
      reason: `Error: ${(error as Error).message}`
    };
  }
}
```

---

### **示例 2: 大额支出检测器**

```typescript
// agent/custom_scripts/listeners/large-expense-detector.ts
export const config: ListenerConfig = {
  id: "large_expense_detector",
  name: "Large Expense Detector",
  description: "Alerts on expenses over $500",
  enabled: true,
  event: "transaction_received"
};

export async function handler(
  transaction: Transaction,
  context: ListenerContext
): Promise<ListenerResult> {
  const THRESHOLD = 500;

  // 只处理支出
  if (transaction.type !== 'expense') {
    return { executed: false, reason: "Not an expense" };
  }

  // 检查金额
  if (Math.abs(transaction.amount) < THRESHOLD) {
    return { executed: false, reason: `Amount below threshold ($${THRESHOLD})` };
  }

  // 标记交易
  await context.flagTransaction(transaction.transaction_id);

  // 发送通知
  await context.notify(
    `⚠️ Large expense detected: $${Math.abs(transaction.amount)} at ${transaction.merchant}`,
    { priority: "high" }
  );

  return {
    executed: true,
    reason: `Flagged large expense: $${Math.abs(transaction.amount)}`,
    actions: ["flagged", "notified"]
  };
}
```

---

### **示例 3: 重复交易检测器**

```typescript
// agent/custom_scripts/listeners/duplicate-detector.ts
export const config: ListenerConfig = {
  id: "duplicate_detector",
  name: "Duplicate Transaction Detector",
  description: "Detects potential duplicate transactions",
  enabled: true,
  event: "transaction_received"
};

export async function handler(
  transaction: Transaction,
  context: ListenerContext
): Promise<ListenerResult> {
  // 获取财务仪表板状态
  const state = await context.uiState.get<FinancialDashboardState>("financial_dashboard");
  
  if (!state) {
    return { executed: false, reason: "No transaction history" };
  }

  // 查找相似交易（相同商户、相同金额、24小时内）
  const recentTransactions = state.expenses.filter(exp => {
    const timeDiff = new Date(transaction.transaction_date).getTime() - new Date(exp.date).getTime();
    const within24Hours = Math.abs(timeDiff) < 24 * 60 * 60 * 1000;
    
    return within24Hours &&
           exp.amount === Math.abs(transaction.amount) &&
           exp.description.includes(transaction.merchant);
  });

  if (recentTransactions.length > 0) {
    await context.addTag(transaction.transaction_id, "potential_duplicate");
    await context.notify(
      `Possible duplicate transaction: $${Math.abs(transaction.amount)} at ${transaction.merchant}`,
      { priority: "normal" }
    );

    return {
      executed: true,
      reason: `Found ${recentTransactions.length} similar recent transaction(s)`,
      actions: ["tagged:potential_duplicate", "notified"]
    };
  }

  return { executed: false, reason: "No duplicates found" };
}
```

---

## 💡 最佳实践

### **1. 性能优化**

#### **使用快速模型**
```typescript
// ✅ 好：日常分类使用 haiku
await context.callAgent({ ..., model: "haiku" });

// ❌ 避免：不必要地使用 opus
await context.callAgent({ ..., model: "opus" });
```

#### **提前返回**
```typescript
// ✅ 好：尽早跳过不需要处理的情况
if (transaction.category) {
  return { executed: false, reason: "Already categorized" };
}

// ... 后续逻辑
```

---

### **2. 错误处理**

```typescript
export async function handler(transaction, context): Promise<ListenerResult> {
  try {
    // 你的逻辑
    return { executed: true, reason: "Success" };
  } catch (error) {
    // 捕获错误并返回失败结果
    return {
      executed: false,
      reason: `Error: ${(error as Error).message}`
    };
  }
}
```

---

### **3. 清晰的日志**

```typescript
return {
  executed: true,
  reason: "Categorized as Food with 95% confidence",  // ✅ 清晰描述
  actions: ["categorized", "category:Food"]           // ✅ 详细操作列表
};

// ❌ 避免模糊的消息
return { executed: true, reason: "Done" };
```

---

### **4. 状态管理**

```typescript
// ✅ 好：先获取，再修改，最后保存
let state = await context.uiState.get("financial_dashboard");
if (!state) {
  state = initializeState();
}
state.expenses.push(newExpense);
await context.uiState.set("financial_dashboard", state);

// ❌ 避免：直接覆盖（丢失现有数据）
await context.uiState.set("financial_dashboard", { expenses: [newExpense] });
```

---

## 🔄 常见模式

### **模式 1: AI 分类**

```typescript
const classification = await context.callAgent<{ category: string }>({
  prompt: `Categorize: ${data.description}`,
  schema: { type: "object", properties: { category: { type: "string" } } },
  model: "haiku"
});

await context.updateTransaction(data.id, { category: classification.category });
```

---

### **模式 2: 条件通知**

```typescript
if (condition) {
  await context.notify("重要事件", { priority: "high" });
  await context.flagTransaction(data.id);
}
```

---

### **模式 3: 累积统计**

```typescript
let state = await context.uiState.get<DashboardState>("dashboard");
if (!state) state = { total: 0, count: 0 };

state.total += data.amount;
state.count += 1;

await context.uiState.set("dashboard", state);
```

---

## 🐍 Python 实现参考

```python
# agent/custom_scripts/listeners/transaction_classifier.py
from typing import TypedDict

class ListenerConfig(TypedDict):
    id: str
    name: str
    description: str
    enabled: bool
    event: str

config: ListenerConfig = {
    'id': 'transaction_classifier',
    'name': 'Transaction Classifier',
    'description': 'Automatically categorizes transactions',
    'enabled': True,
    'event': 'transaction_received'
}

async def handler(transaction: dict, context) -> dict:
    """处理交易分类"""
    
    # 跳过已分类
    if transaction.get('category'):
        return {'executed': False, 'reason': 'Already categorized'}
    
    # 调用 AI 分类
    classification = await context.call_agent({
        'prompt': f"Categorize: {transaction['merchant']}",
        'schema': {
            'type': 'object',
            'properties': {
                'category': {'type': 'string'},
                'confidence': {'type': 'number'}
            }
        },
        'model': 'haiku'
    })
    
    # 更新交易
    if classification['confidence'] > 0.7:
        await context.update_transaction(
            transaction['transaction_id'],
            {'category': classification['category']}
        )
        
        return {
            'executed': True,
            'reason': f"Categorized as {classification['category']}",
            'actions': ['categorized']
        }
    
    return {'executed': False, 'reason': 'Low confidence'}
```

---

## ✅ 检查清单

开发 Listener 前检查：

- [ ] 确定监听的事件类型（`transaction_received`）
- [ ] 定义清晰的处理逻辑（什么情况下执行？）
- [ ] 选择合适的 AI 模型（通常用 `haiku`）
- [ ] 处理边界情况（已处理、缺失数据）
- [ ] 添加错误处理（`try/catch`）
- [ ] 返回清晰的日志消息
- [ ] 测试热重载（保存文件后自动加载）

---

## 📚 相关文档

- **ARCHITECTURE_ACTUAL.md** - 系统架构
- **PLUGIN_LOADING.md** - 插件加载机制
- **ACTION_TEMPLATE.md** - Action 开发模板
- **DATABASE_SCHEMA.md** - 数据库结构
