"""
WebSocket 多轮对话测试

测试 Finance Agent 的 WebSocket 聊天功能
对应 Email Agent 的 WebSocket 客户端测试

用法：
  python scripts/test_websocket_chat.py

功能：
  1. 连接到 WebSocket 服务器 (ws://localhost:3000/ws)
  2. 自动创建/加入会话
  3. 支持多轮对话
  4. 实时接收 AI 流式响应
  5. 显示 session_id 和消息统计
"""

import asyncio
import json
import sys
import os
from pathlib import Path
from typing import Optional, Dict, Any

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# 第三方库检查
try:
    import websockets
except ImportError:
    print("❌ 缺少依赖: websockets")
    print("\n请安装: pip install websockets")
    sys.exit(1)

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()


class WebSocketChatClient:
    """WebSocket 聊天客户端"""
    
    def __init__(self, url: str = "ws://localhost:3000/ws"):
        self.url = url
        self.websocket: Optional[Any] = None
        self.session_id: Optional[str] = None
        self.is_connected = False
        self.message_count = 0
        self.current_response = ""
        self.is_receiving = False
        
    async def connect(self):
        """连接到 WebSocket 服务器"""
        try:
            print(f"🔌 正在连接到 {self.url}...")
            self.websocket = await websockets.connect(self.url)
            self.is_connected = True
            print("✅ 连接成功！")
            
            # 启动消息接收任务
            asyncio.create_task(self._receive_messages())
            
            # 等待初始连接消息
            await asyncio.sleep(0.5)
            
        except Exception as e:
            print(f"❌ 连接失败: {e}")
            print("\n提示:")
            print("  1. 确保服务器正在运行: python server/server.py")
            print("  2. 检查端口是否正确 (默认 3000)")
            sys.exit(1)
    
    async def _receive_messages(self):
        """接收 WebSocket 消息（后台任务）"""
        try:
            async for message in self.websocket:
                data = json.loads(message)
                await self._handle_message(data)
        except websockets.exceptions.ConnectionClosed:
            print("\n❌ WebSocket 连接已关闭")
            self.is_connected = False
        except Exception as e:
            print(f"\n❌ 接收消息错误: {e}")
            self.is_connected = False
    
    async def _handle_message(self, data: Dict[str, Any]):
        """处理接收到的消息"""
        msg_type = data.get('type')
        
        # 连接确认
        if msg_type == 'connected':
            print(f"📡 {data.get('message', '已连接到服务器')}")
            sessions = data.get('availableSessions', [])
            if sessions:
                print(f"   可用会话: {sessions}")
        
        # 会话信息
        elif msg_type == 'session_info':
            self.session_id = data.get('sessionId') or data.get('session_id')
            self.message_count = data.get('messageCount', 0)
            is_active = data.get('isActive', False)
            print(f"\n📋 会话信息:")
            print(f"   Session ID: {self.session_id}")
            print(f"   消息数: {self.message_count}")
            print(f"   状态: {'处理中' if is_active else '空闲'}")
        
        # 订阅确认
        elif msg_type == 'subscribed':
            session_id = data.get('sessionId')
            print(f"✅ 已订阅会话: {session_id}")
        
        # 用户消息（回显）
        elif msg_type == 'user_message':
            content = data.get('content', '')
            print(f"\n👤 你: {content}")
        
        # AI 助手消息（流式）
        elif msg_type == 'assistant_message':
            content = data.get('content', '')
            if not self.is_receiving:
                self.is_receiving = True
                self.current_response = ""
                print("\n🤖 AI: ", end='', flush=True)
            
            self.current_response += content
            print(content, end='', flush=True)
        
        # 工具使用
        elif msg_type == 'tool_use':
            tool_name = data.get('toolName')
            tool_input = data.get('toolInput', {})
            print(f"\n🔧 使用工具: {tool_name}")
            print(f"   参数: {json.dumps(tool_input, ensure_ascii=False, indent=2)}")
        
        # 工具结果
        elif msg_type == 'tool_result':
            tool_use_id = data.get('toolUseId')
            content = data.get('content')
            is_error = data.get('isError', False)
            status = "❌ 错误" if is_error else "✅ 成功"
            print(f"\n   {status}: {content}")
        
        # 结果消息（对话结束）
        elif msg_type == 'result':
            if self.is_receiving:
                print()  # 换行
                self.is_receiving = False
            
            success = data.get('success', True)
            if success:
                cost = data.get('cost', 0)
                duration = data.get('duration', 0)
                print(f"\n💰 成本: ${cost:.4f} | ⏱️  耗时: {duration}ms")
            else:
                error = data.get('error', 'Unknown error')
                print(f"\n❌ 错误: {error}")
        
        # 系统消息
        elif msg_type == 'system':
            subtype = data.get('subtype')
            print(f"\n📢 系统: {subtype}")
        
        # 错误消息
        elif msg_type == 'error':
            error = data.get('error', 'Unknown error')
            print(f"\n❌ 错误: {error}")
        
        # 报告更新（自动推送）
        elif msg_type == 'reports_update':
            reports = data.get('reports', [])
            # 静默处理（不打印，避免干扰对话）
            pass
        
        # UI 状态更新
        elif msg_type == 'ui_state_update':
            state_id = data.get('stateId')
            # 静默处理
            pass
        
        # UI 状态模板列表（服务器启动时发送）
        elif msg_type == 'ui_state_templates':
            templates = data.get('templates', [])
            # 静默处理（不打印，避免干扰对话）
            pass
        
        # 未知消息类型
        else:
            print(f"\n❓ 未知消息类型: {msg_type}")
            print(f"   数据: {json.dumps(data, ensure_ascii=False, indent=2)}")
    
    async def send_chat_message(self, content: str, new_conversation: bool = False):
        """发送聊天消息"""
        if not self.is_connected:
            print("❌ 未连接到服务器")
            return
        
        message = {
            'type': 'chat',
            'content': content,
            'sessionId': self.session_id or 'default',
            'newConversation': new_conversation
        }
        
        await self.websocket.send(json.dumps(message, ensure_ascii=False))
        
        # 等待响应完成
        await asyncio.sleep(0.2)  # 给服务器一点时间处理
    
    async def create_new_conversation(self):
        """开始新对话（清除上下文）"""
        if self.session_id:
            print("\n🔄 开始新对话...")
            await self.send_chat_message("", new_conversation=True)
            await asyncio.sleep(0.3)
    
    async def close(self):
        """关闭连接"""
        if self.websocket:
            await self.websocket.close()
            self.is_connected = False
            print("\n👋 连接已关闭")


async def interactive_mode():
    """交互式对话模式"""
    
    print("="*70)
    print("💬 Finance Agent - WebSocket 多轮对话测试")
    print("="*70)
    print("\n提示:")
    print("  - 输入消息开始对话")
    print("  - 输入 'new' 开始新对话（清除上下文）")
    print("  - 输入 'quit' 退出")
    print("="*70)
    
    # 创建客户端并连接
    client = WebSocketChatClient()
    await client.connect()
    
    # 等待连接稳定
    await asyncio.sleep(1)
    
    turn = 0
    
    try:
        while client.is_connected:
            # 用户输入
            try:
                user_input = await asyncio.get_event_loop().run_in_executor(
                    None, 
                    input, 
                    f"\n[第 {turn + 1} 轮] 你: "
                )
                user_input = user_input.strip()
            except EOFError:
                break
            
            # 退出
            if user_input.lower() in ['quit', 'exit', 'q', '退出']:
                break
            
            # 开始新对话
            if user_input.lower() in ['new', 'reset', '新对话']:
                await client.create_new_conversation()
                turn = 0
                continue
            
            # 空输入
            if not user_input:
                continue
            
            # 发送消息
            await client.send_chat_message(user_input)
            turn += 1
            
            # 等待响应完成（简单延迟，实际应该监听 result 消息）
            await asyncio.sleep(0.5)
            while client.is_receiving:
                await asyncio.sleep(0.1)
    
    except KeyboardInterrupt:
        print("\n\n⚠️  收到中断信号")
    
    finally:
        # 关闭连接
        await client.close()
        
        # 显示统计
        print("\n" + "="*70)
        print("📊 会话统计")
        print("="*70)
        print(f"Session ID: {client.session_id}")
        print(f"对话轮数: {turn}")
        print("="*70)


async def auto_test_mode():
    """自动测试模式（预设问题）"""
    
    print("="*70)
    print("⚡ Finance Agent - WebSocket 自动测试")
    print("="*70)
    
    # 创建客户端并连接
    client = WebSocketChatClient()
    await client.connect()
    
    # 等待连接稳定
    await asyncio.sleep(1)
    
    # 预设问题
    questions = [
        "你好，请介绍一下你的功能",
        "我想了解最近的市场报告",
        "有什么投资建议吗？",
        "综合前面的分析，你觉得现在适合投资吗？"
    ]
    
    try:
        for i, question in enumerate(questions, 1):
            print(f"\n{'─'*70}")
            print(f"[{i}/{len(questions)}] 测试问题: {question}")
            print('─'*70)
            
            # 发送消息
            await client.send_chat_message(question)
            
            # 等待响应完成
            await asyncio.sleep(1)
            while client.is_receiving:
                await asyncio.sleep(0.2)
            
            # 间隔
            if i < len(questions):
                await asyncio.sleep(2)
        
        # 测试新对话
        print(f"\n{'─'*70}")
        print("🔄 测试新对话功能")
        print('─'*70)
        await client.create_new_conversation()
        await asyncio.sleep(1)
        
        # 再问一个问题
        await client.send_chat_message("现在开始新的对话，你还记得之前的内容吗？")
        await asyncio.sleep(1)
        while client.is_receiving:
            await asyncio.sleep(0.2)
    
    except KeyboardInterrupt:
        print("\n\n⚠️  测试中断")
    
    finally:
        await client.close()
        
        print("\n" + "="*70)
        print("✅ 自动测试完成!")
        print("="*70)


async def main():
    """主函数"""
    
    print("\n选择测试模式:")
    print("  1. 交互式对话（手动输入问题）")
    print("  2. 自动测试（预设问题）")
    
    choice = input("\n请选择 (1/2): ").strip()
    
    if choice == "1":
        await interactive_mode()
    elif choice == "2":
        await auto_test_mode()
    else:
        print("❌ 无效选择")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 再见!")
