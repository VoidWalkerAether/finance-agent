#!/usr/bin/env python3
"""
测试 Finance Agent Server

使用方法:
python scripts/test_server.py
"""

import asyncio
import websockets
import json
import aiohttp


async def test_health_check():
    """测试健康检查端点"""
    print("\n" + "=" * 60)
    print("🧪 Test 1: Health Check")
    print("=" * 60)
    
    async with aiohttp.ClientSession() as session:
        async with session.get("http://localhost:3000/health") as response:
            data = await response.json()
            print(f"Status: {response.status}")
            print(f"Response: {json.dumps(data, indent=2)}")
            assert response.status == 200
            assert data["status"] == "healthy"
            print("✅ Health check passed!")


async def test_get_reports():
    """测试获取报告列表"""
    print("\n" + "=" * 60)
    print("🧪 Test 2: Get Reports")
    print("=" * 60)
    
    async with aiohttp.ClientSession() as session:
        async with session.get("http://localhost:3000/api/reports") as response:
            data = await response.json()
            print(f"Status: {response.status}")
            print(f"Total reports: {data.get('total', 0)}")
            print(f"Returned: {len(data.get('reports', []))}")
            print("✅ Get reports passed!")


async def test_get_watchlist():
    """测试获取关注列表"""
    print("\n" + "=" * 60)
    print("🧪 Test 3: Get Watchlist")
    print("=" * 60)
    
    async with aiohttp.ClientSession() as session:
        async with session.get("http://localhost:3000/api/watchlist") as response:
            data = await response.json()
            print(f"Status: {response.status}")
            print(f"Watchlist items: {len(data.get('watchlist', []))}")
            print("✅ Get watchlist passed!")


async def test_websocket_connection():
    """测试 WebSocket 连接"""
    print("\n" + "=" * 60)
    print("🧪 Test 4: WebSocket Connection")
    print("=" * 60)
    
    uri = "ws://localhost:3000/ws"
    
    try:
        async with websockets.connect(uri) as websocket:
            print(f"✅ Connected to {uri}")
            
            # 接收连接确认消息
            message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            data = json.loads(message)
            print(f"Received: {data.get('type', 'unknown')}")
            
            # 发送测试消息
            test_message = {
                "type": "chat",
                "content": "Hello, Finance Agent!",
                "sessionId": "test_session_001"
            }
            
            await websocket.send(json.dumps(test_message))
            print("Sent test message")
            
            # 接收响应（最多等待 30 秒）
            print("Waiting for AI response...")
            timeout = 30
            start_time = asyncio.get_event_loop().time()
            
            while True:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    data = json.loads(message)
                    msg_type = data.get("type", "unknown")
                    print(f"  [{msg_type}] {str(data)[:100]}...")
                    
                    # 检查是否完成
                    if msg_type == "result":
                        print("✅ WebSocket test passed!")
                        break
                        
                    # 超时检查
                    if asyncio.get_event_loop().time() - start_time > timeout:
                        print("⚠️  Timeout waiting for result")
                        break
                        
                except asyncio.TimeoutError:
                    # 继续等待
                    pass
                    
    except Exception as e:
        print(f"❌ WebSocket test failed: {e}")


async def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("🧪 Finance Agent Server Test Suite")
    print("=" * 60)
    print("\nMake sure the server is running on http://localhost:3000")
    print("Start server with: python server/server.py")
    
    try:
        # 基础 API 测试
        await test_health_check()
        await test_get_reports()
        await test_get_watchlist()
        
        # WebSocket 测试（需要 API Key）
        print("\n⚠️  WebSocket test requires ANTHROPIC_AUTH_TOKEN in .env")
        choice = input("Run WebSocket test? (y/n): ")
        
        if choice.lower() == 'y':
            await test_websocket_connection()
        else:
            print("Skipped WebSocket test")
        
        print("\n" + "=" * 60)
        print("✅ All tests completed!")
        print("=" * 60 + "\n")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
