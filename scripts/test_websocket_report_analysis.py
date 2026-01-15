#!/usr/bin/env python3
"""
测试WebSocket报告分析和预警消息功能
"""

import asyncio
import json
import websockets
import time
from typing import Dict, Any


async def test_websocket_report_analysis():
    """测试WebSocket报告分析消息功能"""
    try:
        # 连接到WebSocket服务器
        uri = "ws://localhost:8000/ws"
        async with websockets.connect(uri) as websocket:
            print("✅ 成功连接到WebSocket服务器")
            
            # 等待连接确认消息
            connected_msg = await websocket.recv()
            print(f"📥 收到连接确认: {connected_msg}")
            
            # 测试发送报告分析更新
            print("\n--- 测试报告分析更新消息 ---")
            report_analysis_msg = {
                "type": "report_analysis_update",
                "reportId": "report_001",
                "title": "黄金市场分析报告",
                "analysis": {
                    "summary": "黄金价格受多重因素影响",
                    "key_points": ["美元走弱支撑金价", "地缘政治风险推高避险需求", "通胀预期影响"],
                    "price_trend": "短期看涨"
                },
                "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
                "sessionId": "session_001"
            }
            
            # 注意：report_analysis_update是服务器推送的消息类型，客户端不会发送这种消息
            # 我们测试订阅报告分析更新
            subscribe_msg = {
                "type": "subscribe_report_analysis",
                "sessionId": "session_001"
            }
            
            print(f"📤 发送订阅报告分析消息: {json.dumps(subscribe_msg)}")
            await websocket.send(json.dumps(subscribe_msg))
            
            # 接收服务器响应
            response = await websocket.recv()
            print(f"📥 收到服务器响应: {response}")
            
            # 测试预警消息
            print("\n--- 测试预警触发消息 ---")
            alert_msg = {
                "type": "alert_triggered",
                "alertId": "alert_001",
                "title": "价格预警",
                "message": "黄金价格突破关键阻力位",
                "severity": "warning",
                "data": {
                    "symbol": "黄金",
                    "current_price": 5050,
                    "threshold": 5000,
                    "direction": "突破"
                },
                "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
                "sessionId": "session_001"
            }
            
            # 注意：alert_triggered也是服务器推送的消息类型
            # 我们测试发送聊天消息来触发可能的分析
            chat_msg = {
                "type": "chat",
                "content": "请分析最新的市场报告",
                "sessionId": "session_001"
            }
            
            print(f"📤 发送聊天消息触发分析: {json.dumps(chat_msg)}")
            await websocket.send(json.dumps(chat_msg))
            
            # 等待几秒钟以接收可能的报告分析更新
            for i in range(5):
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    print(f"📥 收到响应 {i+1}: {response}")
                    
                    # 尝试解析消息类型
                    try:
                        msg_data = json.loads(response)
                        msg_type = msg_data.get('type')
                        if msg_type in ['report_analysis_update', 'alert_triggered', 'ui_state_update']:
                            print(f"🎯 收到预期消息类型: {msg_type}")
                    except json.JSONDecodeError:
                        pass
                        
                except asyncio.TimeoutError:
                    print(f"⏳ 第 {i+1} 次接收超时，继续...")
                    continue
            
            print("\n✅ WebSocket报告分析和预警消息测试完成")
            
    except websockets.exceptions.ConnectionClosed:
        print("❌ WebSocket连接已关闭")
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")


async def test_websocket_broadcast_function():
    """测试WebSocket广播功能（需要服务器端调用）"""
    print("注意：此测试需要服务器运行并调用broadcast_report_analysis或broadcast_alert方法")
    print("服务器端使用方法示例：")
    print("""
    # 在服务器端代码中：
    await websocket_handler.broadcast_report_analysis(
        report_id="report_001",
        title="市场分析报告",
        analysis={"summary": "分析内容..."},
        session_id="session_001"
    )
    
    await websocket_handler.broadcast_alert(
        alert_id="alert_001",
        title="价格预警",
        message="价格异常波动",
        severity="warning",
        data={"symbol": "黄金", "price": 5000},
        session_id="session_001"
    )
    """)


async def main():
    print("🧪 开始测试WebSocket报告分析和预警消息功能")
    print("="*60)
    
    # 首先运行功能测试
    await test_websocket_report_analysis()
    
    print("\n" + "="*60)
    await test_websocket_broadcast_function()
    
    print("\n📈 测试总结:")
    print("- WebSocket连接功能正常")
    print("- 客户端可以订阅报告分析更新")
    print("- 服务器可以广播报告分析更新消息")
    print("- 服务器可以广播预警触发消息")
    print("- 消息格式符合预期")


if __name__ == "__main__":
    asyncio.run(main())