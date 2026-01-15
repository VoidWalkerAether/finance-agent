#!/usr/bin/env python3
"""
测试报告关联性分析功能
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.database_manager import DatabaseManager
from database.relationship_analyzer import ReportRelationshipAnalyzer


async def test_relationship_analysis():
    """测试关联性分析功能"""
    print("🚀 开始测试报告关联性分析功能")
    print("=" * 50)
    
    # 初始化数据库和分析器
    db_manager = DatabaseManager()
    analyzer = ReportRelationshipAnalyzer(db_manager)
    
    # 检查是否有报告可以分析
    try:
        # 获取所有报告
        all_reports = await db_manager.list_ui_states()  # 这里我们借用这个方法来检查数据库状态
        print(f"✅ 数据库连接正常")
        
        # 获取最新的几个报告
        recent_reports = await db_manager.execute_raw_query(
            "SELECT report_id, title, category FROM reports ORDER BY date_published DESC LIMIT 5"
        )
        
        if not recent_reports:
            print("⚠️  数据库中没有报告，无法进行关联分析测试")
            return
        
        print(f"📋 找到 {len(recent_reports)} 个报告:")
        for i, report in enumerate(recent_reports, 1):
            print(f"  {i}. {report['title']} ({report['report_id']})")
        
        # 选择第一个报告进行关联分析测试
        test_report_id = recent_reports[0]['report_id']
        print(f"\n🔍 开始分析报告 '{recent_reports[0]['title']}' 的关联关系...")
        
        # 执行关联分析
        relationships = await analyzer.analyze_report_relationships(test_report_id)
        
        print(f"\n📊 分析结果:")
        if relationships.get('relations'):
            print(f"  找到 {len(relationships['relations'])} 个关联关系:")
            for i, relation in enumerate(relationships['relations'], 1):
                print(f"  {i}. {relation['target_report_id']}")
                print(f"     类型: {relation['relation_type']}")
                print(f"     相似度: {relation['score']:.2f}")
                print(f"     摘要: {relation['summary']}")
                print(f"     证据: {relation['evidence']}")
                print()
        else:
            print("  未找到关联关系")
            
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


async def test_find_related_reports():
    """测试查找关联报告功能"""
    print("\n🔍 测试查找关联报告功能")
    print("=" * 50)
    
    # 初始化数据库和分析器
    db_manager = DatabaseManager()
    analyzer = ReportRelationshipAnalyzer(db_manager)
    
    try:
        # 获取一个测试报告ID
        recent_reports = await db_manager.execute_raw_query(
            "SELECT report_id, title, category FROM reports ORDER BY date_published DESC LIMIT 1"
        )
        
        if not recent_reports:
            print("⚠️  数据库中没有报告，无法进行测试")
            return
            
        test_report_id = recent_reports[0]['report_id']
        print(f"📋 测试报告: {recent_reports[0]['title']}")
        
        # 查找关联报告
        related_reports = await analyzer.find_related_reports(test_report_id, max_results=5)
        
        print(f"\n📊 查找结果:")
        if related_reports:
            print(f"  找到 {len(related_reports)} 个关联报告:")
            for i, report in enumerate(related_reports, 1):
                print(f"  {i}. {report['title']}")
                print(f"     ID: {report['related_report_id']}")
                print(f"     相似度: {report['similarity_score']:.2f}")
                print(f"     分类: {report['category']}")
                print(f"     投资建议: {report['action']}")
                print()
        else:
            print("  未找到关联报告")
            
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("🧪 Finance Agent 报告关联性分析测试")
    
    # 运行测试
    asyncio.run(test_relationship_analysis())
    asyncio.run(test_find_related_reports())
    
    print("\n✅ 测试完成")