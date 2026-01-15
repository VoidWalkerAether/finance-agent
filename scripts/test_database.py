"""
测试 DatabaseManager

运行: python -m asyncio scripts/test_database.py
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from database.database_manager import DatabaseManager


async def test_database():
    """测试数据库基本功能"""
    
    print("=" * 60)
    print("🧪 测试 Finance Agent DatabaseManager")
    print("=" * 60)
    
    # 1. 初始化数据库
    print("\n1️⃣ 初始化数据库...")
    db = DatabaseManager("data/finance_test.db")
    print("✅ 数据库初始化成功")
    
    # 2. 测试 UI State
    print("\n2️⃣ 测试 UI State 管理...")
    test_state = {
        "high_priority_reports": [
            {
                "report_id": "test_001",
                "title": "测试报告",
                "importance_score": 9
            }
        ],
        "stats": {
            "total_reports": 1,
            "this_month": 1
        }
    }
    
    await db.set_ui_state("report_dashboard", test_state)
    retrieved_state = await db.get_ui_state("report_dashboard")
    
    assert retrieved_state == test_state, "UI State 读写失败"
    print("✅ UI State 读写正常")
    
    # 3. 测试报告插入
    print("\n3️⃣ 测试报告插入...")
    test_report = {
        'report_id': 'test_report_001',
        'title': '测试报告：A股走势分析',
        'report_type': '市场策略报告',
        'category': 'A股策略',
        'date_published': '2025-11',
        'sources': ['测试来源1', '测试来源2'],
        'content': '这是一份测试报告的内容...',
        'summary_one_sentence': '这是一句话总结',
        'sentiment': 'neutral',
        'key_drivers': ['政策面', '基本面'],
        'importance_score': 8,
        'urgency_score': 7,
        'reliability_score': 9,
        'action': 'watch',
        'target_allocation': '测试配置建议',
        'timing': '测试时机',
        'holding_period': 'medium',
        'confidence_level': 'medium',
        'analysis_json': {
            'test_key': 'test_value',
            'metrics': {'score': 9}
        },
        'original_file_path': '/test/path/report.txt',
        'file_size': 1024
    }
    
    report_id = await db.upsert_report(test_report)
    print(f"✅ 报告插入成功 (ID: {report_id})")
    
    # 4. 测试报告查询
    print("\n4️⃣ 测试报告查询...")
    retrieved_report = await db.get_report('test_report_001')
    
    assert retrieved_report is not None, "报告查询失败"
    assert retrieved_report['title'] == test_report['title'], "报告数据不一致"
    assert isinstance(retrieved_report['analysis_json'], dict), "JSON 反序列化失败"
    print("✅ 报告查询正常")
    
    # 5. 测试搜索功能
    print("\n5️⃣ 测试搜索功能...")
    
    # 按分类搜索
    results = await db.search_reports(category='A股策略', limit=10)
    assert len(results) > 0, "分类搜索失败"
    print(f"✅ 分类搜索: 找到 {len(results)} 条记录")
    
    # 按投资建议搜索
    results = await db.search_reports(action='watch', limit=10)
    assert len(results) > 0, "投资建议搜索失败"
    print(f"✅ 投资建议搜索: 找到 {len(results)} 条记录")
    
    # 按评分搜索
    results = await db.search_reports(min_importance=8, limit=10)
    assert len(results) > 0, "评分搜索失败"
    print(f"✅ 评分搜索: 找到 {len(results)} 条记录")
    
    # 6. 测试全文搜索 (FTS5)
    print("\n6️⃣ 测试 FTS5 全文搜索...")
    results = await db.search_reports(query='A股', limit=10)
    print(f"✅ 全文搜索 'A股': 找到 {len(results)} 条记录")
    
    # 7. 测试统计功能
    print("\n7️⃣ 测试统计功能...")
    stats = await db.get_report_stats()
    print(f"✅ 统计信息:")
    print(f"   - 总报告数: {stats['total_reports']}")
    print(f"   - 分类分布: {stats['by_category']}")
    print(f"   - 投资建议分布: {stats['by_action']}")
    print(f"   - 平均重要性: {stats['avg_importance']}")
    
    # 8. 测试组件实例管理
    print("\n8️⃣ 测试组件实例管理...")
    await db.create_component_instance(
        instance_id='comp_test_001',
        component_id='report_dashboard',
        state_id='report_dashboard',
        session_id='test_session_001'
    )
    
    instances = await db.get_component_instances_by_session('test_session_001')
    assert len(instances) > 0, "组件实例查询失败"
    print(f"✅ 组件实例管理: 找到 {len(instances)} 个实例")
    
    # 9. 测试高优先级报告视图
    print("\n9️⃣ 测试高优先级报告视图...")
    high_priority = await db.get_high_priority_reports(limit=5)
    print(f"✅ 高优先级报告: {len(high_priority)} 条")
    
    print("\n" + "=" * 60)
    print("🎉 所有测试通过!")
    print("=" * 60)


async def cleanup():
    """清理测试数据"""
    print("\n🧹 清理测试数据库...")
    test_db_path = Path("data/finance_test.db")
    if test_db_path.exists():
        test_db_path.unlink()
        print("✅ 测试数据库已删除")


if __name__ == "__main__":
    try:
        asyncio.run(test_database())
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        # 可选: 清理测试数据
        # asyncio.run(cleanup())
        pass
