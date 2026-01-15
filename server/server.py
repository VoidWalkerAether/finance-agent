"""
Finance Agent Server - FastAPI 主入口

基于 Email Agent 架构的智能金融报告分析系统服务端

功能：
1. WebSocket 实时通信（/ws）
2. REST API 端点（报告、关注列表、UI State 等）
3. 插件系统热重载（Listeners、Actions、UI States）
4. 异步初始化和生命周期管理

参考：
- Email Agent: email-agent/server/server.ts
- 架构文档: FEATURES_ROADMAP.md
"""

import os
import sys
import asyncio
from pathlib import Path
from typing import Optional

# 强制无缓冲输出（确保 print 日志立即显示）
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# FastAPI 相关
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

# 环境变量
from dotenv import load_dotenv

# 项目模块
from ccsdk.websocket_handler import WebSocketHandler
from ccsdk.listeners_manager import ListenersManager
from ccsdk.actions_manager import ActionsManager
from ccsdk.ui_state_manager import UIStateManager
from database.database_manager import DatabaseManager

# 服务层
from server.services import ReportAnalysisService, SearchService

# API 端点路由
from server.endpoints import (
    reports as reports_endpoint,
    watchlist as watchlist_endpoint,
    ui_states as ui_states_endpoint,
    actions as actions_endpoint,
    listeners as listeners_endpoint,
    search as search_endpoint
)

# 加载环境变量
load_dotenv()

# ============================================================================
# 环境配置（遵守内存规范：不硬编码模型，从环境变量读取）
# ============================================================================

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_AUTH_TOKEN")  # Claude SDK 默认环境变量
DATABASE_PATH = os.getenv("DATABASE_PATH", "./data/finance.db")
SERVER_PORT = int(os.getenv("SERVER_PORT", "3000"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
REPORT_DIR = os.getenv("REPORT_DIR", "./report")

# 验证必需的环境变量
if not ANTHROPIC_API_KEY:
    print("⚠️  Warning: ANTHROPIC_AUTH_TOKEN not set in environment variables")
    print("   Please set it in .env file or export it before starting the server")

# ============================================================================
# 创建 FastAPI 应用
# ============================================================================

app = FastAPI(
    title="Finance Agent API",
    description="智能金融报告分析助手 API",
    version="1.0.0",
    docs_url="/api/docs",  # Swagger UI
    redoc_url="/api/redoc",  # ReDoc
)

# ============================================================================
# CORS 配置（允许前端跨域访问）
# ============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 开发环境允许所有来源，生产环境应指定具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# 初始化管理器（遵循正确的依赖顺序）
# 顺序：DB → UIState → Actions → Listeners → WebSocket
# ============================================================================

print("🚀 Initializing Finance Agent Server...")

# 1. 数据库管理器（最先初始化，单例模式）
db_manager = DatabaseManager()

# 2. UI 状态管理器（依赖数据库）
ui_state_manager = UIStateManager(db_manager)

# 3. Actions 管理器（依赖数据库和 UI 状态）
actions_manager = ActionsManager(db_manager, ui_state_manager)

# 4. Listeners 管理器（依赖最多）
def notification_callback(notification: dict):
    """Listener 通知回调"""
    print(f"[Server] Listener notification: {notification}")
    # TODO: 可以通过 WebSocket 广播通知到前端

def log_broadcast_callback(log: dict):
    """Listener 日志广播回调"""
    # 通过 WebSocket 广播日志
    asyncio.create_task(ws_handler.broadcast_listener_log(log))

listeners_manager = ListenersManager(
    database=db_manager,
    notification_callback=notification_callback,
    log_broadcast_callback=log_broadcast_callback,
    ui_state_manager=ui_state_manager
)

# 5. WebSocket 处理器（整合所有管理器）
ws_handler = WebSocketHandler(
    db_manager=db_manager,
    ui_state_manager=ui_state_manager,
    search_service=None  # ✅ 暂时为 None，后面注入
)

# 将 ActionsManager 和 ListenersManager 注入到 WebSocketHandler
# （用于处理 execute_action 消息）
ws_handler.actions_manager = actions_manager
ws_handler.listeners_manager = listeners_manager

# 6. 报告分析服务
report_service = ReportAnalysisService(
    database_manager=db_manager,
    listeners_manager=listeners_manager
)

# 7. 搜索服务
search_service = SearchService(
    database_manager=db_manager
)

# ✅ 注入 search_service 到 WebSocketHandler
ws_handler.search_service = search_service

print("✅ Managers initialized successfully")

# ============================================================================
# 依赖注入到端点模块
# ============================================================================

reports_endpoint.set_dependencies(db_manager, report_service)
watchlist_endpoint.set_dependencies(db_manager)
ui_states_endpoint.set_dependencies(ui_state_manager)
actions_endpoint.set_dependencies(actions_manager)
listeners_endpoint.set_dependencies(listeners_manager)
search_endpoint.set_dependencies(search_service)

# ============================================================================
# 服务器生命周期事件
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """
    服务器启动时的异步初始化
    对应 Email Agent 的 server.ts 第 74-129 行
    """
    print("\n" + "=" * 60)
    print("🔧 Starting Finance Agent Server - Async Initialization")
    print("=" * 60)
    
    try:
        # 1. 数据库已在初始化时完成 schema 加载
        print("\n[1/5] Database initialization...")
        stats = await db_manager.get_report_stats()
        report_count = stats.get('total_reports', 0) if stats else 0
        print(f"   ✅ Database ready: {report_count} reports indexed")
        
        # 2. 加载 Listeners
        print("\n[2/5] Loading listeners...")
        listeners = await listeners_manager.load_all_listeners()
        print(f"   ✅ Loaded {len(listeners)} listener(s)")
        
        # 3. 加载 Actions
        print("\n[3/5] Loading actions...")
        actions = await actions_manager.load_all_templates()
        print(f"   ✅ Loaded {len(actions)} action template(s)")
        
        # 4. 加载 UI States
        print("\n[4/5] Loading UI states...")
        ui_states = await ui_state_manager.load_all_templates()
        print(f"   ✅ Loaded {len(ui_states)} UI state template(s)")
        
        # 5. 启动热重载（文件监听）
        print("\n[5/5] Starting hot reload watchers...")
        
        # Listeners 热重载
        asyncio.create_task(
            listeners_manager.watch_listeners(
                lambda ls: print(f"   🔄 [Hot Reload] Listeners reloaded: {len(ls)} listener(s)")
            )
        )
        
        # Actions 热重载
        asyncio.create_task(
            actions_manager.watch_templates(
                lambda ts: print(f"   🔄 [Hot Reload] Actions reloaded: {len(ts)} template(s)")
            )
        )
        
        # UI States 热重载
        asyncio.create_task(
            ui_state_manager.watch_templates(
                lambda ts: print(f"   🔄 [Hot Reload] UI States reloaded: {len(ts)} template(s)")
            )
        )
        
        print("   ✅ Hot reload watchers started")
        
        # 启动成功信息
        print("\n" + "=" * 60)
        print("✅ Finance Agent Server Started Successfully!")
        print("=" * 60)
        print(f"\n📡 Server listening on: http://localhost:{SERVER_PORT}")
        print(f"🔌 WebSocket endpoint: ws://localhost:{SERVER_PORT}/ws")
        print(f"📚 API documentation: http://localhost:{SERVER_PORT}/api/docs")
        print(f"📊 Database: {DATABASE_PATH}")
        print(f"📁 Report directory: {REPORT_DIR}")
        print("\n" + "=" * 60 + "\n")
        
    except Exception as e:
        print(f"\n❌ Failed to start server: {e}")
        import traceback
        traceback.print_exc()
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """服务器关闭时的清理"""
    print("\n🛑 Shutting down Finance Agent Server...")
    
    # 停止 WebSocket Handler
    await ws_handler.stop()
    
    # DatabaseManager 使用 aiosqlite，不需要显式关闭
    # 每次操作都是独立的连接上下文
    
    print("✅ Server shutdown complete\n")

# ============================================================================
# 全局异常处理器
# ============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理器"""
    print(f"❌ Unhandled error: {exc}")
    import traceback
    traceback.print_exc()
    
    return JSONResponse(
        status_code=500,
        content={
            "error": str(exc),
            "type": type(exc).__name__,
            "detail": "Internal server error"
        }
    )

# ============================================================================
# WebSocket 端点
# ============================================================================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket 连接端点
    对应 Email Agent 的 server.ts 第 141-153 行
    
    功能：
    - 实时聊天对话
    - UI 状态更新推送
    - Action 执行
    - Listener 日志广播
    """
    await websocket.accept()
    
    # 调用 WebSocketHandler 的 on_open 方法
    await ws_handler.on_open(websocket)
    
    try:
        # 持续接收消息
        while True:
            message = await websocket.receive_text()
            await ws_handler.on_message(websocket, message)
            
    except WebSocketDisconnect:
        # 客户端断开连接
        await ws_handler.on_close(websocket)
    except Exception as e:
        print(f"❌ WebSocket error: {e}")
        await ws_handler.on_close(websocket)

# ============================================================================
# REST API 端点（模块化路由）
# ============================================================================

# 注册模块化路由
app.include_router(reports_endpoint.router)
app.include_router(watchlist_endpoint.router)
app.include_router(ui_states_endpoint.router)
app.include_router(actions_endpoint.router)
app.include_router(listeners_endpoint.router)
app.include_router(search_endpoint.router)


# ---------- 健康检查 ----------

@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "service": "finance-agent",
        "version": "1.0.0"
    }


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "Finance Agent API",
        "docs": "/api/docs",
        "websocket": "/ws"
    }

# ============================================================================
# 主入口
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    # 启动服务器
    uvicorn.run(
        "server.server:app",
        host="0.0.0.0",
        port=SERVER_PORT,
        reload=True,  # 开发模式自动重载
        log_level=LOG_LEVEL.lower(),
        access_log=True
    )
