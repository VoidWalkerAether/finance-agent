"""日志写入器 - 将 Listener 执行日志写入 JSONL 文件

对应 TypeScript: email-agent/ccsdk/log-writer.ts

功能:
1. 为每个 Listener 创建独立的 JSONL 日志文件
2. 支持日志追加写入
3. 支持读取最近的 N 条日志
4. 支持读取所有 Listeners 的日志并合并排序
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from .message_types import ListenerLogEntry


class LogWriter:
    """
    日志写入器
    对应 TypeScript: LogWriter (log-writer.ts)
    
    日志文件位置: agent/custom_scripts/listeners/.logs/{listener_id}.jsonl
    """
    
    def __init__(self, listeners_dir: str):
        """
        初始化日志写入器
        
        Args:
            listeners_dir: Listeners 目录路径
        """
        self.logs_dir = os.path.join(listeners_dir, ".logs")
    
    async def ensure_logs_dir(self) -> None:
        """确保日志目录存在"""
        try:
            Path(self.logs_dir).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"[LogWriter] Failed to create logs directory: {e}")
    
    async def append_log(self, listener_id: str, entry: ListenerLogEntry) -> None:
        """
        追加日志条目到 JSONL 文件
        对应 TypeScript: appendLog()
        
        Args:
            listener_id: Listener ID
            entry: 日志条目
        """
        try:
            await self.ensure_logs_dir()
            
            log_file = os.path.join(self.logs_dir, f"{listener_id}.jsonl")
            log_line = json.dumps(entry.__dict__, ensure_ascii=False) + "\n"
            
            # 追加写入
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(log_line)
        except Exception as e:
            print(f"[LogWriter] Failed to write log for listener {listener_id}: {e}")
    
    async def read_logs(
        self, 
        listener_id: str, 
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        读取指定 Listener 的最近 N 条日志
        对应 TypeScript: readLogs()
        
        Args:
            listener_id: Listener ID
            limit: 返回的最大条目数
        
        Returns:
            日志条目列表（最新的在前）
        """
        try:
            log_file = os.path.join(self.logs_dir, f"{listener_id}.jsonl")
            
            # 检查文件是否存在
            if not os.path.exists(log_file):
                return []
            
            # 读取文件内容
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = [line.strip() for line in content.split('\n') if line.strip()]
            
            # 解析 JSON 行
            entries = []
            for line in lines:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
            
            # 返回最后 N 条记录（倒序，最新的在前）
            return list(reversed(entries[-limit:]))
        except Exception as e:
            print(f"[LogWriter] Failed to read logs for listener {listener_id}: {e}")
            return []
    
    async def read_all_logs(
        self, 
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        读取所有 Listeners 的日志并按时间排序
        对应 TypeScript: readAllLogs()
        
        Args:
            limit: 返回的最大条目数
        
        Returns:
            合并后的日志列表（按时间戳倒序）
        """
        try:
            await self.ensure_logs_dir()
            
            all_entries = []
            
            # 获取所有 .jsonl 文件
            if not os.path.exists(self.logs_dir):
                return []
            
            files = [f for f in os.listdir(self.logs_dir) if f.endswith('.jsonl')]
            
            # 读取每个文件
            for file in files:
                listener_id = file.replace('.jsonl', '')
                entries = await self.read_logs(listener_id, limit)
                
                # 添加 listener_id 字段
                for entry in entries:
                    entry['listener_id'] = listener_id
                    all_entries.append(entry)
            
            # 按时间戳排序（最新的在前）
            all_entries.sort(
                key=lambda x: datetime.fromisoformat(x.get('timestamp', '1970-01-01T00:00:00')),
                reverse=True
            )
            
            return all_entries[:limit]
        except Exception as e:
            print(f"[LogWriter] Failed to read all logs: {e}")
            return []
