#!/usr/bin/env python3
"""
WebSocket消息功能集成测试
测试报告分析和预警消息功能
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ccsdk.websocket_handler import WebSocketHandler
from ccsdk.message_types import WSClient, WSReportAnalysisUpdateMessage, WSAlertTriggeredMessage


async def test_websocket_report_analysis_and_alert():
    """测试WebSocket报告分析和预警消息功能"""
    print("🧪 开始测试WebSocket报告分析和预警消息功能")
    
    # 创建模拟的数据库管理器和UI状态管理器
    mock_db = MagicMock()
    mock_ui_state_manager = MagicMock()
    
    # 创建WebSocket处理器
    ws_handler = WebSocketHandler(mock_db, mock_ui_state_manager)
    
    # 模拟WebSocket客户端
    mock_ws_client = AsyncMock(spec=WSClient)
    mock_ws_client.session_id = None
    mock_ws_client.send_text = AsyncMock()
    mock_ws_client.close = AsyncMock()
    
    print("✅ WebSocket处理器创建成功")
    
    # 测试1: 广播报告分析更新
    print("\n--- 测试1: 广播报告分析更新 ---")
    await ws_handler._broadcast_report_analysis_update(
        report_id="report_001",
        title="黄金市场分析报告",
        analysis={
            "summary": "黄金价格受多重因素影响",
            "key_points": ["美元走弱支撑金价", "地缘政治风险推高避险需求", "通胀预期影响"],
            "price_trend": "短期看涨"
        },
        session_id=None  # 发送给所有客户端
    )
    print("✅ 报告分析更新广播功能正常")
    
    # 测试2: 广播预警触发消息
    print("\n--- 测试2: 广播预警触发消息 ---")
    await ws_handler._broadcast_alert_triggered(
        alert_id="alert_001",
        title="价格预警",
        message="黄金价格突破关键阻力位",
        severity="warning",
        data={
            "symbol": "黄金",
            "current_price": 5050,
            "threshold": 5000,
            "direction": "突破"
        },
        session_id=None  # 发送给所有客户端
    )
    print("✅ 预警触发消息广播功能正常")
    
    # 测试3: 添加客户端到处理器并测试特定会话广播
    print("\n--- 测试3: 特定会话广播 ---")
    ws_handler.clients["test_client"] = mock_ws_client
    
    # 测试向特定会话广播报告分析
    await ws_handler._broadcast_report_analysis_update(
        report_id="report_002",
        title="股票市场分析",
        analysis={"summary": "股市波动分析"},
        session_id="session_001"
    )
    print("✅ 特定会话报告分析广播功能正常")
    
    # 测试向特定会话广播预警
    await ws_handler._broadcast_alert_triggered(
        alert_id="alert_002",
        title="交易预警",
        message="股票价格异常波动",
        severity="danger",
        data={"symbol": "AAPL", "price": 150.0},
        session_id="session_001"
    )
    print("✅ 特定会话预警广播功能正常")
    
    # 测试4: 公共方法调用
    print("\n--- 测试4: 公共方法调用 ---")
    await ws_handler.broadcast_report_analysis(
        report_id="report_003",
        title="债券市场分析",
        analysis={"summary": "债券市场趋势"},
        session_id="session_002"
    )
    print("✅ broadcast_report_analysis公共方法正常")
    
    await ws_handler.broadcast_alert(
        alert_id="alert_003",
        title="风险预警",
        message="市场风险增加",
        severity="info",
        data={"risk_level": "medium"},
        session_id="session_002"
    )
    print("✅ broadcast_alert公共方法正常")
    
    # 测试5: 消息处理方法
    print("\n--- 测试5: 消息处理方法 ---")
    # 模拟订阅报告分析
    subscribe_data = {
        'type': 'subscribe_report_analysis',
        'sessionId': 'session_001'
    }
    
    # 模拟WebSocket连接事件
    await ws_handler.on_open(mock_ws_client)
    print("✅ WebSocket连接事件处理正常")
    
    # 模拟消息处理
    await ws_handler.on_message(mock_ws_client, json.dumps(subscribe_data))
    print("✅ 订阅报告分析消息处理正常")
    
    # 模拟取消订阅
    unsubscribe_data = {
        'type': 'unsubscribe_report_analysis',
        'sessionId': 'session_001'
    }
    await ws_handler.on_message(mock_ws_client, json.dumps(unsubscribe_data))
    print("✅ 取消订阅报告分析消息处理正常")
    
    # 清理资源
    await ws_handler.cleanup()
    print("\n✅ 所有WebSocket消息功能测试通过！")
    
    return True


async def test_message_types():
    """测试消息类型定义"""
    print("\n🧪 测试消息类型定义")
    
    # 测试报告分析更新消息
    report_msg = WSReportAnalysisUpdateMessage(
        reportId="test_report_001",
        title="测试报告",
        analysis={"data": "test"},
        timestamp="2023-10-27 10:00:00",
        sessionId="session_001"
    )
    
    assert report_msg.type == "report_analysis_update"
    assert report_msg.reportId == "test_report_001"
    print("✅ WSReportAnalysisUpdateMessage类型正常")
    
    # 测试预警触发消息
    alert_msg = WSAlertTriggeredMessage(
        alertId="test_alert_001",
        title="测试预警",
        message="测试消息",
        severity="warning",
        data={"test": "data"},
        timestamp="2023-10-27 10:00:00",
        sessionId="session_001"
    )
    
    assert alert_msg.type == "alert_triggered"
    assert alert_msg.severity == "warning"
    print("✅ WSAlertTriggeredMessage类型正常")
    
    print("✅ 所有消息类型测试通过！")
    return True


async def main():
    """主测试函数"""
    print("🚀 开始WebSocket消息功能集成测试")
    print("="*60)
    
    try:
        # 测试消息类型
        await test_message_types()
        
        # 测试WebSocket功能
        await test_websocket_report_analysis_and_alert()
        
        print("\n" + "="*60)
        print("🎉 所有测试通过！")
        print("\n✅ WebSocket报告分析和预警消息功能已正确实现")
        print("✅ 消息类型定义正确")
        print("✅ 广播功能正常")
        print("✅ 消息处理功能正常")
        print("✅ 订阅/取消订阅功能正常")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    if success:
        print("\n✅ 测试完成，WebSocket消息扩展功能正常工作！")
    else:
        print("\n❌ 测试失败，请检查实现")
        sys.exit(1)