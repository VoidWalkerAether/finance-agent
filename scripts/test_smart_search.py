#!/usr/bin/env python3
"""
测试智能搜索功能

功能测试：
1. 意图识别测试
2. 金融问题搜索测试（本地数据库）
3. 通用问题搜索测试（网络搜索）
4. 智能搜索端到端测试

使用方法:
python scripts/test_smart_search.py
"""

import asyncio
import aiohttp
import json
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))


async def test_classify_intent():
    """测试意图识别接口"""
    print("\n" + "=" * 60)
    print("🧪 Test 1: 意图识别 (Intent Classification)")
    print("=" * 60)
    
    test_cases = [
        {
            "name": "金融问题 - 黄金投资",
            "query": "现在是买入黄金的好时机吗？",
            "expected_intent": "FINANCE"
        },
        {
            "name": "金融问题 - A股分析",
            "query": "A股现在处于什么阶段？",
            "expected_intent": "FINANCE"
        },
        {
            "name": "金融问题 - 芯片投资",
            "query": "AI芯片概念股有哪些值得关注？",
            "expected_intent": "FINANCE"
        },
        {
            "name": "通用问题 - 天气",
            "query": "今天北京天气怎么样？",
            "expected_intent": "GENERAL"
        },
        {
            "name": "通用问题 - 常识",
            "query": "世界上最高的山峰是什么？",
            "expected_intent": "GENERAL"
        },
        {
            "name": "通用问题 - 闲聊",
            "query": "你好，今天过得怎么样？",
            "expected_intent": "GENERAL"
        }
    ]
    
    async with aiohttp.ClientSession() as session:
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n📝 测试用例 {i}: {test_case['name']}")
            print(f"   查询: {test_case['query']}")
            
            payload = {"query": test_case['query']}
            
            try:
                async with session.post(
                    "http://localhost:3000/api/search/classify",
                    json=payload
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        intent = data.get("intent", "UNKNOWN")
                        reason = data.get("reason", "")
                        confidence = data.get("confidence", 0.0)
                        
                        print(f"   结果: {intent}")
                        print(f"   理由: {reason}")
                        print(f"   置信度: {confidence:.2f}")
                        
                        if intent == test_case['expected_intent']:
                            print(f"   ✅ 通过 (期望: {test_case['expected_intent']})")
                        else:
                            print(f"   ❌ 失败 (期望: {test_case['expected_intent']}, 实际: {intent})")
                    else:
                        print(f"   ❌ HTTP 错误: {response.status}")
                        error_text = await response.text()
                        print(f"   错误信息: {error_text}")
            except Exception as e:
                print(f"   ❌ 请求失败: {e}")


async def test_smart_search_finance():
    """测试金融问题智能搜索（本地数据库）"""
    print("\n" + "=" * 60)
    print("🧪 Test 2: 金融问题智能搜索 (本地数据库)")
    print("=" * 60)
    
    test_queries = [
        "黄金投资策略分析",
        "A股市场现状如何",
        "AI芯片行业前景"
    ]
    
    async with aiohttp.ClientSession() as session:
        for i, query in enumerate(test_queries, 1):
            print(f"\n📝 查询 {i}: {query}")
            
            payload = {
                "query": query,
                "limit": 5
            }
            
            try:
                async with session.post(
                    "http://localhost:3000/api/search/smart",
                    json=payload
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        print(f"   意图: {data.get('intent', {}).get('intent', 'UNKNOWN')}")
                        print(f"   搜索类型: {data.get('search_type', 'unknown')}")
                        
                        results = data.get('results', [])
                        print(f"   结果数量: {len(results)}")
                        
                        if results:
                            print(f"   前 3 条结果:")
                            for j, result in enumerate(results[:3], 1):
                                title = result.get('title', '无标题')
                                score = result.get('score', 0.0)
                                print(f"      {j}. {title} (相关度: {score:.3f})")
                            print(f"   ✅ 测试通过")
                        else:
                            print(f"   ⚠️  未找到结果")
                    else:
                        print(f"   ❌ HTTP 错误: {response.status}")
                        error_text = await response.text()
                        print(f"   错误信息: {error_text}")
            except Exception as e:
                print(f"   ❌ 请求失败: {e}")


async def test_smart_search_general():
    """测试通用问题智能搜索（网络搜索）"""
    print("\n" + "=" * 60)
    print("🧪 Test 3: 通用问题智能搜索 (网络搜索)")
    print("=" * 60)
    
    print("\n⚠️  注意: 此测试需要 ANTHROPIC_AUTH_TOKEN 环境变量")
    print("⚠️  注意: 此测试会调用 Claude API 并产生费用")
    
    choice = input("\n是否继续测试网络搜索功能? (y/n): ")
    if choice.lower() != 'y':
        print("跳过网络搜索测试")
        return
    
    test_queries = [
        "今天北京的天气如何",
        "2024年诺贝尔物理学奖得主是谁"
    ]
    
    async with aiohttp.ClientSession() as session:
        for i, query in enumerate(test_queries, 1):
            print(f"\n📝 查询 {i}: {query}")
            
            payload = {
                "query": query,
                "limit": 5
            }
            
            try:
                # 网络搜索可能需要较长时间
                timeout = aiohttp.ClientTimeout(total=60)
                async with session.post(
                    "http://localhost:3000/api/search/smart",
                    json=payload,
                    timeout=timeout
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        print(f"   意图: {data.get('intent', {}).get('intent', 'UNKNOWN')}")
                        print(f"   搜索类型: {data.get('search_type', 'unknown')}")
                        
                        results = data.get('results', [])
                        print(f"   结果数量: {len(results)}")
                        
                        if results:
                            print(f"   搜索结果预览:")
                            for j, result in enumerate(results, 1):
                                content = result.get('content', '')
                                preview = content[:200] + "..." if len(content) > 200 else content
                                print(f"      {preview}")
                            print(f"   ✅ 测试通过")
                        else:
                            print(f"   ⚠️  未找到结果")
                    else:
                        print(f"   ❌ HTTP 错误: {response.status}")
                        error_text = await response.text()
                        print(f"   错误信息: {error_text}")
            except asyncio.TimeoutError:
                print(f"   ❌ 请求超时（超过 60 秒）")
            except Exception as e:
                print(f"   ❌ 请求失败: {e}")


async def test_edge_cases():
    """测试边界情况"""
    print("\n" + "=" * 60)
    print("🧪 Test 4: 边界情况测试")
    print("=" * 60)
    
    test_cases = [
        {
            "name": "空查询",
            "payload": {"query": ""},
            "should_fail": True
        },
        {
            "name": "缺少 query 参数",
            "payload": {},
            "should_fail": True
        },
        {
            "name": "超长查询",
            "payload": {"query": "黄金" * 500},
            "should_fail": False
        },
        {
            "name": "特殊字符查询",
            "payload": {"query": "!@#$%^&*()黄金"},
            "should_fail": False
        }
    ]
    
    async with aiohttp.ClientSession() as session:
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n📝 测试用例 {i}: {test_case['name']}")
            
            try:
                async with session.post(
                    "http://localhost:3000/api/search/smart",
                    json=test_case['payload']
                ) as response:
                    if test_case['should_fail']:
                        if response.status != 200:
                            print(f"   ✅ 正确返回错误 (状态码: {response.status})")
                        else:
                            print(f"   ❌ 应该失败但成功了")
                    else:
                        if response.status == 200:
                            print(f"   ✅ 正常处理")
                        else:
                            print(f"   ❌ 处理失败 (状态码: {response.status})")
            except Exception as e:
                if test_case['should_fail']:
                    print(f"   ✅ 正确抛出异常: {e}")
                else:
                    print(f"   ❌ 不应该失败: {e}")


async def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("🧪 智能搜索功能测试套件")
    print("=" * 60)
    print("\n确保服务器运行在 http://localhost:3000")
    print("启动服务器: python server/server.py")
    
    try:
        # 等待用户确认
        input("\n按 Enter 键开始测试...")
        
        # 测试 1: 意图识别
        #await test_classify_intent()
        
        # 测试 2: 金融问题搜索（本地数据库）
        #await test_smart_search_finance()
        
        # 测试 3: 通用问题搜索（网络搜索，可选）
        await test_smart_search_general()
        
        # 测试 4: 边界情况
        await test_edge_cases()
        
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
