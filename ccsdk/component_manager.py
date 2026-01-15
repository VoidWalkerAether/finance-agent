"""
ComponentManager - Finance Agent 组件管理系统

负责:
- 文件基础的组件模板发现 (agent/custom_scripts/components/)
- 热重载 (当模板文件更改时)
- 组件实例注册
- 实例生命周期管理
- 与UIStateManager和WebSocketHandler集成
"""

import asyncio
import json
import os
import importlib.util
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime

from .message_types import (
    UIStateTemplate,
    ActionTemplate,
    ActionInstance,
    ActionResult,
    ListenerResult,
    WSUIStateUpdateMessage,
    UIStateLogEntry,
    ComponentTemplate,
    ComponentInstance,
    ComponentLogEntry,
    WSComponentInstanceMessage,
    WSComponentUpdateMessage
)
from .ui_state_manager import UIStateManager
from database.database_manager import DatabaseManager


class ComponentManager:
    """
    ComponentManager 处理:
    - 文件基础的组件模板发现 (agent/custom_scripts/components/)
    - 热重载 (当模板文件更改时)
    - 组件实例注册
    - 实例生命周期管理
    """
    
    def __init__(self, db: DatabaseManager, ui_state_manager: UIStateManager):
        self.components_dir = Path("agent/custom_scripts/components")
        self.templates: Dict[str, ComponentTemplate] = {}
        self.instances: Dict[str, ComponentInstance] = {}
        self.db = db
        self.ui_state_manager = ui_state_manager
        
        # 确保目录存在
        self.components_dir.mkdir(parents=True, exist_ok=True)
        
        # 热重载相关
        self.watcher_task = None
        self.watcher_callback = None

    async def load_all_templates(self) -> List[ComponentTemplate]:
        """
        从目录加载所有组件模板
        """
        self.templates.clear()
        
        try:
            if not self.components_dir.exists():
                print("Components directory does not exist yet, will be created on first template")
                self.components_dir.mkdir(parents=True, exist_ok=True)
                return []
            
            files = [f for f in self.components_dir.iterdir() 
                    if f.is_file() and (f.suffix in ['.py', '.ts', '.tsx']) and not f.name.startswith('_')]
            
            for file in files:
                await self.load_template(file.name)
                
        except Exception as error:
            print(f"Error loading component templates: {error}")
        
        return list(self.templates.values())

    async def load_template(self, filename: str):
        """
        加载单个模板文件
        """
        try:
            file_path = self.components_dir / filename
            
            # 为Python文件加载模块
            if file_path.suffix == '.py':
                spec = importlib.util.spec_from_file_location("component_module", file_path)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    if hasattr(module, 'config') and isinstance(module.config, dict):
                        config = module.config
                        if config.get('id') and config.get('stateId'):
                            template = ComponentTemplate(
                                id=config['id'],
                                name=config.get('name', config['id']),
                                description=config.get('description', ''),
                                stateId=config['stateId']
                            )
                            self.templates[config['id']] = template
                            print(f"✓ Loaded component template: {config['id']}")
                        else:
                            print(f"⚠ Invalid component template {filename}: missing id or stateId in config")
                    else:
                        print(f"⚠ Invalid component template {filename}: missing config")
            else:
                # 对于TypeScript文件，我们目前暂时跳过，因为Python无法直接加载
                print(f"⚠ Skipping non-Python component file: {filename}")
                
        except Exception as error:
            print(f"✗ Error loading component template {filename}: {error}")

    def get_template(self, id: str) -> Optional[ComponentTemplate]:
        """
        通过ID获取模板
        """
        return self.templates.get(id)

    def get_all_templates(self) -> List[ComponentTemplate]:
        """
        获取所有模板
        """
        return list(self.templates.values())

    async def register_instance(self, instance: ComponentInstance) -> None:
        """
        注册组件实例
        """
        # 存储在内存中
        self.instances[instance.instanceId] = instance
        
        # 存储在数据库中
        try:
            await self.db.create_component_instance(
                instance_id=instance.instanceId,
                component_id=instance.componentId,
                state_id=instance.stateId,
                session_id=instance.sessionId
            )
            print(f"✓ Registered component instance: {instance.componentId} ({instance.instanceId})")
        except Exception as error:
            print(f"Error registering component instance: {error}")

    def get_instance(self, instance_id: str) -> Optional[ComponentInstance]:
        """
        通过ID获取组件实例
        """
        return self.instances.get(instance_id)

    async def get_instances_by_session(self, session_id: str) -> List[ComponentInstance]:
        """
        获取会话的所有实例
        """
        try:
            db_instances = await self.db.get_component_instances_by_session(session_id)
            result = []
            for db_instance in db_instances:
                instance = ComponentInstance(
                    instanceId=db_instance['instance_id'],
                    componentId=db_instance['component_id'],
                    stateId=db_instance['state_id'],
                    sessionId=db_instance['session_id']
                )
                result.append(instance)
            return result
        except Exception as error:
            print(f"Error getting component instances for session: {error}")
            return []

    async def create_instance(
        self,
        component_id: str,
        session_id: str,
        state_id: str,
        props: Optional[Dict[str, Any]] = None
    ) -> ComponentInstance:
        """
        创建组件实例
        """
        from uuid import uuid4
        instance_id = f"comp_{int(datetime.now().timestamp() * 1000)}_{uuid4().hex[:8]}"
        
        instance = ComponentInstance(
            instanceId=instance_id,
            componentId=component_id,
            stateId=state_id,
            sessionId=session_id,
            props=props or {}
        )
        
        await self.register_instance(instance)
        return instance

    async def watch_templates(self, on_change: Callable[[List[ComponentTemplate]], None]):
        """
        监视模板文件更改 (需要安装 watchdog)
        """
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler
            
            class ComponentTemplateHandler(FileSystemEventHandler):
                def __init__(self, component_manager: 'ComponentManager', on_change_callback: Callable):
                    self.component_manager = component_manager
                    self.on_change = on_change_callback
                
                def on_modified(self, event):
                    if not event.is_directory and event.src_path.endswith(('.py', '.ts', '.tsx')):
                        print(f"Component template modified: {event.src_path}")
                        # 重新加载所有模板
                        asyncio.create_task(self.reload_templates())
                
                def on_created(self, event):
                    if not event.is_directory and event.src_path.endswith(('.py', '.ts', '.tsx')):
                        print(f"Component template created: {event.src_path}")
                        # 重新加载所有模板
                        asyncio.create_task(self.reload_templates())
                
                async def reload_templates(self):
                    templates = await self.component_manager.load_all_templates()
                    self.on_change(templates)
            
            if not self.components_dir.exists():
                self.components_dir.mkdir(parents=True, exist_ok=True)
            
            event_handler = ComponentTemplateHandler(self, on_change)
            observer = Observer()
            observer.schedule(event_handler, str(self.components_dir), recursive=False)
            observer.start()
            
            print(f"Watching component templates in {self.components_dir}")
            
            # 保持观察器运行
            self.watcher_task = observer
            self.watcher_callback = on_change
            
        except ImportError:
            print("⚠️  watchdog not installed, hot reload disabled. Install with: pip install watchdog")
        except Exception as error:
            print(f"Error watching component templates: {error}")

    def stop_watching(self):
        """
        停止监视模板文件更改
        """
        if self.watcher_task:
            try:
                self.watcher_task.stop()
                self.watcher_task.join()
                self.watcher_task = None
                print("Stopped watching component templates")
            except Exception as error:
                print(f"Error stopping watcher: {error}")

    async def get_component_data(
        self,
        instance_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        获取组件数据 (模板 + 状态)
        """
        instance = self.instances.get(instance_id)
        
        if not instance:
            print(f"Component instance not found: {instance_id}")
            return None
        
        template = self.templates.get(instance.componentId)
        
        if not template:
            print(f"Component template not found: {instance.componentId}")
            return None
        
        try:
            state = await self.ui_state_manager.get_state(instance.stateId)
            
            return {
                'template': template,
                'state': state,
                'instance': instance
            }
        except Exception as error:
            print(f"Error getting component data: {error}")
            return None

    async def update_component_state(
        self,
        instance_id: str,
        new_state: Dict[str, Any]
    ) -> bool:
        """
        更新组件关联的UI状态
        """
        instance = self.instances.get(instance_id)
        
        if not instance:
            print(f"Component instance not found: {instance_id}")
            return False
        
        try:
            await self.ui_state_manager.set_state(instance.stateId, new_state)
            return True
        except Exception as error:
            print(f"Error updating component state: {error}")
            return False

    def prune_old_instances(self, days_old: int = 7) -> None:
        """
        清理旧的组件实例 (暂未实现)
        """
        # 在Finance Agent中，我们依赖数据库的清理机制
        print(f"⚠️  prune_old_instances not implemented for Finance Agent")


# 导入必要的类型定义
__all__ = [
    'ComponentTemplate',
    'ComponentInstance',
    'ComponentManager'
]
