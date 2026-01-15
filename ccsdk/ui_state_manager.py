"""UIStateManager - UI 状态管理器

对应 TypeScript: email-agent/ccsdk/ui-state-manager.ts

核心功能:
1. 模板发现 - 扫描 agent/custom_scripts/ui-states/ 目录
2. 热重载 - watchdog 监听文件变化,自动重新加载
3. 数据库操作 - 持久化状态到 SQLite
4. 日志记录 - JSONL 格式记录所有状态更新
5. 广播更新 - 通知订阅者状态变化 (WebSocket)
"""

import os
import sys
import importlib.util
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any, Set
from datetime import datetime
import asyncio
import json

# 热重载功能是可选的,如果未安装 watchdog 则禁用
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileModifiedEvent
    WATCHDOG_AVAILABLE = True
except ImportError:
    Observer = None
    FileSystemEventHandler = None
    FileModifiedEvent = None
    WATCHDOG_AVAILABLE = False
    print("[警告] watchdog 未安装,热重载功能已禁用. 安装: pip install watchdog")

from .message_types import UIStateTemplate, UIStateLogEntry
from database.database_manager import DatabaseManager


class UIStateManager:
    """
    UI State 管理器
    对应 TypeScript: UIStateManager
    
    职责:
    1. 加载所有 UI State 模板
    2. 提供状态 CRUD 操作 (get/set/delete)
    3. 持久化状态到数据库
    4. 广播状态更新到订阅者
    5. 热重载支持
    6. 审计日志记录
    """
    
    def __init__(
        self,
        database: DatabaseManager,
        update_callback: Optional[Callable[[str, Any], None]] = None
    ):
        """
        初始化 UIStateManager
        
        Args:
            database: 数据库管理器
            update_callback: 状态更新回调函数 (用于 WebSocket 广播)
        """
        self.ui_states_dir = os.path.join(os.getcwd(), "agent/custom_scripts/ui-states")
        self.logs_dir = os.path.join(os.getcwd(), "agent/custom_scripts/.logs/ui-states")
        self.templates: Dict[str, UIStateTemplate] = {}
        self.update_callbacks: Set[Callable[[str, Any], None]] = set()
        self.database = database
        self.watcher_active = False
        self.observer: Optional[Observer] = None
        
        # 注册更新回调
        if update_callback:
            self.update_callbacks.add(update_callback)
        
        # 确保日志目录存在
        self._ensure_logs_dir()
    
    def _ensure_logs_dir(self):
        """确保日志目录存在"""
        Path(self.logs_dir).mkdir(parents=True, exist_ok=True)
    
    # ============================================================================
    # 模板管理
    # ============================================================================
    
    async def load_all_templates(self) -> List[UIStateTemplate]:
        """
        加载所有 UI State 模板
        对应 TypeScript: loadAllTemplates()
        
        Returns:
            List[UIStateTemplate]: 模板配置列表
        """
        self.templates.clear()
        
        try:
            # 确保目录存在
            Path(self.ui_states_dir).mkdir(parents=True, exist_ok=True)
            
            # 扫描所有 .py 文件
            files = [f for f in os.listdir(self.ui_states_dir) 
                    if f.endswith('.py') and not f.startswith('_') and not f.startswith('.')]
            
            for file in files:
                await self._load_template(file)
            
            print(f"[UIStateManager] Loaded {len(self.templates)} UI state template(s)")
        except Exception as e:
            print(f"[UIStateManager] Error loading templates: {e}")
        
        return list(self.templates.values())
    
    async def _load_template(self, filename: str) -> None:
        """
        加载单个模板文件
        对应 TypeScript: loadTemplate()
        
        Args:
            filename: 文件名 (如 portfolio_dashboard.py)
        """
        try:
            file_path = os.path.join(self.ui_states_dir, filename)
            module_name = filename[:-3]  # 去掉 .py
            
            # 动态导入模块 (支持热重载)
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if not spec or not spec.loader:
                print(f"[UIStateManager] Failed to load spec for {filename}")
                return
            
            module = importlib.util.module_from_spec(spec)
            
            # 清除缓存以支持热重载
            if module_name in sys.modules:
                del sys.modules[module_name]
            
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            
            # 验证模板导出
            if not hasattr(module, 'config'):
                print(f"[UIStateManager] Invalid template {filename}: missing config")
                return
            
            config = module.config
            
            # 验证必需字段
            if not isinstance(config, dict) or 'id' not in config or 'initialState' not in config:
                print(f"[UIStateManager] Invalid template {filename}: missing id or initialState")
                return
            
            # 转换为 UIStateTemplate 对象
            template = UIStateTemplate(
                id=config['id'],
                name=config.get('name', config['id']),
                description=config.get('description', ''),
                initialState=config['initialState']
            )
            
            self.templates[template.id] = template
            print(f"[UIStateManager] ✓ Loaded template: {template.id} ({template.name})")
            
        except Exception as e:
            print(f"[UIStateManager] Error loading template {filename}: {e}")
            import traceback
            traceback.print_exc()
    
    def get_template(self, template_id: str) -> Optional[UIStateTemplate]:
        """
        获取指定模板
        对应 TypeScript: getTemplate()
        """
        return self.templates.get(template_id)
    
    def get_all_templates(self) -> List[UIStateTemplate]:
        """
        获取所有模板
        对应 TypeScript: getAllTemplates()
        """
        return list(self.templates.values())
    
    # ============================================================================
    # 状态 CRUD 操作
    # ============================================================================
    
    async def get_state(self, state_id: str) -> Optional[Any]:
        """
        获取 UI 状态
        对应 TypeScript: getState()
        
        Args:
            state_id: 状态 ID
        
        Returns:
            Any: 状态数据,如果不存在则返回模板的 initialState
        """
        try:
            # 1. 尝试从数据库获取
            result = self.database.get_ui_state(state_id)
            
            if result is not None:
                return result
            
            # 2. 如果数据库没有,返回模板的 initialState
            template = self.templates.get(state_id)
            if template:
                return template.initialState
            
            return None
            
        except Exception as e:
            print(f"[UIStateManager] Error getting state {state_id}: {e}")
            return None
    
    async def set_state(self, state_id: str, data: Any) -> None:
        """
        设置/更新 UI 状态
        对应 TypeScript: setState()
        
        Args:
            state_id: 状态 ID
            data: 状态数据
        """
        try:
            # 1. 保存到数据库
            await self.database.set_ui_state(state_id, data)
            
            # 2. 记录日志
            await self._log_state_update(state_id, data)
            
            # 3. 通知所有订阅者 (WebSocket 广播)
            self._notify_state_update(state_id, data)
            
            print(f"[UIStateManager] ✓ State updated: {state_id}")
            
        except Exception as e:
            print(f"[UIStateManager] Error setting state {state_id}: {e}")
            raise
    
    async def list_states(self) -> List[Dict[str, str]]:
        """
        列出所有 UI 状态
        对应 TypeScript: listStates()
        
        Returns:
            List[Dict]: [{'stateId': '...', 'updatedAt': '...'}]
        """
        try:
            return await self.database.list_ui_states()
        except Exception as e:
            print(f"[UIStateManager] Error listing states: {e}")
            return []
    
    async def delete_state(self, state_id: str) -> None:
        """
        删除 UI 状态
        对应 TypeScript: deleteState()
        
        Args:
            state_id: 状态 ID
        """
        try:
            await self.database.delete_ui_state(state_id)
            print(f"[UIStateManager] ✓ State deleted: {state_id}")
        except Exception as e:
            print(f"[UIStateManager] Error deleting state {state_id}: {e}")
            raise
    
    async def initialize_state_if_needed(self, state_id: str) -> bool:
        """
        如果状态不存在,使用模板初始化
        对应 TypeScript: initializeStateIfNeeded()
        
        Args:
            state_id: 状态 ID
        
        Returns:
            bool: True 表示已初始化,False 表示已存在或无模板
        """
        try:
            # 1. 检查是否已存在
            existing = await self.get_state(state_id)
            if existing is not None:
                return False  # 已存在
            
            # 2. 查找模板
            template = self.templates.get(state_id)
            if not template:
                print(f"[UIStateManager] No template found for state: {state_id}")
                return False
            
            # 3. 使用 initialState 初始化
            await self.set_state(state_id, template.initialState)
            print(f"[UIStateManager] ✓ Initialized state: {state_id}")
            return True
            
        except Exception as e:
            print(f"[UIStateManager] Error initializing state {state_id}: {e}")
            return False
    
    # ============================================================================
    # 订阅和广播
    # ============================================================================
    
    def on_state_update(self, callback: Callable[[str, Any], None]) -> Callable[[], None]:
        """
        订阅状态更新
        对应 TypeScript: onStateUpdate()
        
        Args:
            callback: 回调函数 (stateId, data) => void
        
        Returns:
            Callable: 取消订阅函数
        """
        self.update_callbacks.add(callback)
        
        # 返回取消订阅函数
        def unsubscribe():
            self.update_callbacks.discard(callback)
        
        return unsubscribe
    
    def _notify_state_update(self, state_id: str, data: Any) -> None:
        """
        通知所有订阅者状态更新
        对应 TypeScript: notifyStateUpdate()
        
        Args:
            state_id: 状态 ID
            data: 状态数据
        """
        for callback in self.update_callbacks:
            try:
                callback(state_id, data)
            except Exception as e:
                print(f"[UIStateManager] Error in update callback: {e}")
    
    # ============================================================================
    # 日志记录
    # ============================================================================
    
    async def _log_state_update(self, state_id: str, data: Any) -> None:
        """
        记录状态更新到 JSONL 文件
        对应 TypeScript: logStateUpdate()
        
        Args:
            state_id: 状态 ID
            data: 状态数据
        """
        try:
            date = datetime.now().strftime("%Y-%m-%d")
            log_file = os.path.join(self.logs_dir, f"{date}.jsonl")
            
            log_entry = UIStateLogEntry(
                timestamp=datetime.now().isoformat(),
                stateId=state_id,
                action="update",
                dataSize=len(json.dumps(data, ensure_ascii=False))
            )
            
            # 异步写入日志
            async def write_log():
                with open(log_file, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(log_entry.__dict__, ensure_ascii=False) + '\n')
            
            await write_log()
            
        except Exception as e:
            print(f"[UIStateManager] Failed to log state update: {e}")
    
    # ============================================================================
    # 热重载
    # ============================================================================
    
    async def watch_templates(self, on_change: Callable[[List[UIStateTemplate]], None]) -> None:
        """
        监听模板文件变化并热重载
        对应 TypeScript: watchTemplates()
        
        Args:
            on_change: 文件变化时的回调函数
        """
        if not WATCHDOG_AVAILABLE:
            print("[UIStateManager] 热重载功能不可用 (watchdog 未安装)")
            return
        
        if self.watcher_active:
            print("[UIStateManager] File watcher already active")
            return
        
        try:
            self.watcher_active = True
            print(f"[UIStateManager] Watching {self.ui_states_dir} for changes...")
            
            # 创建事件处理器
            class UIStateFileHandler(FileSystemEventHandler):
                def __init__(handler_self, manager):
                    handler_self.manager = manager
                
                def on_modified(handler_self, event):
                    if isinstance(event, FileModifiedEvent) and event.src_path.endswith('.py'):
                        filename = os.path.basename(event.src_path)
                        if not filename.startswith('_') and not filename.startswith('.'):
                            print(f"[UIStateManager] File modified: {filename}")
                            asyncio.create_task(handler_self._reload_templates())
                
                async def _reload_templates(handler_self):
                    print("[UIStateManager] Reloading templates...")
                    templates = await handler_self.manager.load_all_templates()
                    await on_change(templates)
            
            # 启动 watchdog 观察者
            event_handler = UIStateFileHandler(self)
            self.observer = Observer()
            self.observer.schedule(event_handler, self.ui_states_dir, recursive=False)
            self.observer.start()
            
            print("[UIStateManager] File watcher started")
            
        except Exception as e:
            print(f"[UIStateManager] Error watching templates: {e}")
            self.watcher_active = False
    
    def stop_watching(self) -> None:
        """停止文件监听"""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.watcher_active = False
            print("[UIStateManager] File watcher stopped")
    
    # ============================================================================
    # 工具方法
    # ============================================================================
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取统计信息
        对应 TypeScript: getStats()
        """
        return {
            'total_templates': len(self.templates),
            'template_ids': list(self.templates.keys()),
            'watching': self.watcher_active
        }
