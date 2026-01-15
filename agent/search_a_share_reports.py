#!/usr/bin/env python3
#-*-coding:utf-8 -*-
"""
搜索本地报告数据库中关于A股的相关报告
使用多种关键词进行搜索："A股"、"上涨空间"、"市场走势"、"投资机会"、"行情分析"等
"""

import sqlite3
import json
from datetime import datetime

def search_a_share_reports():
    """搜索A股相关报告"""

    # 数据库路径
    db_path = '/Users/caiwei/workbench/claude-agent-sdk-demos/finance-agent/data/finance.db'

    # 搜索关键词
    keywords = [
        'A股', '上涨', '涨幅', '行情', '走势', '投资机会', '市场', '分析',
        '策略', '牛市', '熊市', '震荡', '反弹', '回调', '突破', '支撑'
    ]

    # 创建数据库连接
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # 使结果可以按列名访问
    cursor = conn.cursor()

    print("="*80)
    print("A股相关报告搜索结果")
    print("="*80)

    total_reports_found = 0

    for keyword in keywords:
        print(f"\n【关键词：{keyword}】")
        print("-"*60)

        # 构建查询（搜索标题、分类、内容和摘要）
        query = """
        SELECT title, category, date_published, summary_one_sentence, action,
               importance_score, urgency_score, reliability_score, sentiment,
               key_drivers, target_allocation, timing, confidence_level
        FROM reports
        WHERE title LIKE ? OR category LIKE ? OR content LIKE ? OR summary_one_sentence LIKE ?
        ORDER BY importance_score DESC, date_published DESC
        LIMIT 10
        """

        # 执行查询
        search_pattern = f'%{keyword}%'
        cursor.execute(query, (search_pattern, search_pattern, search_pattern, search_pattern))
        results = cursor.fetchall()

        if results:
            total_reports_found += len(results)
            for i, row in enumerate(results, 1):
                print(f"\n{i}. 报告标题：{row['title']}")
                print(f"   分类：{row['category']}")
                print(f"   发布日期：{row['date_published']}")
                print(f"   一句话摘要：{row['summary_one_sentence']}")
                print(f"   操作建议：{row['action']}")
                print(f"   重要性评分：{row['importance_score']}/10")
                print(f"   情绪态度：{row['sentiment']}")
                if row['key_drivers']:
                    try:
                        drivers = json.loads(row['key_drivers'])
                        print(f"   核心驱动因素：{', '.join(drivers)}")
                    except:
                        print(f"   核心驱动因素：{row['key_drivers']}")
                if row['target_allocation']:
                    print(f"   目标配置：{row['target_allocation']}")
                if row['timing']:
                    print(f"   时机建议：{row['timing']}")
        else:
            print("   未找到相关报告")

    print(f"\n{'='*80}")
    print(f"搜索结果统计：共找到 {total_reports_found} 份相关报告")
    print("="*80)

    # 显示最近的报告详情
    print("\n【最近的重要报告详情】")
    print("-"*60)

    cursor.execute("""
    SELECT title, category, date_published, content, summary_one_sentence,
           action, importance_score, sentiment, key_drivers, target_allocation,
           timing, confidence_level, holding_period
    FROM reports
    ORDER BY importance_score DESC, date_published DESC
    LIMIT 5
    """)

    latest_reports = cursor.fetchall()

    for i, row in enumerate(latest_reports, 1):
        print(f"\n{i}. {'='*60}")
        print(f"报告标题：{row['title']}")
        print(f"分类：{row['category']}")
        print(f"发布日期：{row['date_published']}")
        print(f"重要性评分：{row['importance_score']}/10")
        print(f"情绪态度：{row['sentiment']}")

        print(f"\n核心摘要：")
        print(f"  {row['summary_one_sentence']}")

        print(f"\n投资建议：")
        print(f"  操作建议：{row['action']}")
        print(f"  持有期：{row['holding_period']}")
        print(f"  信心水平：{row['confidence_level']}")

        if row['key_drivers']:
            try:
                drivers = json.loads(row['key_drivers'])
                print(f"  核心驱动因素：{', '.join(drivers)}")
            except:
                print(f"  核心驱动因素：{row['key_drivers']}")

        if row['target_allocation']:
            print(f"  资产配置建议：{row['target_allocation']}")

        if row['timing']:
            print(f"  时机建议：{row['timing']}")

        # 显示部分内容预览
        if row['content']:
            content_preview = row['content'][:800] + '...' if len(row['content']) > 800 else row['content']
            print(f"\n内容预览：")
            print(f"  {content_preview}")

        print(f"\n{'='*80}")

    conn.close()

if __name__ == "__main__":
    search_a_share_reports()