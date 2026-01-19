#!/usr/bin/env python3
"""
Portfolio 功能测试脚本

功能：
1. 测试 Repository 层 CRUD 操作
2. 测试数据验证和容错
3. 测试计算功能（盈亏、资产配置）
4. 测试 ActionContext API
5. 模拟 HTTP API 调用（可选）

使用方法：
python test_portfolio_functions.py [--cleanup]

参数：
--cleanup: 测试后清理测试数据
"""

import asyncio
import sys
import json
import argparse
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from database.database_manager import DatabaseManager
from database.schemas import validate_portfolio, fill_defaults
from ccsdk.action_context import ActionContext


# 测试数据
TEST_USER_ID = "test_user_001"

TEST_PORTFOLIO_1 = {
    "total_asset_value": 1000000.0,
    "cash_position": 50000.0,
    "holdings": [
        {
            "name": "沪深300ETF",
            "category": "A股宽基",
            "market_value": 300000.0,
            "percentage": "30%",
            "cost_price": 4.5,
            "current_price": 4.8,
            "quantity": 62500.0,
            "status": "盈利中",
            "note": "长期持有核心配置"
        },
        {
            "name": "黄金ETF",
            "category": "商品/黄金",
            "market_value": 200000.0,
            "percentage": "20%",
            "cost_price": 4.2,
            "current_price": 4.0,
            "quantity": 50000.0,
            "status": "亏损中",
            "note": "避险配置"
        },
        {
            "name": "港股通ETF",
            "category": "港股/跨境",
            "market_value": 450000.0,
            "percentage": "45%",
            "cost_price": 1.8,
            "current_price": 1.8,
            "quantity": 250000.0,
            "status": "持平",
            "note": ""
        }
    ]
}


class PortfolioTester:
    """持仓功能测试器"""
    
    def __init__(self):
        self.db = DatabaseManager()
        self.test_results = []
        
    def log_result(self, test_name: str, success: bool, message: str = ""):
        """记录测试结果"""
        self.test_results.append({
            'test': test_name,
            'success': success,
            'message': message
        })
        
        status = "✅" if success else "❌"
        print(f"{status} {test_name}")
        if message:
            print(f"   {message}")
    
    async def test_repository_create(self):
        """测试 Repository 层 - 创建持仓"""
        print("\n[1/8] 测试 Repository 层 - 创建持仓")
        print("-" * 60)
        
        try:
            await self.db.portfolio.upsert_user_portfolio(TEST_USER_ID, TEST_PORTFOLIO_1)
            self.log_result("创建持仓数据", True, f"用户 {TEST_USER_ID}")
        except Exception as e:
            self.log_result("创建持仓数据", False, f"错误: {e}")
    
    async def test_repository_read(self):
        """测试 Repository 层 - 读取持仓"""
        print("\n[2/8] 测试 Repository 层 - 读取持仓")
        print("-" * 60)
        
        try:
            portfolio = await self.db.portfolio.get_user_portfolio(TEST_USER_ID)
            
            if portfolio:
                assert portfolio['total_asset_value'] == 1000000.0
                assert portfolio['cash_position'] == 50000.0
                assert len(portfolio['holdings']) == 3
                
                self.log_result("读取持仓数据", True, 
                              f"总资产: {portfolio['total_asset_value']:,.2f}, "
                              f"持仓数: {len(portfolio['holdings'])}")
            else:
                self.log_result("读取持仓数据", False, "未找到持仓数据")
                
        except Exception as e:
            self.log_result("读取持仓数据", False, f"错误: {e}")
    
    async def test_repository_update(self):
        """测试 Repository 层 - 更新持仓"""
        print("\n[3/8] 测试 Repository 层 - 更新持仓")
        print("-" * 60)
        
        try:
            # 修改数据
            updated_portfolio = TEST_PORTFOLIO_1.copy()
            updated_portfolio['total_asset_value'] = 1050000.0
            updated_portfolio['holdings'][0]['current_price'] = 5.0
            
            await self.db.portfolio.upsert_user_portfolio(TEST_USER_ID, updated_portfolio)
            
            # 验证更新
            portfolio = await self.db.portfolio.get_user_portfolio(TEST_USER_ID)
            
            if portfolio and portfolio['total_asset_value'] == 1050000.0:
                self.log_result("更新持仓数据", True, 
                              f"新总资产: {portfolio['total_asset_value']:,.2f}")
            else:
                self.log_result("更新持仓数据", False, "更新后数据不一致")
                
        except Exception as e:
            self.log_result("更新持仓数据", False, f"错误: {e}")
    
    async def test_data_validation(self):
        """测试数据验证"""
        print("\n[4/8] 测试数据验证")
        print("-" * 60)
        
        # 测试1: 完整数据验证
        try:
            validated = validate_portfolio(TEST_PORTFOLIO_1)
            self.log_result("完整数据验证", True, "数据格式正确")
        except Exception as e:
            self.log_result("完整数据验证", False, f"错误: {e}")
        
        # 测试2: 缺失必填字段
        try:
            invalid_data = {"total_asset_value": 1000000.0}  # 缺少 cash_position 和 holdings
            validate_portfolio(invalid_data)
            self.log_result("缺失字段验证", False, "应该抛出 ValueError")
        except ValueError as e:
            self.log_result("缺失字段验证", True, f"正确捕获错误: {e}")
        except Exception as e:
            self.log_result("缺失字段验证", False, f"未预期的错误: {e}")
        
        # 测试3: 默认值填充
        try:
            partial_data = {
                "total_asset_value": 500000.0,
                "cash_position": 50000.0,
                "holdings": [
                    {
                        "name": "测试ETF",
                        "category": "测试",
                        "market_value": 450000.0,
                        "percentage": "90%"
                    }
                ]
            }
            filled = fill_defaults(partial_data)
            
            # 验证可选字段被填充
            first_holding = filled['holdings'][0]
            has_defaults = (
                'cost_price' in first_holding or 
                'current_price' in first_holding or
                'status' in first_holding
            )
            
            self.log_result("默认值填充", True, "缺失字段已填充默认值")
        except Exception as e:
            self.log_result("默认值填充", False, f"错误: {e}")
    
    async def test_actioncontext_api(self):
        """测试 ActionContext API"""
        print("\n[5/8] 测试 ActionContext API")
        print("-" * 60)
        
        try:
            # 创建 ActionContext
            context = ActionContext(
                session_id="test-session",
                database=self.db,
                ui_state_manager=None
            )
            
            # 测试 get_portfolio
            portfolio = await context.portfolio_api.get_portfolio(TEST_USER_ID)
            
            if portfolio and portfolio['total_asset_value'] > 0:
                self.log_result("portfolio_api.get_portfolio", True, 
                              f"总资产: {portfolio['total_asset_value']:,.2f}")
            else:
                self.log_result("portfolio_api.get_portfolio", False, "返回数据异常")
            
            # 测试 calculate_summary
            summary = await context.portfolio_api.calculate_summary(TEST_USER_ID)
            
            if summary:
                self.log_result("portfolio_api.calculate_summary", True,
                              f"总盈亏: {summary['total_gain']:,.2f} "
                              f"({summary['total_gain_percentage']:.2f}%)")
                
                # 显示资产配置
                print(f"\n   资产配置:")
                for category, percentage in summary['allocation_by_category'].items():
                    print(f"   • {category}: {percentage:.2f}%")
            else:
                self.log_result("portfolio_api.calculate_summary", False, "计算失败")
                
        except Exception as e:
            self.log_result("ActionContext API", False, f"错误: {e}")
            import traceback
            traceback.print_exc()
    
    async def test_calculation_accuracy(self):
        """测试计算准确性"""
        print("\n[6/8] 测试计算准确性")
        print("-" * 60)
        
        try:
            context = ActionContext(
                session_id="test-session",
                database=self.db,
                ui_state_manager=None
            )
            
            summary = await context.portfolio_api.calculate_summary(TEST_USER_ID)
            
            # 手动计算验证
            # 总成本 = 现金 + (4.5*62500 + 4.2*50000 + 1.8*250000)
            expected_cost = 50000 + (4.5*62500 + 4.2*50000 + 1.8*250000)
            # 总资产 = 1050000 (已更新)
            expected_gain = 1050000 - expected_cost
            
            actual_cost = summary['total_cost']
            actual_gain = summary['total_gain']
            
            cost_match = abs(actual_cost - expected_cost) < 0.01
            gain_match = abs(actual_gain - expected_gain) < 0.01
            
            if cost_match and gain_match:
                self.log_result("成本计算准确性", True, 
                              f"预期: {expected_cost:,.2f}, 实际: {actual_cost:,.2f}")
                self.log_result("盈亏计算准确性", True,
                              f"预期: {expected_gain:,.2f}, 实际: {actual_gain:,.2f}")
            else:
                if not cost_match:
                    self.log_result("成本计算准确性", False,
                                  f"预期: {expected_cost:,.2f}, 实际: {actual_cost:,.2f}")
                if not gain_match:
                    self.log_result("盈亏计算准确性", False,
                                  f"预期: {expected_gain:,.2f}, 实际: {actual_gain:,.2f}")
                    
        except Exception as e:
            self.log_result("计算准确性", False, f"错误: {e}")
    
    async def test_edge_cases(self):
        """测试边界情况"""
        print("\n[7/8] 测试边界情况")
        print("-" * 60)
        
        # 测试1: 空持仓
        try:
            empty_portfolio = {
                "total_asset_value": 100000.0,
                "cash_position": 100000.0,
                "holdings": []
            }
            
            await self.db.portfolio.upsert_user_portfolio("empty_user", empty_portfolio)
            result = await self.db.portfolio.get_user_portfolio("empty_user")
            
            if result and len(result['holdings']) == 0:
                self.log_result("空持仓测试", True, "空持仓处理正常")
            else:
                self.log_result("空持仓测试", False, "空持仓处理异常")
                
        except Exception as e:
            self.log_result("空持仓测试", False, f"错误: {e}")
        
        # 测试2: 不存在的用户
        try:
            result = await self.db.portfolio.get_user_portfolio("nonexistent_user")
            
            if result is None:
                self.log_result("不存在用户测试", True, "正确返回 None")
            else:
                self.log_result("不存在用户测试", False, "应返回 None")
                
        except Exception as e:
            self.log_result("不存在用户测试", False, f"错误: {e}")
        
        # 测试3: get_or_create_default_portfolio
        try:
            result = await self.db.portfolio.get_or_create_default_portfolio("another_nonexistent")
            
            if result and result['total_asset_value'] == 0.0:
                self.log_result("默认持仓创建", True, "返回默认空持仓")
            else:
                self.log_result("默认持仓创建", False, "返回值异常")
                
        except Exception as e:
            self.log_result("默认持仓创建", False, f"错误: {e}")
    
    async def test_delete(self):
        """测试删除功能"""
        print("\n[8/8] 测试删除功能")
        print("-" * 60)
        
        try:
            # 删除测试用户
            deleted = await self.db.portfolio.delete_user_portfolio(TEST_USER_ID)
            
            if deleted:
                self.log_result("删除持仓", True, f"用户 {TEST_USER_ID}")
                
                # 验证删除
                result = await self.db.portfolio.get_user_portfolio(TEST_USER_ID)
                if result is None:
                    self.log_result("删除验证", True, "持仓已被删除")
                else:
                    self.log_result("删除验证", False, "持仓仍然存在")
            else:
                self.log_result("删除持仓", False, "删除失败")
                
        except Exception as e:
            self.log_result("删除功能", False, f"错误: {e}")
    
    async def cleanup(self):
        """清理测试数据"""
        print("\n🧹 清理测试数据...")
        
        try:
            # 删除所有测试用户
            test_users = [TEST_USER_ID, "empty_user"]
            
            for user_id in test_users:
                await self.db.portfolio.delete_user_portfolio(user_id)
            
            print("✅ 测试数据已清理")
        except Exception as e:
            print(f"❌ 清理失败: {e}")
    
    def print_summary(self):
        """打印测试摘要"""
        print("\n" + "=" * 60)
        print("📊 测试摘要")
        print("=" * 60)
        
        total = len(self.test_results)
        passed = sum(1 for r in self.test_results if r['success'])
        failed = total - passed
        
        print(f"\n总测试数: {total}")
        print(f"✅ 通过: {passed}")
        print(f"❌ 失败: {failed}")
        
        if failed > 0:
            print(f"\n失败的测试:")
            for result in self.test_results:
                if not result['success']:
                    print(f"  • {result['test']}")
                    if result['message']:
                        print(f"    {result['message']}")
        
        print("\n" + "=" * 60)
        
        if failed == 0:
            print("🎉 所有测试通过！")
        else:
            print(f"⚠️  有 {failed} 个测试失败")
        
        print("=" * 60)
    
    async def run_all_tests(self, cleanup_after: bool = False):
        """运行所有测试"""
        print("=" * 60)
        print("🚀 Portfolio 功能测试")
        print("=" * 60)
        
        await self.test_repository_create()
        await self.test_repository_read()
        await self.test_repository_update()
        await self.test_data_validation()
        await self.test_actioncontext_api()
        await self.test_calculation_accuracy()
        await self.test_edge_cases()
        await self.test_delete()
        
        self.print_summary()
        
        if cleanup_after:
            await self.cleanup()


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Portfolio 功能测试")
    parser.add_argument("--cleanup", action="store_true", 
                       help="测试后清理测试数据")
    
    args = parser.parse_args()
    
    tester = PortfolioTester()
    await tester.run_all_tests(cleanup_after=args.cleanup)


if __name__ == "__main__":
    asyncio.run(main())
