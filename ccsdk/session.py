"""
Session 类 - 管理单个 Claude 对话会话

对应 TypeScript: email-agent/ccsdk/session.ts

核心功能:
- 管理多轮对话(通过 sdk_session_id)
- 并发控制(queryPromise → asyncio.Lock)
- WebSocket 订阅管理
- 消息广播
"""

import asyncio
import json
import sys
from typing import Set, Optional, Any, Dict
from pathlib import Path

# 强制无缓冲输出（确保 print 日志立即显示）
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

from .ai_client import AIClient, AIQueryOptions
# 导入 SearchService 用于意图识别
from server.services.search_service import SearchService
from .message_types import (
    WSClient, SDKMessage, SDKUserMessage,
    WSAssistantMessage, WSToolUseMessage, WSToolResultMessage,
    WSResultMessage, WSSystemMessage, WSUserMessage, WSErrorMessage, WSSessionInfo
)

# 导入数据库管理器
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from database.database_manager import DatabaseManager


class Session:
    """
    Session 类 - 管理单个 Claude 对话会话
    
    对应 TypeScript: Session (session.ts 第 8-207 行)
    
    核心属性:
    - id: 会话唯一标识
    - sdk_session_id: Claude SDK 的会话 ID(用于多轮对话)
    - query_lock: asyncio.Lock 并发控制(对应 TS 的 queryPromise)
    - subscribers: WebSocket 客户端集合
    - message_count: 消息计数器
    """
    
    def __init__(
        self,
        session_id: str,
        db: Optional[DatabaseManager] = None,
        ui_state_manager: Optional[Any] = None
    ):
        """
        初始化会话
        
        对应 TypeScript: constructor() (session.ts 第 18-23 行)
        
        Args:
            session_id: 会话唯一标识
            db: 数据库管理器实例(可选)
            ui_state_manager: UI 状态管理器(可选)
        """
        self.id = session_id
        self.db = db or DatabaseManager()
        self.ui_state_manager = ui_state_manager
        
        # 并发控制 (对应 TS 的 queryPromise)
        self._query_lock = asyncio.Lock()
        self._is_querying = False
        
        # WebSocket 订阅者
        self.subscribers: Set[WSClient] = set()
        
        # 消息计数
        self.message_count = 0
        
        # AI 客户端
        self.ai_client = AIClient()
        
        # 初始化 SearchService 用于意图识别
        self.search_service = SearchService(self.db)
        
        # SDK 会话 ID (用于多轮对话)
        self.sdk_session_id: Optional[str] = None
        
        print(f"✅ Session 创建: {self.id}")
    
    async def add_user_message(self, content: str) -> None:
        """
        处理单个用户消息
        
        对应 TypeScript: addUserMessage() (session.ts 第 26-66 行)
        
        核心逻辑:
        1. 等待之前的查询完成(并发控制)
        2. 根据是否有 sdk_session_id 决定 resume 或新对话
        3. 流式处理 AI 响应
        4. 广播消息到所有订阅者
        5. 捕获 SDK session ID 用于多轮对话
        
        Args:
            content: 用户消息内容
        """
        # 并发控制: 等待之前的查询完成
        # 对应 TS: if (this.queryPromise) await this.queryPromise;
        async with self._query_lock:
            self._is_querying = True  # ⚠️ P1 修复: 设置查询状态
            self.message_count += 1
            print(f"\n{'='*60}")
            print(f"📨 [Session] 处理消息 #{self.message_count} in session {self.id}")
            print(f"📝 [Session] 用户问题: {content[:100]}..." if len(content) > 100 else f"📝 [Session] 用户问题: {content}")
            print(f"{'='*60}\n")
            
            try:
                # 多轮对话: 使用 resume 恢复会话
                # 对应 TS: const options = this.sdkSessionId ? { resume: this.sdkSessionId } : {};
                options: Dict[str, Any] = {}
                if self.sdk_session_id:
                    options['resume'] = self.sdk_session_id
                    print(f"🔄 [Session] 恢复会话: {self.sdk_session_id}")
                else:
                    print(f"🆕 [Session] 创建新会话")
                
                # 1. 意图识别 (拦截 WebSocket 消息并分类)
                print(f"🔍 [Session {self.id}] 正在识别用户意图...")
                intent_data = await self.search_service.classify_intent(content)
                intent = intent_data.get("intent", "GENERAL")
                
                # 2. 根据意图定制系统提示词
                if intent == "PORTFOLIO":
                    print(f"📊 [Session {self.id}] 识别为 PORTFOLIO 意图，切换至审计模式")
                    # 动态覆盖 system_prompt，绕过“研报助手”强制搜研报的协议
                    options["system_prompt"] = "你是一个专业的私人财富管理顾问。当用户询问组合是否合规或检查持仓风险时，请优先使用 audit-portfolio 技能进行审计。请输出结构化的审计结论。"
                    # 显式继承并允许 Skill 工具
                    options["allowed_tools"] = self.ai_client.default_options.allowed_tools
                
                print(f"🚀 [Session] 开始调用 AI 客户端流式查询...")
                message_count = 0
                
                # 流式查询 AI
                # 对应 TS: for await (const message of this.aiClient.queryStream(...))
                async for message in self.ai_client.query_stream(content, options):
                    message_count += 1
                    print(f"📦 [Session] 收到消息 #{message_count}, 类型: {message.type}")
                    
                    # 广播消息到所有订阅者
                    await self._broadcast_to_subscribers(message)
                    
                    # 捕获 SDK session ID
                    # 对应 TS: if (message.type === 'system' && message.subtype === 'init')
                    if message.type == 'system' and message.subtype == 'init':
                        print(f"🔑 [Session] 系统消息详情: {message.__dict__}")
                        session_id = getattr(message, 'session_id', None)
                        if session_id:
                            self.sdk_session_id = session_id
                            print(f"🔑 [Session] 捕获 SDK session ID: {self.sdk_session_id}")
                        else:
                            print(f"⚠️  [Session] SystemMessage 中没有 session_id!")
                    
                    # 检查对话是否结束
                    # 对应 TS: if (message.type === 'result')
                    if message.type == 'result':
                        print(f"✅ [Session] 结果已接收, 共收到 {message_count} 条消息")
                        print(f"✅ [Session] 准备接收下一条用户消息\n")
            
            except Exception as error:
                print(f"❌ Session {self.id} 错误: {error}")
                await self._broadcast_error(f"查询失败: {str(error)}")
            
            finally:
                self._is_querying = False  # ⚠️ P1 修复: 清除查询状态
    
    def subscribe(self, client: WSClient) -> None:
        """
        订阅 WebSocket 客户端到此会话
        
        对应 TypeScript: subscribe() (session.ts 第 69-80 行)
        
        Args:
            client: WebSocket 客户端
        """
        self.subscribers.add(client)
        client.session_id = self.id
        
        # 发送会话信息给新订阅者
        # 对应 TS: client.send(JSON.stringify({ type: 'session_info', ... }))
        session_info = WSSessionInfo(
            type='session_info',
            session_id=self.id,
            message_count=self.message_count,
            is_active=self._is_querying
        )
        
        asyncio.create_task(client.send_text(json.dumps(session_info.__dict__)))
        print(f"📥 客户端订阅会话: {self.id}")
    
    def unsubscribe(self, client: WSClient) -> None:
        """
        取消订阅 WebSocket 客户端
        
        对应 TypeScript: unsubscribe() (session.ts 第 83-85 行)
        
        Args:
            client: WebSocket 客户端
        """
        self.subscribers.discard(client)
        print(f"📤 客户端取消订阅会话: {self.id}")
    
    async def _broadcast_to_subscribers(self, message: SDKMessage) -> None:
        """
        广播消息到所有订阅者
        
        对应 TypeScript: broadcastToSubscribers() (session.ts 第 88-169 行)
        
        核心逻辑:
        1. 解析 SDK 消息类型
        2. 转换为 WebSocket 消息格式
        3. 广播到所有订阅者
        
        Args:
            message: SDK 消息
        """
        ws_message: Optional[Any] = None
        
        # 处理助手消息
        # 对应 TS: if (message.type === "assistant")
        if message.type == "assistant":
            content = message.content
            print(f"  🤖 [Broadcast] 助手消息, content 类型: {type(content).__name__}")
            
            # 文本内容
            if isinstance(content, str):
                print(f"  💬 [Broadcast] 文本内容: {content[:50]}..." if len(content) > 50 else f"  💬 [Broadcast] 文本内容: {content}")
                ws_message = WSAssistantMessage(
                    type='assistant_message',
                    content=content,
                    session_id=self.id
                )
            
            # 内容块数组
            elif isinstance(content, list):
                print(f"  📦 [Broadcast] 内容块数组, 共 {len(content)} 个 block")
                for i, block in enumerate(content, 1):
                    block_msg = None
                    
                    # 确保 block 是字典类型
                    if not isinstance(block, dict):
                        print(f"  ⚠️  [Broadcast] 跳过非字典类型的 block #{i}: {type(block)}")
                        continue
                    
                    block_type = block.get('type')
                    print(f"  ├─ Block #{i}: type={block_type}")
                    
                    if block_type == 'text':
                        text = block.get('text', '')
                        print(f"  │  💬 文本: {text[:50]}..." if len(text) > 50 else f"  │  💬 文本: {text}")
                        block_msg = WSAssistantMessage(
                            type='assistant_message',
                            content=text,
                            session_id=self.id
                        )
                    
                    elif block_type == 'tool_use':
                        # ⚠️ 工具调用不广播到前端（中间过程，用户不需要看到）
                        tool_name = block.get('name', '')
                        tool_input = block.get('input', {})
                        print(f"  │  🔧 工具调用: {tool_name}")
                        print(f"  │  📝 参数: {json.dumps(tool_input, ensure_ascii=False)[:100]}...")
                        print(f"  │  🚫 [跳过广播] 工具调用不发送到前端")
                        # 跳过广播，不创建 block_msg
                        continue
                    
                    elif block_type == 'tool_result':
                        # ⚠️ 工具结果不广播到前端（中间过程，用户不需要看到）
                        tool_use_id = block.get('tool_use_id', '')
                        is_error = block.get('is_error', False)
                        result_content = str(block.get('content', ''))[:100]
                        print(f"  │  ✅ 工具结果: {tool_use_id[:20]}... (错误={is_error})")
                        print(f"  │  📊 结果: {result_content}...")
                        print(f"  │  🚫 [跳过广播] 工具结果不发送到前端")
                        # 跳过广播，不创建 block_msg
                        continue
                    
                    if block_msg:
                        await self._broadcast(block_msg.__dict__)
                
                return  # 已经逐块广播,不需要继续
        
        # 处理结果消息
        # 对应 TS: else if (message.type === "result")
        elif message.type == "result":
            print(f"  🏁 [Broadcast] 结果消息, subtype={message.subtype}")
            if message.subtype == "success":
                print(f"  ✅ [Broadcast] 成功! 耗时={message.duration_ms}ms, 成本=${message.total_cost_usd}")
                ws_message = WSResultMessage(
                    type='result',
                    success=True,
                    result=message.result,
                    cost=message.total_cost_usd,
                    duration=message.duration_ms,
                    session_id=self.id
                )
            else:
                print(f"  ❌ [Broadcast] 失败: {message.subtype}")
                ws_message = WSResultMessage(
                    type='result',
                    success=False,
                    error=message.subtype,
                    session_id=self.id
                )
        
        # 处理系统消息
        # 对应 TS: else if (message.type === "system")
        elif message.type == "system":
            print(f"  ⚙️  [Broadcast] 系统消息, subtype={message.subtype}")
            ws_message = WSSystemMessage(
                type='system',
                subtype=message.subtype,
                session_id=self.id,
                data=message.data
            )
        
        # 处理用户消息(回显)
        # 对应 TS: else if (message.type === "user")
        elif message.type == "user":
            content = str(message.content)
            
            # ⚠️ 检查内容是否包含工具对象（防御性编程）
            if 'ToolResultBlock' in content or 'ToolUseBlock' in content or 'tool_use_id' in content:
                print(f"  🚫 [Broadcast] UserMessage 包含工具对象信息，跳过广播: {content[:100]}...")
                return  # 直接返回，不广播
            
            print(f"  👤 [Broadcast] 用户消息回显: {content[:50]}..." if len(content) > 50 else f"  👤 [Broadcast] 用户消息回显: {content}")
            ws_message = WSUserMessage(
                type='user_message',
                content=content,
                session_id=self.id
            )
        
        # 广播消息
        if ws_message:
            print(f"  📡 [Broadcast] 广播消息类型: {ws_message.type} 给 {len(self.subscribers)} 个客户端")
            await self._broadcast(ws_message.__dict__)
    
    async def _broadcast(self, message: Dict[str, Any]) -> None:
        """
        广播消息到所有订阅者
        
        对应 TypeScript: broadcast() (session.ts 第 171-181 行)
        
        Args:
            message: 消息字典
        """
        message_str = json.dumps(message)
        
        # 创建广播任务列表
        tasks = []
        dead_clients = []
        
        for client in self.subscribers:
            try:
                tasks.append(client.send_text(message_str))
            except Exception as error:
                print(f'❌ 广播错误: {error}')
                dead_clients.append(client)
        
        # 执行所有广播任务
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        # 清理失效客户端
        for client in dead_clients:
            self.subscribers.discard(client)
    
    async def _broadcast_error(self, error: str) -> None:
        """
        广播错误消息
        
        对应 TypeScript: broadcastError() (session.ts 第 183-189 行)
        
        Args:
            error: 错误信息
        """
        error_msg = WSErrorMessage(
            type='error',
            error=error,
            session_id=self.id
        )
        await self._broadcast(error_msg.__dict__)
    
    def has_subscribers(self) -> bool:
        """
        检查会话是否有订阅者
        
        对应 TypeScript: hasSubscribers() (session.ts 第 192-194 行)
        
        Returns:
            bool: 是否有订阅者
        """
        return len(self.subscribers) > 0
    
    async def cleanup(self) -> None:
        """
        清理会话资源
        
        对应 TypeScript: cleanup() (session.ts 第 197-200 行)
        """
        self.subscribers.clear()
        print(f"🧹 会话清理: {self.id}")
    
    def end_conversation(self) -> None:
        """
        结束当前对话(开始新对话)
        
        对应 TypeScript: endConversation() (session.ts 第 203-206 行)
        """
        self.sdk_session_id = None
        self._is_querying = False  # ⚠️ P1 修复: 重置查询状态
        print(f"🔚 结束对话: {self.id}")
