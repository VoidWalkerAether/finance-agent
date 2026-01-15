"""
测试报告上传功能

测试场景:
1. 上传文本报告
2. 验证 AI 分析结果
3. 查询已上传的报告
"""

import asyncio
import aiohttp
import json


async def test_upload_report():
    """测试上传报告"""
    
    # 测试报告内容
    test_report = {
        "title": "2025年黄金市场展望 - 测试报告",
        "content": """
【核心观点】
2025年黄金市场预计将呈现震荡上行态势。主要驱动因素包括：
1. 美联储降息预期增强
2. 地缘政治风险持续
3. 全球央行增持黄金储备

【投资建议】
建议配置：黄金ETF 15-20%，实物黄金 5%
操作时机：逢低分批建仓
持有周期：6-12个月

【风险提示】
- 美元走强可能压制金价
- 实际利率上行风险
- 技术面调整压力
""",
        "category": "黄金市场分析"
    }
    
    print("=" * 60)
    print("📤 测试报告上传功能")
    print("=" * 60)
    
    async with aiohttp.ClientSession() as session:
        # 1. 上传报告
        print("\n1️⃣ 上传报告...")
        async with session.post(
            "http://localhost:3000/api/reports",
            data=test_report
        ) as resp:
            if resp.status == 200:
                result = await resp.json()
                print(f"   ✅ 上传成功!")
                print(f"   - Report ID: {result['report_id']}")
                print(f"   - Sentiment: {result['analysis_summary'].get('sentiment')}")
                print(f"   - Action: {result['analysis_summary'].get('action')}")
                print(f"   - Importance: {result['analysis_summary'].get('importance_score')}/10")
                print(f"   - Summary: {result['analysis_summary'].get('summary')}")
                
                report_id = result['report_id']
            else:
                error_text = await resp.text()
                print(f"   ❌ 上传失败: {resp.status}")
                print(f"   错误: {error_text}")
                return
        
        # 2. 查询报告详情
        print("\n2️⃣ 查询报告详情...")
        async with session.get(
            f"http://localhost:3000/api/reports/{report_id}"
        ) as resp:
            if resp.status == 200:
                result = await resp.json()
                report = result['report']
                print(f"   ✅ 查询成功!")
                print(f"   - Title: {report['title']}")
                print(f"   - Category: {report['category']}")
                print(f"   - Sentiment: {report['sentiment']}")
                print(f"   - Action: {report['action']}")
                
                # 显示投资建议
                if report.get('target_allocation'):
                    print(f"   - 建议配置: {report['target_allocation']}")
                if report.get('timing'):
                    print(f"   - 操作时机: {report['timing']}")
            else:
                print(f"   ❌ 查询失败: {resp.status}")
        
        # 3. 搜索报告
        print("\n3️⃣ 搜索报告（关键词：黄金）...")
        async with session.post(
            "http://localhost:3000/api/reports/search",
            json={"query": "黄金", "limit": 5}
        ) as resp:
            if resp.status == 200:
                result = await resp.json()
                print(f"   ✅ 搜索成功! 找到 {result['count']} 条结果")
                
                for i, r in enumerate(result['results'][:3], 1):
                    print(f"   {i}. {r['title']}")
                    print(f"      - 评分: {r.get('importance_score', 'N/A')}/10")
                    print(f"      - 建议: {r.get('action', 'N/A')}")
            else:
                print(f"   ❌ 搜索失败: {resp.status}")
        
        # 4. 获取报告统计
        print("\n4️⃣ 获取报告统计...")
        async with session.get(
            "http://localhost:3000/api/reports/stats/overview"
        ) as resp:
            if resp.status == 200:
                stats = await resp.json()
                print(f"   ✅ 统计信息:")
                print(f"   - 总报告数: {stats.get('total_reports', 0)}")
                print(f"   - 平均重要性: {stats.get('avg_importance', 0)}/10")
                
                if stats.get('by_category'):
                    print(f"   - 按分类:")
                    for cat, count in list(stats['by_category'].items())[:3]:
                        print(f"      • {cat}: {count} 份")
                
                if stats.get('by_action'):
                    print(f"   - 按建议:")
                    for action, count in stats['by_action'].items():
                        print(f"      • {action}: {count} 份")
            else:
                print(f"   ❌ 获取统计失败: {resp.status}")
    
    print("\n" + "=" * 60)
    print("✅ 测试完成!")
    print("=" * 60)


async def test_upload_with_file():
    """测试文件上传"""
    
    print("\n" + "=" * 60)
    print("📁 测试文件上传功能")
    print("=" * 60)
    
    # 创建测试文件
    test_content = """
【A股市场周报 - 2025-12-02】

核心观点：
本周A股市场呈现震荡整理态势，上证指数在3000点附近反复争夺。
主要驱动因素包括：
1. 政策面：稳增长政策陆续出台
2. 资金面：北向资金净流入100亿
3. 技术面：均线系统趋于粘合

板块表现：
- 科技板块领涨，半导体、AI概念活跃
- 消费板块走势分化，白酒龙头承压
- 金融板块表现平稳，银行股低位震荡

投资建议：
1. 配置建议：科技蓝筹30%，价值股50%，现金20%
2. 操作策略：逢低布局优质成长股
3. 持有周期：中长期（3-6个月）
4. 风险提示：关注外部市场波动风险
"""
    
    async with aiohttp.ClientSession() as session:
        # 使用 FormData 上传
        data = aiohttp.FormData()
        data.add_field('title', 'A股市场周报 - 测试文件上传')
        data.add_field('content', test_content)
        data.add_field('category', 'A股市场分析')
        
        print("\n📤 上传文件...")
        async with session.post(
            "http://localhost:3000/api/reports",
            data=data
        ) as resp:
            if resp.status == 200:
                result = await resp.json()
                print(f"✅ 文件上传成功!")
                print(f"   - Report ID: {result['report_id']}")
                print(f"   - 分析摘要: {result['analysis_summary'].get('summary', 'N/A')}")
            else:
                error_text = await resp.text()
                print(f"❌ 上传失败: {resp.status}")
                print(f"   错误: {error_text}")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    print("\n🧪 Finance Agent - 报告上传功能测试\n")
    
    try:
        # 运行测试
        asyncio.run(test_upload_report())
        asyncio.run(test_upload_with_file())
        
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断")
    except Exception as e:
        print(f"\n\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
