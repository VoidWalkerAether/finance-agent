"""
快速对话测试 - 简化版

用法：
  python scripts/quick_chat_test.py
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

if not os.getenv('ANTHROPIC_AUTH_TOKEN'):
    print("❌ 请先配置 .env 文件中的 ANTHROPIC_AUTH_TOKEN")
    sys.exit(1)

from ccsdk.ai_client import AIClient
from database.database_manager import DatabaseManager


async def interactive_chat():
    """交互式对话测试"""
    
    print("="*60)
    print("💬 Finance Agent - 交互式对话测试")
    print("="*60)
    
    # 初始化
    db = DatabaseManager()
    ai_client = AIClient()
    
    # 获取一份报告
    print("\n📄 正在获取报告...")
    reports = await db.search_reports(limit=2)
    
    if not reports:
        print("❌ 数据库中没有报告，请先导入:")
        print("   python scripts/batch_import_reports.py --dir report")
        return
    
    report = reports[0]
    print(f"✅ 使用报告: {report.get('title', 'N/A')}")
    
    # 构建系统提示（作为上下文）
    system_prompt = f"""你是金融分析助手。当前分析报告：

标题：{report.get('title')}
分类：{report.get('category', 'N/A')}
摘要：{report.get('summary_one_sentence', 'N/A')}
操作建议：{report.get('analysis_json', 'N/A')}
重要性：{report.get('importance_score', 'N/A')}/10

请简洁回答用户问题，每次回答 50-150 字。"""
    
    print("\n" + "="*60)
    print("开始对话（输入 'quit' 退出）")
    print("="*60)
    
    turn = 0
    sdk_session_id = None  # 用于多轮对话
    
    while True:
        # 用户输入
        print(f"\n[第 {turn + 1} 轮]")
        user_input = input("👤 你: ").strip()
        
        if user_input.lower() in ['quit', 'exit', 'q', '退出']:
            print("\n👋 对话结束")
            break
        
        if not user_input:
            continue
        
        # 获取 AI 回答
        print("🤖 AI: ", end='', flush=True)
        
        response = ""
        try:
            # 构建完整的提示词（包含上下文）
            full_prompt = f"{system_prompt}\n\n用户问题: {user_input}"
            
            print(full_prompt)
            # 构建查询选项
            options = {}
            if sdk_session_id:
                options['resume'] = sdk_session_id
            
            # 流式输出
            async for message in ai_client.query_stream(full_prompt, options):
                # 提取文本内容
                if hasattr(message, 'type') and message.type == 'assistant':
                    content = message.content
                    if isinstance(content, str):
                        response += content
                        print(content, end='', flush=True)
                    elif isinstance(content, list):
                        for block in content:
                            if isinstance(block, dict) and block.get('type') == 'text':
                                text = block.get('text', '')
                                response += text
                                print(text, end='', flush=True)
                
                # 捕获 session_id
                if hasattr(message, 'type') and message.type == 'system' and hasattr(message, 'subtype'):
                    if message.subtype == 'init' and hasattr(message, 'session_id'):
                        sdk_session_id = message.session_id
            
            print()  # 换行
            turn += 1
            
        except Exception as e:
            print(f"\n❌ 错误: {e}")
            import traceback
            traceback.print_exc()
    
    # 显示会话统计
    print("\n" + "="*60)
    print("📊 会话统计")
    print("="*60)
    print(f"对话轮数: {turn}")


async def quick_test():
    """快速自动测试"""
    
    print("="*60)
    print("⚡ 快速自动对话测试")
    print("="*60)
    
    db = DatabaseManager()
    ai_client = AIClient()
    
    # 获取报告
    reports = await db.search_reports(limit=1)
    if not reports:
        print("❌ 请先导入报告")
        return
    
    report = reports[0]
    print(f"\n📄 报告: {report.get('title')}")
    
    # 系统提示
    system_prompt = f"""你是金融助手。当前报告：

标题：{report.get('title')}
摘要：{report.get('summary_one_sentence', 'N/A')}
建议：{report.get('action', 'N/A')}

请简洁回答，50-100字。"""
    
    # 快速问答
    questions = [
        "这份报告的主要观点是什么？",
        "有什么投资建议？",
        "需要注意哪些风险？"
    ]
    
    sdk_session_id = None
    
    for i, q in enumerate(questions, 1):
        print(f"\n{'─'*60}")
        print(f"[{i}] ❓ {q}")
        
        print("💡 ", end='', flush=True)
        
        # 构建完整提示词
        full_prompt = f"{system_prompt}\n\n用户问题: {q}"
        
        options = {}
        if sdk_session_id:
            options['resume'] = sdk_session_id
        
        response = ""
        async for message in ai_client.query_stream(full_prompt, options):
            # 提取文本内容
            if hasattr(message, 'type') and message.type == 'assistant':
                content = message.content
                if isinstance(content, str):
                    response += content
                    print(content, end='', flush=True)
                elif isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get('type') == 'text':
                            text = block.get('text', '')
                            response += text
                            print(text, end='', flush=True)
            
            # 捕获 session_id
            if hasattr(message, 'type') and message.type == 'system' and hasattr(message, 'subtype'):
                if message.subtype == 'init' and hasattr(message, 'session_id'):
                    sdk_session_id = message.session_id
        
        print()
        
        if i < len(questions):
            await asyncio.sleep(1)
    
    print("\n" + "="*60)
    print("✅ 测试完成!")
    print("="*60)


async def main():
    """主函数"""
    
    print("\n选择测试模式:")
    print("  1. 交互式对话（手动输入问题）")
    print("  2. 快速自动测试（预设问题）")
    
    choice = input("\n请选择 (1/2): ").strip()
    
    if choice == "1":
        await interactive_chat()
    elif choice == "2":
        await quick_test()
    else:
        print("无效选择")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 再见!")
