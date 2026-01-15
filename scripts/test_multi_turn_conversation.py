"""
测试多轮对话功能

功能：
- 测试与报告相关的多轮对话
- 验证会话上下文保持
- 测试不同类型的问题
- 验证 AI 能够记住之前的对话内容
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

# 验证 API Key
if not os.getenv('ANTHROPIC_AUTH_TOKEN'):
    print("\n" + "="*60)
    print("⚠️  错误: 未找到 ANTHROPIC_AUTH_TOKEN 环境变量")
    print("="*60)
    print("\n请先配置 .env 文件")
    sys.exit(1)

from ccsdk.session import Session
from ccsdk.ai_client import AIClient
from database.database_manager import DatabaseManager


class ConversationTester:
    """多轮对话测试器"""
    
    def __init__(self):
        self.db = DatabaseManager()
        self.session = None
        self.ai_client = AIClient()
    
    async def setup(self):
        """初始化测试环境"""
        print("=" * 70)
        print("🧪 多轮对话功能测试")
        print("=" * 70)
        
        # 1. 检查数据库中是否有报告
        print("\n[1/3] 检查数据库...")
        stats = await self.db.get_report_stats()
        total_reports = stats.get('total_reports', 0)
        
        if total_reports == 0:
            print("  ⚠️  数据库中没有报告，请先导入报告:")
            print("     python scripts/batch_import_reports.py --dir report")
            return False
        
        print(f"  ✅ 找到 {total_reports} 份报告")
        
        # 2. 获取一份示例报告
        print("\n[2/3] 获取示例报告...")
        reports = await self.db.search_reports(limit=1)
        
        if not reports:
            print("  ❌ 无法获取报告")
            return False
        
        self.report = reports[0]
        print(f"  ✅ 使用报告: {self.report.get('title', 'N/A')}")
        print(f"     - ID: {self.report.get('report_id')}")
        print(f"     - 分类: {self.report.get('category', 'N/A')}")
        print(f"     - 操作建议: {self.report.get('action', 'N/A')}")
        
        # 3. 创建会话
        print("\n[3/3] 创建会话...")
        self.session = Session(
            session_id=f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            db=self.db
        )
        print(f"  ✅ 会话创建成功: {self.session.session_id}")
        
        return True
    
    def _build_system_prompt(self) -> str:
        """构建系统提示词"""
        return f"""你是一位专业的金融分析助手。

当前报告信息：
- 标题：{self.report.get('title', 'N/A')}
- 分类：{self.report.get('category', 'N/A')}
- 发布日期：{self.report.get('date_published', 'N/A')}
- 一句话摘要：{self.report.get('summary_one_sentence', 'N/A')}
- 情绪：{self.report.get('sentiment', 'N/A')}
- 操作建议：{self.report.get('action', 'N/A')}
- 重要性评分：{self.report.get('importance_score', 'N/A')}/10

报告内容摘要：
{self.report.get('content', '')[:500]}...

你的任务：
1. 回答用户关于这份报告的问题
2. 记住之前的对话内容，保持上下文连贯
3. 提供专业、准确的金融分析建议
4. 如果用户问到具体数字或细节，基于报告内容回答
5. 保持简洁，每次回答控制在 100-200 字

注意：你可以访问完整的报告数据，包括投资建议、风险评估等。
"""
    
    async def ask_question(self, question: str, question_num: int) -> str:
        """
        发送问题并获取回答
        
        Args:
            question: 用户问题
            question_num: 问题编号
        
        Returns:
            AI 回答
        """
        print(f"\n{'─'*70}")
        print(f"❓ 问题 {question_num}: {question}")
        print(f"{'─'*70}")
        
        # 添加消息到会话
        self.session.add_message("user", question)
        
        # 获取 AI 回答
        print("🤔 AI 正在思考...")
        
        response_text = ""
        async for chunk in self.ai_client.stream_message(self.session.get_messages()):
            response_text += chunk
            # 实时显示（可选）
            # print(chunk, end='', flush=True)
        
        # 添加 AI 回答到会话
        self.session.add_message("assistant", response_text)
        
        print(f"\n💡 回答:\n{response_text}")
        
        return response_text
    
    async def run_conversation_test(self):
        """运行对话测试"""
        
        # 定义测试问题序列
        test_questions = [
            # 第 1 轮：基本信息
            "这份报告的主要观点是什么？",
            
            # 第 2 轮：跟进问题（测试上下文记忆）
            "为什么会有这样的观点？",
            
            # 第 3 轮：具体细节
            "报告给出了什么具体的投资建议？",
            
            # 第 4 轮：风险分析
            "有哪些风险需要注意？",
            
            # 第 5 轮：对比之前的内容（测试长期记忆）
            "综合前面的分析，你认为现在应该采取什么行动？",
            
            # 第 6 轮：假设性问题
            "如果我已经持有相关资产，应该继续持有还是减仓？"
        ]
        
        print("\n" + "="*70)
        print("🗣️  开始多轮对话测试")
        print("="*70)
        print(f"\n总共 {len(test_questions)} 个问题")
        
        responses = []
        
        for i, question in enumerate(test_questions, 1):
            try:
                response = await self.ask_question(question, i)
                responses.append({
                    'question': question,
                    'response': response
                })
                
                # 短暂延迟，避免 API 限流
                if i < len(test_questions):
                    print("\n⏳ 等待 2 秒...")
                    await asyncio.sleep(2)
                
            except Exception as e:
                print(f"\n❌ 问题 {i} 失败: {e}")
                import traceback
                traceback.print_exc()
                break
        
        return responses
    
    def print_summary(self, responses: list):
        """打印测试总结"""
        print("\n" + "="*70)
        print("📊 测试总结")
        print("="*70)
        
        print(f"\n✅ 成功完成 {len(responses)}/{6} 轮对话")
        
        # 分析会话历史
        print(f"\n📝 会话历史:")
        print(f"   - 总消息数: {len(self.session.get_messages())}")
        print(f"   - 用户消息: {len([m for m in self.session.get_messages() if m['role'] == 'user'])}")
        print(f"   - AI 回答: {len([m for m in self.session.get_messages() if m['role'] == 'assistant'])}")
        
        # 统计回答长度
        total_chars = sum(len(r['response']) for r in responses)
        avg_chars = total_chars / len(responses) if responses else 0
        print(f"\n📏 回答统计:")
        print(f"   - 总字符数: {total_chars}")
        print(f"   - 平均长度: {avg_chars:.0f} 字符")
        
        # 显示对话摘要
        print(f"\n💬 对话摘要:")
        for i, item in enumerate(responses, 1):
            q_preview = item['question'][:40] + "..." if len(item['question']) > 40 else item['question']
            r_preview = item['response'][:60] + "..." if len(item['response']) > 60 else item['response']
            print(f"\n   [{i}] Q: {q_preview}")
            print(f"       A: {r_preview}")
    
    async def test_context_retention(self):
        """测试上下文保持能力"""
        print("\n" + "="*70)
        print("🧠 测试上下文记忆能力")
        print("="*70)
        
        # 测试问题：引用之前的对话内容
        test_cases = [
            {
                'setup': "我的投资期限是 3 个月",
                'followup': "根据我刚才说的投资期限，你有什么建议？",
                'expected_keywords': ['3个月', '短期', '期限']
            },
            {
                'setup': "我的风险偏好是保守型",
                'followup': "结合我的风险偏好，应该如何配置？",
                'expected_keywords': ['保守', '风险', '稳健']
            }
        ]
        
        for i, case in enumerate(test_cases, 1):
            print(f"\n测试 {i}: 上下文引用")
            
            # 设置上下文
            print(f"\n设置上下文: {case['setup']}")
            await self.ask_question(case['setup'], f"C{i}.1")
            
            await asyncio.sleep(1)
            
            # 测试引用
            print(f"\n测试引用: {case['followup']}")
            response = await self.ask_question(case['followup'], f"C{i}.2")
            
            # 检查是否包含预期关键词
            found_keywords = [kw for kw in case['expected_keywords'] if kw in response]
            
            if found_keywords:
                print(f"\n✅ 上下文保持成功！找到关键词: {found_keywords}")
            else:
                print(f"\n⚠️  可能未保持上下文，未找到预期关键词: {case['expected_keywords']}")
            
            if i < len(test_cases):
                await asyncio.sleep(2)
    
    async def run(self):
        """运行完整测试"""
        # 初始化
        if not await self.setup():
            return
        
        try:
            # 1. 基本对话测试
            responses = await self.run_conversation_test()
            
            # 2. 打印总结
            self.print_summary(responses)
            
            # 3. 上下文记忆测试
            print("\n")
            user_input = input("是否继续测试上下文记忆能力？(y/n): ").strip().lower()
            if user_input == 'y':
                await self.test_context_retention()
            
            # 4. 最终总结
            print("\n" + "="*70)
            print("✅ 测试完成!")
            print("="*70)
            print(f"\n会话 ID: {self.session.session_id}")
            print(f"总消息数: {len(self.session.get_messages())}")
            
            # 保存会话历史（可选）
            save = input("\n是否保存会话历史到文件？(y/n): ").strip().lower()
            if save == 'y':
                await self.save_conversation()
        
        except KeyboardInterrupt:
            print("\n\n⚠️  测试被用户中断")
        except Exception as e:
            print(f"\n\n❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()
    
    async def save_conversation(self):
        """保存对话历史到文件"""
        output_dir = Path("test_output")
        output_dir.mkdir(exist_ok=True)
        
        filename = f"conversation_{self.session.session_id}.json"
        filepath = output_dir / filename
        
        import json
        
        conversation_data = {
            'session_id': self.session.session_id,
            'report': {
                'id': self.report.get('report_id'),
                'title': self.report.get('title'),
                'category': self.report.get('category')
            },
            'messages': self.session.get_messages(),
            'timestamp': datetime.now().isoformat()
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(conversation_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 会话历史已保存: {filepath}")


async def main():
    """主函数"""
    print("\n" + "="*70)
    print("🚀 Finance Agent - 多轮对话测试工具")
    print("="*70)
    print("\n功能:")
    print("  1. 测试与报告相关的多轮对话")
    print("  2. 验证会话上下文保持")
    print("  3. 测试 AI 记忆能力")
    print("\n" + "="*70)
    
    tester = ConversationTester()
    await tester.run()


if __name__ == "__main__":
    asyncio.run(main())
