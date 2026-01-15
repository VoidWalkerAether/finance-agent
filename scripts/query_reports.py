#!/usr/bin/env python3
"""
报告数据查询脚本

功能：
- 支持查询 reports 表和 reports_fts 表
- 支持多种查询条件
- 支持无条件查询（默认返回最新2条记录）
- 支持全文搜索和结构化查询
"""

import asyncio
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from database.database_manager import DatabaseManager
import aiosqlite


async def query_reports_table(
    query: Optional[str] = None,
    category: Optional[str] = None,
    action: Optional[str] = None,
    min_importance: Optional[int] = None,
    limit: int = 2,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """
    查询 reports 表数据
    
    Args:
        query: FTS5 全文搜索关键词
        category: 分类筛选
        action: 投资建议筛选
        min_importance: 最小重要性评分
        limit: 返回数量
        offset: 偏移量
    
    Returns:
        List[Dict]: 报告列表
    """
    db = DatabaseManager()
    results = await db.search_reports(
        query=query,
        category=category,
        action=action,
        min_importance=min_importance,
        limit=limit,
        offset=offset
    )
    return results


async def query_fts_table(
    search_term: Optional[str] = None,
    limit: int = 2
) -> List[Dict[str, Any]]:
    """
    直接查询 reports_fts 表
    
    Args:
        search_term: 搜索词
        limit: 返回数量
    
    Returns:
        List[Dict]: 匹配的报告ID和相关内容
    """
    db = DatabaseManager()
    
    if search_term:
        sql = """
            SELECT r.report_id, r.title, r.category, r.date_published, r.importance_score
            FROM reports_fts f
            JOIN reports r ON f.report_id = r.report_id
            WHERE f.reports_fts MATCH ?
            ORDER BY r.date_published DESC, r.importance_score DESC
            LIMIT ?
        """
        params = [search_term, limit]
    else:
        sql = """
            SELECT r.report_id, r.title, r.category, r.date_published, r.importance_score
            FROM reports_fts f
            JOIN reports r ON f.report_id = r.report_id
            ORDER BY r.date_published DESC, r.importance_score DESC
            LIMIT ?
        """
        params = [limit]
    
    # 使用 aiosqlite 直接连接数据库
    async with aiosqlite.connect(db.db_path) as conn:
        conn.row_factory = lambda cursor, row: {
            col[0]: row[idx] for idx, col in enumerate(cursor.description)
        }
        cursor = await conn.execute(sql, params)
        results = await cursor.fetchall()
        return results


async def list_all_reports(limit: int = 10) -> List[Dict[str, Any]]:
    """
    列出所有报告（无条件查询）
    
    Args:
        limit: 返回数量
    
    Returns:
        List[Dict]: 报告列表
    """
    db = DatabaseManager()
    return await db.list_all_reports(limit=limit)


async def get_report_details(report_id: str) -> Optional[Dict[str, Any]]:
    """
    获取报告详细信息
    
    Args:
        report_id: 报告ID
    
    Returns:
        Dict: 报告详细信息
    """
    db = DatabaseManager()
    return await db.get_report(report_id)


def print_results(results: List[Dict[str, Any]], title: str):
    """打印查询结果"""
    print(f"\n{'='*60}")
    print(f"📊 {title}")
    print(f"{'='*60}")
    
    if not results:
        print("未找到任何记录")
        return
    
    print(f"共找到 {len(results)} 条记录:\n")
    
    for i, record in enumerate(results, 1):
        print(f"{i}. {record.get('title', 'N/A')}")
        print(f"   ID: {record.get('report_id', 'N/A')}")
        print(f"   分类: {record.get('category', 'N/A')}")
        print(f"   日期: {record.get('date_published', 'N/A')}")
        print(f"   重要性: {record.get('importance_score', 'N/A')}")
        if 'action' in record:
            print(f"   操作建议: {record.get('action', 'N/A')}")
        print()


async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="报告数据查询工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 无条件查询最新的2条记录
  python scripts/query_reports.py
  
  # 查询最新的5条记录
  python scripts/query_reports.py --limit 5
  
  # 全文搜索包含"黄金"的报告
  python scripts/query_reports.py --search "黄金"
  
  # 按分类查询
  python scripts/query_reports.py --category "A股与黄金综合策略"
  
  # 按投资建议查询
  python scripts/query_reports.py --action "watch"
  
  # 查询高重要性报告
  python scripts/query_reports.py --min-importance 8
  
  # 直接查询 FTS 表
  python scripts/query_reports.py --fts "黄金"
  
  # 获取报告详细信息
  python scripts/query_reports.py --details "analysis_A股与黄金综合策略_20251127_105237"
        """
    )
    
    parser.add_argument(
        '--search', '-s',
        type=str,
        help='全文搜索关键词'
    )
    
    parser.add_argument(
        '--category', '-c',
        type=str,
        help='按分类筛选'
    )
    
    parser.add_argument(
        '--action', '-a',
        type=str,
        choices=['buy', 'sell', 'hold', 'watch'],
        help='按投资建议筛选'
    )
    
    parser.add_argument(
        '--min-importance', '-m',
        type=int,
        help='最小重要性评分'
    )
    
    parser.add_argument(
        '--limit', '-l',
        type=int,
        default=2,
        help='返回记录数量（默认: 2）'
    )
    
    parser.add_argument(
        '--fts', '-f',
        type=str,
        help='直接查询 FTS 表'
    )
    
    parser.add_argument(
        '--details', '-d',
        type=str,
        help='获取报告详细信息'
    )
    
    parser.add_argument(
        '--all', '-A',
        action='store_true',
        help='列出所有报告（无筛选）'
    )
    
    args = parser.parse_args()
    
    try:
        if args.details:
            # 获取报告详细信息
            print(f"🔍 正在查询报告详细信息: {args.details}")
            report = await get_report_details(args.details)
            if report:
                print(f"\n📄 报告详细信息:")
                print(f"标题: {report.get('title', 'N/A')}")
                print(f"分类: {report.get('category', 'N/A')}")
                print(f"日期: {report.get('date_published', 'N/A')}")
                print(f"重要性: {report.get('importance_score', 'N/A')}/10")
                print(f"操作建议: {report.get('action', 'N/A')}")
                print(f"情感: {report.get('sentiment', 'N/A')}")
                print(f"一句话总结: {report.get('summary_one_sentence', 'N/A')}")
                print(f"内容预览: {report.get('content', '')[:200]}...")
            else:
                print(f"❌ 未找到报告: {args.details}")
        elif args.fts:
            # 直接查询 FTS 表
            print(f"🔍 正在查询 FTS 表: '{args.fts}'")
            results = await query_fts_table(search_term=args.fts, limit=args.limit)
            print_results(results, f"FTS 表查询结果 (搜索词: '{args.fts}')")
        elif args.all:
            # 列出所有报告
            print("🔍 正在查询所有报告...")
            results = await list_all_reports(limit=args.limit)
            print_results(results, "所有报告")
        elif any([args.search, args.category, args.action, args.min_importance]):
            # 结构化查询
            conditions = []
            if args.search:
                conditions.append(f"搜索词: '{args.search}'")
            if args.category:
                conditions.append(f"分类: '{args.category}'")
            if args.action:
                conditions.append(f"操作建议: '{args.action}'")
            if args.min_importance:
                conditions.append(f"最小重要性: {args.min_importance}")
            
            condition_str = ", ".join(conditions)
            print(f"🔍 正在查询 reports 表 ({condition_str})")
            
            results = await query_reports_table(
                query=args.search,
                category=args.category,
                action=args.action,
                min_importance=args.min_importance,
                limit=args.limit
            )
            print_results(results, f"Reports 表查询结果 ({condition_str})")
        else:
            # 默认查询（无条件）
            print("🔍 正在执行默认查询（最新2条记录）...")
            results = await query_reports_table(limit=args.limit)
            print_results(results, "最新报告")
            
    except Exception as e:
        print(f"\n❌ 查询失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())