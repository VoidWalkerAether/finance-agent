"""Listeners Manager - 管理插件加载、执行和热重载

对应 TypeScript: email-agent/ccsdk/listeners-manager.ts

核心功能:
1. 插件加载 - 扫描 agent/custom_scripts/listeners/ 目录
2. 事件触发 - check_event() 匹配并执行对应的 Listeners
3. 上下文注入 - 为 Listener 提供 ListenerContext (AI、数据库、通知等能力)
4. 热重载 - watchdog 监听文件变化，自动重新加载
5. 日志记录 - JSONL 格式记录执行日志
"""

import os
import sys
import importlib.util
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime
import asyncio

# watchdog 是可选依赖，用于热重载
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileModifiedEvent
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    print("[警告] watchdog 未安装,热重载功能已禁用. 安装: pip install watchdog")

from .message_types import (
    ListenerConfig,
    ListenerResult,
    ListenerLogEntry,
    EventType,
    NotifyOptions
)
from .log_writer import LogWriter
from .agent_tools import AgentTools

# 避免循环导入，使用 TYPE_CHECKING
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from database.database_manager import DatabaseManager


class ListenerContext:
    """
    Listener 上下文 - 提供给 Listener Handler 的能力
    对应 TypeScript: ListenerContext
    """
    
    def __init__(
        self,
        listener_config: Any,  # dict 或 ListenerConfig
        database: Any,  # DatabaseManager type
        agent_tools: AgentTools,
        notification_callback: Optional[Callable] = None,
        ui_state_manager: Optional[Any] = None
    ):
        self.listener_config = listener_config
        self.database = database
        self.agent_tools = agent_tools
        self.notification_callback = notification_callback
        self.ui_state_manager = ui_state_manager
        
        # 支持 dict 和 ListenerConfig
        self.listener_id = listener_config.get('id') if isinstance(listener_config, dict) else listener_config.id
        self.listener_name = listener_config.get('name') if isinstance(listener_config, dict) else listener_config.name
    
    async def notify(self, message: str, options: Optional[Any] = None) -> None:
        """
        发送通知到前端
        对应 TypeScript: notify()
        
        Args:
            message: 通知消息
            options: 通知选项（优先级等）- dict 或 NotifyOptions
        """
        # 支持 dict 和 NotifyOptions
        if isinstance(options, dict):
            priority = options.get('priority', 'normal')
        elif options:
            priority = options.priority
        else:
            priority = "normal"
        
        print(f"[ListenerContext] NOTIFY from {self.listener_id}:")
        print(f"  - Message: {message}")
        print(f"  - Priority: {priority}")
        
        if self.notification_callback:
            await self.notification_callback({
                'type': 'listener_notification',
                'listener_id': self.listener_id,
                'listener_name': self.listener_name,
                'priority': priority,
                'message': message,
                'timestamp': datetime.now().isoformat()
            })
    
    async def add_tag(self, report_id: str, tag: str) -> None:
        """
        给报告添加标签
        
        Args:
            report_id: 报告 ID
            tag: 标签名称
        """
        print(f"[ListenerContext] Adding tag '{tag}' to report {report_id}")
        # TODO: 实现数据库操作
        # await self.database.add_report_tag(report_id, tag)
    
    async def call_agent(self, prompt: str, schema: Dict[str, Any]) -> Any:
        """
        调用 AI 获取结构化输出
        对应 TypeScript: callAgent()
        
        Args:
            prompt: 提示词
            schema: JSON Schema
        
        Returns:
            结构化数据
        """
        print(f"[ListenerContext] callAgent() called by {self.listener_id}")
        return await self.agent_tools.call_agent(prompt, schema)
    
    @property
    def ui_state(self):
        """
        UI State 操作
        对应 TypeScript: uiState
        """
        class UIStateOps:
            def __init__(ctx_self, ui_manager):
                ctx_self.ui_manager = ui_manager
            
            async def get(ctx_self, state_id: str):
                """获取 UI State"""
                if not ctx_self.ui_manager:
                    print('[ListenerContext] UIStateManager not available')
                    return None
                return await ctx_self.ui_manager.get_state(state_id)
            
            async def set(ctx_self, state_id: str, data: Any):
                """设置 UI State"""
                if not ctx_self.ui_manager:
                    print('[ListenerContext] UIStateManager not available')
                    return
                await ctx_self.ui_manager.set_state(state_id, data)
            
            async def initialize_if_needed(ctx_self, state_id: str):
                """如果不存在则初始化"""
                if not ctx_self.ui_manager:
                    return False
                return await ctx_self.ui_manager.initialize_state_if_needed(state_id)
        
        return UIStateOps(self.ui_state_manager)
    
    def log(self, message: str, level: str = "info") -> None:
        """记录日志"""
        prefix = f"[{self.listener_id}]"
        if level == "error":
            print(f"❌ {prefix} {message}")
        elif level == "warn":
            print(f"⚠️  {prefix} {message}")
        else:
            print(f"✓ {prefix} {message}")


class ListenersManager:
    """
    Listeners 管理器
    对应 TypeScript: ListenersManager
    
    职责:
    1. 加载所有 Listener 插件
    2. 事件触发时执行匹配的 Listeners
    3. 提供上下文能力（AI、数据库、通知等）
    4. 热重载支持
    5. 执行日志记录
    """
    
    def __init__(
        self,
        database: Any,  # DatabaseManager type
        agent_tools: Optional[AgentTools] = None,
        notification_callback: Optional[Callable] = None,
        log_broadcast_callback: Optional[Callable] = None,
        ui_state_manager: Optional[Any] = None
    ):
        """
        初始化 ListenersManager
        
        Args:
            database: 数据库管理器
            agent_tools: Agent 工具（AI 调用）
            notification_callback: 通知回调函数
            log_broadcast_callback: 日志广播回调
            ui_state_manager: UI State 管理器（可选）
        """
        self.listeners_dir = os.path.join(os.getcwd(), "agent/custom_scripts/listeners")
        self.listeners: Dict[str, Dict[str, Any]] = {}
        self.database = database
        self.agent_tools = agent_tools or AgentTools()
        self.notification_callback = notification_callback
        self.log_broadcast_callback = log_broadcast_callback
        self.ui_state_manager = ui_state_manager
        self.log_writer = LogWriter(self.listeners_dir)
        self.watcher_active = False
        self.observer: Optional[Observer] = None
    
    async def load_all_listeners(self) -> List[ListenerConfig]:
        """
        加载所有 Listener 文件
        对应 TypeScript: loadAllListeners()
        
        Returns:
            Listener 配置列表
        """
        self.listeners.clear()
        
        try:
            # 确保目录存在
            Path(self.listeners_dir).mkdir(parents=True, exist_ok=True)
            
            # 扫描所有 .py 文件
            files = [f for f in os.listdir(self.listeners_dir) 
                    if f.endswith('.py') and not f.startswith('_') and not f.startswith('.')]
            
            for file in files:
                await self._load_listener(file)
            
            print(f"[ListenersManager] Loaded {len(self.listeners)} listener(s)")
        except Exception as e:
            print(f"[ListenersManager] Error loading listeners: {e}")
        
        return [l['config'] for l in self.listeners.values()]
    
    async def _load_listener(self, filename: str) -> None:
        """
        加载单个 Listener 文件
        对应 TypeScript: loadListener()
        
        Args:
            filename: 文件名（如 report_analyzer.py）
        """
        try:
            file_path = os.path.join(self.listeners_dir, filename)
            module_name = filename[:-3]  # 去掉 .py
            
            # 动态导入模块（支持热重载）
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if not spec or not spec.loader:
                print(f"[ListenersManager] Failed to load spec for {filename}")
                return
            
            module = importlib.util.module_from_spec(spec)
            
            # 清除缓存以支持热重载
            if module_name in sys.modules:
                del sys.modules[module_name]
            
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            
            # 验证模块导出
            if not hasattr(module, 'config') or not hasattr(module, 'handler'):
                print(f"[ListenersManager] Invalid listener {filename}: missing config or handler")
                return
            
            config = module.config
            
            # 只加载启用的 Listeners
            # config 可能是 dict 或 ListenerConfig 对象
            enabled = config.get('enabled', True) if isinstance(config, dict) else config.enabled
            
            if enabled:
                self.listeners[config['id'] if isinstance(config, dict) else config.id] = {
                    'config': config,
                    'handler': module.handler
                }
                listener_id = config['id'] if isinstance(config, dict) else config.id
                listener_name = config['name'] if isinstance(config, dict) else config.name
                print(f"[ListenersManager] ✓ Loaded listener: {listener_id} ({listener_name})")
            else:
                listener_id = config['id'] if isinstance(config, dict) else config.id
                print(f"[ListenersManager] ✗ Skipped disabled listener: {listener_id}")
        except Exception as e:
            print(f"[ListenersManager] Error loading listener {filename}: {e}")
            import traceback
            traceback.print_exc()
    
    def _create_context(self, listener_config: Any) -> ListenerContext:
        """
        创建 Listener 上下文对象
        对应 TypeScript: createContext()
        
        Args:
            listener_config: Listener 配置 (dict 或 ListenerConfig)
        
        Returns:
            ListenerContext 实例
        """
        return ListenerContext(
            listener_config=listener_config,
            database=self.database,
            agent_tools=self.agent_tools,
            notification_callback=self.notification_callback,
            ui_state_manager=self.ui_state_manager
        )
    
    async def check_event(self, event: EventType, data: Any) -> None:
        """
        检查事件并执行匹配的 Listeners
        对应 TypeScript: checkEvent()
        
        Args:
            event: 事件类型
            data: 事件数据
        """
        # 查找匹配的 Listeners
        matching_listeners = []
        for listener in self.listeners.values():
            config = listener['config']
            listener_event = config.get('event') if isinstance(config, dict) else config.event
            if listener_event == event:
                matching_listeners.append(listener)
        
        if not matching_listeners:
            return
        
        print(f"[ListenersManager] Triggering {len(matching_listeners)} listener(s) for event: {event}")
        
        # 执行每个 Listener
        for listener in matching_listeners:
            start_time = datetime.now()
            result: Optional[ListenerResult] = None
            error: Optional[Exception] = None
            
            config = listener['config']
            listener_id = config.get('id') if isinstance(config, dict) else config.id
            listener_name = config.get('name') if isinstance(config, dict) else config.name
            
            try:
                # 创建上下文
                context = self._create_context(config)
                
                # 执行 handler
                handler_result = await listener['handler'](data, context)
                
                # 如果 handler 返回结果，使用它；否则推断成功
                if handler_result:
                    # 支持 dict 和 ListenerResult 对象
                    if isinstance(handler_result, dict):
                        result = ListenerResult(
                            executed=handler_result.get('executed', True),
                            reason=handler_result.get('reason', 'Success'),
                            data=handler_result.get('data'),
                            actions=handler_result.get('actions')
                        )
                    else:
                        result = handler_result
                else:
                    result = ListenerResult(
                        executed=True,
                        reason="Listener completed successfully"
                    )
                
                print(f"[ListenersManager] ✓ {listener_id} executed successfully")
            except Exception as err:
                error = err
                print(f"[ListenersManager] ✗ {listener_id} failed: {error}")
                
                # 创建错误结果
                result = ListenerResult(
                    executed=False,
                    reason=f"Error: {str(error)}"
                )
            
            # 计算执行时间
            execution_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            # 创建日志条目
            log_entry = ListenerLogEntry(
                timestamp=datetime.now().isoformat(),
                report_id=data.get('report_id', 'unknown'),
                report_title=data.get('title', 'No title'),
                executed=result.executed if result else False,
                reason=result.reason if result else "",
                actions=result.actions if result else None,
                execution_time_ms=execution_time_ms,
                error=str(error) if error else None
            )
            
            # 异步写入日志文件（不阻塞）
            asyncio.create_task(
                self.log_writer.append_log(listener_id, log_entry)
            )
            
            # 广播日志（WebSocket）
            if self.log_broadcast_callback:
                await self.log_broadcast_callback({
                    **log_entry.__dict__,
                    'listener_id': listener_id,
                    'listener_name': listener_name
                })
    
    def get_all_listeners(self) -> List[ListenerConfig]:
        """
        获取所有 Listener 配置
        对应 TypeScript: getAllListeners()
        """
        return [l['config'] for l in self.listeners.values()]
    
    def get_listener(self, listener_id: str) -> Optional[Dict[str, Any]]:
        """
        获取指定 Listener
        对应 TypeScript: getListener()
        """
        return self.listeners.get(listener_id)
    
    async def watch_listeners(self, on_change: Callable[[List[ListenerConfig]], None]) -> None:
        """
        监听文件变化并热重载
        对应 TypeScript: watchListeners()
        
        Args:
            on_change: 文件变化时的回调函数
        """
        if not WATCHDOG_AVAILABLE:
            print("[ListenersManager] watchdog 未安装，无法启用热重载")
            return
        
        if self.watcher_active:
            print("[ListenersManager] File watcher already active")
            return
        
        try:
            self.watcher_active = True
            print(f"[ListenersManager] Watching {self.listeners_dir} for changes...")
            
            # 创建事件处理器
            class ListenerFileHandler(FileSystemEventHandler):
                def __init__(handler_self, manager):
                    handler_self.manager = manager
                
                def on_modified(handler_self, event):
                    if isinstance(event, FileModifiedEvent) and event.src_path.endswith('.py'):
                        filename = os.path.basename(event.src_path)
                        if not filename.startswith('_') and not filename.startswith('.'):
                            print(f"[ListenersManager] File modified: {filename}")
                            asyncio.create_task(handler_self._reload_listeners())
                
                async def _reload_listeners(handler_self):
                    print("[ListenersManager] Reloading listeners...")
                    listeners = await handler_self.manager.load_all_listeners()
                    await on_change(listeners)
            
            # 启动 watchdog 观察者
            event_handler = ListenerFileHandler(self)
            self.observer = Observer()
            self.observer.schedule(event_handler, self.listeners_dir, recursive=False)
            self.observer.start()
            
            print("[ListenersManager] File watcher started")
        except Exception as e:
            print(f"[ListenersManager] Error watching listeners: {e}")
            self.watcher_active = False
    
    def stop_watching(self) -> None:
        """停止文件监听"""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.watcher_active = False
            print("[ListenersManager] File watcher stopped")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取统计信息
        对应 TypeScript: getStats()
        """
        listeners = list(self.listeners.values())
        by_event: Dict[str, int] = {}
        
        for listener in listeners:
            event = listener['config'].event
            by_event[event] = by_event.get(event, 0) + 1
        
        return {
            'total': len(self.listeners),
            'by_event': by_event,
            'enabled': len([l for l in listeners if l['config'].enabled])
        }
    
    def get_log_writer(self) -> LogWriter:
        """
        获取日志写入器实例
        对应 TypeScript: getLogWriter()
        """
        return self.log_writer
