#!/usr/bin/env python3
"""
最终集成测试脚本
验证所有UI功能和WebSocket消息扩展是否正常工作
"""

import asyncio
import json
import websockets
import time
from typing import Dict, Any

async def test_websocket_integration():
    """测试WebSocket集成"""
    print("🧪 开始WebSocket集成测试...")
    
    try:
        # 连接到WebSocket服务器
        uri = "ws://localhost:3000/ws"
        async with websockets.connect(uri) as websocket:
            print("✅ 成功连接到WebSocket服务器")
            
            # 等待连接确认消息
            response = await asyncio.wait_for(websocket.recv(), timeout=5)
            response_data = json.loads(response)
            print(f"📡 收到服务器响应: {response_data.get('type')}")
            
            # 测试订阅报告分析
            subscribe_msg = {
                "type": "subscribe_report_analysis",
                "sessionId": "test_session_1"
            }
            await websocket.send(json.dumps(subscribe_msg))
            print("📤 发送报告分析订阅请求")
            
            response = await asyncio.wait_for(websocket.recv(), timeout=5)
            response_data = json.loads(response)
            print(f"📥 收到订阅响应: {response_data.get('type')}")
            
            # 等待可能的报告分析更新
            print("⏳ 等待报告分析更新...")
            for i in range(3):
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=2)
                    response_data = json.loads(response)
                    print(f"📊 收到消息: {response_data.get('type')}")
                    if response_data.get('type') == 'report_analysis_update':
                        print(f"📈 报告分析更新: {response_data.get('title', 'N/A')}")
                    elif response_data.get('type') == 'alert_triggered':
                        print(f"⚠️  预警触发: {response_data.get('message', 'N/A')}")
                except asyncio.TimeoutError:
                    print(f"⏳ 暂无新消息 ({i+1}/3)")
            
            print("✅ WebSocket集成测试完成")
            
    except Exception as e:
        print(f"❌ WebSocket集成测试失败: {e}")

async def test_message_types():
    """测试消息类型定义"""
    print("\n🔍 开始消息类型测试...")
    
    try:
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
        
        from ccsdk.message_types import (
            WSReportAnalysisUpdateMessage,
            WSAlertTriggeredMessage,
            WSComponentInstanceMessage,
            OutgoingMessage
        )
        
        # 测试报告分析更新消息
        report_msg = WSReportAnalysisUpdateMessage(
            reportId="test_report_1",
            title="测试报告",
            analysis={"key_metrics": {"price": 100.5, "change": 2.5}},
            timestamp=time.strftime('%Y-%m-%d %H:%M:%S')
        )
        print(f"✅ 报告分析消息创建成功: {report_msg.type}")
        
        # 测试预警触发消息
        alert_msg = WSAlertTriggeredMessage(
            alertId="test_alert_1",
            title="价格预警",
            message="黄金价格突破关键点位",
            severity="high"
        )
        print(f"✅ 预警消息创建成功: {alert_msg.type}")
        
        # 测试组件实例消息
        from ccsdk.message_types import ComponentInstance
        component_instance = ComponentInstance(
            instanceId="test_instance_1",
            componentId="portfolio_dashboard",
            sessionId="test_session_1"
        )
        component_msg = WSComponentInstanceMessage(instance=component_instance)
        print(f"✅ 组件实例消息创建成功: {component_msg.type}")
        
        print("✅ 消息类型测试完成")
        
    except Exception as e:
        print(f"❌ 消息类型测试失败: {e}")

async def test_ui_components():
    """测试UI组件集成"""
    print("\n🖥️  开始UI组件测试...")
    
    try:
        # 检查前端组件文件是否存在
        import os
        
        component_files = [
            "client/components/custom/MarketMonitor.tsx",
            "client/components/custom/WatchlistTable.tsx",
            "client/components/custom/PortfolioDashboard.tsx",
            "client/hooks/useReportAnalysis.ts",
            "client/hooks/WebSocketManager.ts"
        ]
        
        for file_path in component_files:
            full_path = f"/Users/caiwei/workbench/claude-agent-sdk-demos/finance-agent/{file_path}"
            if os.path.exists(full_path):
                print(f"✅ 组件文件存在: {file_path}")
            else:
                print(f"❌ 组件文件不存在: {file_path}")
        
        print("✅ UI组件测试完成")
        
    except Exception as e:
        print(f"❌ UI组件测试失败: {e}")

async def main():
    """主测试函数"""
    print("🚀 开始Finance Agent UI功能最终集成测试")
    print("="*50)
    
    await test_message_types()
    await test_ui_components()
    await test_websocket_integration()
    
    print("="*50)
    print("🎉 所有测试完成！")

if __name__ == "__main__":
    asyncio.run(main())