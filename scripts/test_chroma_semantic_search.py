#!/usr/bin/env python3
"""
ChromaDB 语义搜索功能测试脚本

此脚本用于测试ChromaDB的语义搜索功能，验证是否能够根据语义相似性返回相关结果，
而不是仅仅返回所有文档。
"""

import os
import asyncio
from typing import List, Dict, Any
from pathlib import Path

# 添加项目路径以导入模块
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))


# 加载环境变量
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
    print(f"[DEBUG] 已加载环境变量文件: {env_path}")

from database.database_manager import DatabaseManager


async def test_chroma_semantic_search():
    """测试ChromaDB语义搜索功能"""
    print("=" * 60)
    print("🔍 ChromaDB 语义搜索功能测试")
    print("=" * 60)
    
    # 初始化数据库管理器
    db_manager = DatabaseManager()
    
    # 检查是否启用了ChromaDB
    if not hasattr(db_manager, 'chroma_client') or not db_manager.chroma_client:
        print("❌ ChromaDB 未初始化或不可用")
        return
    
    print("✅ ChromaDB 客户端已初始化")
    
    # 检查是否启用了ChromaDB（通过环境变量）
    use_chromadb = os.getenv('USE_CHROMADB', 'false').lower() == 'true'
    print(f"📊 USE_CHROMADB 环境变量: {use_chromadb}")
    
    # 首先检查数据库中有什么报告
    print("\n📋 查询数据库中的所有报告...")
    all_reports = await db_manager.search_reports(limit=100)  # 获取所有报告
    print(f"📊 数据库中总共找到 {len(all_reports)} 份报告:")
    
    for i, report in enumerate(all_reports, 1):
        print(f"  {i}. {report.get('title', 'N/A')} [ID: {report.get('report_id', 'N/A')}]")
        print(f"     分类: {report.get('category', 'N/A')}")
        print(f"     重要性: {report.get('importance_score', 'N/A')}")
        print()
    
    if len(all_reports) == 0:
        print("⚠️  数据库中没有报告，无法进行语义搜索测试")
        return
    
    # 测试1: 使用中文关键词搜索
    print("🔍 测试1: 使用中文关键词 '芯片 投资' 搜索")
    try:
        results1 = await db_manager._chroma_search_reports(query="芯片")
        print(f"   找到 {len(results1)} 份相关报告:")
        for i, report in enumerate(results1, 1):
            print(f"   {i}. {report.get('title', 'N/A')} [ID: {report.get('report_id', 'N/A')}]")
            print(f"      分类: {report.get('category', 'N/A')}")
            print(f"      相关性: {report.get('content', '')[:100] if report.get('content') else 'N/A'}...")
        print()
    except Exception as e:
        print(f"   ❌ 搜索失败: {e}")
        import traceback
        traceback.print_exc()
    
    # 测试2: 使用英文关键词搜索
    print("🔍 测试2: 使用英文关键词 'gold investment' 搜索")
    try:
        results2 = await db_manager._chroma_search_reports(query="gold investment")
        print(f"   找到 {len(results2)} 份相关报告:")
        for i, report in enumerate(results2, 1):
            print(f"   {i}. {report.get('title', 'N/A')} [ID: {report.get('report_id', 'N/A')}]")
            print(f"      分类: {report.get('category', 'N/A')}")
            print(f"      相关性: {report.get('content', '')[:100] if report.get('content') else 'N/A'}...")
        print()
    except Exception as e:
        print(f"   ❌ 搜索失败: {e}")
        import traceback
        traceback.print_exc()
    
    # 测试3: 使用不相关的关键词搜索
    print("🔍 测试3: 使用不相关的关键词 '人工智能 机器学习' 搜索")
    try:
        results3 = await db_manager._chroma_search_reports(query="北京天气")
        print(f"   找到 {len(results3)} 份相关报告:")
        for i, report in enumerate(results3, 1):
            print(f"   {i}. {report.get('title', 'N/A')} [ID: {report.get('report_id', 'N/A')}]")
            print(f"      分类: {report.get('category', 'N/A')}")
            print(f"      相关性: {report.get('content', '')[:100] if report.get('content') else 'N/A'}...")
        print()
    except Exception as e:
        print(f"   ❌ 搜索失败: {e}")
        import traceback
        traceback.print_exc()
    
    # 测试4: 验证向量搜索是否真正基于语义相似性
    print("🔍 测试4: 验证向量搜索是否基于语义相似性")
    try:
        # 使用一个完全随机的查询
        results4 = await db_manager._chroma_search_reports(query="xyz123 abc456")
        print(f"   随机关键词搜索结果数量: {len(results4)}")
        if len(results4) == len(all_reports):
            print("   ⚠️  警告: 随机关键词返回了所有报告，说明向量搜索可能未正确工作")
        else:
            print("   ✅ 随机关键词未返回所有报告，向量搜索可能正常工作")
        print()
    except Exception as e:
        print(f"   ❌ 搜索失败: {e}")
        import traceback
        traceback.print_exc()
    
    # 测试5: 测试带过滤条件的搜索
    print("🔍 测试5: 测试带元数据过滤条件的搜索")
    try:
        # 尝试按类别过滤
        if all_reports:
            sample_category = all_reports[0].get('category')
            if sample_category:
                print(f"   按类别 '{sample_category}' 过滤...")
                results5 = await db_manager._chroma_search_reports(
                    query="投资", 
                    category=sample_category
                )
                print(f"   找到 {len(results5)} 份相关报告:")
                for i, report in enumerate(results5, 1):
                    print(f"   {i}. {report.get('title', 'N/A')} [分类: {report.get('category', 'N/A')}]")
        print()
    except Exception as e:
        print(f"   ❌ 搜索失败: {e}")
        import traceback
        traceback.print_exc()
    
    # 总结
    print("=" * 60)
    print("📊 测试总结:")
    print(f"   - 总报告数: {len(all_reports)}")
    print(f"   - 中文关键词搜索结果: {len(results1) if 'results1' in locals() else 'N/A'}")
    print(f"   - 英文关键词搜索结果: {len(results2) if 'results2' in locals() else 'N/A'}")
    print(f"   - 不相关关键词搜索结果: {len(results3) if 'results3' in locals() else 'N/A'}")
    print(f"   - 随机关键词搜索结果: {len(results4) if 'results4' in locals() else 'N/A'}")
    print("=" * 60)


def test_embedding_function():
    """测试嵌入函数功能"""
    print("\n🔍 测试嵌入函数功能")
    print("-" * 40)
    
    try:
        # 尝试创建嵌入函数
        embedding_model = os.getenv('EMBEDDING_MODEL', 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
        print(f"📊 使用嵌入模型: {embedding_model}")
        
        from chromadb.utils import embedding_functions
        embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=embedding_model
        )
        
        # 测试文本嵌入
        test_texts = [
            "黄金投资策略",
            "gold investment strategy", 
            "人工智能发展",
            "random text about nothing"
        ]
        
        print("📝 测试文本嵌入功能:")
        embeddings = embedding_function(test_texts)
        
        for i, (text, embedding) in enumerate(zip(test_texts, embeddings)):
            print(f"   {i+1}. '{text}' -> 嵌入维度: {len(embedding) if embedding is not None else 'N/A'}")
        
        print("✅ 嵌入函数功能正常")
        
    except Exception as e:
        print(f"❌ 嵌入函数测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("🚀 开始 ChromaDB 语义搜索功能测试")
    
    # 首先测试嵌入函数
    test_embedding_function()
    
    # 然后进行主要的语义搜索测试
    asyncio.run(test_chroma_semantic_search())
    
    print("\n✅ 测试完成!")