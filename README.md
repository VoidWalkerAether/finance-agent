# Finance Agent - 智能金融报告分析助手

> ⚠️ **重要提示**: 这是一个基于 Claude Agent SDK 的演示应用，仅用于本地开发和学习。不建议部署到生产环境或大规模使用。

基于 [Claude Agent SDK](https://docs.anthropic.com/en/docs/claude-code/sdk/sdk-overview) 构建的智能金融报告分析系统，可以自动分析金融报告、提取投资建议、监控关注标的，并提供多轮对话式的投资分析服务。

## ✨ 核心特性

- 🤖 **智能对话分析** - 基于 Claude Agent SDK 的多轮对话，深度理解金融报告内容
- 📊 **自动信息提取** - 自动提取报告中的投资标的、策略建议、风险提示等关键信息
- 🔍 **语义搜索引擎** - 使用 ChromaDB 向量数据库实现报告语义检索和相似度搜索
- 📈 **实时监控系统** - 关注列表管理、价格提醒、风险检测等实时监控功能
- 🔌 **插件化架构** - 支持自定义 Listeners（事件监听）、Actions（一键操作）、UI States（状态管理）
- 📡 **实时通信** - WebSocket + REST API 双协议支持，实时推送分析结果
- 🔥 **热重载机制** - 插件代码修改后自动重载，无需重启服务

## 📋 功能概览

### 核心功能

| 功能模块 | 说明 | 状态 |
|---------|------|------|
| **多轮对话** | Claude Agent SDK 驱动的智能对话系统 | ✅ 已实现 |
| **报告分析** | 自动提取投资标的、策略、风险等信息 | ✅ 已实现 |
| **语义搜索** | 基于 ChromaDB 的向量检索和全文搜索 | ✅ 已实现 |
| **关注列表** | 管理关注的行业/公司/ETF 标的 | ✅ 已实现 |
| **价格提醒** | 设置价格预警，触发通知 | ✅ 已实现 |
| **事件监听** | Listeners 系统自动响应报告事件 | ✅ 已实现 |
| **动作执行** | Actions 系统提供一键操作按钮 | ✅ 已实现 |
| **状态管理** | UI States 持久化前端展示状态 | ✅ 已实现 |
| **实时推送** | WebSocket 实时广播更新 | ✅ 已实现 |

### 插件系统

```
agent/custom_scripts/
├── listeners/              # 事件监听器（自动触发）
│   ├── report_analyzer.py      # 新报告自动分析
│   └── watchlist_monitor.py    # 关注列表监控
├── actions/                # 用户动作（一键执行）
│   ├── add_to_watchlist.py     # 添加到关注列表
│   └── set_price_alert.py      # 设置价格提醒
├── ui-states/              # UI 状态模板
│   ├── financial_dashboard.py  # 财务仪表盘状态
│   └── price_alerts.py         # 价格提醒状态
└── components/             # 前端组件模板
    └── portfolio_dashboard.py  # 投资组合仪表盘
```

## 🚀 快速开始

### 环境要求

- Python 3.10+ 
- Anthropic API Key ([获取地址](https://console.anthropic.com))

### 安装步骤

#### 1. 克隆仓库

```bash
git clone https://github.com/VoidWalkerAether/finance-agent.git
cd finance-agent
```

#### 2. 创建虚拟环境并安装依赖

```bash
# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

#### 3. 配置环境变量

```bash
# 复制环境变量模板
cp .env\ copy.example .env

# 编辑 .env 文件，填入你的 API Key
# ANTHROPIC_AUTH_TOKEN=sk-ant-api03-xxxxx
```

**必需的环境变量**：

```env
# Anthropic API Key（必需）
ANTHROPIC_AUTH_TOKEN=sk-ant-api03-xxxxx

# 数据库路径（可选，默认 ./data/finance.db）
DATABASE_PATH=./data/finance.db

# 服务器端口（可选，默认 3000）
SERVER_PORT=3000

# 报告文件目录（可选，默认 ./report）
REPORT_DIR=./report
```

#### 4. 启动服务

**方式 A：使用启动脚本（推荐）**

```bash
./run_server.sh
```

**方式 B：直接运行**

```bash
python server/server.py
```

**方式 C：使用 uvicorn**

```bash
uvicorn server.server:app --reload --port 3000
```

### 验证服务

#### 1. 健康检查

```bash
curl http://localhost:3000/health
```

**预期输出：**

```json
{
  "status": "healthy",
  "service": "finance-agent",
  "version": "1.0.0"
}
```

#### 2. 查看 API 文档

浏览器访问：[http://localhost:3000/api/docs](http://localhost:3000/api/docs)

#### 3. 测试 WebSocket 连接

```bash
# 使用 wscat 工具
npm install -g wscat
wscat -c ws://localhost:3000/ws

# 发送测试消息
{"type": "chat", "content": "你好，分析一下最新的 A 股报告", "sessionId": "test_001"}
```

## 🏗️ 项目架构

### 目录结构

```
finance-agent/
├── agent/                      # 自定义脚本层（用户可扩展）
│   ├── custom_scripts/
│   │   ├── listeners/          # 事件监听器
│   │   ├── actions/            # 用户动作
│   │   ├── ui-states/          # UI 状态模板
│   │   └── components/         # 前端组件模板
│   ├── a_share_investment_analysis.md  # 示例分析报告
│   └── search_a_share_reports.py       # 报告搜索脚本
│
├── ccsdk/                      # 核心 SDK 层（Agent 引擎）
│   ├── session.py              # 会话管理（多轮对话）
│   ├── websocket_handler.py    # WebSocket 连接与消息分发
│   ├── listeners_manager.py    # 监听器加载、执行、热重载
│   ├── actions_manager.py      # 动作模板加载、实例注册、执行
│   ├── ui_state_manager.py     # UI 状态持久化、广播
│   ├── component_manager.py    # 组件模板管理
│   ├── ai_client.py            # Claude SDK 封装
│   ├── agent_tools.py          # AI 工具调用
│   ├── custom_tools.py         # 自定义工具（MCP Server）
│   └── message_types.py        # 消息类型定义
│
├── database/                   # 数据库层
│   ├── repositories/           # 数据仓库
│   │   └── watchlist_repo.py  # 关注列表仓库
│   ├── database_manager.py     # SQLite 操作管理
│   ├── relationship_analyzer.py # 关系分析器
│   ├── schema.sql              # 数据库表结构
│   └── sample_data.sql         # 示例数据
│
├── server/                     # 服务端
│   ├── endpoints/              # REST API 端点
│   │   ├── reports.py          # 报告相关 API
│   │   ├── watchlist.py        # 关注列表 API
│   │   ├── search.py           # 搜索 API
│   │   ├── ui_states.py        # UI 状态 API
│   │   ├── actions.py          # 动作 API
│   │   └── listeners.py        # 监听器 API
│   ├── services/               # 业务服务层
│   │   ├── report_service.py   # 报告分析服务
│   │   └── search_service.py   # 搜索服务
│   └── server.py               # FastAPI 主入口
│
├── client/                     # 前端（React）
│   ├── components/             # React 组件
│   │   └── custom/             # 自定义组件
│   └── hooks/                  # React Hooks
│
├── scripts/                    # 测试与工具脚本
├── report/                     # 报告文件目录
├── .env                        # 环境变量配置
├── requirements.txt            # Python 依赖
├── run_server.sh               # 启动脚本
└── README.md                   # 本文档
```

### 架构层次

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
│  │   (消息路由 / 实时广播 / 会话管理)                   │        │
│  └──────────────────────┬───────────────────────────────┘        │
│                         │                                         │
│  ┌──────────────────────▼──────────────────────────────┐        │
│  │              Session Manager                         │        │
│  │   (多轮对话 + AI 调用 + 消息广播)                    │        │
│  └──────────┬──────────────────────────┬────────────────┘        │
│             │                          │                          │
│  ┌──────────▼────────┐    ┌───────────▼──────────┐              │
│  │  ListenersManager │    │   ActionsManager     │              │
│  │  (事件触发/热重载) │    │   (动作执行/日志)    │              │
│  └──────────┬────────┘    └───────────┬──────────┘              │
│             │                          │                          │
│  ┌──────────▼────────┐    ┌───────────▼──────────┐              │
│  │  UIStateManager   │    │  ComponentManager    │              │
│  │  (状态持久化/广播) │    │  (组件注册/管理)     │              │
│  └──────────┬────────┘    └───────────┬──────────┘              │
│             │                          │                          │
│  ┌──────────▼──────────────────────────▼──────────┐             │
│  │           DatabaseManager (SQLite)              │             │
│  │  Reports | UI States | Components | Watchlist  │             │
│  └─────────────────────────────────────────────────┘             │
│                                                                   │
│  ┌───────────────────────────────────────────────────┐          │
│  │       Search Service (ChromaDB)                   │          │
│  │  Vector Search | Semantic Search | FTS5          │          │
│  └───────────────────────────────────────────────────┘          │
└───────────────────────────────────────────────────────────────────┘
```

## 📡 API 文档

### WebSocket 协议

**连接地址**：`ws://localhost:3000/ws`

#### 消息类型

##### 1. 聊天消息（客户端 → 服务端）

```json
{
  "type": "chat",
  "content": "分析最新的 A 股报告",
  "sessionId": "session_001",
  "newConversation": false
}
```

##### 2. 助手响应（服务端 → 客户端）

```json
{
  "type": "assistant_message",
  "content": "根据最新报告分析...",
  "sessionId": "session_001"
}
```

##### 3. 执行动作（客户端 → 服务端）

```json
{
  "type": "execute_action",
  "instanceId": "act_123",
  "sessionId": "session_001"
}
```

##### 4. 动作结果（服务端 → 客户端）

```json
{
  "type": "action_result",
  "instanceId": "act_123",
  "result": {
    "success": true,
    "message": "已添加到关注列表"
  },
  "sessionId": "session_001"
}
```

##### 5. UI 状态更新（服务端 → 客户端）

```json
{
  "type": "ui_state_update",
  "stateId": "portfolio_dashboard",
  "data": {
    "total_value": 100000,
    "holdings": [...]
  }
}
```

### REST API 端点

完整的 API 文档访问：[http://localhost:3000/api/docs](http://localhost:3000/api/docs)

#### 核心端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/api/reports` | GET | 获取报告列表 |
| `/api/reports/search` | POST | 搜索报告 |
| `/api/watchlist` | GET | 获取关注列表 |
| `/api/watchlist` | POST | 添加关注项 |
| `/api/ui-states` | GET | 获取所有 UI State |
| `/api/ui-states/{state_id}` | GET | 获取指定 UI State |
| `/api/action-templates` | GET | 获取 Action 模板 |
| `/api/listeners` | GET | 获取 Listener 列表 |

#### 示例：搜索报告

```bash
curl -X POST http://localhost:3000/api/reports/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "黄金投资",
    "limit": 10
  }'
```

**响应：**

```json
{
  "results": [
    {
      "report_id": "report_001",
      "title": "A股4000拉锯要不要买黄金",
      "category": "A股",
      "date": "2025-11-26",
      "relevance_score": 0.95
    }
  ],
  "total": 1
}
```

## 🔌 插件开发指南

### 创建自定义 Listener

Listener 是**被动触发**的插件，当特定事件发生时自动执行。

#### 示例：创建报告分析监听器

**文件路径**：`agent/custom_scripts/listeners/my_analyzer.py`

```python
from typing import Dict, Any

# 配置信息
config = {
    'id': 'my_analyzer',
    'name': '我的报告分析器',
    'description': '自动分析新上传的报告',
    'enabled': True,
    'event': 'report_received'  # 监听 report_received 事件
}

# 处理函数
async def handler(event_data: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    处理报告接收事件
    
    Args:
        event_data: 事件数据，包含报告信息
        context: 上下文对象，提供数据库、AI 调用等能力
    
    Returns:
        执行结果
    """
    report = event_data.get('report', {})
    report_id = report.get('report_id')
    content = report.get('content', '')
    
    # 1. 使用 AI 分析报告
    analysis = await context.call_agent(
        prompt=f"分析以下金融报告，提取关键投资信息：\n\n{content}",
        schema={
            "type": "object",
            "properties": {
                "investment_targets": {"type": "array"},
                "strategies": {"type": "array"},
                "risks": {"type": "array"}
            }
        }
    )
    
    # 2. 保存分析结果到数据库
    await context.database.update_report(report_id, {
        'structured_data': analysis
    })
    
    # 3. 发送通知
    await context.notify(
        f"报告 {report.get('title')} 分析完成！",
        priority="normal"
    )
    
    return {
        'executed': True,
        'reason': '报告分析成功',
        'data': analysis
    }
```

#### 可用的事件类型

- `report_received` - 新报告上传
- `report_analyzed` - 报告分析完成
- `price_alert` - 价格触发预警
- `daily_summary` - 每日定时任务
- `user_query` - 用户提问

### 创建自定义 Action

Action 是**主动触发**的操作，由用户点击按钮执行。

#### 示例：创建导出报告 Action

**文件路径**：`agent/custom_scripts/actions/export_report.py`

```python
from typing import Dict, Any

# 配置信息
config = {
    'id': 'export_report',
    'name': '导出报告',
    'description': '将报告导出为 PDF 或 Excel',
    'icon': '📥',
    'parameterSchema': {
        'type': 'object',
        'properties': {
            'report_id': {
                'type': 'string',
                'description': '报告 ID'
            },
            'format': {
                'type': 'string',
                'enum': ['pdf', 'excel'],
                'description': '导出格式'
            }
        },
        'required': ['report_id', 'format']
    }
}

# 处理函数
async def handler(params: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    执行导出操作
    
    Args:
        params: 参数，由 AI 生成的 ActionInstance 提供
        context: 上下文对象
    
    Returns:
        执行结果
    """
    report_id = params['report_id']
    format_type = params['format']
    
    # 1. 从数据库获取报告
    report = await context.database.get_report(report_id)
    
    # 2. 生成导出文件
    if format_type == 'pdf':
        file_path = await generate_pdf(report)
    else:
        file_path = await generate_excel(report)
    
    # 3. 发送成功通知
    await context.notify(
        f"报告已导出为 {format_type.upper()} 格式",
        type="success"
    )
    
    return {
        'success': True,
        'message': f'报告已导出',
        'data': {
            'file_path': file_path,
            'format': format_type
        }
    }
```

### 创建 UI State 模板

UI State 用于持久化前端展示的状态数据。

#### 示例：创建投资组合状态

**文件路径**：`agent/custom_scripts/ui-states/portfolio_dashboard.py`

```python
from typing import TypedDict, List

# 类型定义
class Holding(TypedDict):
    name: str               # 标的名称
    type: str               # 类型（ETF/股票/债券）
    shares: float           # 持仓数量
    cost_basis: float       # 成本价
    current_value: float    # 当前市值
    gain: float             # 收益

class PortfolioState(TypedDict):
    total_value: float      # 总资产
    allocation: dict        # 资产配置
    holdings: List[Holding] # 持仓列表

# 配置信息
config = {
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

#### 在 Listener/Action 中更新 UI State

```python
# 在 Listener 或 Action 中更新状态
async def update_portfolio(context):
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
    
    # 3. 保存并广播（自动触发 WebSocket 推送）
    await context.ui_state.set('portfolio_dashboard', state)
```

## 🛠️ 开发与调试

### 热重载机制

项目支持插件代码热重载，无需重启服务：

- **Listeners** - 修改后自动重新加载
- **Actions** - 修改后自动重新加载
- **UI States** - 修改后自动重新加载

修改插件代码后，查看控制台日志确认重载：

```
🔄 [Hot Reload] Listeners reloaded: 2 listener(s)
🔄 [Hot Reload] Actions reloaded: 3 action(s)
🔄 [Hot Reload] UI States reloaded: 2 state(s)
```

### 查看日志

插件执行日志存储在 JSONL 文件中：

```
agent/custom_scripts/.logs/
├── listeners/
│   └── 2025-01-15.jsonl
├── actions/
│   └── 2025-01-15.jsonl
└── ui-states/
    └── 2025-01-15.jsonl
```

### 测试脚本

项目提供了多个测试脚本：

```bash
# 测试数据库
python scripts/test_database.py

# 测试 WebSocket
python scripts/test_websocket_chat.py

# 测试搜索服务
python scripts/test_smart_search.py

# 测试 Actions Manager
python scripts/test_actions_manager.py
```

## 🚢 部署说明

### 开发环境

```bash
# 使用开发服务器（支持热重载）
uvicorn server.server:app --reload --port 3000
```

### 生产环境

#### 使用 uvicorn（多 worker）

```bash
uvicorn server.server:app --host 0.0.0.0 --port 3000 --workers 4
```

#### 使用 gunicorn + uvicorn worker

```bash
gunicorn server.server:app \
  -w 4 \
  -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:3000
```

#### Docker 部署（可选）

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 3000

CMD ["uvicorn", "server.server:app", "--host", "0.0.0.0", "--port", "3000"]
```

## 🐛 常见问题

### Q1: 服务器启动失败

**检查 Python 版本**

```bash
python3 --version  # 需要 3.10+
```

**检查依赖安装**

```bash
pip list | grep fastapi
pip list | grep claude-agent-sdk
```

### Q2: WebSocket 连接被拒绝

**检查 API Key**

```bash
cat .env | grep ANTHROPIC_AUTH_TOKEN
```

确保 API Key 正确且有效。

### Q3: 端口被占用

**查找占用端口的进程**

```bash
# macOS/Linux
lsof -i :3000

# Windows
netstat -ano | findstr :3000
```

**修改端口**

在 `.env` 中设置：

```env
SERVER_PORT=3001
```

### Q4: 数据库错误

**重新初始化数据库**

```bash
rm -f data/finance.db
python server/server.py  # 会自动重建数据库
```

### Q5: ChromaDB 向量数据库错误

**清理 ChromaDB 数据**

```bash
python scripts/cleanup_database.py
```

## 📚 参考资源

### 官方文档

- [Claude Agent SDK Documentation](https://docs.anthropic.com/en/docs/claude-code/sdk/sdk-overview)
- [Anthropic API Reference](https://docs.anthropic.com/claude/reference)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [ChromaDB Documentation](https://docs.trychroma.com/)

### 项目文档

- [架构文档](./ARCHITECTURE_ACTUAL.md) - 详细的架构说明
- [功能规划](./FEATURES_ROADMAP.md) - 功能清单和开发路线图
- [快速启动](./QUICKSTART.md) - 快速启动指南
- [数据库设计](./DATABASE_SCHEMA.md) - 数据库表结构
- [WebSocket 集成](./WEBSOCKET_INTEGRATION.md) - WebSocket 协议详解
- [Action 模板](./ACTION_TEMPLATE.md) - Action 开发模板
- [Listener 模板](./LISTENER_TEMPLATE.md) - Listener 开发模板

### 示例代码

- [Email Agent](../email-agent) - 邮件助手示例（TypeScript 版本）
- [Research Agent](../research-agent) - 研究助手示例
- [Excel Demo](../excel-demo) - Excel 处理示例

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

### 开发规范

1. 代码风格遵循 PEP 8
2. 提交前运行测试脚本
3. 添加必要的注释和文档
4. 保持插件代码的独立性

### 提交流程

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 📄 开源许可

MIT License - 这是演示代码，仅供学习和参考。

---

**Built with ❤️ using [Claude Agent SDK](https://github.com/anthropics/claude-agent-sdk)**

如有问题，请访问 [GitHub Issues](https://github.com/your-repo/claude-agent-sdk-demos/issues)
