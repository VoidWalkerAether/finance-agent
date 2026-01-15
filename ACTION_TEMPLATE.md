# Action 动作开发模板

> **文档目的**：提供完整的 Action 开发指南，包括文件结构、API 参考、参数定义和实际示例。
> **适用场景**：需要**用户主动触发的操作**（如手动添加费用、生成报表、导出数据）。

---

## 📋 目录

1. [Action 是什么](#action-是什么)
2. [文件结构](#文件结构)
3. [配置对象 (config)](#配置对象-config)
4. [处理函数 (handler)](#处理函数-handler)
5. [上下文 API (ActionContext)](#上下文-api-actioncontext)
6. [返回值 (ActionResult)](#返回值-actionresult)
7. [完整示例](#完整示例)
8. [最佳实践](#最佳实践)
9. [Python 实现参考](#python-实现参考)

---

## 🎬 Action 是什么

### **定义**
Action（动作）是**用户触发的可执行操作**，通过 AI 对话生成按钮，用户点击后执行预定义的逻辑。

### **与 Listener 的区别**

| 特性 | Action | Listener |
|------|--------|----------|
| **触发方式** | 手动（用户点击按钮） | 自动（事件驱动） |
| **执行时机** | 用户主动点击 | 事件发生时立即执行 |
| **典型场景** | 手动添加费用、生成报表 | 新交易自动分类、自动标记 |
| **用户感知** | 明确的用户操作 | 后台静默执行 |
| **生成方式** | AI 在对话中生成按钮 | 启动时加载 |

### **工作流程**

```
用户对话: "帮我添加一笔 $50 的午餐费用"
  ↓
AI 生成 Action 实例（包含参数）
  ↓ {templateId: "add_expense", params: {amount: 50, category: "Food"}}
  ↓
前端显示按钮: [添加费用: $50 午餐]
  ↓
用户点击按钮
  ↓
执行 handler(params, context)
  ↓
返回结果 + 可选的 UI 组件
```

### **使用场景（Finance Agent）**
- ✅ 手动添加费用/收入
- ✅ 更新交易分类
- ✅ 生成月度报表
- ✅ 导出 CSV 数据
- ✅ 批量处理交易
- ✅ 创建预算目标

---

## 📁 文件结构

### **文件位置**
```
agent/custom_scripts/actions/
├── add-expense.ts           # 添加费用
├── generate-report.ts       # 生成报表
├── export-csv.ts            # 导出数据
└── _draft-action.ts         # ❌ 以 _ 开头会被跳过
```

### **最小文件结构**

```typescript
// agent/custom_scripts/actions/my-action.ts
import type { ActionTemplate, ActionContext, ActionResult } from '../types';

// ===== 必需导出 1: config (模板定义) =====
export const config: ActionTemplate = {
  id: "my_action",                  // 唯一 ID
  name: "My Action",                // 显示名称
  description: "Description",       // 描述
  icon: "📝",                       // 图标（emoji）
  parameterSchema: {                // 参数定义（JSON Schema）
    type: "object",
    properties: {
      param1: { type: "string", description: "参数1" }
    },
    required: ["param1"]
  }
};

// ===== 必需导出 2: handler (执行逻辑) =====
export async function handler(
  params: Record<string, any>,      // 参数对象
  context: ActionContext            // 上下文（提供 API）
): Promise<ActionResult> {
  // 你的逻辑
  return {
    success: true,
    message: "操作成功"
  };
}
```

---

## ⚙️ 配置对象 (config)

### **TypeScript 接口**

```typescript
interface ActionTemplate {
  id: string;              // 唯一标识符
  name: string;            // 显示名称
  description: string;     // 描述
  icon?: string;           // 图标（emoji）
  parameterSchema: {       // 参数定义（JSON Schema）
    type: "object";
    properties: Record<string, any>;
    required?: string[];
  };
}
```

### **字段说明**

| 字段 | 类型 | 必需 | 说明 | 示例 |
|------|------|------|------|------|
| `id` | `string` | ✅ | 唯一标识符（下划线命名） | `"add_expense"` |
| `name` | `string` | ✅ | 显示名称（显示在按钮上） | `"Add Expense"` |
| `description` | `string` | ✅ | 功能描述（AI 用于选择模板） | `"Add an expense to the dashboard"` |
| `icon` | `string` | ❌ | 图标（emoji 或图标名） | `"💰"`, `"📊"` |
| `parameterSchema` | `object` | ✅ | 参数定义（JSON Schema 格式） | 见下方示例 |

---

### **参数定义 (parameterSchema)**

使用 **JSON Schema** 定义参数，AI 会根据 schema 生成参数。

#### **基础示例**

```typescript
parameterSchema: {
  type: "object",
  properties: {
    amount: {
      type: "number",
      description: "金额（美元）"
    },
    category: {
      type: "string",
      description: "分类",
      enum: ["Food", "Transportation", "Shopping", "Entertainment", "Other"]
    },
    description: {
      type: "string",
      description: "描述"
    },
    date: {
      type: "string",
      description: "日期（ISO 格式，可选）"
    }
  },
  required: ["amount", "category", "description"]  // 必填字段
}
```

#### **支持的类型**

| JSON Schema 类型 | TypeScript 类型 | 示例 |
|-----------------|----------------|------|
| `"string"` | `string` | `"Food"`, `"2024-01-15"` |
| `"number"` | `number` | `49.99`, `100` |
| `"integer"` | `number` (整数) | `5`, `10` |
| `"boolean"` | `boolean` | `true`, `false` |
| `"array"` | `any[]` | `["tag1", "tag2"]` |
| `"object"` | `object` | `{key: "value"}` |

#### **高级特性**

##### **枚举（enum）**
```typescript
{
  category: {
    type: "string",
    enum: ["Food", "Transportation", "Shopping"],
    description: "选择分类"
  }
}
```

##### **默认值（default）**
```typescript
{
  priority: {
    type: "string",
    enum: ["low", "medium", "high"],
    default: "medium",
    description: "优先级"
  }
}
```

##### **数组类型**
```typescript
{
  tags: {
    type: "array",
    items: { type: "string" },
    description: "标签列表"
  }
}
```

---

### **配置示例**

```typescript
export const config: ActionTemplate = {
  id: "add_expense",
  name: "Add Expense",
  description: "Add an expense to the financial dashboard",
  icon: "💰",
  parameterSchema: {
    type: "object",
    properties: {
      amount: {
        type: "number",
        description: "Amount in dollars"
      },
      category: {
        type: "string",
        description: "Expense category",
        enum: ["Food", "Transportation", "Shopping", "Entertainment", "Utilities", "Healthcare", "Travel", "Other"]
      },
      description: {
        type: "string",
        description: "Description of the expense"
      },
      date: {
        type: "string",
        description: "Date (ISO format, defaults to today)"
      }
    },
    required: ["amount", "category", "description"]
  }
};
```

---

## 🔧 处理函数 (handler)

### **函数签名**

```typescript
async function handler(
  params: Record<string, any>,    // 参数对象（符合 parameterSchema）
  context: ActionContext          // 上下文对象（提供 API）
): Promise<ActionResult>          // 返回执行结果
```

### **参数说明**

#### **1. params（参数对象）**

根据 `parameterSchema` 定义的参数，AI 会自动填充。

**示例：**
```typescript
// parameterSchema 定义了 amount, category, description
// AI 生成的 params：
{
  amount: 49.99,
  category: "Food",
  description: "Lunch at Subway",
  date: "2024-01-15"
}
```

**类型安全（推荐）：**
```typescript
interface AddExpenseParams {
  amount: number;
  category: string;
  description: string;
  date?: string;
}

export async function handler(
  params: AddExpenseParams,     // 类型安全
  context: ActionContext
): Promise<ActionResult> {
  // params.amount 是 number
  // params.category 是 string
}
```

#### **2. context（上下文对象）**

提供各种能力的 API，详见下一节。

---

## 🔌 上下文 API (ActionContext)

### **完整接口**

```typescript
interface ActionContext {
  // ===== 会话信息 =====
  sessionId: string;

  // ===== Email API（Email Agent）=====
  emailAPI: {
    getInbox(options?: { limit?: number; includeRead?: boolean }): Promise<Email[]>;
    searchEmails(criteria: EmailSearchCriteria): Promise<Email[]>;
    getEmailsByIds(ids: string[]): Promise<Email[]>;
    getEmailById(id: string): Promise<Email | null>;
  };

  // ===== Transaction API（Finance Agent）=====
  transactionAPI: {
    getTransactions(options?: { limit?: number; type?: string }): Promise<Transaction[]>;
    searchTransactions(criteria: SearchCriteria): Promise<Transaction[]>;
    getTransactionById(id: string): Promise<Transaction | null>;
  };

  // ===== 直接操作 =====
  updateTransaction(transactionId: string, updates: Partial<Transaction>): Promise<void>;
  flagTransaction(transactionId: string): Promise<void>;
  addTag(transactionId: string, tag: string): Promise<void>;

  // ===== AI 调用 =====
  callAgent<T>(options: any): Promise<T>;

  // ===== 会话消息注入 =====
  addUserMessage(content: string): void;
  addAssistantMessage(content: string): void;

  // ===== 通知 =====
  notify(message: string, options?: any): void;

  // ===== 外部 API =====
  fetch(url: string, options?: RequestInit): Promise<Response>;

  // ===== 日志 =====
  log(message: string, level?: "info" | "warn" | "error"): void;

  // ===== UI 状态操作 =====
  uiState: {
    get<T>(stateId: string): Promise<T | null>;
    set<T>(stateId: string, data: T): Promise<void>;
  };
}
```

---

### **API 详解**

#### **1. transactionAPI - 查询交易**

##### **getTransactions() - 获取交易列表**

```typescript
const transactions = await context.transactionAPI.getTransactions({
  limit: 50,
  type: "expense"
});
```

##### **searchTransactions() - 搜索交易**

```typescript
const results = await context.transactionAPI.searchTransactions({
  merchant: "Amazon",
  dateRange: { start: "2024-01-01", end: "2024-01-31" }
});
```

---

#### **2. 直接操作**

```typescript
// 更新交易
await context.updateTransaction(transactionId, {
  category: "Food",
  tags: ["lunch"]
});

// 标记交易
await context.flagTransaction(transactionId);

// 添加标签
await context.addTag(transactionId, "business");
```

---

#### **3. callAgent() - 调用 AI**

与 Listener 相同，用于智能分析。

```typescript
const analysis = await context.callAgent<{ summary: string }>({
  prompt: "Summarize these transactions...",
  schema: { type: "object", properties: { summary: { type: "string" } } },
  model: "haiku"
});
```

---

#### **4. 会话消息注入**

```typescript
// 向会话中添加消息（显示在聊天界面）
context.addUserMessage("用户说的话");
context.addAssistantMessage("助手的回复");
```

---

#### **5. notify() - 发送通知**

```typescript
context.notify("操作完成！", { type: "success" });
```

---

#### **6. log() - 记录日志**

```typescript
context.log("正在处理交易...", "info");
context.log("警告：金额异常", "warn");
context.log("错误：保存失败", "error");
```

---

#### **7. uiState - UI 状态操作**

与 Listener 相同。

```typescript
let state = await context.uiState.get("financial_dashboard");
if (!state) state = { expenses: [], income: [] };

state.expenses.push(newExpense);

await context.uiState.set("financial_dashboard", state);
```

---

## 📤 返回值 (ActionResult)

### **接口定义**

```typescript
interface ActionResult {
  success: boolean;                     // 是否成功
  message: string;                      // 结果消息（显示给用户）
  data?: Record<string, any>;           // 返回数据（可选）
  suggestedActions?: ActionInstance[];  // 后续建议操作（可选）
  refreshInbox?: boolean;               // 是否刷新收件箱（可选）
  components?: ComponentInstance[];     // 要渲染的组件（可选）
}
```

### **字段说明**

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `success` | `boolean` | ✅ | 是否成功执行 |
| `message` | `string` | ✅ | 结果消息（显示给用户） |
| `data` | `object` | ❌ | 返回数据（供 AI 使用） |
| `suggestedActions` | `ActionInstance[]` | ❌ | 建议的后续操作 |
| `refreshInbox` | `boolean` | ❌ | 是否刷新数据列表 |
| `components` | `ComponentInstance[]` | ❌ | 要渲染的 UI 组件 |

### **返回值示例**

#### **成功执行**
```typescript
return {
  success: true,
  message: "Added expense: $49.99 for Food"
};
```

#### **失败**
```typescript
return {
  success: false,
  message: "Failed to add expense: Invalid amount"
};
```

#### **带组件渲染**
```typescript
return {
  success: true,
  message: "Updated financial dashboard",
  components: [{
    instanceId: `comp_${Date.now()}`,
    componentId: "financial_dashboard",
    stateId: "financial_dashboard"
  }]
};
```

#### **带后续建议**
```typescript
return {
  success: true,
  message: "Expense added",
  suggestedActions: [{
    instanceId: "action_2",
    templateId: "generate_report",
    label: "Generate Monthly Report",
    params: { month: "2024-01" }
  }]
};
```

---

## 📝 完整示例

### **示例 1: 添加费用（Finance Agent）**

```typescript
// agent/custom_scripts/actions/add-expense.ts
import type { ActionTemplate, ActionContext, ActionResult } from '../types';
import type { FinancialDashboardState, Expense } from '../ui-states/financial-dashboard';

export const config: ActionTemplate = {
  id: 'add_expense',
  name: 'Add Expense',
  description: 'Add an expense to the financial dashboard',
  icon: '💰',
  parameterSchema: {
    type: 'object',
    properties: {
      amount: {
        type: 'number',
        description: 'Amount in dollars'
      },
      category: {
        type: 'string',
        description: 'Expense category',
        enum: ['Food', 'Transportation', 'Shopping', 'Entertainment', 'Utilities', 'Healthcare', 'Travel', 'Other']
      },
      description: {
        type: 'string',
        description: 'Description of the expense'
      },
      date: {
        type: 'string',
        description: 'Date (ISO format, defaults to today)'
      }
    },
    required: ['amount', 'category', 'description']
  }
};

export async function handler(
  params: {
    amount: number;
    category: string;
    description: string;
    date?: string;
  },
  context: ActionContext
): Promise<ActionResult> {
  try {
    const stateId = 'financial_dashboard';

    // 获取现有状态
    let state = await context.uiState.get<FinancialDashboardState>(stateId);

    if (!state) {
      state = {
        expenses: [],
        income: [],
        categories: {},
        monthlyTotals: {}
      };
    }

    const expenseDate = params.date || new Date().toISOString();

    // 创建费用对象
    const expense: Expense = {
      id: `exp_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      amount: params.amount,
      category: params.category,
      description: params.description,
      date: expenseDate,
      source: 'manual'
    };

    // 添加到费用数组
    state.expenses.push(expense);

    // 更新分类统计
    if (!state.categories[params.category]) {
      state.categories[params.category] = { total: 0, count: 0 };
    }
    state.categories[params.category].total += params.amount;
    state.categories[params.category].count += 1;

    // 更新月度统计
    const month = expenseDate.substring(0, 7);
    if (!state.monthlyTotals[month]) {
      state.monthlyTotals[month] = { expenses: 0, income: 0, net: 0 };
    }
    state.monthlyTotals[month].expenses += params.amount;
    state.monthlyTotals[month].net =
      state.monthlyTotals[month].income - state.monthlyTotals[month].expenses;

    // 保存状态
    await context.uiState.set(stateId, state);

    context.log(`Added expense: $${params.amount} for ${params.category}`);

    return {
      success: true,
      message: `Added expense: $${params.amount} for ${params.category}`,
      components: [{
        instanceId: `comp_${Date.now()}`,
        componentId: 'financial_dashboard',
        stateId
      }]
    };
  } catch (error) {
    context.log(`Error adding expense: ${error}`, 'error');
    return {
      success: false,
      message: `Failed to add expense: ${(error as Error).message}`
    };
  }
}
```

---

### **示例 2: 生成月度报表**

```typescript
// agent/custom_scripts/actions/generate-monthly-report.ts
export const config: ActionTemplate = {
  id: 'generate_monthly_report',
  name: 'Generate Monthly Report',
  description: 'Generate a financial summary for a specific month',
  icon: '📊',
  parameterSchema: {
    type: 'object',
    properties: {
      month: {
        type: 'string',
        description: 'Month in YYYY-MM format'
      }
    },
    required: ['month']
  }
};

export async function handler(
  params: { month: string },
  context: ActionContext
): Promise<ActionResult> {
  try {
    const state = await context.uiState.get<FinancialDashboardState>('financial_dashboard');

    if (!state) {
      return {
        success: false,
        message: 'No financial data found'
      };
    }

    // 筛选指定月份的交易
    const monthExpenses = state.expenses.filter(exp => 
      exp.date.startsWith(params.month)
    );
    const monthIncome = state.income.filter(inc => 
      inc.date.startsWith(params.month)
    );

    // 计算统计
    const totalExpenses = monthExpenses.reduce((sum, exp) => sum + exp.amount, 0);
    const totalIncome = monthIncome.reduce((sum, inc) => sum + inc.amount, 0);
    const net = totalIncome - totalExpenses;

    // 分类统计
    const categoryBreakdown = monthExpenses.reduce((acc, exp) => {
      if (!acc[exp.category]) acc[exp.category] = 0;
      acc[exp.category] += exp.amount;
      return acc;
    }, {} as Record<string, number>);

    // 生成报表文本
    const report = `
📊 **Financial Report for ${params.month}**

💰 Income: $${totalIncome.toFixed(2)}
💸 Expenses: $${totalExpenses.toFixed(2)}
📈 Net: $${net.toFixed(2)} ${net >= 0 ? '✅' : '❌'}

**Expense Breakdown:**
${Object.entries(categoryBreakdown)
  .sort((a, b) => b[1] - a[1])
  .map(([cat, amt]) => `- ${cat}: $${amt.toFixed(2)}`)
  .join('\n')}
`;

    context.log(`Generated report for ${params.month}`);

    return {
      success: true,
      message: report,
      data: {
        month: params.month,
        totalIncome,
        totalExpenses,
        net,
        categoryBreakdown
      }
    };
  } catch (error) {
    return {
      success: false,
      message: `Failed to generate report: ${(error as Error).message}`
    };
  }
}
```

---

### **示例 3: 批量分类交易**

```typescript
// agent/custom_scripts/actions/batch-categorize.ts
export const config: ActionTemplate = {
  id: 'batch_categorize',
  name: 'Batch Categorize Transactions',
  description: 'Automatically categorize all uncategorized transactions',
  icon: '🔄',
  parameterSchema: {
    type: 'object',
    properties: {
      limit: {
        type: 'integer',
        description: 'Maximum number of transactions to process',
        default: 10
      }
    }
  }
};

export async function handler(
  params: { limit?: number },
  context: ActionContext
): Promise<ActionResult> {
  try {
    const limit = params.limit || 10;

    // 获取未分类的交易
    const uncategorized = await context.transactionAPI.searchTransactions({
      category: null,
      limit
    });

    if (uncategorized.length === 0) {
      return {
        success: true,
        message: "No uncategorized transactions found"
      };
    }

    context.log(`Categorizing ${uncategorized.length} transactions...`);

    let categorized = 0;

    for (const transaction of uncategorized) {
      // 使用 AI 分类
      const result = await context.callAgent<{ category: string }>({
        prompt: `Categorize: ${transaction.merchant} - ${transaction.description}`,
        schema: {
          type: "object",
          properties: {
            category: {
              type: "string",
              enum: ["Food", "Transportation", "Shopping", "Entertainment", "Other"]
            }
          },
          required: ["category"]
        },
        model: "haiku"
      });

      await context.updateTransaction(transaction.transaction_id, {
        category: result.category
      });

      categorized++;
    }

    return {
      success: true,
      message: `Successfully categorized ${categorized} transaction(s)`,
      refreshInbox: true
    };
  } catch (error) {
    return {
      success: false,
      message: `Error: ${(error as Error).message}`
    };
  }
}
```

---

## 💡 最佳实践

### **1. 参数验证**

```typescript
export async function handler(params, context): Promise<ActionResult> {
  // 验证必填参数
  if (!params.amount || params.amount <= 0) {
    return {
      success: false,
      message: "Invalid amount: must be greater than 0"
    };
  }

  // 验证枚举值
  const validCategories = ["Food", "Transportation", "Shopping"];
  if (!validCategories.includes(params.category)) {
    return {
      success: false,
      message: `Invalid category: must be one of ${validCategories.join(", ")}`
    };
  }

  // 继续执行...
}
```

---

### **2. 错误处理**

```typescript
try {
  // 你的逻辑
  return { success: true, message: "Success" };
} catch (error) {
  context.log(`Error: ${error}`, 'error');
  return {
    success: false,
    message: `Failed: ${(error as Error).message}`
  };
}
```

---

### **3. 清晰的反馈**

```typescript
// ✅ 好：详细的成功消息
return {
  success: true,
  message: "Added expense: $49.99 for Food (Lunch at Subway)"
};

// ❌ 避免：模糊的消息
return { success: true, message: "Done" };
```

---

### **4. 组件渲染**

```typescript
// 当 Action 更新了 UI 状态，返回对应的组件
return {
  success: true,
  message: "Updated dashboard",
  components: [{
    instanceId: `comp_${Date.now()}`,
    componentId: "financial_dashboard",
    stateId: "financial_dashboard"
  }]
};
```

---

## 🐍 Python 实现参考

```python
# agent/custom_scripts/actions/add_expense.py
from typing import TypedDict

class ActionTemplate(TypedDict):
    id: str
    name: str
    description: str
    icon: str
    parameterSchema: dict

config: ActionTemplate = {
    'id': 'add_expense',
    'name': 'Add Expense',
    'description': 'Add an expense to the dashboard',
    'icon': '💰',
    'parameterSchema': {
        'type': 'object',
        'properties': {
            'amount': {'type': 'number', 'description': 'Amount'},
            'category': {'type': 'string', 'enum': ['Food', 'Transportation']},
            'description': {'type': 'string'}
        },
        'required': ['amount', 'category', 'description']
    }
}

async def handler(params: dict, context) -> dict:
    """添加费用"""
    try:
        state_id = 'financial_dashboard'
        
        # 获取状态
        state = await context.ui_state.get(state_id)
        if not state:
            state = {'expenses': [], 'income': [], 'categories': {}}
        
        # 创建费用
        expense = {
            'id': f"exp_{int(time.time())}",
            'amount': params['amount'],
            'category': params['category'],
            'description': params['description'],
            'date': datetime.now().isoformat()
        }
        
        # 添加到状态
        state['expenses'].append(expense)
        
        # 保存状态
        await context.ui_state.set(state_id, state)
        
        return {
            'success': True,
            'message': f"Added expense: ${params['amount']} for {params['category']}",
            'components': [{
                'instanceId': f"comp_{int(time.time())}",
                'componentId': 'financial_dashboard',
                'stateId': state_id
            }]
        }
    except Exception as error:
        return {
            'success': False,
            'message': f"Failed: {str(error)}"
        }
```

---

## ✅ 检查清单

开发 Action 前检查：

- [ ] 定义清晰的参数 schema（必填/可选/默认值）
- [ ] 使用合适的参数类型（number/string/enum）
- [ ] 添加参数验证逻辑
- [ ] 处理边界情况（状态不存在、参数无效）
- [ ] 添加错误处理（try/catch）
- [ ] 返回清晰的成功/失败消息
- [ ] 如果更新 UI 状态，返回对应组件
- [ ] 测试 AI 生成参数的准确性

---

## 📚 相关文档

- **LISTENER_TEMPLATE.md** - Listener 开发模板
- **PLUGIN_LOADING.md** - 插件加载机制
- **DATABASE_SCHEMA.md** - 数据库结构
- **ARCHITECTURE_ACTUAL.md** - 系统架构
