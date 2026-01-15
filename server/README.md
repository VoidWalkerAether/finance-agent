# Finance Agent Server

智能金融报告分析系统 - FastAPI 服务端

## 📋 功能特性

### ✅ 已实现

- **WebSocket 实时通信**：支持多轮对话、UI 状态推送、Action 执行
- **REST API 端点**：报告管理、关注列表、UI State、Actions、Listeners
- **插件系统**：Listeners、Actions、UI States 热重载
- **异步架构**：基于 FastAPI + asyncio 的高性能异步服务
- **数据库管理**：SQLite + FTS5 全文搜索

### 🎯 核心端点

#### 报告相关
```
GET    /api/reports                    # 获取报告列表（分页）
GET    /api/reports/{report_id}        # 获取报告详情
POST   /api/reports/search             # 全文搜索（FTS5）
```

#### 关注列表
```
GET    /api/watchlist                  # 获取关注列表
POST   /api/watchlist                  # 添加关注项
DELETE /api/watchlist/{id}             # 删除关注项
```

#### UI State
```
GET    /api/ui-states                  # 获取所有状态
GET    /api/ui-state/{state_id}        # 获取单个状态
PUT    /api/ui-state/{state_id}        # 更新状态
GET    /api/ui-state-templates         # 获取模板列表
```

#### Actions & Listeners
```
GET    /api/action-templates           # 获取 Action 模板
POST   /api/actions/execute            # 执行 Action
GET    /api/listeners                  # 获取所有 Listeners
GET    /api/listener/{id}/logs         # 获取 Listener 日志
```

#### WebSocket
```
WS     /ws                             # WebSocket 连接端点
```

## 🚀 快速开始

### 1. 环境准备

**环境变量配置（.env）**
```bash
# Claude API Key（必需）
ANTHROPIC_AUTH_TOKEN=sk-ant-xxx

# 数据库路径
DATABASE_PATH=./data/finance.db

# 服务器端口
SERVER_PORT=3000

# 日志级别
LOG_LEVEL=INFO

# 报告目录
REPORT_DIR=./report
```

### 2. 安装依赖

```bash
# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

**必需依赖**：
```
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
python-dotenv>=1.0.0
websockets>=12.0
aiohttp>=3.9.0
aiosqlite>=0.19.0
```

### 3. 启动服务器

**方法 A：使用启动脚本（推荐）**
```bash
./run_server.sh
```

**方法 B：直接运行**
```bash
python server/server.py
```

**方法 C：使用 uvicorn**
```bash
# 开发模式（热重载）
uvicorn server.server:app --reload --host 0.0.0.0 --port 3000

# 生产模式
uvicorn server.server:app --host 0.0.0.0 --port 3000 --workers 4
```

### 4. 验证服务

**健康检查**
```bash
curl http://localhost:3000/health
```

**API 文档**
- Swagger UI: http://localhost:3000/api/docs
- ReDoc: http://localhost:3000/api/redoc

**运行测试**
```bash
python scripts/test_server.py
```

## 🏗️ 架构设计

### 管理器初始化顺序

遵循严格的依赖顺序，避免循环依赖：

```python
1. DatabaseManager          # 数据库（最先）
2. UIStateManager           # UI 状态（依赖 DB）
3. ActionsManager           # 动作系统（依赖 DB + UIState）
4. ListenersManager         # 监听器（依赖 DB + UIState）
5. WebSocketHandler         # WebSocket（整合所有）
```

### 异步初始化流程

```python
@app.on_event("startup")
async def startup_event():
    1. 初始化数据库
    2. 加载 Listeners
    3. 加载 Actions
    4. 加载 UI States
    5. 启动热重载监听器
```

### WebSocket 消息流程

```
Client → WebSocket → WebSocketHandler → Session → AIClient
                                       ↓
                                  Broadcast ← UI States
                                             ← Actions
                                             ← Listeners
```

## 📡 WebSocket 协议

### Client → Server

**聊天消息**
```json
{
  "type": "chat",
  "content": "分析最新的A股报告",
  "sessionId": "session_123"
}
```

**执行 Action**
```json
{
  "type": "execute_action",
  "instanceId": "act_456",
  "sessionId": "session_123"
}
```

### Server → Client

**助手消息**
```json
{
  "type": "assistant_message",
  "content": "我已经分析了报告...",
  "sessionId": "session_123"
}
```

**UI 状态更新**
```json
{
  "type": "ui_state_update",
  "stateId": "portfolio_dashboard",
  "data": { "total_value": 100000 }
}
```

**Action 实例**
```json
{
  "type": "action_instances",
  "actions": [{
    "instanceId": "act_789",
    "templateId": "set_price_alert",
    "label": "设置价格提醒",
    "params": { ... }
  }]
}
```

## 🛠️ 开发指南

### 添加新的 REST 端点

**推荐方式**：使用模块化路由

```python
# server/endpoints/custom.py
from fastapi import APIRouter

router = APIRouter(prefix="/api/custom", tags=["custom"])

@router.get("/")
async def get_custom_data():
    return {"message": "Custom endpoint"}

# server/server.py
from server.endpoints import custom
app.include_router(custom.router)
```

### 注册新的管理器

```python
# server/server.py
from ccsdk.my_manager import MyManager

my_manager = MyManager(db_manager)

# 注入到 WebSocketHandler（如果需要）
ws_handler.my_manager = my_manager
```

### 调试技巧

**启用详细日志**
```bash
LOG_LEVEL=DEBUG python server/server.py
```

**检查管理器状态**
```bash
curl http://localhost:3000/api/listeners  # 查看 Listeners
curl http://localhost:3000/api/action-templates  # 查看 Actions
```

## ⚠️ 注意事项

### 1. 环境变量

- ✅ **从环境变量读取配置**（不硬编码）
- ❌ **禁止在代码中指定模型**（违反项目规范）
- ✅ **Claude SDK 自动读取 `ANTHROPIC_AUTH_TOKEN`**

### 2. 模块化设计

- ✅ **API 代码应在 `server/endpoints/` 中**
- ❌ **不要将 API 逻辑写在 `database_manager.py`**
- ✅ **使用 FastAPI 依赖注入**

### 3. 异步操作

- ✅ **所有数据库操作必须异步**（`async/await`）
- ✅ **使用 `asyncio.create_task()` 启动后台任务**
- ❌ **避免阻塞操作**（会影响性能）

### 4. 错误处理

- ✅ **使用全局异常处理器**
- ✅ **返回友好错误信息**
- ✅ **记录详细日志**

## 🔧 故障排查

### 服务器无法启动

**检查 Python 版本**
```bash
python3 --version  # 需要 3.10+
```

**检查依赖**
```bash
pip list | grep fastapi
pip list | grep uvicorn
```

**检查端口占用**
```bash
lsof -i :3000  # macOS/Linux
netstat -ano | findstr :3000  # Windows
```

### WebSocket 连接失败

**检查 API Key**
```bash
# .env 文件中是否有 ANTHROPIC_AUTH_TOKEN
cat .env | grep ANTHROPIC
```

**检查防火墙**
```bash
# 允许端口 3000
```

### 数据库错误

**检查数据库文件**
```bash
ls -lh data/finance.db
```

**重新初始化**
```bash
rm data/finance.db
python server/server.py  # 会自动重建
```

## 📚 参考资料

- [Email Agent 源码](../../email-agent/)
- [FEATURES_ROADMAP.md](../FEATURES_ROADMAP.md)
- [IMPLEMENTATION_CHECKLIST.md](../IMPLEMENTATION_CHECKLIST.md)
- [FastAPI 文档](https://fastapi.tiangolo.com/)

## 📝 TODO

- [ ] 创建 `server/endpoints/` 模块化路由
- [ ] 添加报告上传功能（`POST /api/reports`）
- [ ] 实现 Action 执行完整流程
- [ ] 添加单元测试
- [ ] 性能优化（连接池、缓存）

---

**Last Updated**: 2025-12-02
**Version**: 1.0.0
