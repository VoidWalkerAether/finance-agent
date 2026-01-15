#!/usr/bin/env python3
"""
检查 ChromaDB 数据的脚本
支持检查数据、删除所有数据、删除特定报告数据等功能
"""

import argparse
import os
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv


def check_chromadb():
    """检查 ChromaDB 数据"""
    # 加载环境变量
    env_path = project_root / '.env'
    if env_path.exists():
        load_dotenv(env_path)

    # 获取 ChromaDB 配置
    USE_CHROMADB = os.getenv('USE_CHROMADB', 'false').lower() == 'true'
    CHROMA_DB_PATH = os.getenv('CHROMA_DB_PATH', './chroma_db')

    print(f"USE_CHROMADB: {USE_CHROMADB}")
    print(f"CHROMA_DB_PATH: {CHROMA_DB_PATH}")

    if not USE_CHROMADB:
        print("ChromaDB 未启用")
        return

    try:
        import chromadb
        from chromadb.utils import embedding_functions
        
        # 初始化 ChromaDB 客户端
        print(f"正在连接到 ChromaDB: {CHROMA_DB_PATH}")
        client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        print("ChromaDB 客户端初始化成功")
        
        # 列出所有集合
        collections = client.list_collections()
        print(f"集合列表: {[c.name for c in collections]}")
        
        # 检查 reports 集合
        try:
            collection = client.get_collection(name="reports")
            count = collection.count()
            print(f"reports 集合中的文档数量: {count}")
            
            if count > 0:
                # 获取所有文档（因为看起来数据可能被分成了单个字符）
                results = collection.peek(limit=count)
                print(f"获取到 {len(results['ids'])} 个文档:")
                
                # 检查第一个文档以了解结构
                if results['ids'] and len(results['ids']) > 0:
                    # 尝试使用 get 方法获取更多信息
                    all_results = collection.get(limit=count)
                    print(f"使用 get 方法获取到 {len(all_results['ids'])} 个文档:")
                    
                    for i in range(min(10, len(all_results['ids']))):  # 只显示前10个
                        if i < len(all_results['ids']):
                            doc_id = all_results['ids'][i]
                            metadata = all_results['metadatas'][i] if i < len(all_results['metadatas']) else {}
                            document = all_results['documents'][i] if i < len(all_results['documents']) else ""
                            
                            print(f"  {i+1}. ID: {doc_id}")
                            print(f"     metadata 类型: {type(metadata).__name__}")
                            if isinstance(metadata, dict):
                                print(f"     标题: {metadata.get('title', 'N/A')}")
                                print(f"     报告ID: {metadata.get('report_id', 'N/A')}")
                                print(f"     分类: {metadata.get('category', 'N/A')}")
                                print(f"     情绪: {metadata.get('sentiment', 'N/A')}")
                                print(f"     投资建议: {metadata.get('action', 'N/A')}")
                            else:
                                print(f"     metadata 内容: {metadata}")
                            print(f"     文档内容: {document[:100]}...")  # 只显示前100个字符
                            print(f"     内容长度: {len(document)}")
                            print()
            else:
                print("reports 集合为空")
                
        except Exception as e:
            print(f"获取 reports 集合失败: {e}")
            
    except ImportError as e:
        print(f"导入 ChromaDB 失败: {e}")
    except Exception as e:
        print(f"连接 ChromaDB 失败: {e}")

def delete_all_chromadb_data():
    """删除 ChromaDB 中的所有数据"""
    # 加载环境变量
    env_path = project_root / '.env'
    if env_path.exists():
        load_dotenv(env_path)

    # 获取 ChromaDB 配置
    USE_CHROMADB = os.getenv('USE_CHROMADB', 'false').lower() == 'true'
    CHROMA_DB_PATH = os.getenv('CHROMA_DB_PATH', './chroma_db')

    if not USE_CHROMADB:
        print("ChromaDB 未启用")
        return

    try:
        import chromadb
        
        # 初始化 ChromaDB 客户端
        print(f"正在连接到 ChromaDB: {CHROMA_DB_PATH}")
        client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        print("ChromaDB 客户端初始化成功")
        
        # 获取 reports 集合
        try:
            collection = client.get_collection(name="reports")
            count = collection.count()
            print(f"删除前 reports 集合中的文档数量: {count}")
            
            if count > 0:
                # 获取所有文档ID
                all_docs = collection.get(limit=count)
                ids_to_delete = all_docs['ids']
                
                # 删除所有文档
                collection.delete(ids=ids_to_delete)
                print(f"已删除 {len(ids_to_delete)} 个文档")
                
                # 确认删除结果
                new_count = collection.count()
                print(f"删除后 reports 集合中的文档数量: {new_count}")
            else:
                print("reports 集合为空，无需删除")
                
        except Exception as e:
            print(f"获取或删除 reports 集合数据失败: {e}")
            
    except ImportError as e:
        print(f"导入 ChromaDB 失败: {e}")
    except Exception as e:
        print(f"删除 ChromaDB 数据失败: {e}")

def delete_report_by_id(report_id):
    """根据报告 ID 删除 ChromaDB 中的数据"""
    # 加载环境变量
    env_path = project_root / '.env'
    if env_path.exists():
        load_dotenv(env_path)

    # 获取 ChromaDB 配置
    USE_CHROMADB = os.getenv('USE_CHROMADB', 'false').lower() == 'true'
    CHROMA_DB_PATH = os.getenv('CHROMA_DB_PATH', './chroma_db')

    if not USE_CHROMADB:
        print("ChromaDB 未启用")
        return

    try:
        import chromadb
        
        # 初始化 ChromaDB 客户端
        print(f"正在连接到 ChromaDB: {CHROMA_DB_PATH}")
        client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        print("ChromaDB 客户端初始化成功")
        
        # 获取 reports 集合
        try:
            collection = client.get_collection(name="reports")
            print(f"正在查找报告 ID: {report_id}")
            
            # 尝试获取特定报告
            results = collection.get(ids=[report_id])
            if results['ids']:
                print(f"找到报告 ID: {report_id}，正在删除...")
                collection.delete(ids=[report_id])
                print(f"报告 {report_id} 已成功删除")
            else:
                print(f"未找到报告 ID: {report_id}")
                
        except Exception as e:
            print(f"删除报告失败: {e}")
            
    except ImportError as e:
        print(f"导入 ChromaDB 失败: {e}")
    except Exception as e:
        print(f"删除报告失败: {e}")

def main():
    parser = argparse.ArgumentParser(description="ChromaDB 管理脚本")
    parser.add_argument("--check", action="store_true", help="检查 ChromaDB 数据")
    parser.add_argument("--delete-all", action="store_true", help="删除 ChromaDB 中的所有数据")
    parser.add_argument("--delete-report", type=str, help="根据报告 ID 删除特定报告")
    
    args = parser.parse_args()
    
    # 如果没有任何参数，显示帮助信息
    if not any([args.check, args.delete_all, args.delete_report]):
        parser.print_help()
        return
    
    # 执行相应操作
    if args.check:
        check_chromadb()
    
    if args.delete_all:
        confirm = input("\n⚠️  确定要删除 ChromaDB 中的所有数据吗? (输入 'yes' 确认): ")
        if confirm.lower() == 'yes':
            delete_all_chromadb_data()
        else:
            print("❌ 操作已取消")
    
    if args.delete_report:
        confirm = input(f"\n⚠️  确定要删除报告 '{args.delete_report}' 吗? (输入 'yes' 确认): ")
        if confirm.lower() == 'yes':
            delete_report_by_id(args.delete_report)
        else:
            print("❌ 操作已取消")

if __name__ == "__main__":
    main()