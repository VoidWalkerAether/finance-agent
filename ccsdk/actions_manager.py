"""
ActionsManager - 动作执行系统

对应 TypeScript: email-agent/ccsdk/actions-manager.ts

核心功能:
1. 模板管理 - 自动加载 Action 模板
2. 实例注册 - 管理 Agent 创建的动作实例
3. 动作执行 - 执行用户触发的操作
4. 日志记录 - JSONL 格式的审计跟踪
5. 热重载 - 开发时自动重新加载
6. 上下文提供 - 为 handler 提供丰富能力
7. WebSocket 集成 - 与前端实时通信
"""

import os
import json
import asyncio
import importlib.util
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from dataclasses import asdict

from .message_types import (
    ActionTemplate, ActionInstance, ActionResult, ActionLogEntry
)
from database.database_manager import DatabaseManager

# 热重载功能（可选）
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileModifiedEvent
    WATCHDOG_AVAILABLE = True
except ImportError:
    Observer = None
    FileSystemEventHandler = None
    FileModifiedEvent = None
    WATCHDOG_AVAILABLE = False
    print("[警告] watchdog 未安装，热重载功能已禁用. 安装: pip install watchdog")


class ActionModule:
    """Action 模块包装"""
    def __init__(self, config: ActionTemplate, handler: Callable):
        self.config = config
        self.handler = handler


class ActionsManager:
    """
    ActionsManager - 动作执行引擎
    
    对应 TypeScript: ActionsManager (actions-manager.ts)
    """
    
    def __init__(
        self,
        database: DatabaseManager,
        ui_state_manager: Optional[Any] = None
    ):
        """
        初始化 ActionsManager
        
        Args:
            database: 数据库管理器
            ui_state_manager: UI 状态管理器（可选）
        """
        self.database = database
        self.ui_state_manager = ui_state_manager
        
        # Actions 目录
        self.actions_dir = os.path.join(os.getcwd(), "agent/custom_scripts/actions")
        self.logs_dir = os.path.join(os.getcwd(), "agent/custom_scripts/.logs/actions")
        
        # 模板存储 {template_id: ActionModule}
        self.templates: Dict[str, ActionModule] = {}
        
        # 实例存储 {instance_id: ActionInstance}
        self.instances: Dict[str, ActionInstance] = {}
        
        # 热重载监听器
        self._observer = None
        
        # 确保日志目录存在
        self._ensure_logs_dir()
        
        print(f"✅ ActionsManager 初始化完成")
    
    def _ensure_logs_dir(self):
        """确保日志目录存在"""
        if not os.path.exists(self.logs_dir):
            os.makedirs(self.logs_dir, exist_ok=True)
    
    # ==================== 模板管理 ====================
    
    async def load_all_templates(self) -> List[ActionTemplate]:
        """
        加载所有 Action 模板
        对应 TS: loadAllTemplates() (actions-manager.ts 第 38-59 行)
        
        Returns:
            List[ActionTemplate]: 加载的模板列表
        """
        self.templates.clear()
        
        try:
            if not os.path.exists(self.actions_dir):
                print("[ActionsManager] Actions 目录不存在，跳过加载")
                return []
            
            files = os.listdir(self.actions_dir)
            
            for file in files:
                if file.endswith('.py') and not file.startswith('_'):
                    await self._load_template(file)
        
        except Exception as e:
            print(f"❌ 加载 Action 模板时出错: {e}")
        
        templates = [module.config for module in self.templates.values()]
        print(f"[ActionsManager] 已加载 {len(templates)} 个 Action 模板")
        return templates
    
    async def _load_template(self, filename: str):
        """
        加载单个模板文件
        对应 TS: loadTemplate() (actions-manager.ts 第 64-82 行)
        
        Args:
            filename: 文件名
        """
        try:
            file_path = os.path.join(self.actions_dir, filename)
            
            # 动态导入模块
            spec = importlib.util.spec_from_file_location(
                f"actions.{filename[:-3]}",
                file_path
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # 验证模块结构
            if not hasattr(module, 'config') or not hasattr(module, 'handler'):
                print(f"⚠️  无效的 Action 模板 {filename}: 缺少 config 或 handler")
                return
            
            config = module.config
            handler = module.handler
            
            # 验证 config 类型
            if not isinstance(config, dict):
                print(f"⚠️  无效的 Action 模板 {filename}: config 必须是 dict")
                return
            
            # 转换为 ActionTemplate
            template = ActionTemplate(
                id=config['id'],
                name=config['name'],
                description=config.get('description', ''),
                icon=config.get('icon', '🚀'),
                parameterSchema=config.get('parameterSchema', {})
            )
            
            # 存储模板
            self.templates[template.id] = ActionModule(template, handler)
            print(f"[ActionsManager] ✓ 加载模板: {template.id} ({template.name})")
        
        except Exception as e:
            print(f"❌ 加载模板 {filename} 时出错: {e}")
            import traceback
            traceback.print_exc()
    
    def get_template(self, template_id: str) -> Optional[ActionTemplate]:
        """
        获取单个模板
        对应 TS: getTemplate() (actions-manager.ts 第 87-89 行)
        
        Args:
            template_id: 模板 ID
            
        Returns:
            Optional[ActionTemplate]: 模板配置，不存在则返回 None
        """
        module = self.templates.get(template_id)
        return module.config if module else None
    
    def get_all_templates(self) -> List[ActionTemplate]:
        """
        获取所有模板
        对应 TS: getAllTemplates() (actions-manager.ts 第 94-96 行)
        
        Returns:
            List[ActionTemplate]: 所有模板列表
        """
        return [module.config for module in self.templates.values()]
    
    # ==================== 实例管理 ====================
    
    def register_instance(self, instance: ActionInstance) -> None:
        """
        注册 Action 实例
        由 Agent 在对话中创建实例时调用
        对应 TS: registerInstance() (actions-manager.ts 第 101-103 行)
        
        Args:
            instance: Action 实例
        """
        self.instances[instance.instanceId] = instance
        print(f"[ActionsManager] 注册 Action 实例: {instance.instanceId} ({instance.label})")
    
    def get_instance(self, instance_id: str) -> Optional[ActionInstance]:
        """
        获取 Action 实例
        对应 TS: getInstance() (actions-manager.ts 第 108-110 行)
        
        Args:
            instance_id: 实例 ID
            
        Returns:
            Optional[ActionInstance]: 实例，不存在则返回 None
        """
        return self.instances.get(instance_id)
    
    # ==================== 动作执行 ====================
    
    async def execute_action(
        self,
        instance_id: str,
        context: 'ActionContext'
    ) -> ActionResult:
        """
        执行 Action
        对应 TS: executeAction() (actions-manager.ts 第 115-169 行)
        
        Args:
            instance_id: 实例 ID
            context: Action 上下文
            
        Returns:
            ActionResult: 执行结果
        """
        start_time = datetime.now()
        
        # 1. 查找实例
        instance = self.instances.get(instance_id)
        if not instance:
            return ActionResult(
                success=False,
                message="Action 实例不存在"
            )
        
        # 2. 查找模板
        template_module = self.templates.get(instance.templateId)
        if not template_module:
            return ActionResult(
                success=False,
                message=f"Action 模板 '{instance.templateId}' 不存在"
            )
        
        result: ActionResult
        error: Optional[str] = None
        
        try:
            # 3. 执行 handler
            context.log(f"执行 Action: {instance.label}")
            result = await template_module.handler(instance.params or {}, context)
            
            # 确保返回 ActionResult 类型
            if not isinstance(result, ActionResult):
                if isinstance(result, dict):
                    result = ActionResult(**result)
                else:
                    result = ActionResult(
                        success=True,
                        message="执行完成",
                        data=result
                    )
        
        except Exception as e:
            error = str(e)
            result = ActionResult(
                success=False,
                message=f"Action 执行失败: {error}"
            )
            context.log(f"Action 执行失败: {error}", "error")
            import traceback
            traceback.print_exc()
        
        # 4. 计算执行时间
        duration = int((datetime.now() - start_time).total_seconds() * 1000)
        
        # 5. 记录日志
        await self._log_execution(ActionLogEntry(
            timestamp=datetime.now().isoformat(),
            instanceId=instance.instanceId,
            templateId=instance.templateId,
            sessionId=instance.sessionId,
            params=instance.params or {},
            result=result,
            duration=duration,
            error=error
        ))
        
        return result
    
    async def _log_execution(self, entry: ActionLogEntry):
        """
        记录 Action 执行日志到 JSONL 文件
        对应 TS: logExecution() (actions-manager.ts 第 174-182 行)
        
        Args:
            entry: 日志条目
        """
        try:
            # 按日期分文件
            date = datetime.now().strftime('%Y-%m-%d')
            log_file = os.path.join(self.logs_dir, f"{date}.jsonl")
            
            # 转换为 dict（处理嵌套的 dataclass）
            log_data = {
                'timestamp': entry.timestamp,
                'instanceId': entry.instanceId,
                'templateId': entry.templateId,
                'sessionId': entry.sessionId,
                'params': entry.params,
                'result': {
                    'success': entry.result.success,
                    'message': entry.result.message,
                    'data': entry.result.data,
                    'components': entry.result.components
                },
                'duration': entry.duration,
                'error': entry.error
            }
            
            # 写入日志
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_data, ensure_ascii=False) + '\n')
        
        except Exception as e:
            print(f"❌ 记录 Action 日志失败: {e}")
    
    # ==================== 热重载 ====================
    
    async def watch_templates(self, on_change: Callable[[List[ActionTemplate]], None]):
        """
        监听 Action 模板文件变化并热重载
        对应 TS: watchTemplates() (actions-manager.ts 第 187-207 行)
        
        Args:
            on_change: 变化回调函数
        """
        if not WATCHDOG_AVAILABLE:
            print("[ActionsManager] 热重载功能不可用 (watchdog 未安装)")
            return
        
        if not os.path.exists(self.actions_dir):
            print("[ActionsManager] Actions 目录不存在，跳过监听")
            return
        
        class ActionTemplateHandler(FileSystemEventHandler):
            def __init__(handler_self, manager: 'ActionsManager'):
                handler_self.manager = manager
                handler_self.on_change = on_change
            
            def on_modified(handler_self, event):
                if event.src_path.endswith('.py'):
                    filename = os.path.basename(event.src_path)
                    print(f"[ActionsManager] 检测到文件变化: {filename}")
                    
                    # 重新加载所有模板
                    asyncio.create_task(handler_self._reload_templates())
            
            async def _reload_templates(handler_self):
                templates = await handler_self.manager.load_all_templates()
                handler_self.on_change(templates)
        
        # 创建观察者
        event_handler = ActionTemplateHandler(self)
        self._observer = Observer()
        self._observer.schedule(event_handler, self.actions_dir, recursive=False)
        self._observer.start()
        
        print(f"✅ ActionsManager 开始监听文件变化: {self.actions_dir}")
    
    def stop_watching(self):
        """停止监听文件变化"""
        if self._observer:
            self._observer.stop()
            self._observer.join()
            print("✅ ActionsManager 停止监听文件变化")
    
    # ==================== 统计信息 ====================
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            'total_templates': len(self.templates),
            'template_ids': list(self.templates.keys()),
            'total_instances': len(self.instances),
            'watching': self._observer is not None and self._observer.is_alive() if self._observer else False
        }
