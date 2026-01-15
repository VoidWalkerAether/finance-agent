"""
Agent Tools 测试脚本
测试 callAgent() 功能

测试场景:
1. 基本结构化输出
2. 复杂 schema
3. 不同模型选择
4. 错误处理

注意: 需要安装 claude-agent-sdk
  pip install claude-agent-sdk
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from ccsdk.agent_tools import AgentTools, get_agent_tools


async def test_basic_call():
    """测试 1: 基本调用"""
    print("\n🧪 Test 1: Basic Call Agent")
    print("=" * 60)
    
    tools = AgentTools()
    
    # 简单的分类任务
    schema = {
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "description": "报告类别"
            },
            "sentiment": {
                "type": "string",
                "enum": ["positive", "negative", "neutral"],
                "description": "情感倾向"
            }
        },
        "required": ["category", "sentiment"]
    }
    
    prompt = """
    分析以下金融报告并分类：
    
    标题: A股市场强势反弹，科技股领涨
    内容: 今日A股市场整体表现强劲，上证指数上涨2.3%，创业板指数上涨3.1%。
          科技板块表现尤为突出，半导体、人工智能等概念股涨幅居前。
    """
    
    result = await tools.call_agent(prompt, schema)
    
    # 验证结果
    assert isinstance(result, dict), "Result should be a dict"
    assert "category" in result, "Should have category field"
    assert "sentiment" in result, "Should have sentiment field"
    assert result["sentiment"] in ["positive", "negative", "neutral"], "Invalid sentiment"
    
    print(f"\n✅ Test passed!")
    print(f"  - Category: {result['category']}")
    print(f"  - Sentiment: {result['sentiment']}")


async def test_complex_schema():
    """测试 2: 复杂 Schema"""
    print("\n🧪 Test 2: Complex Schema")
    print("=" * 60)
    
    tools = get_agent_tools()  # 使用单例
    
    # 复杂的报告分析
    schema = {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "报告标题"
            },
            "summary": {
                "type": "string",
                "description": "简短摘要（50字以内）"
            },
            "key_points": {
                "type": "array",
                "items": {"type": "string"},
                "description": "关键要点列表"
            },
            "risk_level": {
                "type": "string",
                "enum": ["low", "medium", "high"],
                "description": "风险等级"
            },
            "action_recommendation": {
                "type": "string",
                "enum": ["buy", "hold", "sell"],
                "description": "行动建议"
            },
            "confidence": {
                "type": "number",
                "minimum": 0,
                "maximum": 1,
                "description": "置信度 (0-1)"
            }
        },
        "required": ["title", "summary", "key_points", "risk_level", "action_recommendation", "confidence"]
    }
    
    prompt = """
    分析以下金融报告：
    
    【黄金投资分析】
    近期国际黄金价格持续上涨，已突破2100美元/盎司。主要驱动因素包括：
    1. 美联储暂停加息，美元走弱
    2. 地缘政治风险上升
    3. 全球通胀预期增强
    
    技术面分析显示黄金处于上升通道，短期支撑位在2080美元。
    但需注意，如果美国经济数据超预期，可能引发获利回吐。
    
    请提供完整的分析和投资建议。
    """
    
    result = await tools.call_agent(prompt, schema)
    
    # 验证结果
    assert isinstance(result, dict), "Result should be a dict"
    assert "title" in result, "Should have title"
    assert "summary" in result, "Should have summary"
    assert "key_points" in result, "Should have key_points"
    assert isinstance(result["key_points"], list), "key_points should be a list"
    assert "risk_level" in result, "Should have risk_level"
    assert "action_recommendation" in result, "Should have action_recommendation"
    assert "confidence" in result, "Should have confidence"
    assert 0 <= result["confidence"] <= 1, "Confidence should be between 0 and 1"
    
    print(f"\n✅ Test passed!")
    print(f"  - Title: {result['title']}")
    print(f"  - Summary: {result['summary']}")
    print(f"  - Key Points: {len(result['key_points'])} items")
    print(f"  - Risk Level: {result['risk_level']}")
    print(f"  - Recommendation: {result['action_recommendation']}")
    print(f"  - Confidence: {result['confidence']}")


async def test_financial_transaction_analysis():
    """测试 3: 金融交易分析"""
    print("\n🧪 Test 3: Financial Transaction Analysis")
    print("=" * 60)
    
    tools = get_agent_tools()
    
    # 交易分类和提取
    schema = {
        "type": "object",
        "properties": {
            "transactions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "description": {"type": "string"},
                        "amount": {"type": "number"},
                        "category": {
                            "type": "string",
                            "enum": ["餐饮", "交通", "娱乐", "购物", "住房", "医疗", "其他"]
                        },
                        "is_recurring": {"type": "boolean"}
                    },
                    "required": ["description", "amount", "category", "is_recurring"]
                }
            },
            "total_amount": {"type": "number"},
            "spending_summary": {"type": "string"}
        },
        "required": ["transactions", "total_amount", "spending_summary"]
    }
    
    prompt = """
    从以下文本中提取所有交易信息：
    
    今天早上在星巴克买了一杯咖啡，花了35元。
    中午打车去见客户，车费62元。
    下午在超市买了一些日用品，总共156元。
    晚上和朋友聚餐，AA制我付了180元。
    
    请提取所有交易，分类并计算总额。
    """
    
    result = await tools.call_agent(prompt, schema)
    
    # 验证结果
    assert isinstance(result, dict), "Result should be a dict"
    assert "transactions" in result, "Should have transactions"
    assert isinstance(result["transactions"], list), "transactions should be a list"
    assert len(result["transactions"]) > 0, "Should have at least one transaction"
    assert "total_amount" in result, "Should have total_amount"
    assert "spending_summary" in result, "Should have spending_summary"
    
    print(f"\n✅ Test passed!")
    print(f"  - Transactions: {len(result['transactions'])} items")
    print(f"  - Total Amount: ¥{result['total_amount']}")
    print(f"  - Summary: {result['spending_summary']}")
    
    # 打印每笔交易
    for i, tx in enumerate(result["transactions"], 1):
        print(f"    {i}. {tx['description']} - ¥{tx['amount']} ({tx['category']})")


async def test_error_handling():
    """测试 4: 错误处理"""
    print("\n🧪 Test 4: Error Handling")
    print("=" * 60)
    
    # 测试无效 API Key
    try:
        invalid_tools = AgentTools(api_key="invalid_key")
        schema = {"type": "object", "properties": {"test": {"type": "string"}}}
        await invalid_tools.call_agent("test", schema)
        assert False, "Should raise error with invalid API key"
    except Exception as e:
        print(f"  ✅ Correctly caught error: {type(e).__name__}")
    
    # 测试缺少 API Key
    import os
    old_key = os.environ.get("ANTHROPIC_API_KEY")
    if old_key:
        del os.environ["ANTHROPIC_API_KEY"]
    
    try:
        AgentTools()
        assert False, "Should raise error when API key is missing"
    except ValueError as e:
        print(f"  ✅ Correctly caught missing API key: {e}")
    
    # 恢复环境变量
    if old_key:
        os.environ["ANTHROPIC_API_KEY"] = old_key
    
    print("\n✅ Test passed!")


async def test_model_selection():
    """测试 5: 模型选择由环境变量控制"""
    print("\n🧪 Test 5: Model Selection (via Environment)")
    print("=" * 60)
    
    tools = get_agent_tools()
    
    schema = {
        "type": "object",
        "properties": {
            "answer": {"type": "string"}
        },
        "required": ["answer"]
    }
    
    # 模型由环境变量 ANTHROPIC_MODEL 控制
    # 或由 SDK 默认配置决定
    print(f"\n  使用环境变量配置的模型")
    result = await tools.call_agent(
        prompt="用一句话总结：量子计算的核心优势是什么？",
        schema=schema
    )
    assert "answer" in result, "Should return answer"
    print(f"    ✅ 响应: {result['answer'][:50]}...")
    
    print("\n✅ Test passed!")


async def main():
    """运行所有测试"""
    print("=" * 60)
    print("🧪 Agent Tools Test Suite")
    print("=" * 60)
    
    try:
        await test_basic_call()
        await test_complex_schema()
        await test_financial_transaction_analysis()
        await test_error_handling()
        await test_model_selection()
        
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
