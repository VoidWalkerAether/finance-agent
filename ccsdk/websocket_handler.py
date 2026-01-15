"""
Finance Agent WebSocket Handler
对应 TypeScript: WebSocketHandler (websocket-handler.ts)

核心功能:
1. WebSocket 连接管理 (客户端连接/断开)
2. Session 管理 (创建/订阅/清理)
3. 消息路由 (chat/subscribe/unsubscribe)
4. 数据广播 (reports_update/ui_state_update)
5. 自动数据推送 (定时刷新报告列表)

映射关系:
- Email Agent 的 inbox_update → Finance Agent 的 reports_update
- Email Agent 的 emailAPI → Finance Agent 的 reportAPI
"""

import asyncio
import json
import time
from typing import Dict, Set, Optional, Any, List
from dataclasses import dataclass

from .session import Session
from .message_types import WSClient, IncomingMessage, WSReportAnalysisUpdateMessage, WSAlertTriggeredMessage
from database.database_manager import DatabaseManager

# UI State Manager (可选)
try:
    from .ui_state_manager import UIStateManager
    UI_STATE_AVAILABLE = True
except ImportError:
    UIStateManager = None
    UI_STATE_AVAILABLE = False


@dataclass
class WebSocketHandler:
    """
    WebSocket 处理器 - 管理 WebSocket 连接和消息路由
    对应 TypeScript: WebSocketHandler (websocket-handler.ts 第 11-666 行)
    """
    
    def __init__(
        self,
        db_manager: Optional[DatabaseManager] = None,
        ui_state_manager: Optional['UIStateManager'] = None,
        search_service: Optional[Any] = None  # ✅ 添加 search_service 参数
    ):
        """
        初始化 WebSocket Handler
        
        Args:
            db_manager: 数据库管理器
            ui_state_manager: UI 状态管理器 (可选)
            search_service: 搜索服务 (可选)
        """
        self.db = db_manager or DatabaseManager()
        self.ui_state_manager = ui_state_manager
        self.search_service = search_service  # ✅ 保存 search_service
        
        # Session 管理
        self.sessions: Dict[str, Session] = {}
        
        # 客户端管理 (client_id -> WSClient)
        self.clients: Dict[str, WSClient] = {}
        
        # 搜索会话管理 (session_id -> SearchSession)
        self.search_sessions: Dict[str, Any] = {}  # ✅ 添加搜索会话管理
        
        # 后台任务
        self._report_watcher_task: Optional[asyncio.Task] = None
        
        # 初始化 UI State 监听器
        if self.ui_state_manager:
            self._init_ui_state_watcher()
        
    async def start(self):
        """启动 WebSocket Handler"""
        # 启动报告数据监控 (对应 TS 的 initEmailWatcher)
        self._report_watcher_task = asyncio.create_task(self._init_report_watcher())
        print("✅ WebSocket Handler started")
        
    async def stop(self):
        """停止 WebSocket Handler"""
        # 取消后台任务
        if self._report_watcher_task:
            self._report_watcher_task.cancel()
            
        # 清理所有 Session
        for session in self.sessions.values():
            await session.cleanup()
        
        # 清理所有 SearchSession
        for search_session in self.search_sessions.values():  # ✅ 添加
            await search_session.cleanup()
            
        print("✅ WebSocket Handler stopped")
    
    # ==================== 数据监控 ====================
    
    def _init_ui_state_watcher(self):
        """
        初始化 UI State 监听器
        对应 TS: initUIStateWatcher (websocket-handler.ts 第 87-94 行)
        """
        if not self.ui_state_manager:
            return
        
        # 订阅 UI State 更新
        self.ui_state_manager.on_state_update(self._on_ui_state_update)
        print("✅ UI State watcher initialized")
    
    def _on_ui_state_update(self, state_id: str, data: Any):
        """
        UI State 更新回调
        对应 TS: 回调函数 (websocket-handler.ts 第 91-93 行)
        """
        # 创建异步任务广播更新
        asyncio.create_task(self._broadcast_ui_state_update(state_id, data))
    
    async def _init_report_watcher(self):
        """
        初始化报告数据监控 (定时推送报告列表)
        对应 TS: initEmailWatcher (websocket-handler.ts 第 33-41 行)
        """
        # 发送初始数据
        await self._broadcast_reports_update()
        
        # 定时轮询 (每 5 秒刷新一次)
        while True:
            try:
                await asyncio.sleep(5)
                await self._broadcast_reports_update()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"❌ Error in report watcher: {e}")
    
    async def _get_recent_reports(self, limit: int = 30) -> List[Dict[str, Any]]:
        """
        获取最近的报告列表
        对应 TS: getRecentEmails (websocket-handler.ts 第 43-68 行)
        """
        try:
            reports = await self.db.search_reports(limit=limit)
            
            # 简化数据 (只返回列表需要的字段)
            simplified = []
            for report in reports:
                simplified.append({
                    'id': report.get('id'),
                    'report_id': report.get('report_id'),
                    'title': report.get('title'),
                    'category': report.get('category'),
                    'summary_one_sentence': report.get('summary_one_sentence'),
                    'key_drivers': report.get('key_drivers'),
                    'date_published': report.get('date_published'),
                    'importance_score': report.get('importance_score'),
                    'action': report.get('action'),
                    'content': report.get('content'),
                    'sentiment': report.get('sentiment'),
                    'sources': report.get('sources'),
                })
            
            return simplified
        except Exception as e:
            print(f"❌ Error fetching recent reports: {e}")
            return []
    
    async def _broadcast_reports_update(self):
        """
        广播报告列表更新
        对应 TS: broadcastInboxUpdate (websocket-handler.ts 第 70-85 行)
        """
        reports = await self._get_recent_reports()
        message = json.dumps({
            'type': 'reports_update',
            'reports': reports
        }, ensure_ascii=False)
        
        # 广播给所有客户端
        for client in self.clients.values():
            try:
                await client.send_text(message)
            except Exception as e:
                print(f"❌ Error sending reports update: {e}")
    
    async def _broadcast_ui_state_update(self, state_id: str, data: Any):
        """
        广播 UI State 更新
        对应 TS: broadcastUIStateUpdate (websocket-handler.ts 第 96-111 行)
        """
        message = json.dumps({
            'type': 'ui_state_update',
            'stateId': state_id,
            'data': data
        }, ensure_ascii=False)
        
        # 广播给所有客户端
        for client in self.clients.values():
            try:
                await client.send_text(message)
            except Exception as e:
                print(f"❌ Error sending UI state update: {e}")
    
    async def _broadcast_report_analysis_update(self, report_id: str, title: str, analysis: Any, session_id: Optional[str] = None):
        """
        广播报告分析更新
        """
        message_obj = WSReportAnalysisUpdateMessage(
            reportId=report_id,
            title=title,
            analysis=analysis,
            timestamp=time.strftime('%Y-%m-%d %H:%M:%S'),
            sessionId=session_id or ""
        )
        
        # 转换为字典并序列化
        message_dict = {
            'type': message_obj.type,
            'reportId': message_obj.reportId,
            'title': message_obj.title,
            'analysis': message_obj.analysis,
            'timestamp': message_obj.timestamp,
            'sessionId': message_obj.sessionId
        }
        
        message = json.dumps(message_dict, ensure_ascii=False)
        
        # 广播给所有客户端或特定会话的客户端
        for client in self.clients.values():
            # 如果指定了session_id，只发送给该会话的客户端
            if session_id:
                if hasattr(client, 'session_id') and client.session_id == session_id:
                    try:
                        await client.send_text(message)
                    except Exception as e:
                        print(f"❌ Error sending report analysis update: {e}")
            else:
                # 否则发送给所有客户端
                try:
                    await client.send_text(message)
                except Exception as e:
                    print(f"❌ Error sending report analysis update: {e}")
    
    async def _broadcast_alert_triggered(self, alert_id: str, title: str, message_text: str, severity: str = "info", data: Any = None, session_id: Optional[str] = None):
        """
        广播预警触发消息
        """
        message_obj = WSAlertTriggeredMessage(
            alertId=alert_id,
            title=title,
            message=message_text,
            severity=severity,
            data=data,
            timestamp=time.strftime('%Y-%m-%d %H:%M:%S'),
            sessionId=session_id or ""
        )
        
        # 转换为字典并序列化
        message_dict = {
            'type': message_obj.type,
            'alertId': message_obj.alertId,
            'title': message_obj.title,
            'message': message_obj.message,
            'severity': message_obj.severity,
            'data': message_obj.data,
            'timestamp': message_obj.timestamp,
            'sessionId': message_obj.sessionId
        }
        
        message = json.dumps(message_dict, ensure_ascii=False)
        
        # 广播给所有客户端或特定会话的客户端
        for client in self.clients.values():
            # 如果指定了session_id，只发送给该会话的客户端
            if session_id:
                if hasattr(client, 'session_id') and client.session_id == session_id:
                    try:
                        await client.send_text(message)
                    except Exception as e:
                        print(f"❌ Error sending alert triggered message: {e}")
            else:
                # 否则发送给所有客户端
                try:
                    await client.send_text(message)
                except Exception as e:
                    print(f"❌ Error sending alert triggered message: {e}")
    
    # ==================== Session 管理 ====================
    
    def _generate_session_id(self) -> str:
        """
        生成唯一的 Session ID
        对应 TS: generateSessionId (websocket-handler.ts 第 130-132 行)
        """
        timestamp = int(time.time() * 1000)
        random_part = hex(int(time.time() * 1000000) % 1000000)[2:]
        return f"session-{timestamp}-{random_part}"
    
    def _get_or_create_session(self, session_id: Optional[str] = None) -> Session:
        """
        获取或创建 Session
        对应 TS: getOrCreateSession (websocket-handler.ts 第 134-143 行)
        """
        if session_id and session_id in self.sessions:
            return self.sessions[session_id]
        
        new_session_id = session_id or self._generate_session_id()
        # 注入 UI State Manager 到 Session
        session = Session(
            new_session_id,
            self.db,
            ui_state_manager=self.ui_state_manager
        )
        self.sessions[new_session_id] = session
        return session
    
    async def _cleanup_empty_sessions(self):
        """
        清理空的 Session (无订阅者)
        对应 TS: cleanupEmptySessions (websocket-handler.ts 第 363-376 行)
        """
        for session_id, session in list(self.sessions.items()):
            if not session.has_subscribers():
                # 1 分钟宽限期后再清理
                await asyncio.sleep(60)
                if not session.has_subscribers():
                    await session.cleanup()
                    del self.sessions[session_id]
                    print(f"🗑️  Cleaned up empty session: {session_id}")
    
    # ==================== WebSocket 事件处理 ====================
    
    async def on_open(self, ws: WSClient):
        """
        客户端连接事件
        对应 TS: onOpen (websocket-handler.ts 第 145-189 行)
        """
        # 生成唯一的客户端 ID
        client_id = f"{int(time.time() * 1000)}-{hex(int(time.time() * 1000000) % 1000000)[2:]}"
        self.clients[client_id] = ws
        print(f"🔌 WebSocket client connected: {client_id}")
        
        # 发送连接确认
        await ws.send_text(json.dumps({
            'type': 'connected',
            'message': 'Connected to Finance Agent',
            'availableSessions': list(self.sessions.keys())
        }, ensure_ascii=False))
        
        # 发送初始报告列表
        reports = await self._get_recent_reports()
        await ws.send_text(json.dumps({
            'type': 'reports_update',
            'reports': reports
        }, ensure_ascii=False))
        
        # 发送 UI State 模板列表
        if self.ui_state_manager:
            try:
                ui_state_templates = self.ui_state_manager.get_all_templates()
                await ws.send_text(json.dumps({
                    'type': 'ui_state_templates',
                    'templates': [{
                        'id': t.id,
                        'name': t.name,
                        'description': t.description
                    } for t in ui_state_templates]
                }, ensure_ascii=False))
            except Exception as e:
                print(f"⚠️  Error sending UI state templates: {e}")
    
    async def on_message(self, ws: WSClient, message: str):
        """
        处理客户端消息
        对应 TS: onMessage (websocket-handler.ts 第 191-340 行)
        """
        try:
            data: IncomingMessage = json.loads(message)
            msg_type = data.get('type')
            
            if msg_type == 'chat':
                await self._handle_chat_message(ws, data)
                
            elif msg_type == 'subscribe':
                await self._handle_subscribe(ws, data)
                
            elif msg_type == 'unsubscribe':
                await self._handle_unsubscribe(ws, data)
                
            elif msg_type == 'request_reports':
                await self._handle_request_reports(ws, data)
                
            elif msg_type == 'subscribe_report_analysis':
                await self._handle_subscribe_report_analysis(ws, data)
                
            elif msg_type == 'unsubscribe_report_analysis':
                await self._handle_unsubscribe_report_analysis(ws, data)
            
            elif msg_type == 'search':  # ✅ 添加搜索消息处理
                await self._handle_search_message(ws, data)
                
            else:
                await ws.send_text(json.dumps({
                    'type': 'error',
                    'error': f'Unknown message type: {msg_type}'
                }, ensure_ascii=False))
                
        except Exception as e:
            print(f"❌ WebSocket error: {e}")
            await ws.send_text(json.dumps({
                'type': 'error',
                'error': 'Failed to process message'
            }, ensure_ascii=False))
    
    async def on_close(self, ws: WSClient):
        """
        客户端断开事件
        对应 TS: onClose (websocket-handler.ts 第 342-361 行)
        """
        # 从 Session 中取消订阅
        if hasattr(ws, 'session_id') and ws.session_id:
            session = self.sessions.get(ws.session_id)
            if session:
                session.unsubscribe(ws)
            
            # 清理搜索会话  # ✅ 添加
            if ws.session_id in self.search_sessions:
                search_session = self.search_sessions[ws.session_id]
                await search_session.cleanup()
                del self.search_sessions[ws.session_id]
                print(f"🗑️  Cleaned up search session: {ws.session_id}")
        
        # 从客户端列表中移除
        client_id = None
        for cid, client in self.clients.items():
            if client == ws:
                client_id = cid
                break
        
        if client_id:
            del self.clients[client_id]
            print(f"🔌 WebSocket client disconnected: {client_id}")
        
        # 清理空 Session
        asyncio.create_task(self._cleanup_empty_sessions())
    
    # ==================== 消息处理 ====================
    
    async def _handle_chat_message(self, ws: WSClient, data: IncomingMessage):
        """
        处理聊天消息
        对应 TS: case 'chat' (websocket-handler.ts 第 196-213 行)
        """
        session_id = data.get('sessionId')
        content = data.get('content', '')
        new_conversation = data.get('newConversation', False)
        
        # 获取或创建 Session
        session = self._get_or_create_session(session_id)
        
        # 自动订阅发送者到该 Session
        if not hasattr(ws, 'session_id') or ws.session_id != session.id:
            session.subscribe(ws)
        
        # 是否开启新对话
        if new_conversation:
            await session.end_conversation()
        
        # 添加用户消息并流式响应
        await session.add_user_message(content)
    
    async def _handle_subscribe(self, ws: WSClient, data: IncomingMessage):
        """
        处理订阅请求
        对应 TS: case 'subscribe' (websocket-handler.ts 第 215-237 行)
        """
        session_id = data.get('sessionId')
        
        if not session_id:
            await ws.send_text(json.dumps({
                'type': 'error',
                'error': 'Missing sessionId'
            }, ensure_ascii=False))
            return
        
        session = self.sessions.get(session_id)
        if session:
            # 从当前 Session 取消订阅
            if hasattr(ws, 'session_id') and ws.session_id and ws.session_id != session_id:
                current_session = self.sessions.get(ws.session_id)
                if current_session:
                    current_session.unsubscribe(ws)
            
            # 订阅新 Session
            session.subscribe(ws)
            await ws.send_text(json.dumps({
                'type': 'subscribed',
                'sessionId': session_id
            }, ensure_ascii=False))
        else:
            await ws.send_text(json.dumps({
                'type': 'error',
                'error': 'Session not found'
            }, ensure_ascii=False))
    
    async def _handle_unsubscribe(self, ws: WSClient, data: IncomingMessage):
        """
        处理取消订阅
        对应 TS: case 'unsubscribe' (websocket-handler.ts 第 239-251 行)
        """
        session_id = data.get('sessionId')
        
        if not session_id:
            return
        
        session = self.sessions.get(session_id)
        if session:
            session.unsubscribe(ws)
            ws.session_id = None
            await ws.send_text(json.dumps({
                'type': 'unsubscribed',
                'sessionId': session_id
            }, ensure_ascii=False))
    
    async def _handle_request_reports(self, ws: WSClient, data: IncomingMessage):
        """
        处理请求报告列表
        对应 TS: case 'request_inbox' (websocket-handler.ts 第 253-261 行)
        """
        reports = await self._get_recent_reports()
        await ws.send_text(json.dumps({
            'type': 'reports_update',
            'reports': reports
        }, ensure_ascii=False))
    
    async def _handle_subscribe_report_analysis(self, ws: WSClient, data: IncomingMessage):
        """
        处理订阅报告分析请求
        """
        session_id = data.get('sessionId')
        
        if not session_id:
            await ws.send_text(json.dumps({
                'type': 'error',
                'error': 'Missing sessionId for report analysis subscription'
            }, ensure_ascii=False))
            return
        
        # 这里可以添加特定于报告分析订阅的逻辑
        # 例如：将客户端添加到报告分析更新的订阅列表
        await ws.send_text(json.dumps({
            'type': 'subscribed_report_analysis',
            'sessionId': session_id,
            'message': 'Successfully subscribed to report analysis updates'
        }, ensure_ascii=False))
    
    async def _handle_unsubscribe_report_analysis(self, ws: WSClient, data: IncomingMessage):
        """
        处理取消订阅报告分析请求
        """
        session_id = data.get('sessionId')
        
        if not session_id:
            return
        
        # 这里可以添加特定于报告分析取消订阅的逻辑
        await ws.send_text(json.dumps({
            'type': 'unsubscribed_report_analysis',
            'sessionId': session_id,
            'message': 'Successfully unsubscribed from report analysis updates'
        }, ensure_ascii=False))
    
    # ==================== 公开方法 ====================
    
    def get_active_sessions_count(self) -> int:
        """获取活动 Session 数量"""
        return len(self.sessions)
    
    def get_active_sessions(self) -> List[str]:
        """获取活动 Session ID 列表"""
        return list(self.sessions.keys())
    
    async def broadcast_report_analysis(self, report_id: str, title: str, analysis: Any, session_id: Optional[str] = None):
        """
        公共方法：广播报告分析更新
        可由监听器或其他模块调用
        """
        await self._broadcast_report_analysis_update(report_id, title, analysis, session_id)
    
    async def broadcast_alert(self, alert_id: str, title: str, message: str, severity: str = "info", data: Any = None, session_id: Optional[str] = None):
        """
        公共方法：广播预警触发消息
        可由监听器或其他模块调用
        """
        await self._broadcast_alert_triggered(alert_id, title, message, severity, data, session_id)
    
    async def _handle_search_message(self, ws: WSClient, data: IncomingMessage):
        """
        处理搜索消息
        
        Args:
            ws: WebSocket 客户端
            data: 搜索请求数据
        """
        # 检查 search_service 是否可用
        if not self.search_service:
            await ws.send_text(json.dumps({
                'type': 'search_error',
                'error': 'Search service not available',
                'message': '搜索服务未初始化'
            }, ensure_ascii=False))
            return
        
        try:
            query = data.get('query', '')
            session_id = data.get('session_id') or self._generate_session_id()
            limit = data.get('limit', 10)
            
            if not query:
                await ws.send_text(json.dumps({
                    'type': 'search_error',
                    'error': 'Query is required',
                    'message': '查询语句不能为空'
                }, ensure_ascii=False))
                return
            
            print(f"🔍 [WebSocketHandler] 接收搜索请求: {query} (session: {session_id})")
            
            # 获取或创建搜索会话
            if session_id not in self.search_sessions:
                from .search_session import SearchSession
                
                # 如果客户端传递了 session_id，说明是多轮对话，将其作为 resume_id
                resume_id = session_id if session_id and not session_id.startswith('session-') else None
                
                search_session = SearchSession(
                    websocket=ws,
                    search_service=self.search_service,
                    session_id=session_id,
                    resume_id=resume_id  # 传递 resume_id
                )
                self.search_sessions[session_id] = search_session
                print(f"🆕 [WebSocketHandler] 创建新搜索会话: {session_id} (resume: {resume_id})")
            else:
                search_session = self.search_sessions[session_id]
                print(f"♻️  [WebSocketHandler] 复用已有搜索会话: {session_id} (resume: {search_session.resume_id})")
            
            # 处理查询
            await search_session.handle_query(query, limit)
            
        except Exception as e:
            print(f"❌ [WebSocketHandler] 搜索消息处理失败: {e}")
            import traceback
            traceback.print_exc()
            await ws.send_text(json.dumps({
                'type': 'search_error',
                'error': str(e),
                'message': '搜索处理失败'
            }, ensure_ascii=False))
    
    async def cleanup(self):
        """清理所有资源"""
        await self.stop()
