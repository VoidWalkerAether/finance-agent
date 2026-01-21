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
7. 列出所有持仓数据
8. 查看指定用户持仓详情
9. 删除指定用户持仓数据
10. 列出所有投资原则档案
11. 查看指定用户的投资原则详情
12. 删除指定用户的投资原则数据

使用方法：
python cleanup_database.py [options]

参数：
--all: 清理所有报告数据
--report-id REPORT_ID: 清理指定报告ID的数据
--stats: 显示数据库统计信息
--list: 列出所有报告
--list-relationships: 列出所有关联关系
--report-relationships REPORT_ID: 查询指定报告的关联关系
--list-portfolios: 列出所有持仓数据
--portfolio-detail USER_ID: 查看指定用户的持仓详情
--cleanup-portfolio USER_ID: 删除指定用户的持仓数据
--list-principles: 列出所有投资原则档案
--principles-detail USER_ID: 查看指定用户的投资原则详情
--cleanup-principles USER_ID: 删除指定用户的投资原则数据
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
        
        # 持仓用户数
        cursor.execute("SELECT COUNT(*) as count FROM user_portfolios")
        portfolios_count = cursor.fetchone()['count']
        print(f"💼 持仓用户数: {portfolios_count}")
        
        # 投资原则档案数
        cursor.execute("SELECT COUNT(*) as count FROM user_investment_principles")
        principles_count = cursor.fetchone()['count']
        print(f"📊 投资原则档案数: {principles_count}")
        
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
        
        # 清理持仓数据
        cursor.execute("DELETE FROM user_portfolios")
        portfolios_count = cursor.rowcount
        
        # 清理投资原则数据
        cursor.execute("DELETE FROM user_investment_principles")
        principles_count = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        print(f"✅ 成功清理:")
        print(f"   • 报告数据: {deleted_count} 条")
        print(f"   • UI 状态: {ui_states_count} 条")
        print(f"   • 组件实例: {component_count} 条")
        print(f"   • 关注列表: {watchlist_count} 条")
        print(f"   • 持仓数据: {portfolios_count} 条")
        print(f"   • 投资原则: {principles_count} 条")
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


def list_all_portfolios():
    """列出所有持仓数据"""
    print("💼 所有持仓数据列表")
    print("=" * 100)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT user_id, total_asset_value, cash_position, holdings_json, 
                   created_at, updated_at
            FROM user_portfolios
            ORDER BY updated_at DESC
        """)
        
        portfolios = cursor.fetchall()
        
        if not portfolios:
            print("📭 暂无持仓数据")
            return
        
        print(f"{'用户ID':<15} {'总资产':<15} {'现金':<15} {'持仓数':<8} {'更新时间':<20}")
        print("-" * 100)
        
        import json
        for portfolio in portfolios:
            try:
                holdings = json.loads(portfolio['holdings_json'])
                holdings_count = len(holdings)
            except:
                holdings_count = 0
            
            print(f"{portfolio['user_id']:<15} "
                  f"{portfolio['total_asset_value']:>14,.2f} "
                  f"{portfolio['cash_position']:>14,.2f} "
                  f"{holdings_count:<8} "
                  f"{portfolio['updated_at']:<20}")
        
        print(f"\n📈 总计: {len(portfolios)} 个用户持仓")
        conn.close()
        
    except Exception as e:
        print(f"❌ 获取持仓列表失败: {e}")


def show_portfolio_detail(user_id: str):
    """显示指定用户的持仓详情"""
    print(f"💼 用户 '{user_id}' 的持仓详情")
    print("=" * 100)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT user_id, total_asset_value, cash_position, holdings_json, 
                   created_at, updated_at
            FROM user_portfolios
            WHERE user_id = ?
        """, (user_id,))
        
        portfolio = cursor.fetchone()
        
        if not portfolio:
            print(f"⚠️  用户 '{user_id}' 没有持仓数据")
            return
        
        print(f"\n📊 基本信息:")
        print(f"   用户ID: {portfolio['user_id']}")
        print(f"   总资产: {portfolio['total_asset_value']:,.2f}")
        print(f"   现金头寸: {portfolio['cash_position']:,.2f}")
        print(f"   创建时间: {portfolio['created_at']}")
        print(f"   更新时间: {portfolio['updated_at']}")
        
        # 解析持仓明细
        import json
        try:
            holdings = json.loads(portfolio['holdings_json'])
            
            if holdings:
                print(f"\n📋 持仓明细 ({len(holdings)} 项):")
                print(f"{'名称':<20} {'类别':<15} {'市值':<15} {'占比':<8} {'状态':<10}")
                print("-" * 100)
                
                for holding in holdings:
                    print(f"{holding.get('name', 'N/A'):<20} "
                          f"{holding.get('category', 'N/A'):<15} "
                          f"{holding.get('market_value', 0):>14,.2f} "
                          f"{holding.get('percentage', 'N/A'):<8} "
                          f"{holding.get('status', 'N/A'):<10}")
                    
                    # 显示详细信息
                    if holding.get('cost_price') or holding.get('current_price'):
                        details = []
                        if holding.get('cost_price'):
                            details.append(f"成本价: {holding['cost_price']:.2f}")
                        if holding.get('current_price'):
                            details.append(f"当前价: {holding['current_price']:.2f}")
                        if holding.get('quantity'):
                            details.append(f"数量: {holding['quantity']:.2f}")
                        if holding.get('note'):
                            details.append(f"备注: {holding['note']}")
                        
                        if details:
                            print(f"         {' | '.join(details)}")
            else:
                print(f"\n📭 暂无持仓明细")
                
        except json.JSONDecodeError as e:
            print(f"\n❌ 解析持仓数据失败: {e}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 获取持仓详情失败: {e}")


def cleanup_portfolio_by_user(user_id: str):
    """删除指定用户的持仓数据"""
    print(f"🗑️  删除用户 '{user_id}' 的持仓数据")
    print("=" * 50)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 检查持仓是否存在
        cursor.execute("SELECT total_asset_value FROM user_portfolios WHERE user_id = ?", (user_id,))
        portfolio = cursor.fetchone()
        
        if not portfolio:
            print(f"⚠️  用户 '{user_id}' 没有持仓数据")
            return
        
        print(f"💰 总资产: {portfolio['total_asset_value']:,.2f}")
        
        # 删除持仓数据
        cursor.execute("DELETE FROM user_portfolios WHERE user_id = ?", (user_id,))
        deleted_count = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        if deleted_count > 0:
            print(f"✅ 成功删除用户 '{user_id}' 的持仓数据")
        else:
            print(f"⚠️  未找到用户 '{user_id}' 的持仓数据")
            
    except Exception as e:
        print(f"❌ 删除失败: {e}")


def list_all_principles():
    """列出所有投资原则档案"""
    print("📊 所有投资原则档案列表")
    print("=" * 100)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT user_id, profile_name, version, is_active, 
                   created_at, updated_at
            FROM user_investment_principles
            ORDER BY user_id, is_active DESC, updated_at DESC
        """)
        
        principles_list = cursor.fetchall()
        
        if not principles_list:
            print("📭 暂无投资原则数据")
            return
        
        print(f"{'用户ID':<15} {'档案名称':<30} {'版本':<8} {'状态':<8} {'更新时间':<20}")
        print("-" * 100)
        
        for principle in principles_list:
            status = "✅ 激活" if principle['is_active'] else "⏸️  未激活"
            print(f"{principle['user_id']:<15} "
                  f"{principle['profile_name']:<30} "
                  f"{principle['version'] or 'N/A':<8} "
                  f"{status:<8} "
                  f"{principle['updated_at']:<20}")
        
        print(f"\n📈 总计: {len(principles_list)} 个档案")
        conn.close()
        
    except Exception as e:
        print(f"❌ 获取投资原则列表失败: {e}")


def show_principles_detail(user_id: str):
    """显示指定用户的投资原则详情"""
    print(f"📊 用户 '{user_id}' 的投资原则详情")
    print("=" * 100)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT user_id, profile_name, principles_json, version, is_active,
                   created_at, updated_at
            FROM user_investment_principles
            WHERE user_id = ?
            ORDER BY is_active DESC, updated_at DESC
        """, (user_id,))
        
        principles_list = cursor.fetchall()
        
        if not principles_list:
            print(f"⚠️  用户 '{user_id}' 没有投资原则数据")
            return
        
        # 显示每个档案
        for idx, principle in enumerate(principles_list, 1):
            status_icon = "✅" if principle['is_active'] else "⏸️"
            print(f"\n{status_icon} 档案 {idx}: {principle['profile_name']}")
            print("-" * 100)
            print(f"   版本: {principle['version'] or 'N/A'}")
            print(f"   状态: {'激活' if principle['is_active'] else '未激活'}")
            print(f"   创建时间: {principle['created_at']}")
            print(f"   更新时间: {principle['updated_at']}")
            
            # 解析原则内容
            import json
            try:
                principles_data = json.loads(principle['principles_json'])
                
                # 显示仓位管理规则
                wm = principles_data.get('weight_management', {})
                if wm:
                    print(f"\n   📊 仓位权重管理:")
                    print(f"      • 单一品种初始权重: {wm.get('single_position_initial', 0)*100:.1f}%")
                    print(f"      • 单一品种常规上限: {wm.get('single_position_max_normal', 0)*100:.1f}%")
                    print(f"      • 单一品种极限上限: {wm.get('single_position_max_extreme', 0)*100:.1f}%")
                    print(f"      • 极限条件: {wm.get('extreme_condition', 'N/A')}")
                    print(f"      • 目标持仓数量: {wm.get('target_position_count_min', 0)}-{wm.get('target_position_count_max', 0)} 个")
                    print(f"      • 跨市场数量: {wm.get('target_market_count_min', 0)}-{wm.get('target_market_count_max', 0)} 个")
                    
                    three_low = wm.get('three_low_principle', {})
                    if three_low:
                        print(f"      • 三低原则: 低杠杆={three_low.get('low_leverage', False)}, "
                              f"低相关={three_low.get('low_correlation', False)}, "
                              f"低集中度={three_low.get('low_concentration', False)}")
                
                # 显示回撤止损规则
                dc = principles_data.get('drawdown_control', {})
                if dc:
                    print(f"\n   ⚠️  回撤止损纪律:")
                    print(f"      • 个股平均止损: {dc.get('single_stock_stop_loss_avg', 0)*100:.1f}%")
                    print(f"      • NAV 回调触发阈值: {dc.get('portfolio_nav_step_trigger', 0)*100:.1f}%")
                    print(f"      • 每次减仓比例: {dc.get('portfolio_reduce_ratio_per_step', 0)*100:.0f}%")
                    print(f"      • 年度净值调整上限: {dc.get('annual_nav_adjustment_max', 0)*100:.0f}%")
                
            except json.JSONDecodeError as e:
                print(f"\n   ❌ 解析原则数据失败: {e}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 获取投资原则详情失败: {e}")


def cleanup_principles_by_user(user_id: str):
    """删除指定用户的投资原则数据"""
    print(f"🗑️  删除用户 '{user_id}' 的投资原则数据")
    print("=" * 50)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 检查原则是否存在
        cursor.execute("SELECT COUNT(*) as count FROM user_investment_principles WHERE user_id = ?", (user_id,))
        count = cursor.fetchone()['count']
        
        if count == 0:
            print(f"⚠️  用户 '{user_id}' 没有投资原则数据")
            return
        
        print(f"📁 找到 {count} 个档案")
        
        # 删除原则数据
        cursor.execute("DELETE FROM user_investment_principles WHERE user_id = ?", (user_id,))
        deleted_count = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        if deleted_count > 0:
            print(f"✅ 成功删除用户 '{user_id}' 的 {deleted_count} 个投资原则档案")
        else:
            print(f"⚠️  未找到用户 '{user_id}' 的投资原则数据")
            
    except Exception as e:
        print(f"❌ 删除失败: {e}")

def main():
    parser = argparse.ArgumentParser(description="Finance Agent 数据库清理工具")
    parser.add_argument("--all", action="store_true", help="清理所有报告数据")
    parser.add_argument("--report-id", type=str, help="清理指定报告ID的数据")
    parser.add_argument("--stats", action="store_true", help="显示数据库统计信息")
    parser.add_argument("--list", action="store_true", help="列出所有报告")
    parser.add_argument("--list-relationships", action="store_true", help="列出所有关联关系")
    parser.add_argument("--report-relationships", type=str, help="查询指定报告的关联关系")
    parser.add_argument("--list-portfolios", action="store_true", help="列出所有持仓数据")
    parser.add_argument("--portfolio-detail", type=str, help="查看指定用户的持仓详情")
    parser.add_argument("--cleanup-portfolio", type=str, help="删除指定用户的持仓数据")
    parser.add_argument("--list-principles", action="store_true", help="列出所有投资原则档案")
    parser.add_argument("--principles-detail", type=str, help="查看指定用户的投资原则详情")
    parser.add_argument("--cleanup-principles", type=str, help="删除指定用户的投资原则数据")
    
    args = parser.parse_args()
    
    # 如果没有任何参数，显示帮助信息
    if not any([args.all, args.report_id, args.stats, args.list, args.list_relationships, 
                args.report_relationships, args.list_portfolios, args.portfolio_detail, args.cleanup_portfolio,
                args.list_principles, args.principles_detail, args.cleanup_principles]):
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
    
    if args.list_portfolios:
        list_all_portfolios()
    
    if args.portfolio_detail:
        show_portfolio_detail(args.portfolio_detail)
    
    if args.list_principles:
        list_all_principles()
    
    if args.principles_detail:
        show_principles_detail(args.principles_detail)
    
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
    
    if args.cleanup_portfolio:
        # 确认操作
        confirm = input(f"\n⚠️  确定要删除用户 '{args.cleanup_portfolio}' 的持仓数据吗? (输入 'yes' 确认): ")
        if confirm.lower() == 'yes':
            cleanup_portfolio_by_user(args.cleanup_portfolio)
        else:
            print("❌ 操作已取消")
    
    if args.cleanup_principles:
        # 确认操作
        confirm = input(f"\n⚠️  确定要删除用户 '{args.cleanup_principles}' 的投资原则数据吗? (输入 'yes' 确认): ")
        if confirm.lower() == 'yes':
            cleanup_principles_by_user(args.cleanup_principles)
        else:
            print("❌ 操作已取消")

if __name__ == "__main__":
    main()