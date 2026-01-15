# Finance Agent 功能规划与开发路线图

> 基于 Email Agent 架构的智能金融报告分析系统  
> 最后更新: 2025-11-27

---

## 📋 目录

- [系统概述](#系统概述)
- [核心功能清单](#核心功能清单)
- [功能对比矩阵](#功能对比矩阵)
- [技术架构](#技术架构)
- [开发路线图](#开发路线图)
- [详细功能说明](#详细功能说明)
- [数据库设计](#数据库设计)
- [API 规范](#api-规范)

---

## 系统概述

Finance Agent 是一个智能金融报告分析助手，可以：
1. 自动提取报告重要信息（结构化存储）
2. 关联历史报告进行对比分析
3. 提取投资策略和建议
4. 管理关注的行业/公司/ETF
5. 实时风险提示和价格预警
6. 基于知识库的多轮对话
7. 一键执行投资操作（Actions）
8. 实时可视化仪表盘（UI Components）

---

## 核心功能清单

### ✅ 已实现功能

| 模块 | 功能 | 状态 | 文件 |
|------|------|------|------|
| **Session** | 多轮对话管理 | ✅ 完成 | `ccsdk/session.py` |
| **AIClient** | Claude SDK 集成 | ✅ 完成 | `ccsdk/ai_client.py` |
| **AgentTools** | AI 工具调用 | ✅ 完成 | `ccsdk/agent_tools.py` |
| **DatabaseManager** | SQLite 数据库 | ✅ 完成 | `ccsdk/database_manager.py` |
| **WebSocket** | 实时通信 | ✅ 完成 | `ccsdk/websocket_handler.py` |

### 🚧 待实现功能（按优先级排序）

#### P0 - 核心必需功能

| 模块 | 功能 | 工作量 | 依赖 |
|------|------|--------|------|
| **ListenersManager** | 事件驱动插件系统 | 2天 | - |
| **UIStateManager** | UI 状态管理 | 2天 | DatabaseManager |
| **ActionsManager** | 动作执行引擎 | 3天 | ListenersManager |
| **示例 Listeners** | 报告分析、监控 | 1天 | ListenersManager |
| **示例 Actions** | 价格提醒、导出 | 1天 | ActionsManager |

#### P1 - 重要功能

| 模块 | 功能 | 工作量 | 依赖 |
|------|------|--------|------|
| **ComponentManager** | 组件生命周期管理 | 2天 | UIStateManager |
| **Custom Tools** | MCP 金融数据工具 | 1天 | - |
| **前端 UI 组件** | React 可视化组件 | 3天 | ComponentManager |
| **数据库扩展** | UI State/Component 表 | 1天 | DatabaseManager |
| **WebSocket 扩展** | 实时推送协议 | 1天 | WebSocket |

#### P2 - 增强功能

| 模块 | 功能 | 工作量 | 依赖 |
|------|------|--------|------|
| **向量检索** | 报告相似度搜索 | 2天 | DatabaseManager |
| **定时任务** | 自动报告分析 | 1天 | ListenersManager |
| **数据导出** | Excel/PDF 导出 | 1天 | ActionsManager |
| **市场数据集成** | AKShare/TuShare | 2天 | Custom Tools |

---

## 功能对比矩阵

### Email Agent vs Finance Agent

| 功能模块 | Email Agent | Finance Agent | 优先级 | 差异说明 |
|---------|-------------|---------------|--------|---------|
| **核心会话** | Session + AIClient | ✅ 已完成 | P0 | 相同架构 |
| **数据源** | IMAP 邮件同步 | 报告文件上传 | P0 | 不同数据源 |
| **插件系统** | ListenersManager | 🚧 待实现 | P0 | 相同架构 |
| **动作系统** | ActionsManager | ❌ 缺失 | P0 | 需要实现 |
| **状态管理** | UIStateManager | ❌ 缺失 | P0 | 需要实现 |
| **组件系统** | ComponentManager | ❌ 缺失 | P1 | 需要实现 |
| **自定义工具** | search_inbox / read_emails | ❌ 缺失 | P1 | 需要金融工具 |
| **数据库** | 完整 Schema + FTS5 | ⚠️ 部分实现 | P1 | 需要扩展表 |
| **前端组件** | FinancialDashboard / TaskBoard | ❌ 缺失 | P1 | 需要金融组件 |
| **实时通信** | WebSocket 完整协议 | ⚠️ 部分实现 | P1 | 需要扩展消息 |

---

## 技术架构

### 系统架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (React)                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  Portfolio   │  │   Market     │  │   Report     │          │
│  │  Dashboard   │  │   Monitor    │  │   Timeline   │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                  │                  │                  │
│         └──────────────────┴──────────────────┴─── WebSocket ───┤
└─────────────────────────────────────────────────────────────────┘
                             │
┌────────────────────────────┼─────────────────────────────────────┐
│                       Backend (FastAPI)                          │
│  ┌──────────────────────────▼──────────────────────────┐        │
│  │            WebSocketHandler                          │        │
│  │   (广播: UI State / Actions / Market Data)          │        │
│  └──────────────────────┬───────────────────────────────┘        │
│                         │                                         │
│  ┌──────────────────────▼──────────────────────────────┐        │
│  │              Session Manager                         │        │
│  │   (多轮对话 + AI 调用 + 消息广播)                    │        │
│  └──────────┬──────────────────────────┬────────────────┘        │
│             │                          │                          │
│  ┌──────────▼────────┐    ┌───────────▼──────────┐              │
│  │  ListenersManager │    │   ActionsManager     │              │
│  │  事件触发/插件加载 │    │   动作执行/日志记录  │              │
│  └──────────┬────────┘    └───────────┬──────────┘              │
│             │                          │                          │
│  ┌──────────▼────────┐    ┌───────────▼──────────┐              │
│  │  UIStateManager   │    │  ComponentManager    │              │
│  │  状态持久化/热重载 │    │  组件注册/实例管理   │              │
│  └──────────┬────────┘    └───────────┬──────────┘              │
│             │                          │                          │
│  ┌──────────▼──────────────────────────▼──────────┐             │
│  │           DatabaseManager (SQLite)              │             │
│  │  Reports | UI States | Components | Watchlist  │             │
│  └─────────────────────────────────────────────────┘             │
│                                                                   │
│  ┌───────────────────────────────────────────────────┐          │
│  │       Custom Tools (MCP Server)                   │          │
│  │  search_reports | get_market_data | analyze_trend│          │
│  └───────────────────────────────────────────────────┘          │
└───────────────────────────────────────────────────────────────────┘
```

### 插件架构

```
agent/custom_scripts/
├── listeners/              # 事件监听器（自动触发）
│   ├── report_analyzer.py      # 新报告自动分析
│   ├── watchlist_monitor.py    # 关注列表监控
│   ├── risk_detector.py        # 风险检测
│   └── trend_analyzer.py       # 趋势分析
│
├── actions/                # 用户动作（一键执行）
│   ├── set_price_alert.py      # 设置价格提醒
│   ├── export_report.py        # 导出报告
│   ├── rebalance_portfolio.py  # 资产再平衡
│   └── generate_summary.py     # 生成摘要
│
├── ui-states/              # UI 状态模板
│   ├── portfolio_dashboard.py  # 投资组合状态
│   ├── market_monitor.py       # 市场监控状态
│   ├── risk_assessment.py      # 风险评估状态
│   └── watchlist_tracker.py    # 关注列表状态
│
└── .logs/                  # 执行日志（JSONL）
    ├── listeners/
    │   └── 2025-11-27.jsonl
    ├── actions/
    │   └── 2025-11-27.jsonl
    └── ui-states/
        └── 2025-11-27.jsonl
```

---

## 开发路线图

### Phase 1: 核心插件系统（第 1-2 周）

#### Week 1: ListenersManager

**目标**: 实现事件驱动的插件加载和执行系统

**任务清单**:
- [ ] 实现 `ListenersManager` 核心类
  - [ ] 插件扫描和动态加载
  - [ ] 事件匹配和触发
  - [ ] 上下文注入（ListenerContext）
  - [ ] 热重载（watchdog）
  - [ ] JSONL 日志记录
  
- [ ] 创建示例 Listeners
  - [ ] `report_analyzer.py` - 自动提取报告信息
  - [ ] `watchlist_monitor.py` - 监控关注标的
  - [ ] `risk_detector.py` - 检测风险提示
  
- [ ] 单元测试
  - [ ] 插件加载测试
  - [ ] 事件触发测试
  - [ ] 日志记录测试

**验收标准**:
```python
# 测试用例
async def test_listeners():
    manager = ListenersManager(db)
    await manager.load_all_listeners()
    
    # 触发事件
    result = await manager.check_event('report_received', report_data)
    
    assert result.executed == True
    assert "investment_targets" in result.data
```

#### Week 2: UIStateManager + ComponentManager

**目标**: 实现持久化的 UI 状态管理和组件系统

**任务清单**:
- [ ] 实现 `UIStateManager`
  - [ ] 状态模板加载
  - [ ] 状态 CRUD 操作
  - [ ] WebSocket 广播
  - [ ] 热重载
  
- [ ] 实现 `ComponentManager`
  - [ ] 组件模板注册
  - [ ] 组件实例管理
  - [ ] 生命周期管理
  
- [ ] 数据库扩展
  - [ ] `ui_states` 表
  - [ ] `component_instances` 表
  
- [ ] 创建示例 UI States
  - [ ] `portfolio_dashboard.py`
  - [ ] `market_monitor.py`

**验收标准**:
```python
# 测试用例
async def test_ui_state():
    state_manager = UIStateManager(db, ws_handler)
    
    # 设置状态
    await state_manager.set_state('portfolio_dashboard', {
        'total_value': 100000,
        'allocation': {'stock': 0.6, 'bond': 0.3, 'cash': 0.1}
    })
    
    # 自动广播到前端
    assert ws_handler.last_broadcast['type'] == 'ui_state_update'
```

---

### Phase 2: Actions 系统（第 3-4 周）

#### Week 3: ActionsManager

**目标**: 实现一键执行的动作系统

**任务清单**:
- [ ] 实现 `ActionsManager`
  - [ ] Action 模板加载
  - [ ] Action 实例注册
  - [ ] Action 执行引擎
  - [ ] JSONL 日志记录
  
- [ ] 创建示例 Actions
  - [ ] `set_price_alert.py` - 价格提醒
  - [ ] `export_report.py` - 导出报告
  - [ ] `rebalance_portfolio.py` - 资产再平衡
  
- [ ] WebSocket 集成
  - [ ] `action_instances` 消息
  - [ ] `execute_action` 处理
  
- [ ] 前端按钮组件
  - [ ] `ActionButton.tsx`

**验收标准**:
```python
# AI 在对话中生成 Action
response = {
    'type': 'actions',
    'actions': [{
        'instanceId': 'act_123',
        'templateId': 'set_price_alert',
        'label': '设置黄金价格提醒: ≤3850美元',
        'params': {
            'symbol': 'SGE黄金9999',
            'target_price': 3850,
            'condition': '<='
        }
    }]
}

# 用户点击按钮执行
result = await actions_manager.execute_action('act_123', context)
assert result.success == True
```

#### Week 4: Custom Tools (MCP Server)

**目标**: 提供金融数据工具给 Claude

**任务清单**:
- [ ] 实现 MCP Server (`ccsdk/custom_tools.py`)
  - [ ] `search_reports` - 搜索报告
  - [ ] `get_market_data` - 获取行情
  - [ ] `analyze_trend` - 趋势分析
  - [ ] `compare_reports` - 对比报告
  
- [ ] 集成金融数据源
  - [ ] AKShare API
  - [ ] 本地报告数据库
  
- [ ] 注册到 Session
  - [ ] 将 tools 传递给 ClaudeSDKClient

**验收标准**:
```python
# Claude 可以调用自定义工具
@tool("get_market_data", "获取实时行情", {...})
async def get_market_data(args):
    symbols = args['symbols']
    data = await fetch_market_data(symbols)
    return {"content": [{"type": "text", "text": json.dumps(data)}]}
```

---

### Phase 3: 前端 UI 组件（第 5-6 周）

#### Week 5: React 组件库

**目标**: 实现可视化仪表盘组件

**任务清单**:
- [ ] 组件基础设施
  - [ ] `ComponentRegistry.ts`
  - [ ] `ComponentRenderer.tsx`
  
- [ ] 核心组件
  - [ ] `PortfolioDashboard.tsx` - 投资组合
    - [ ] 资产配置饼图
    - [ ] 持仓列表
    - [ ] 收益曲线图
  - [ ] `MarketMonitor.tsx` - 市场监控
    - [ ] 实时行情表格
    - [ ] 涨跌幅排行
    - [ ] K线图
  - [ ] `WatchlistTable.tsx` - 关注列表
    - [ ] 标的列表
    - [ ] 价格提醒状态
    - [ ] 添加/删除操作

**验收标准**:
```typescript
// 组件接收状态并渲染
<PortfolioDashboard 
  state={{
    totalValue: 100000,
    allocation: {stock: 0.6, bond: 0.3, cash: 0.1},
    holdings: [...]
  }}
  onAction={(actionId, params) => {
    // 触发 Action
  }}
/>
```

#### Week 6: 实时数据集成

**目标**: 实现 WebSocket 实时推送

**任务清单**:
- [ ] WebSocket 消息扩展
  - [ ] `market_data_update` - 行情推送
  - [ ] `alert_triggered` - 提醒触发
  
- [ ] 前端状态同步
  - [ ] `useUIState` hook
  - [ ] `useMarketData` hook
  
- [ ] 性能优化
  - [ ] 数据节流
  - [ ] 虚拟滚动

---

### Phase 4: 数据增强（第 7-8 周）

#### Week 7: 向量检索

**目标**: 实现报告相似度搜索

**任务清单**:
- [ ] 向量化
  - [ ] 使用 OpenAI Embeddings
  - [ ] 存储到 `report_vectors` 表
  
- [ ] 相似度搜索
  - [ ] 余弦相似度计算
  - [ ] TOP-K 检索
  
- [ ] RAG 增强
  - [ ] 检索相关报告
  - [ ] 注入到 Prompt

#### Week 8: 市场数据集成

**目标**: 接入实时金融数据

**任务清单**:
- [ ] AKShare 集成
  - [ ] ETF 实时行情
  - [ ] 指数数据
  - [ ] 资金流向
  
- [ ] 定时任务
  - [ ] 每日报告抓取
  - [ ] 自动分析
  
- [ ] 缓存优化
  - [ ] Redis 缓存
  - [ ] 数据更新策略

---

## 详细功能说明

### 1. ListenersManager - 事件监听系统

#### 核心概念
Listeners 是**被动触发**的插件，当特定事件发生时自动执行。

#### 事件类型
```python
EventType = Literal[
    "report_received",      # 新报告上传
    "report_analyzed",      # 报告分析完成
    "price_alert",          # 价格触发预警
    "daily_summary",        # 每日定时任务
    "user_query"            # 用户提问
]
```

#### Listener 模板结构
```python
# agent/custom_scripts/listeners/watchlist_monitor.py
from types import ListenerConfig, ListenerContext, ListenerResult

config: ListenerConfig = {
    'id': 'watchlist_monitor',
    'name': '关注列表监控',
    'description': '检测报告是否提到关注的标的',
    'enabled': True,
    'event': 'report_received'
}

async def handler(
    event_data: dict,
    context: ListenerContext
) -> ListenerResult:
    """
    处理函数
    
    Args:
        event_data: 事件数据（如报告内容）
        context: 上下文对象（提供 AI、数据库等能力）
    
    Returns:
        ListenerResult: 执行结果
    """
    # 1. 获取用户关注列表
    watchlist = await context.database.get_watchlist()
    
    # 2. 检测报告内容
    report = event_data['report']
    mentioned_items = []
    
    for item in watchlist:
        if item['name'] in report['content']:
            mentioned_items.append(item)
    
    # 3. 发送通知
    if mentioned_items:
        for item in mentioned_items:
            await context.notify(
                f"您关注的 {item['name']} 出现在新报告中！",
                priority="high"
            )
        
        # 4. 更新 UI State
        state = await context.ui_state.get('watchlist_tracker')
        state['alerts'].append({
            'date': report['date'],
            'items': mentioned_items
        })
        await context.ui_state.set('watchlist_tracker', state)
    
    return {
        'executed': len(mentioned_items) > 0,
        'reason': f'发现 {len(mentioned_items)} 个关注标的',
        'data': {'items': mentioned_items}
    }
```

#### ListenerContext API
```python
@dataclass
class ListenerContext:
    # 会话信息
    session_id: str
    
    # 数据库操作
    database: DatabaseManager
    
    # AI 调用
    async def call_agent(
        self,
        prompt: str,
        schema: dict
    ) -> Any:
        """调用 AI 进行分析"""
        pass
    
    # UI 状态管理
    ui_state: UIStateManager
    
    # 通知系统
    async def notify(
        self,
        message: str,
        priority: Literal["low", "normal", "high"] = "normal"
    ) -> None:
        """发送通知到前端"""
        pass
    
    # 报告操作
    async def add_tag(self, report_id: str, tag: str) -> None:
        """给报告添加标签"""
        pass
    
    # 日志
    def log(self, message: str, level: str = "info") -> None:
        """记录日志"""
        pass
```

---

### 2. ActionsManager - 动作执行系统

#### 核心概念
Actions 是**主动触发**的操作，由用户点击按钮执行。

#### Action 生命周期
```
1. AI 在对话中识别需求
   ↓
2. AI 生成 ActionInstance（模板 + 参数）
   ↓
3. 前端渲染 Action 按钮
   ↓
4. 用户点击按钮
   ↓
5. 后端执行 handler 函数
   ↓
6. 返回结果 + 更新 UI
```

#### Action 模板结构
```python
# agent/custom_scripts/actions/set_price_alert.py
from types import ActionTemplate, ActionContext, ActionResult

config: ActionTemplate = {
    'id': 'set_price_alert',
    'name': '设置价格提醒',
    'description': '当标的价格达到目标值时发送通知',
    'icon': '🔔',
    'parameterSchema': {
        'type': 'object',
        'properties': {
            'symbol': {
                'type': 'string',
                'description': '标的名称（如: SGE黄金9999）'
            },
            'target_price': {
                'type': 'number',
                'description': '目标价格'
            },
            'condition': {
                'type': 'string',
                'enum': ['<=', '>='],
                'description': '触发条件'
            }
        },
        'required': ['symbol', 'target_price', 'condition']
    }
}

async def handler(
    params: dict,
    context: ActionContext
) -> ActionResult:
    """
    执行函数
    
    Args:
        params: 参数（由 AI 生成的 ActionInstance 提供）
        context: 上下文对象
    
    Returns:
        ActionResult: 执行结果
    """
    symbol = params['symbol']
    target_price = params['target_price']
    condition = params['condition']
    
    # 1. 保存到数据库
    alert_id = await context.database.add_alert({
        'symbol': symbol,
        'target_price': target_price,
        'condition': condition,
        'status': 'active'
    })
    
    # 2. 更新 UI State
    state = await context.ui_state.get('price_alerts')
    if not state:
        state = {'alerts': []}
    
    state['alerts'].append({
        'id': alert_id,
        'symbol': symbol,
        'target_price': target_price,
        'condition': condition
    })
    await context.ui_state.set('price_alerts', state)
    
    # 3. 发送确认通知
    condition_text = '低于' if condition == '<=' else '高于'
    await context.notify(
        f"已设置 {symbol} 价格提醒: {condition_text} {target_price}",
        type="success"
    )
    
    return {
        'success': True,
        'message': f'已设置 {symbol} 价格提醒',
        'data': {
            'alert_id': alert_id,
            'symbol': symbol,
            'target_price': target_price
        }
    }
```

#### AI 生成 ActionInstance 示例
```python
# AI 在对话中生成
user: "黄金回调到 3850 美元提醒我"

assistant: "好的，我为你设置价格提醒：

[设置价格提醒: SGE黄金9999 ≤ 3850美元]

点击按钮即可生效。"

# WebSocket 消息
{
    'type': 'action_instances',
    'actions': [{
        'instanceId': 'act_1732701234567',
        'templateId': 'set_price_alert',
        'label': '设置价格提醒: SGE黄金9999 ≤ 3850美元',
        'description': '当价格低于 3850 时通知',
        'params': {
            'symbol': 'SGE黄金9999',
            'target_price': 3850,
            'condition': '<='
        },
        'style': 'primary',
        'sessionId': 'session_xyz',
        'createdAt': '2025-11-27T10:30:00Z'
    }],
    'sessionId': 'session_xyz'
}
```

---

### 3. UIStateManager - 状态管理系统

#### 核心概念
UI State 是**持久化的**、**可实时更新的**数据，用于驱动前端组件渲染。

#### 状态模板结构
```python
# agent/custom_scripts/ui-states/portfolio_dashboard.py
from types import UIStateTemplate
from typing import TypedDict, List

class Holding(TypedDict):
    name: str               # 标的名称
    type: str               # 类型（ETF/股票/债券）
    shares: float           # 持仓数量
    cost_basis: float       # 成本价
    current_value: float    # 当前市值
    gain: float             # 收益

class PortfolioState(TypedDict):
    total_value: float      # 总资产
    allocation: dict        # 资产配置 {'stock': 0.6, 'bond': 0.3, ...}
    holdings: List[Holding] # 持仓列表
    performance_history: List[dict]  # 历史收益

config: UIStateTemplate = {
    'id': 'portfolio_dashboard',
    'name': '投资组合仪表盘',
    'description': '显示资产配置、持仓和收益情况',
    'initialState': {
        'total_value': 0,
        'allocation': {},
        'holdings': [],
        'performance_history': []
    }
}
```

#### 状态更新流程
```python
# 在 Listener 或 Action 中更新状态
async def update_portfolio(context: ListenerContext):
    # 1. 获取当前状态
    state = await context.ui_state.get('portfolio_dashboard')
    
    # 2. 更新数据
    state['total_value'] = 105000
    state['holdings'].append({
        'name': 'SGE黄金9999 ETF',
        'type': 'ETF',
        'shares': 1000,
        'cost_basis': 95.0,
        'current_value': 98.5,
        'gain': 3500
    })
    
    # 3. 保存并广播
    await context.ui_state.set('portfolio_dashboard', state)
    # ↑ 自动触发 WebSocket 广播到前端
```

#### 前端组件接收状态
```typescript
// client/components/custom/PortfolioDashboard.tsx
import React from 'react';
import { ComponentProps } from './ComponentRegistry';

interface PortfolioState {
  total_value: number;
  allocation: Record<string, number>;
  holdings: Array<{
    name: string;
    type: string;
    current_value: number;
    gain: number;
  }>;
}

export const PortfolioDashboard: React.FC<ComponentProps<PortfolioState>> = ({
  state,
  onAction
}) => {
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-2xl font-bold mb-4">投资组合</h2>
      
      {/* 总资产 */}
      <div className="text-4xl font-bold text-blue-600">
        ¥{state.total_value.toLocaleString()}
      </div>
      
      {/* 资产配置饼图 */}
      <PieChart data={state.allocation} />
      
      {/* 持仓列表 */}
      <div className="mt-6">
        <h3 className="font-semibold mb-2">持仓明细</h3>
        {state.holdings.map(holding => (
          <div key={holding.name} className="flex justify-between py-2 border-b">
            <span>{holding.name}</span>
            <span className={holding.gain >= 0 ? 'text-green-600' : 'text-red-600'}>
              {holding.gain >= 0 ? '+' : ''}{holding.gain}
            </span>
          </div>
        ))}
      </div>
      
      {/* 触发 Action */}
      <button
        onClick={() => onAction('rebalance_portfolio', {})}
        className="mt-4 px-4 py-2 bg-blue-500 text-white rounded"
      >
        资产再平衡
      </button>
    </div>
  );
};
```

---

### 4. Custom Tools - 金融数据工具

#### MCP Server 集成
```python
# ccsdk/custom_tools.py
from anthropic_sdk import tool, create_sdk_mcp_server
from pydantic import BaseModel
import akshare as ak

class MarketDataArgs(BaseModel):
    symbols: list[str]
    fields: list[str] = ['price', 'change', 'volume']

custom_server = create_sdk_mcp_server(
    name="finance",
    version="1.0.0",
    tools=[
        tool(
            "get_market_data",
            "获取 ETF/股票的实时行情数据",
            MarketDataArgs,
            async (args) => {
                results = {}
                for symbol in args.symbols:
                    # 调用 AKShare API
                    df = ak.fund_etf_spot_em()
                    data = df[df['代码'] == symbol].iloc[0]
                    
                    results[symbol] = {
                        'price': float(data['最新价']),
                        'change': data['涨跌幅'],
                        'volume': data['成交量']
                    }
                
                return {
                    'content': [{
                        'type': 'text',
                        'text': json.dumps(results, ensure_ascii=False)
                    }]
                }
            }
        ),
        
        tool(
            "search_reports",
            "搜索历史报告",
            {...},
            async (args) => {
                # 全文搜索 + 向量检索
                ...
            }
        )
    ]
)
```

#### 在 Session 中注册
```python
# ccsdk/session.py
from custom_tools import custom_server

async def add_user_message(self, content: str):
    # ...
    
    agent_options = ClaudeAgentOptions(
        max_turns=100,
        mcp_servers=[custom_server]  # ← 注册工具
    )
    
    async with ClaudeSDKClient() as client:
        await client.query(content, options=agent_options)
        # Claude 现在可以调用 get_market_data 等工具
```

---

## 数据库设计

### 核心表结构

```sql
-- ========== 报告相关表 ==========

-- 报告主表
CREATE TABLE reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    category TEXT,                     -- A股/黄金/债券/综合
    date TEXT NOT NULL,
    raw_text TEXT,                     -- 原始文本
    structured_data TEXT,              -- JSON 结构化数据
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 全文搜索索引
CREATE VIRTUAL TABLE reports_fts USING fts5(
    report_id UNINDEXED,
    title,
    content,
    category,
    content='reports',
    tokenize='porter unicode61'
);

-- 向量检索表（可选）
CREATE TABLE report_vectors (
    id INTEGER PRIMARY KEY,
    report_id TEXT NOT NULL,
    embedding BLOB,                    -- 向量数据
    FOREIGN KEY (report_id) REFERENCES reports(report_id)
);

-- ========== UI State 相关表 ==========

-- UI 状态表
CREATE TABLE ui_states (
    state_id TEXT PRIMARY KEY,
    template_id TEXT NOT NULL,
    data TEXT NOT NULL,                -- JSON 数据
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 组件实例表
CREATE TABLE component_instances (
    instance_id TEXT PRIMARY KEY,
    component_id TEXT NOT NULL,        -- 组件模板 ID
    state_id TEXT NOT NULL,            -- 关联的 UI State
    session_id TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (state_id) REFERENCES ui_states(state_id)
);

-- ========== 用户数据表 ==========

-- 关注列表
CREATE TABLE watchlist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT DEFAULT 'default',
    target_name TEXT NOT NULL,
    target_type TEXT NOT NULL,         -- ETF/stock/index/industry
    alert_conditions TEXT,             -- JSON: {'price': '<=3850', 'change': '>5%'}
    status TEXT DEFAULT 'active',      -- active/triggered/disabled
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 价格提醒
CREATE TABLE price_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    target_price REAL NOT NULL,
    condition TEXT NOT NULL,           -- <=/>=
    status TEXT DEFAULT 'active',
    triggered_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 投资组合（可选）
CREATE TABLE portfolio (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT DEFAULT 'default',
    symbol TEXT NOT NULL,
    type TEXT NOT NULL,                -- ETF/stock/bond
    shares REAL NOT NULL,
    cost_basis REAL NOT NULL,
    purchase_date TEXT,
    notes TEXT
);

-- ========== 日志表（可选）==========

-- Action 执行日志（也可以只用 JSONL 文件）
CREATE TABLE action_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    instance_id TEXT NOT NULL,
    template_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    params TEXT,                       -- JSON
    result TEXT,                       -- JSON
    duration_ms INTEGER,
    executed_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ========== 索引 ==========

CREATE INDEX idx_reports_date ON reports(date DESC);
CREATE INDEX idx_reports_category ON reports(category);
CREATE INDEX idx_watchlist_status ON watchlist(status);
CREATE INDEX idx_price_alerts_status ON price_alerts(status);
CREATE INDEX idx_ui_states_updated ON ui_states(updated_at DESC);

-- ========== 触发器 ==========

-- 更新时间戳
CREATE TRIGGER update_reports_timestamp 
AFTER UPDATE ON reports
BEGIN
    UPDATE reports SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER update_ui_states_timestamp 
AFTER UPDATE ON ui_states
BEGIN
    UPDATE ui_states SET updated_at = CURRENT_TIMESTAMP WHERE state_id = NEW.state_id;
END;

-- FTS 同步
CREATE TRIGGER reports_fts_insert AFTER INSERT ON reports
BEGIN
    INSERT INTO reports_fts(report_id, title, content, category)
    VALUES (NEW.report_id, NEW.title, NEW.raw_text, NEW.category);
END;

CREATE TRIGGER reports_fts_update AFTER UPDATE ON reports
BEGIN
    UPDATE reports_fts 
    SET title = NEW.title, content = NEW.raw_text, category = NEW.category
    WHERE report_id = NEW.report_id;
END;

CREATE TRIGGER reports_fts_delete AFTER DELETE ON reports
BEGIN
    DELETE FROM reports_fts WHERE report_id = OLD.report_id;
END;
```

---

## API 规范

### HTTP Endpoints

```python
# server/endpoints/reports.py
GET    /api/reports                   # 获取报告列表
GET    /api/reports/:id               # 获取单个报告
POST   /api/reports                   # 上传报告
DELETE /api/reports/:id               # 删除报告
POST   /api/reports/search            # 全文搜索报告

# server/endpoints/ui_states.py
GET    /api/ui-states                 # 获取所有 UI State
GET    /api/ui-state/:stateId         # 获取单个状态
PUT    /api/ui-state/:stateId         # 更新状态
DELETE /api/ui-state/:stateId         # 删除状态
GET    /api/ui-state-templates        # 获取状态模板列表

# server/endpoints/components.py
GET    /api/component-templates       # 获取组件模板列表
GET    /api/components/:sessionId     # 获取会话的组件实例

# server/endpoints/actions.py
POST   /api/actions/execute           # 执行 Action
GET    /api/action-templates          # 获取 Action 模板列表

# server/endpoints/watchlist.py
GET    /api/watchlist                 # 获取关注列表
POST   /api/watchlist                 # 添加关注项
DELETE /api/watchlist/:id             # 删除关注项

# server/endpoints/market.py
GET    /api/market/quote/:symbol      # 获取实时行情
POST   /api/market/batch-quote        # 批量获取行情
```

### WebSocket 消息协议

#### Server → Client

```typescript
// 1. 助手消息（包含 Action 按钮）
{
  type: "assistant_message",
  content: string,
  actions?: ActionInstance[],  // 可执行的动作
  sessionId: string
}

// 2. UI 状态更新
{
  type: "ui_state_update",
  stateId: string,
  data: any,
  timestamp: string
}

// 3. 组件实例推送
{
  type: "component_instance",
  instance: {
    instanceId: string,
    componentId: string,
    stateId: string
  },
  sessionId: string
}

// 4. Action 执行结果
{
  type: "action_result",
  instanceId: string,
  result: {
    success: boolean,
    message: string,
    data?: any
  }
}

// 5. 市场数据更新（实时推送）
{
  type: "market_data_update",
  symbol: string,
  data: {
    price: number,
    change: number,
    timestamp: string
  }
}

// 6. 价格提醒触发
{
  type: "alert_triggered",
  alert: {
    id: number,
    symbol: string,
    condition: string,
    target_price: number,
    current_price: number
  }
}

// 7. 通知消息
{
  type: "notification",
  message: string,
  priority: "low" | "normal" | "high",
  notificationType: "info" | "success" | "warning" | "error"
}

// 8. Listener/Action 模板更新（热重载）
{
  type: "templates_updated",
  templateType: "listener" | "action" | "ui_state" | "component",
  templates: Array<any>
}
```

#### Client → Server

```typescript
// 1. 用户消息
{
  type: "user_message",
  content: string,
  sessionId: string
}

// 2. 执行 Action
{
  type: "execute_action",
  instanceId: string,
  sessionId: string
}

// 3. 组件触发 Action
{
  type: "component_action",
  instanceId: string,      // 组件实例 ID
  actionId: string,         // Action 模板 ID
  params: Record<string, any>
}

// 4. 订阅市场数据
{
  type: "subscribe_market_data",
  symbols: string[]
}

// 5. 取消订阅
{
  type: "unsubscribe_market_data",
  symbols: string[]
}
```

---

## 开发规范

### 代码风格

- **Python**: PEP 8 + Black 格式化
- **TypeScript**: ESLint + Prettier
- **命名**:
  - 文件名: `snake_case.py` / `kebab-case.ts`
  - 类名: `PascalCase`
  - 函数名: `snake_case`
  - 常量: `UPPER_SNAKE_CASE`

### 类型定义

所有插件必须提供完整的类型定义：

```python
# agent/custom_scripts/types.py
from typing import TypedDict, Literal, Callable, Any
from dataclasses import dataclass

class ListenerConfig(TypedDict):
    id: str
    name: str
    description: str
    enabled: bool
    event: Literal["report_received", "price_alert", "daily_summary"]

class ActionTemplate(TypedDict):
    id: str
    name: str
    description: str
    icon: str
    parameterSchema: dict

# ... 其他类型
```

### 日志规范

所有执行日志使用 **JSONL 格式**，按日期分文件：

```jsonl
# .logs/listeners/2025-11-27.jsonl
{"timestamp":"2025-11-27T10:30:00Z","listenerId":"report_analyzer","event":"report_received","executed":true,"duration":234,"result":{"extracted_targets":3}}
{"timestamp":"2025-11-27T10:35:00Z","listenerId":"watchlist_monitor","event":"report_received","executed":false,"reason":"no matches"}

# .logs/actions/2025-11-27.jsonl
{"timestamp":"2025-11-27T11:00:00Z","instanceId":"act_123","templateId":"set_price_alert","params":{"symbol":"黄金","price":3850},"result":{"success":true},"duration":45}
```

### 错误处理

```python
# 统一错误处理模式
try:
    result = await execute_something()
    return {'success': True, 'data': result}
except ValueError as e:
    context.log(f"Validation error: {e}", "error")
    return {'success': False, 'message': f'参数错误: {e}'}
except Exception as e:
    context.log(f"Unexpected error: {e}", "error")
    return {'success': False, 'message': f'执行失败: {e}'}
```

---

## 测试策略

### 单元测试

```python
# tests/test_listeners_manager.py
import pytest
from ccsdk.listeners_manager import ListenersManager

@pytest.mark.asyncio
async def test_load_listeners():
    manager = ListenersManager(db)
    listeners = await manager.load_all_listeners()
    
    assert len(listeners) > 0
    assert 'report_analyzer' in [l.id for l in listeners]

@pytest.mark.asyncio
async def test_trigger_event():
    manager = ListenersManager(db)
    result = await manager.check_event('report_received', {
        'report': {'content': '黄金价格上涨'}
    })
    
    assert result.executed == True
```

### 集成测试

```python
# tests/integration/test_full_workflow.py
@pytest.mark.asyncio
async def test_report_analysis_workflow():
    # 1. 上传报告
    report = await upload_report('test_report.txt')
    
    # 2. 触发 Listener 自动分析
    await listeners_manager.check_event('report_received', report)
    
    # 3. 验证 UI State 更新
    state = await ui_state_manager.get_state('portfolio_dashboard')
    assert len(state['recommended_targets']) > 0
    
    # 4. 验证 WebSocket 广播
    assert ws_handler.last_broadcast['type'] == 'ui_state_update'
```

---

## 部署清单

### 环境变量

```bash
# .env
ANTHROPIC_API_KEY=sk-ant-xxx
ANTHROPIC_MODEL=claude-3-7-sonnet-20250219

# 数据库
DATABASE_PATH=./data/finance.db

# 服务端口
SERVER_PORT=3000

# 日志级别
LOG_LEVEL=INFO

# 市场数据 API（可选）
AKSHARE_TOKEN=xxx
```

### 依赖安装

```bash
# Python 依赖
pip install -r requirements.txt

# Node.js 依赖
npm install
```

### 数据库迁移

```bash
# 初始化数据库
python scripts/init_database.py

# 运行迁移
python scripts/migrate.py
```

### 启动服务

```bash
# 开发模式
npm run dev

# 生产模式
npm run build
npm run start
```

---

## 参考资料

- [Email Agent 源码](../email-agent/)
- [Claude Agent SDK 文档](https://github.com/anthropics/anthropic-sdk-python)
- [IMPLEMENTATION_CHECKLIST.md](./IMPLEMENTATION_CHECKLIST.md)
- [UI_STATE_SYSTEM.md](../email-agent/UI_STATE_SYSTEM.md)
- [ACTIONS_SPEC.md](../email-agent/ACTIONS_SPEC.md)
- [LISTENERS_SPEC.md](../email-agent/LISTENERS_SPEC.md)

---

## 常见问题

### Q1: Listener 和 Action 有什么区别？

**A**: 
- **Listener**: 被动触发，事件发生时自动执行（如新报告上传）
- **Action**: 主动触发，用户点击按钮执行（如设置价格提醒）

### Q2: UI State 和组件的关系？

**A**: 
- **UI State**: 数据（存储在数据库）
- **Component**: 视图（React 组件，根据 State 渲染）
- 关系: `Component = f(State)`

### Q3: 如何实现热重载？

**A**: 使用 `watchdog` 监听文件变化，重新加载模块：
```python
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class ReloadHandler(FileSystemEventHandler):
    def on_modified(self, event):
        # 清除模块缓存
        importlib.invalidate_caches()
        # 重新加载
        await manager.load_all_listeners()
```

### Q4: WebSocket 如何保证消息顺序？

**A**: 使用 `asyncio.Lock` 确保串行处理：
```python
async def handle_message(self, message):
    async with self._message_lock:
        await self._process_message(message)
```

---

**文档维护者**: Finance Agent 开发团队  
**创建日期**: 2025-11-27  
**下次审查**: 每周更新
