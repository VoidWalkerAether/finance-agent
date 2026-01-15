#!/usr/bin/env python3
"""
Finance Agent 数据库管理脚本

功能：
1. 清理所有报告数据
2. 清理特定报告数据
3. 显示数据库统计信息
4. 列出所有报告
5. 列出所有关联关系
6. 查询指定报告的关联关系

使用方法：
python cleanup_database.py [--all] [--report-id REPORT_ID] [--stats] [--list] [--list-relationships] [--report-relationships REPORT_ID]

参数：
--all: 清理所有报告数据
--report-id REPORT_ID: 清理指定报告ID的数据
--stats: 显示数据库统计信息
--list: 列出所有报告
--list-relationships: 列出所有关联关系
--report-relationships REPORT_ID: 查询指定报告的关联关系
"""

import argparse
import sqlite3
import os
from pathlib import Path
from typing import Optional
import sys

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

# 加载环境变量
env_path = project_root / '.env'
if env_path.exists():
    load_dotenv(env_path)

# 获取数据库路径
DATABASE_PATH = os.getenv('DATABASE_PATH', './data/finance.db')

def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def show_stats():
    """显示数据库统计信息"""
    print("📊 数据库统计信息")
    print("=" * 50)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 报告总数
        cursor.execute("SELECT COUNT(*) as count FROM reports")
        total_reports = cursor.fetchone()['count']
        print(f"📋 报告总数: {total_reports}")
        
        # 按分类统计
        cursor.execute("""
            SELECT category, COUNT(*) as count 
            FROM reports 
            WHERE category IS NOT NULL 
            GROUP BY category 
            ORDER BY count DESC
        """)
        categories = cursor.fetchall()
        print(f"\n📂 按分类统计:")
        for category in categories:
            print(f"   • {category['category']}: {category['count']} 份")
        
        # 按操作建议统计
        cursor.execute("""
            SELECT action, COUNT(*) as count 
            FROM reports 
            WHERE action IS NOT NULL 
            GROUP BY action 
            ORDER BY count DESC
        """)
        actions = cursor.fetchall()
        print(f"\n💡 按操作建议统计:")
        for action in actions:
            print(f"   • {action['action']}: {action['count']} 份")
        
        # 高优先级报告
        cursor.execute("SELECT COUNT(*) as count FROM high_priority_reports")
        high_priority = cursor.fetchone()['count']
        print(f"\n⭐ 高优先级报告: {high_priority} 份")
        
        # 关注列表项数
        cursor.execute("SELECT COUNT(*) as count FROM watchlist")
        watchlist_count = cursor.fetchone()['count']
        print(f"👀 关注列表项数: {watchlist_count}")
        
        # 关联关系数量
        cursor.execute("SELECT COUNT(*) as count FROM report_relationships")
        relationships_count = cursor.fetchone()['count']
        print(f"🔗 关联关系数: {relationships_count}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 获取统计信息失败: {e}")

def cleanup_all_reports():
    """清理所有报告数据"""
    print("🗑️  清理所有报告数据...")
    print("=" * 50)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 删除报告数据（触发器会自动清理 FTS 表）
        cursor.execute("DELETE FROM reports")
        deleted_count = cursor.rowcount
        
        # 清理 UI 状态
        cursor.execute("DELETE FROM ui_states")
        ui_states_count = cursor.rowcount
        
        # 清理组件实例
        cursor.execute("DELETE FROM component_instances")
        component_count = cursor.rowcount
        
        # 清理关注列表
        cursor.execute("DELETE FROM watchlist")
        watchlist_count = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        print(f"✅ 成功清理:")
        print(f"   • 报告数据: {deleted_count} 条")
        print(f"   • UI 状态: {ui_states_count} 条")
        print(f"   • 组件实例: {component_count} 条")
        print(f"   • 关注列表: {watchlist_count} 条")
        print(f"\n🎉 所有数据已清理完成!")
        
    except Exception as e:
        print(f"❌ 清理失败: {e}")

def cleanup_report_by_id(report_id: str):
    """清理指定报告ID的数据"""
    print(f"🗑️  清理报告 ID: {report_id}")
    print("=" * 50)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 检查报告是否存在
        cursor.execute("SELECT title FROM reports WHERE report_id = ?", (report_id,))
        report = cursor.fetchone()
        
        if not report:
            print(f"⚠️  报告 ID '{report_id}' 不存在")
            return
        
        print(f"📄 报告标题: {report['title']}")
        
        # 删除报告数据（触发器会自动清理 FTS 表）
        cursor.execute("DELETE FROM reports WHERE report_id = ?", (report_id,))
        deleted_count = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        if deleted_count > 0:
            print(f"✅ 成功清理报告: {report_id}")
        else:
            print(f"⚠️  未找到报告: {report_id}")
            
    except Exception as e:
        print(f"❌ 清理失败: {e}")

def list_all_reports():
    """列出所有报告"""
    print("📋 所有报告列表")
    print("=" * 80)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT report_id, title, category, date_published, importance_score
            FROM reports
            ORDER BY date_published DESC
        """)
        
        reports = cursor.fetchall()
        
        if not reports:
            print("📭 暂无报告数据")
            return
        
        print(f"{'报告ID':<30} {'分类':<15} {'发布日期':<12} {'重要性':<6} {'标题'}")
        print("-" * 80)
        
        for report in reports:
            print(f"{report['report_id']:<30} {report['category'] or 'N/A':<15} "
                  f"{report['date_published'] or 'N/A':<12} {report['importance_score'] or 'N/A':<6} "
                  f"{report['title'][:30]}...")
        
        print(f"\n📈 总计: {len(reports)} 份报告")
        conn.close()
        
    except Exception as e:
        print(f"❌ 获取报告列表失败: {e}")


def list_all_relationships():
    """列出所有关联关系"""
    print("🔗 所有关联关系列表")
    print("=" * 100)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT source_report_id, target_report_id, relation_type, similarity_score, summary
            FROM report_relationships
            ORDER BY created_at DESC
        """)
        
        relationships = cursor.fetchall()
        
        if not relationships:
            print("📭 暂无关联关系数据")
            return
        
        print(f"{'源报告ID':<30} {'目标报告ID':<30} {'关系类型':<10} {'相似度':<8} {'摘要'}")
        print("-" * 100)
        
        for rel in relationships:
            print(f"{rel['source_report_id']:<30} {rel['target_report_id']:<30} "
                  f"{rel['relation_type']:<10} {rel['similarity_score'] or 'N/A':<8} "
                  f"{rel['summary'][:40] if rel['summary'] else 'N/A'}...")
        
        print(f"\n📈 总计: {len(relationships)} 个关联关系")
        conn.close()
        
    except Exception as e:
        print(f"❌ 获取关联关系列表失败: {e}")


def list_relationships_by_report(report_id: str):
    """根据报告ID查询关联关系"""
    print(f"🔗 报告 '{report_id}' 的关联关系")
    print("=" * 100)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 查询作为源报告的关联关系
        cursor.execute("""
            SELECT source_report_id, target_report_id, relation_type, similarity_score, summary
            FROM report_relationships
            WHERE source_report_id = ?
            ORDER BY similarity_score DESC
        """, (report_id,))
        
        source_relationships = cursor.fetchall()
        
        # 查询作为目标报告的关联关系（反向关联）
        cursor.execute("""
            SELECT source_report_id, target_report_id, relation_type, similarity_score, summary
            FROM report_relationships
            WHERE target_report_id = ?
            ORDER BY similarity_score DESC
        """, (report_id,))
        
        target_relationships = cursor.fetchall()
        
        print(f"📊 作为源报告的关联关系 ({len(source_relationships)} 个): ")
        if source_relationships:
            print(f"{'源报告ID':<30} {'目标报告ID':<30} {'关系类型':<10} {'相似度':<8} {'摘要'}")
            print("-" * 100)
            for rel in source_relationships:
                print(f"{rel['source_report_id']:<30} {rel['target_report_id']:<30} "
                      f"{rel['relation_type']:<10} {rel['similarity_score'] or 'N/A':<8} "
                      f"{rel['summary'][:40] if rel['summary'] else 'N/A'}...")
        else:
            print("   暂无作为源报告的关联关系")
        
        print(f"\n📊 作为目标报告的关联关系 ({len(target_relationships)} 个): ")
        if target_relationships:
            print(f"{'源报告ID':<30} {'目标报告ID':<30} {'关系类型':<10} {'相似度':<8} {'摘要'}")
            print("-" * 100)
            for rel in target_relationships:
                print(f"{rel['source_report_id']:<30} {rel['target_report_id']:<30} "
                      f"{rel['relation_type']:<10} {rel['similarity_score'] or 'N/A':<8} "
                      f"{rel['summary'][:40] if rel['summary'] else 'N/A'}...")
        else:
            print("   暂无作为目标报告的关联关系")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 获取关联关系失败: {e}")

def main():
    parser = argparse.ArgumentParser(description="Finance Agent 数据库清理工具")
    parser.add_argument("--all", action="store_true", help="清理所有报告数据")
    parser.add_argument("--report-id", type=str, help="清理指定报告ID的数据")
    parser.add_argument("--stats", action="store_true", help="显示数据库统计信息")
    parser.add_argument("--list", action="store_true", help="列出所有报告")
    parser.add_argument("--list-relationships", action="store_true", help="列出所有关联关系")
    parser.add_argument("--report-relationships", type=str, help="查询指定报告的关联关系")
    
    args = parser.parse_args()
    
    # 如果没有任何参数，显示帮助信息
    if not any([args.all, args.report_id, args.stats, args.list, args.list_relationships, args.report_relationships]):
        parser.print_help()
        return
    
    # 检查数据库文件是否存在
    if not os.path.exists(DATABASE_PATH):
        print(f"❌ 数据库文件不存在: {DATABASE_PATH}")
        return
    
    print(f"📂 数据库路径: {DATABASE_PATH}")
    print()
    
    # 执行相应操作
    if args.stats:
        show_stats()
    
    if args.list:
        list_all_reports()
    
    if args.list_relationships:
        list_all_relationships()
    
    if args.report_relationships:
        list_relationships_by_report(args.report_relationships)
    
    if args.all:
        # 确认操作
        confirm = input("\n⚠️  确定要清理所有报告数据吗? (输入 'yes' 确认): ")
        if confirm.lower() == 'yes':
            cleanup_all_reports()
        else:
            print("❌ 操作已取消")
    
    if args.report_id:
        # 确认操作
        confirm = input(f"\n⚠️  确定要清理报告 '{args.report_id}' 吗? (输入 'yes' 确认): ")
        if confirm.lower() == 'yes':
            cleanup_report_by_id(args.report_id)
        else:
            print("❌ 操作已取消")

if __name__ == "__main__":
    main()