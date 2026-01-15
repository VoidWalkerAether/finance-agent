"""
批量导入报告脚本

功能：
- 批量扫描指定目录的 .txt/.md 文件
- 触发 "report_added" 事件
- 由 report_analyzer Listener 自动分析
- 支持并发导入
"""

import asyncio
import sys
import os
from pathlib import Path
from typing import List

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
    print("\n请按以下步骤配置:")
    print("\n1. 复制 .env.example 到 .env:")
    print("   cp .env.example .env")
    print("\n2. 编辑 .env 文件，设置你的 Claude API Key:")
    print("   ANTHROPIC_AUTH_TOKEN=sk-ant-api03-xxxxx")
    print("\n3. 重新运行此脚本")
    print("\n" + "="*60)
    sys.exit(1)

from ccsdk.listeners_manager import ListenersManager
from database.database_manager import DatabaseManager
from ccsdk.ui_state_manager import UIStateManager


async def import_single_report(
    file_path: Path,
    listeners_manager: ListenersManager
) -> dict:
    """
    导入单个报告
    
    Args:
        file_path: 报告文件路径
        listeners_manager: Listeners 管理器
    
    Returns:
        dict: 导入结果
    """
    try:
        # 读取文件内容
        content = file_path.read_text(encoding='utf-8')
        
        if not content or len(content.strip()) < 50:
            return {
                'file': file_path.name,
                'success': False,
                'error': '文件内容为空或过短'
            }
        
        print(f"📄 导入: {file_path.name} ({len(content)} 字符)")
        
        # 触发 "report_added" 事件
        # report_analyzer Listener 会自动响应
        await listeners_manager.check_event(
            event="report_added",
            data={
                "file_path": str(file_path),
                "filename": file_path.name,
                "content": content,
                "skip_analysis": False  # 需要分析
            }
        )
        
        return {
            'file': file_path.name,
            'success': True,
            'message': '导入成功'
        }
    
    except Exception as e:
        return {
            'file': file_path.name,
            'success': False,
            'error': str(e)
        }


async def batch_import_reports(
    directory: str,
    pattern: str = "*.txt",
    max_concurrent: int = 3
):
    """
    批量导入报告
    
    Args:
        directory: 报告目录
        pattern: 文件匹配模式（默认 *.txt）
        max_concurrent: 最大并发数（默认 3）
    """
    print("=" * 60)
    print("📦 批量导入报告工具")
    print("=" * 60)
    
    # 初始化管理器
    print("\n[1/4] 初始化管理器...")
    db_manager = DatabaseManager()
    ui_state_manager = UIStateManager(db_manager)
    
    # 定义异步通知回调
    async def notification_handler(notification):
        """处理 Listener 通知"""
        message = notification.get('message', str(notification))
        print(f"  通知: {message}")
    
    listeners_manager = ListenersManager(
        database=db_manager,
        notification_callback=notification_handler,
        ui_state_manager=ui_state_manager
    )
    
    # 加载 Listeners
    print("\n[2/4] 加载 Listeners...")
    listeners = await listeners_manager.load_all_listeners()
    print(f"  ✅ 已加载 {len(listeners)} 个 Listener")
    
    # 扫描文件
    print(f"\n[3/4] 扫描目录: {directory}")
    report_dir = Path(directory)
    
    if not report_dir.exists():
        print(f"  ❌ 目录不存在: {directory}")
        return
    
    # 支持多种格式
    files = []
    for ext in ['*.txt', '*.md', '*.text']:
        files.extend(report_dir.glob(ext))
    
    if not files:
        print(f"  ⚠️  未找到任何 .txt/.md 文件")
        return
    
    print(f"  ✅ 找到 {len(files)} 个文件")
    
    # 批量导入（支持并发）
    print(f"\n[4/4] 开始导入（最大并发数: {max_concurrent}）...")
    print("-" * 60)
    
    # 使用信号量控制并发数
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def import_with_semaphore(file_path):
        async with semaphore:
            return await import_single_report(file_path, listeners_manager)
    
    # 并发导入
    tasks = [import_with_semaphore(f) for f in files]
    results = await asyncio.gather(*tasks)
    
    # 统计结果
    print("\n" + "=" * 60)
    print("📊 导入结果统计")
    print("=" * 60)
    
    success_count = sum(1 for r in results if r['success'])
    fail_count = len(results) - success_count
    
    print(f"✅ 成功: {success_count}")
    print(f"❌ 失败: {fail_count}")
    
    if fail_count > 0:
        print("\n失败文件:")
        for result in results:
            if not result['success']:
                print(f"  • {result['file']}: {result['error']}")
    
    # 查询数据库统计
    print("\n" + "=" * 60)
    print("💾 数据库统计")
    print("=" * 60)
    stats = await db_manager.get_report_stats()
    print(f"总报告数: {stats.get('total_reports', 0)}")
    
    if stats.get('by_category'):
        print("\n按分类:")
        for cat, count in list(stats['by_category'].items())[:5]:
            print(f"  • {cat}: {count} 份")
    
    print("\n" + "=" * 60)
    print("✅ 批量导入完成!")
    print("=" * 60)


async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="批量导入金融报告",
        epilog="""
使用示例:
  # 导入 report/ 目录的所有 .txt 文件
  python batch_import_reports.py --dir report
  
  # 导入指定目录，限制并发数为 5
  python batch_import_reports.py --dir /path/to/reports --concurrent 5
  
  # 导入 .md 文件
  python batch_import_reports.py --dir docs --pattern "*.md"
        """
    )
    
    parser.add_argument(
        '--dir', '-d',
        type=str,
        default='report',
        help='报告目录路径（默认: report）'
    )
    
    parser.add_argument(
        '--pattern', '-p',
        type=str,
        default='*.txt',
        help='文件匹配模式（默认: *.txt）'
    )
    
    parser.add_argument(
        '--concurrent', '-c',
        type=int,
        default=3,
        help='最大并发数（默认: 3）'
    )
    
    args = parser.parse_args()
    
    try:
        await batch_import_reports(
            directory=args.dir,
            pattern=args.pattern,
            max_concurrent=args.concurrent
        )
    except KeyboardInterrupt:
        print("\n\n⚠️  导入被用户中断")
    except Exception as e:
        print(f"\n\n❌ 导入失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
