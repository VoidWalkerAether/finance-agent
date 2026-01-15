"""
导入实际报告数据到数据库

导入用户提供的实际数据:
1. analysis_A股与黄金综合策略_20251127_105237.json
2. A股4000拉锯要不要买黄金_20251126102506_11_342_cleaned.txt

运行: python scripts/import_report.py
"""

import asyncio
import json
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from database.database_manager import DatabaseManager


async def import_actual_report():
    """导入用户提供的实际报告"""
    
    print("=" * 70)
    print("📥 导入 A股黄金报告到数据库")
    print("=" * 70)
    
    # 1. 初始化数据库
    print("\n1️⃣ 初始化数据库...")
    db = DatabaseManager("data/finance.db")
    print("✅ 数据库初始化成功")
    
    # 2. 定位文件路径
    print("\n2️⃣ 定位数据文件...")
    json_path = project_root / 'analysis_A股与黄金综合策略_20251127_105237.json'
    txt_path = project_root / 'A股4000拉锯要不要买黄金_20251126102506_11_342_cleaned.txt'
    
    if not json_path.exists():
        print(f"❌ JSON 文件未找到: {json_path}")
        return
    
    if not txt_path.exists():
        print(f"❌ TXT 文件未找到: {txt_path}")
        return
    
    print(f"✅ JSON 文件: {json_path.name}")
    print(f"✅ TXT 文件: {txt_path.name}")
    
    # 3. 读取 JSON 分析文件
    print("\n3️⃣ 读取 JSON 分析数据...")
    with open(json_path, 'r', encoding='utf-8') as f:
        analysis = json.load(f)
    
    print(f"✅ JSON 数据加载成功")
    print(f"   - 报告类型: {analysis['report_info']['type']}")
    print(f"   - 报告分类: {analysis['report_info']['category']}")
    print(f"   - 重要性评分: {analysis['key_metrics']['importance_score']}")
    print(f"   - 投资建议: {analysis['investment_advice']['action']}")
    
    # 4. 读取原始文本文件
    print("\n4️⃣ 读取原始文本内容...")
    with open(txt_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    content_preview = content[:100].replace('\n', ' ')
    print(f"✅ 文本内容加载成功")
    print(f"   - 文件大小: {len(content)} 字符")
    print(f"   - 内容预览: {content_preview}...")
    
    # 5. 构建 report_data
    print("\n5️⃣ 构建报告数据结构...")
    report_data = {
        # 唯一标识 (使用 JSON 文件名)
        'report_id': json_path.stem,  # 'analysis_A股与黄金综合策略_20251127_105237'
        
        # ============ 从 report_info 提取 ============
        'title': analysis['report_info']['title'],
        'report_type': analysis['report_info']['type'],
        'category': analysis['report_info']['category'],
        'date_published': analysis['report_info']['date'],
        'sources': analysis['report_info']['sources'],  # list, 将自动转 JSON
        
        # ============ 原始文本 ============
        'content': content,
        
        # ============ 从 summary 提取 ============
        'summary_one_sentence': analysis['summary']['one_sentence'],
        'sentiment': analysis['summary']['sentiment'],
        'key_drivers': analysis['summary']['key_drivers'],  # list, 将自动转 JSON
        
        # ============ 从 key_metrics 提取 ============
        'importance_score': analysis['key_metrics']['importance_score'],
        'urgency_score': analysis['key_metrics']['urgency_score'],
        'reliability_score': analysis['key_metrics']['reliability_score'],
        
        # ============ 从 investment_advice 提取 ============
        'action': analysis['investment_advice']['action'],
        'target_allocation': analysis['investment_advice']['target_allocation'],
        'timing': analysis['investment_advice']['timing'],
        'holding_period': analysis['investment_advice']['holding_period'],
        'confidence_level': analysis['investment_advice']['confidence_level'],
        
        # ============ 完整 JSON 数据 ============
        'analysis_json': analysis,  # dict, 将自动转 JSON
        
        # ============ 文件信息 ============
        'original_file_path': str(txt_path.absolute()),
        'file_size': txt_path.stat().st_size
    }
    
    print(f"✅ 报告数据结构构建完成")
    print(f"   - report_id: {report_data['report_id']}")
    print(f"   - title: {report_data['title']}")
    
    # 6. 插入数据库
    print("\n6️⃣ 插入报告到数据库...")
    try:
        report_id = await db.upsert_report(report_data)
        print(f"✅ 报告插入成功!")
        print(f"   - 数据库 ID: {report_id}")
        print(f"   - report_id: {report_data['report_id']}")
    except Exception as e:
        print(f"❌ 插入失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 7. 验证数据
    print("\n7️⃣ 验证导入的数据...")
    retrieved = await db.get_report(report_data['report_id'])
    
    if retrieved:
        print(f"✅ 数据验证成功!")
        print(f"   - 标题: {retrieved['title']}")
        print(f"   - 分类: {retrieved['category']}")
        print(f"   - 操作建议: {retrieved['action']}")
        print(f"   - 重要性: {retrieved['importance_score']}/10")
        print(f"   - 内容长度: {len(retrieved['content'])} 字符")
        print(f"   - JSON 字段类型: {type(retrieved['analysis_json'])}")
    else:
        print(f"❌ 数据验证失败: 无法查询到报告")
        return
    
    # 8. 测试 FTS5 全文搜索
    print("\n8️⃣ 测试 FTS5 全文搜索...")
    
    # 搜索 "黄金"
    results = await db.search_reports(query='黄金', limit=5)
    print(f"   - 搜索 '黄金': 找到 {len(results)} 条记录")
    
    # 搜索 "A股"
    results = await db.search_reports(query='A股', limit=5)
    print(f"   - 搜索 'A股': 找到 {len(results)} 条记录")
    
    # 搜索 "ETF"
    results = await db.search_reports(query='ETF', limit=5)
    print(f"   - 搜索 'ETF': 找到 {len(results)} 条记录")
    
    if results:
        print(f"\n   📄 搜索结果示例:")
        for i, r in enumerate(results[:2], 1):
            print(f"      {i}. {r['title']}")
            print(f"         - 分类: {r['category']}")
            print(f"         - 评分: {r['importance_score']}/10")
    
    # 9. 测试结构化查询
    print("\n9️⃣ 测试结构化查询...")
    
    # 按分类查询
    results = await db.search_reports(category='A股与黄金综合策略', limit=5)
    print(f"   - 分类查询: 找到 {len(results)} 条记录")
    
    # 按投资建议查询
    results = await db.search_reports(action='watch', limit=5)
    print(f"   - 投资建议 'watch': 找到 {len(results)} 条记录")
    
    # 高优先级报告
    results = await db.search_reports(min_importance=8, limit=5)
    print(f"   - 高优先级 (≥8分): 找到 {len(results)} 条记录")
    
    # 10. 查询统计信息
    print("\n🔟 数据库统计信息...")
    stats = await db.get_report_stats()
    print(f"   - 总报告数: {stats['total_reports']}")
    print(f"   - 分类分布: {stats['by_category']}")
    print(f"   - 投资建议分布: {stats['by_action']}")
    print(f"   - 平均重要性: {stats['avg_importance']}/10")
    
    # 11. 测试高优先级视图
    print("\n1️⃣1️⃣ 查询高优先级报告视图...")
    high_priority = await db.get_high_priority_reports(limit=5)
    print(f"   - 高优先级报告数: {len(high_priority)}")
    
    if high_priority:
        print(f"\n   📊 高优先级报告:")
        for i, report in enumerate(high_priority, 1):
            print(f"      {i}. {report['title']}")
            print(f"         - 重要性: {report['importance_score']}/10")
            print(f"         - 紧急性: {report['urgency_score']}/10")
            print(f"         - 操作: {report['action']}")
    
    print("\n" + "=" * 70)
    print("🎉 报告导入成功!")
    print("=" * 70)
    print(f"\n📌 下一步:")
    print(f"   1. 使用 search_reports() 搜索报告")
    print(f"   2. 使用 get_report() 查询详细信息")
    print(f"   3. 测试 FTS5 中文全文搜索")
    print(f"   4. 开始实现 Session 类 (Phase 2.1)")


async def show_database_info():
    """显示数据库当前状态"""
    print("\n" + "=" * 70)
    print("📊 数据库当前状态")
    print("=" * 70)
    
    db = DatabaseManager("data/finance.db")
    
    # 统计信息
    stats = await db.get_report_stats()
    print(f"\n总报告数: {stats['total_reports']}")
    
    if stats['total_reports'] > 0:
        print(f"\n分类分布:")
        for category, count in stats['by_category'].items():
            print(f"  - {category}: {count}")
        
        print(f"\n投资建议分布:")
        for action, count in stats['by_action'].items():
            print(f"  - {action}: {count}")
        
        print(f"\n平均重要性评分: {stats['avg_importance']}/10")
        
        # 列出最近的报告
        print(f"\n最近的报告:")
        results = await db.search_reports(limit=5)
        for i, report in enumerate(results, 1):
            print(f"  {i}. {report['title']}")
            print(f"     - ID: {report['report_id']}")
            print(f"     - 评分: {report['importance_score']}/10")
    else:
        print("\n数据库为空，请先运行导入。")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='导入报告数据到数据库')
    parser.add_argument('--info', action='store_true', help='显示数据库当前状态')
    args = parser.parse_args()
    
    try:
        if args.info:
            asyncio.run(show_database_info())
        else:
            asyncio.run(import_actual_report())
    except KeyboardInterrupt:
        print("\n\n⚠️ 用户中断")
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
