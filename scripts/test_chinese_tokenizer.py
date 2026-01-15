#!/usr/bin/env python3
"""
测试中文分词和FTS5搜索的脚本
"""

import sys
import os
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import aiosqlite


async def test_chinese_tokenizer():
    """测试中文分词和FTS5搜索"""
    db_path = "data/finance.db"
    
    print("🔍 测试中文分词和FTS5搜索...")
    
    # 连接数据库
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        
        # 1. 检查FTS5表结构
        print("\n📋 FTS5表结构:")
        try:
            cursor = await db.execute("PRAGMA table_info(reports_fts)")
            rows = await cursor.fetchall()
            for row in rows:
                print(f"  {row['name']}: {row['type']}")
        except Exception as e:
            print(f"  ❌ 获取表结构出错: {e}")
        
        # 2. 测试不同的搜索方式
        print("\n🔍 测试不同搜索方式:")
        test_queries = [
            "A股",
            "黄金",
            "市场", 
            "投资",
            "A股*",
            "黄金*",
            "市场*",
            "投资*",
            "A股 AND 黄金",
            "上证指数"
        ]
        
        for query in test_queries:
            print(f"\n--- 测试查询: '{query}' ---")
            try:
                cursor = await db.execute("""
                    SELECT report_id, title, snippet(reports_fts, 3, '<<', '>>', '...', 32) as content_snippet
                    FROM reports_fts 
                    WHERE reports_fts MATCH ?
                    LIMIT 3
                """, (query,))
                rows = await cursor.fetchall()
                print(f"  找到 {len(rows)} 条结果")
                for row in rows:
                    print(f"    ID: {row['report_id']}")
                    print(f"    标题: {row['title']}")
                    print(f"    内容片段: {row['content_snippet']}")
            except Exception as e:
                print(f"  ❌ 查询出错: {e}")
        
        # 3. 检查完整的FTS5内容
        print("\n📄 FTS5完整内容检查:")
        try:
            cursor = await db.execute("""
                SELECT report_id, title, length(content) as content_length, substr(content, 1, 200) as content_preview
                FROM reports_fts
                LIMIT 1
            """)
            row = await cursor.fetchone()
            if row:
                print(f"  ID: {row['report_id']}")
                print(f"  标题: {row['title']}")
                print(f"  内容长度: {row['content_length']} 字符")
                print(f"  内容预览: {row['content_preview']}...")
        except Exception as e:
            print(f"  ❌ 查询出错: {e}")
            
        # 4. 测试使用LIKE操作符进行模糊搜索
        print("\n🔍 测试LIKE模糊搜索:")
        try:
            cursor = await db.execute("""
                SELECT report_id, title, substr(content, 1, 100) as content_preview
                FROM reports
                WHERE content LIKE '%黄金%'
                LIMIT 3
            """)
            rows = await cursor.fetchall()
            print(f"  使用LIKE '%黄金%' 找到 {len(rows)} 条结果")
            for row in rows:
                print(f"    ID: {row['report_id']}")
                print(f"    标题: {row['title']}")
        except Exception as e:
            print(f"  ❌ LIKE查询出错: {e}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_chinese_tokenizer())