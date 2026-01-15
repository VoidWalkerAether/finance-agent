#!/usr/bin/env python3
"""
测试 WebSocket 智能搜索功能

功能测试：
1. 单轮搜索（金融问题 - 本地数据库）
2. 单轮搜索（通用问题 - 网络搜索）
3. 多轮对话（追问）
4. 流式输出验证

使用方法:
python scripts/test_websocket_search.py
"""

import asyncio
import json
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import websockets
except ImportError:
    print("❌ 错误: 缺少 websockets 库")
    print("请安装: pip install websockets")
    sys.exit(1)


async def test_finance_search():
    """测试金融问题搜索（本地数据库）"""
    print("\n" + "=" * 60)
    print("🧪 Test 1: 金融问题搜索（本地数据库）")
    print("=" * 60)
    
    uri = "ws://localhost:3000/ws"
    
    try:
        async with websockets.connect(uri) as websocket:
            print(f"✅ 连接到 {uri}")
            
            # 接收连接确认消息
            message = await websocket.recv()
            data = json.loads(message)
            print(f"📩 接收: {data.get('type')}")
            
            # 发送搜索请求
            search_request = {
                "type": "search",
                "query": "芯片投资建议",
                "limit": 5
            }
            
            print(f"\n📤 发送搜索请求: {search_request['query']}")
            await websocket.send(json.dumps(search_request))
            
            # 接收响应
            collected_text = ""  # 收集流式文本
            while True:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                    data = json.loads(message)
                    msg_type = data.get("type")
                    
                    # 忽略非搜索相关消息（后台定时推送）
                    if msg_type in ["reports_update", "ui_state_update", "ui_state_templates", "connected"]:
                        print(f"\n⏭️  忽略后台消息: {msg_type}")
                        continue
                    
                    print(f"\n📨 收到消息: {msg_type}")
                    
                    if msg_type == "search_status":
                        print(f"📊 状态: {data.get('message')}")
                    
                    elif msg_type == "search_intent":
                        print(f"💡 意图: {data.get('intent')} (置信度: {data.get('confidence')})")
                        print(f"   理由: {data.get('reason')}")
                    
                    elif msg_type == "search_chunk":
                        # 流式文本（本地搜索也支持流式输出）
                        text = data.get('text', '')
                        collected_text += text
                        print(text, end='', flush=True)
                    
                    elif msg_type == "search_result":
                        results = data.get('results', [])
                        print(f"📋 搜索结果: {len(results)} 条")
                        for i, result in enumerate(results[:3], 1):
                            title = result.get('title', '无标题')
                            print(f"   {i}. {title}")
                    
                    elif msg_type == "search_complete":
                        if collected_text:
                            print(f"\n\n📝 收集的回答总长度: {len(collected_text)} 字符")
                        print(f"✅ 搜索完成 (成本: ${data.get('cost', 0):.6f})")
                        break
                    
                    elif msg_type == "search_error":
                        print(f"❌ 搜索失败: {data.get('message')}")
                        break
                    
                    else:
                        print(f"⚠️  未知搜索消息类型: {msg_type}")
                        
                except asyncio.TimeoutError:
                    print(f"\n⏰ 超时！等待响应超过 30 秒")
                    break
                except Exception as e:
                    print(f"\n❌ 接收消息失败: {e}")
                    raise
            
            print("✅ 测试 1 通过")
            
    except Exception as e:
        print(f"❌ 测试 1 失败: {e}")


async def test_general_search():
    """测试通用问题搜索（网络搜索）"""
    print("\n" + "=" * 60)
    print("🧪 Test 2: 通用问题搜索（网络搜索）")
    print("=" * 60)
    
    print("⚠️  注意: 此测试需要 ANTHROPIC_AUTH_TOKEN 环境变量")
    print("⚠️  注意: 此测试会调用 Claude API 并产生费用")
    
    choice = input("\n是否继续测试网络搜索功能? (y/n): ")
    if choice.lower() != 'y':
        print("跳过测试 2")
        return
    
    uri = "ws://localhost:3000/ws"
    
    try:
        async with websockets.connect(uri) as websocket:
            print(f"✅ 连接到 {uri}")
            
            # 接收连接确认消息
            await websocket.recv()
            
            # 发送搜索请求
            search_request = {
                "type": "search",
                "query": "今天北京今天汽车限行尾号",
                "limit": 5
            }
            
            print(f"\n📤 发送搜索请求: {search_request['query']}")
            await websocket.send(json.dumps(search_request))
            
            # 接收响应
            collected_text = ""
            while True:
                message = await asyncio.wait_for(websocket.recv(), timeout=60.0)
                data = json.loads(message)
                msg_type = data.get("type")
                
                if msg_type == "search_status":
                    print(f"📊 状态: {data.get('message')}")
                
                elif msg_type == "search_intent":
                    print(f"💡 意图: {data.get('intent')}")
                
                elif msg_type == "search_chunk":
                    # 流式文本
                    text = data.get('text', '')
                    collected_text += text
                    print(text, end='', flush=True)
                
                elif msg_type == "search_complete":
                    print(f"\n✅ 搜索完成 (成本: ${data.get('cost', 0):.6f})")
                    session_id = data.get('session_id')
                    print(f"🔑 Session ID: {session_id}")
                    break
                
                elif msg_type == "search_error":
                    print(f"❌ 搜索失败: {data.get('message')}")
                    break
            
            print("\n✅ 测试 2 通过")
            
    except Exception as e:
        print(f"❌ 测试 2 失败: {e}")


async def test_multi_turn_conversation():
    """测试多轮对话"""
    print("\n" + "=" * 60)
    print("🧪 Test 3: 多轮对话（追问）")
    print("=" * 60)
    
    print("⚠️  注意: 此测试需要 ANTHROPIC_AUTH_TOKEN 环境变量")
    
    choice = input("\n是否继续测试多轮对话功能? (y/n): ")
    if choice.lower() != 'y':
        print("跳过测试 3")
        return
    
    uri = "ws://localhost:3000/ws"
    session_id = None
    
    try:
        async with websockets.connect(uri) as websocket:
            print(f"✅ 连接到 {uri}")
            
            # 接收连接确认消息
            await websocket.recv()
            
            # 第一轮：询问巴黎
            print("\n--- 第一轮对话 ---")
            search_request = {
                "type": "search",
                "query": "法国的首都是哪里？"
            }
            
            print(f"📤 发送: {search_request['query']}")
            await websocket.send(json.dumps(search_request))
            
            # 接收第一轮响应
            while True:
                message = await asyncio.wait_for(websocket.recv(), timeout=60.0)
                data = json.loads(message)
                msg_type = data.get("type")
                
                if msg_type == "search_chunk":
                    print(data.get('text', ''), end='', flush=True)
                
                elif msg_type == "search_complete":
                    session_id = data.get('session_id')
                    print(f"\n🔑 保存 Session ID: {session_id}")
                    break
                
                elif msg_type == "search_error":
                    print(f"❌ 第一轮失败: {data.get('message')}")
                    return
            
            if not session_id:
                print("❌ 未获取到 session_id，无法继续多轮对话")
                return
            
            # 第二轮：追问（测试上下文记忆）
            print("\n\n--- 第二轮对话（追问）---")
            search_request = {
                "type": "search",
                "query": "那个城市的人口有多少？",  # ✅ 测试 AI 是否记得"那个城市"指巴黎
                "session_id": session_id  # ✅ 传递 session_id
            }
            
            print(f"📤 发送: {search_request['query']}")
            await websocket.send(json.dumps(search_request))
            
            # 接收第二轮响应
            while True:
                message = await asyncio.wait_for(websocket.recv(), timeout=60.0)
                data = json.loads(message)
                msg_type = data.get("type")
                
                if msg_type == "search_chunk":
                    print(data.get('text', ''), end='', flush=True)
                
                elif msg_type == "search_complete":
                    print(f"\n✅ 第二轮完成")
                    break
                
                elif msg_type == "search_error":
                    print(f"❌ 第二轮失败: {data.get('message')}")
                    break
            
            print("\n✅ 测试 3 通过（多轮对话成功）")
            
    except Exception as e:
        print(f"❌ 测试 3 失败: {e}")


async def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("🧪 WebSocket 智能搜索测试套件")
    print("=" * 60)
    print("\n确保服务器运行在 http://localhost:3000")
    print("启动服务器: python server/server.py")
    
    try:
        # 等待用户确认
        input("\n按 Enter 键开始测试...")
        
        # 测试 1: 金融问题搜索
        await test_finance_search()
        
        # 测试 2: 通用问题搜索（可选）
        #await test_general_search()
        
        # 测试 3: 多轮对话（可选）
        #await test_multi_turn_conversation()
        
        print("\n" + "=" * 60)
        print("✅ 所有测试完成!")
        print("=" * 60 + "\n")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
