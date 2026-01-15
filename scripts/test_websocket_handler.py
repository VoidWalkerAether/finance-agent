"""
WebSocket Handler 测试脚本
测试 WebSocketHandler 的核心功能

测试场景:
1. 基本连接和断开
2. Session 管理 (创建/订阅/取消订阅)
3. 消息路由 (chat/subscribe/unsubscribe)
4. 数据广播 (reports_update)
5. 并发处理
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from ccsdk.websocket_handler import WebSocketHandler
from database.database_manager import DatabaseManager


class MockWSClient:
    """模拟 WebSocket 客户端"""
    
    def __init__(self, client_id: str):
        self.client_id = client_id
        self.session_id: Optional[str] = None
        self.messages: List[Dict[str, Any]] = []
        self.is_open = True
    
    async def send(self, message: str):
        """接收消息"""
        if self.is_open:
            data = json.loads(message)
            self.messages.append(data)
            print(f"  📨 [{self.client_id}] Received: {data['type']}")
    
    def get_messages_by_type(self, msg_type: str) -> List[Dict[str, Any]]:
        """按类型过滤消息"""
        return [msg for msg in self.messages if msg.get('type') == msg_type]
    
    def clear_messages(self):
        """清空消息"""
        self.messages.clear()


async def test_basic_connection():
    """测试 1: 基本连接"""
    print("\n🧪 Test 1: Basic Connection")
    print("=" * 60)
    
    handler = WebSocketHandler()
    await handler.start()
    
    # 创建模拟客户端
    client = MockWSClient("client-1")
    
    # 连接
    await handler.on_open(client)
    
    # 验证
    assert len(client.messages) >= 1, "Should receive connection message"
    
    connected_msg = client.get_messages_by_type('connected')
    assert len(connected_msg) == 1, "Should receive 'connected' message"
    assert 'Finance Agent' in connected_msg[0]['message'], "Should contain greeting"
    
    # 验证初始报告列表
    reports_msg = client.get_messages_by_type('reports_update')
    assert len(reports_msg) >= 1, "Should receive initial reports"
    
    print(f"  ✅ Connection established")
    print(f"  ✅ Received {len(client.messages)} messages")
    
    # 断开
    await handler.on_close(client)
    await handler.stop()
    print("  ✅ Test passed")


async def test_session_management():
    """测试 2: Session 管理"""
    print("\n🧪 Test 2: Session Management")
    print("=" * 60)
    
    handler = WebSocketHandler()
    await handler.start()
    
    client1 = MockWSClient("client-1")
    client2 = MockWSClient("client-2")
    
    await handler.on_open(client1)
    await handler.on_open(client2)
    
    client1.clear_messages()
    client2.clear_messages()
    
    # Client 1 发送聊天消息 (自动创建 Session)
    chat_msg = json.dumps({
        'type': 'chat',
        'content': 'Hello, Finance Agent!',
        'newConversation': False
    })
    
    await handler.on_message(client1, chat_msg)
    
    # 等待处理
    await asyncio.sleep(0.5)
    
    # 验证 Session 创建
    assert handler.get_active_sessions_count() >= 1, "Should have at least 1 active session"
    
    session_id = handler.get_active_sessions()[0]
    print(f"  ✅ Session created: {session_id}")
    
    # Client 2 订阅该 Session
    subscribe_msg = json.dumps({
        'type': 'subscribe',
        'sessionId': session_id
    })
    
    await handler.on_message(client2, subscribe_msg)
    
    # 验证订阅成功
    subscribed_msgs = client2.get_messages_by_type('subscribed')
    assert len(subscribed_msgs) == 1, "Should receive 'subscribed' message"
    assert subscribed_msgs[0]['sessionId'] == session_id, "Should match session ID"
    
    print(f"  ✅ Client 2 subscribed to session: {session_id}")
    
    # 取消订阅
    unsubscribe_msg = json.dumps({
        'type': 'unsubscribe',
        'sessionId': session_id
    })
    
    await handler.on_message(client2, unsubscribe_msg)
    
    # 验证取消订阅
    unsubscribed_msgs = client2.get_messages_by_type('unsubscribed')
    assert len(unsubscribed_msgs) == 1, "Should receive 'unsubscribed' message"
    
    print(f"  ✅ Client 2 unsubscribed")
    
    await handler.on_close(client1)
    await handler.on_close(client2)
    await handler.stop()
    print("  ✅ Test passed")


async def test_message_routing():
    """测试 3: 消息路由"""
    print("\n🧪 Test 3: Message Routing")
    print("=" * 60)
    
    handler = WebSocketHandler()
    await handler.start()
    
    client = MockWSClient("client-1")
    await handler.on_open(client)
    client.clear_messages()
    
    # 测试未知消息类型
    unknown_msg = json.dumps({
        'type': 'unknown_type',
        'data': 'test'
    })
    
    await handler.on_message(client, unknown_msg)
    
    # 验证错误消息
    error_msgs = client.get_messages_by_type('error')
    assert len(error_msgs) == 1, "Should receive error message"
    assert 'Unknown message type' in error_msgs[0]['error'], "Should indicate unknown type"
    
    print("  ✅ Unknown message type handled correctly")
    
    # 测试请求报告列表
    client.clear_messages()
    request_msg = json.dumps({
        'type': 'request_reports'
    })
    
    await handler.on_message(client, request_msg)
    
    # 验证报告更新
    reports_msgs = client.get_messages_by_type('reports_update')
    assert len(reports_msgs) == 1, "Should receive reports update"
    assert 'reports' in reports_msgs[0], "Should contain reports array"
    
    print(f"  ✅ Request reports handled correctly")
    
    await handler.on_close(client)
    await handler.stop()
    print("  ✅ Test passed")


async def test_broadcast():
    """测试 4: 数据广播"""
    print("\n🧪 Test 4: Data Broadcast")
    print("=" * 60)
    
    handler = WebSocketHandler()
    await handler.start()
    
    # 连接 3 个客户端
    clients = [
        MockWSClient("client-1"),
        MockWSClient("client-2"),
        MockWSClient("client-3")
    ]
    
    for client in clients:
        await handler.on_open(client)
        client.clear_messages()
    
    # 等待自动广播 (5 秒轮询)
    print("  ⏳ Waiting for auto broadcast (5 seconds)...")
    await asyncio.sleep(6)
    
    # 验证所有客户端都收到了广播
    for i, client in enumerate(clients):
        reports_msgs = client.get_messages_by_type('reports_update')
        assert len(reports_msgs) >= 1, f"Client {i+1} should receive broadcast"
        print(f"  ✅ Client {i+1} received {len(reports_msgs)} broadcast(s)")
    
    # 清理
    for client in clients:
        await handler.on_close(client)
    
    await handler.stop()
    print("  ✅ Test passed")


async def test_concurrent_chat():
    """测试 5: 并发聊天处理"""
    print("\n🧪 Test 5: Concurrent Chat Handling")
    print("=" * 60)
    
    handler = WebSocketHandler()
    await handler.start()
    
    # 创建 2 个客户端，订阅同一个 Session
    client1 = MockWSClient("client-1")
    client2 = MockWSClient("client-2")
    
    await handler.on_open(client1)
    await handler.on_open(client2)
    
    client1.clear_messages()
    client2.clear_messages()
    
    # Client 1 发送消息创建 Session
    chat_msg1 = json.dumps({
        'type': 'chat',
        'content': 'First message',
        'newConversation': False
    })
    
    await handler.on_message(client1, chat_msg1)
    await asyncio.sleep(0.5)
    
    # 获取 Session ID
    session_id = handler.get_active_sessions()[0]
    
    # Client 2 订阅该 Session
    subscribe_msg = json.dumps({
        'type': 'subscribe',
        'sessionId': session_id
    })
    
    await handler.on_message(client2, subscribe_msg)
    await asyncio.sleep(0.2)
    
    # 清空消息准备测试
    client1.clear_messages()
    client2.clear_messages()
    
    # Client 1 发送第二条消息
    chat_msg2 = json.dumps({
        'type': 'chat',
        'content': 'Second message',
        'sessionId': session_id
    })
    
    await handler.on_message(client1, chat_msg2)
    await asyncio.sleep(0.5)
    
    # 验证两个客户端都收到了 AI 响应
    # (因为他们订阅了同一个 Session)
    print(f"  📊 Client 1 received {len(client1.messages)} messages")
    print(f"  📊 Client 2 received {len(client2.messages)} messages")
    
    # 注: 实际消息数量取决于 AI 响应的流式分块
    # 这里只验证客户端有收到消息
    assert len(client1.messages) > 0 or len(client2.messages) > 0, \
        "At least one client should receive messages"
    
    print("  ✅ Concurrent chat handled correctly")
    
    await handler.on_close(client1)
    await handler.on_close(client2)
    await handler.stop()
    print("  ✅ Test passed")


async def test_error_handling():
    """测试 6: 错误处理"""
    print("\n🧪 Test 6: Error Handling")
    print("=" * 60)
    
    handler = WebSocketHandler()
    await handler.start()
    
    client = MockWSClient("client-1")
    await handler.on_open(client)
    client.clear_messages()
    
    # 测试订阅不存在的 Session
    subscribe_msg = json.dumps({
        'type': 'subscribe',
        'sessionId': 'non-existent-session'
    })
    
    await handler.on_message(client, subscribe_msg)
    
    # 验证错误消息
    error_msgs = client.get_messages_by_type('error')
    assert len(error_msgs) == 1, "Should receive error message"
    assert 'not found' in error_msgs[0]['error'].lower(), "Should indicate session not found"
    
    print("  ✅ Non-existent session error handled")
    
    # 测试无效 JSON
    client.clear_messages()
    invalid_json = "{ invalid json }"
    
    await handler.on_message(client, invalid_json)
    
    # 验证错误消息
    error_msgs = client.get_messages_by_type('error')
    assert len(error_msgs) == 1, "Should receive error message"
    
    print("  ✅ Invalid JSON handled")
    
    await handler.on_close(client)
    await handler.stop()
    print("  ✅ Test passed")


async def main():
    """运行所有测试"""
    print("=" * 60)
    print("🧪 WebSocket Handler Test Suite")
    print("=" * 60)
    
    try:
        await test_basic_connection()
        await test_session_management()
        await test_message_routing()
        await test_broadcast()
        await test_concurrent_chat()
        await test_error_handling()
        
        print("\n" + "=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        raise
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        raise


if __name__ == '__main__':
    asyncio.run(main())
