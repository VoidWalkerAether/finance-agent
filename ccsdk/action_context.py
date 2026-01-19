"""
ActionContext - Action 执行上下文

为 Action handler 提供各种能力:
- AI 调用
- 数据库操作
- UI State 管理
- 通知系统
- 日志记录
- 金融数据 API
"""

from typing import Any, Dict, Optional, Literal, List
from dataclasses import dataclass


@dataclass
class ActionContext:
    """
    Action 执行上下文
    为 Action handler 提供丰富的能力
    
    对应 TypeScript: ActionContext
    """
    
    # ========== 基础信息 ==========
    session_id: str
    database: Any  # DatabaseManager
    ui_state_manager: Optional[Any] = None
    
    # ========== 回调函数 ==========
    _notify_callback: Any = None
    _log_callback: Any = None
    _call_agent_callback: Any = None
    
    # ==================== 通知系统 ====================
    
    async def notify(
        self,
        message: str,
        priority: Literal["low", "normal", "high"] = "normal",
        type: Literal["info", "success", "warning", "error"] = "info"
    ) -> None:
        """
        发送通知到前端
        
        Args:
            message: 通知消息
            priority: 优先级
            type: 通知类型
        """
        if self._notify_callback:
            await self._notify_callback(message, priority, type)
        else:
            print(f"[通知] {message}")
    
    # ==================== 日志记录 ====================
    
    def log(self, message: str, level: str = "info") -> None:
        """
        记录日志
        
        Args:
            message: 日志消息
            level: 日志级别 (info/warning/error)
        """
        if self._log_callback:
            self._log_callback(message, level)
        else:
            print(f"[{level.upper()}] {message}")
    
    # ==================== AI 调用 ====================
    
    async def call_agent(
        self,
        prompt: str,
        schema: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        调用 AI 进行分析
        
        注意: 模型由环境变量 ANTHROPIC_MODEL 控制，不应在代码中指定
        
        Args:
            prompt: 提示词
            schema: 期望返回的 JSON Schema（可选）
            
        Returns:
            Any: AI 返回的结构化数据
        """
        if self._call_agent_callback:
            return await self._call_agent_callback(prompt, schema)
        else:
            raise NotImplementedError("call_agent 未实现")
    
    # ==================== UI State 操作 ====================
    
    @property
    def ui_state(self):
        """UI State 操作"""
        class UIStateOps:
            def __init__(ops_self, manager):
                ops_self.manager = manager
            
            async def get(ops_self, state_id: str) -> Optional[Any]:
                """获取 UI State"""
                if not ops_self.manager:
                    return None
                return await ops_self.manager.get_state(state_id)
            
            async def set(ops_self, state_id: str, data: Any) -> None:
                """设置 UI State"""
                if not ops_self.manager:
                    return
                await ops_self.manager.set_state(state_id, data)
            
            async def initialize_if_needed(ops_self, state_id: str) -> bool:
                """如果不存在则初始化"""
                if not ops_self.manager:
                    return False
                return await ops_self.manager.initialize_state_if_needed(state_id)
        
        return UIStateOps(self.ui_state_manager)
    
    # ==================== 金融数据 API ====================
    
    @property
    def report_api(self):
        """报告数据 API"""
        class ReportAPI:
            def __init__(api_self, db):
                api_self.db = db
            
            async def search_reports(
                api_self,
                criteria: Optional[Dict[str, Any]] = None,
                limit: int = 30
            ) -> List[Dict[str, Any]]:
                """搜索报告"""
                return await api_self.db.search_reports(
                    category=criteria.get('category') if criteria else None,
                    limit=limit
                )
            
            async def get_report(api_self, report_id: str) -> Optional[Dict[str, Any]]:
                """获取单个报告"""
                return await api_self.db.get_report_by_id(report_id)
            
            async def add_tag(api_self, report_id: str, tag: str) -> None:
                """给报告添加标签"""
                # TODO: 实现标签功能
                pass
        
        return ReportAPI(self.database)
    
    @property
    def watchlist_api(self):
        """关注列表 API"""
        class WatchlistAPI:
            def __init__(api_self, db):
                api_self.db = db
            
            async def add_to_watchlist(
                api_self,
                target_name: str,
                target_type: str = "stock",
                notes: Optional[str] = None
            ) -> int:
                """
                添加到关注列表
                
                Args:
                    target_name: 标的名称
                    target_type: 标的类型 (stock/etf/index/industry)
                    notes: 备注
                
                Returns:
                    int: 关注项 ID
                """
                return await api_self.db.watchlist.add_item(
                    target_name=target_name,
                    target_type=target_type,
                    notes=notes
                )
            
            async def get_watchlist(
                api_self,
                status: str = "active"
            ) -> List[Dict[str, Any]]:
                """
                获取关注列表
                
                Args:
                    status: 状态 (active/inactive)
                
                Returns:
                    List[Dict]: 关注项列表
                """
                return await api_self.db.watchlist.get_list(status=status)
            
            async def get_item(api_self, item_id: int) -> Optional[Dict[str, Any]]:
                """
                获取单个关注项
                
                Args:
                    item_id: 关注项 ID
                
                Returns:
                    Dict: 关注项数据
                """
                return await api_self.db.watchlist.get_item(item_id)
            
            async def update_item(
                api_self,
                item_id: int,
                updates: Dict[str, Any]
            ) -> bool:
                """
                更新关注项
                
                Args:
                    item_id: 关注项 ID
                    updates: 要更新的字段
                
                Returns:
                    bool: 是否成功
                """
                return await api_self.db.watchlist.update_item(item_id, updates)
            
            async def remove_from_watchlist(api_self, item_id: int) -> bool:
                """
                从关注列表移除 (软删除)
                
                Args:
                    item_id: 关注项 ID
                
                Returns:
                    bool: 是否成功
                """
                return await api_self.db.watchlist.remove_item(item_id)
            
            async def delete_item(api_self, item_id: int) -> bool:
                """
                完全删除关注项 (硕删除)
                
                Args:
                    item_id: 关注项 ID
                
                Returns:
                    bool: 是否成功
                """
                return await api_self.db.watchlist.delete_item(item_id)
        
        return WatchlistAPI(self.database)
    
    @property
    def alert_api(self):
        """价格提醒 API"""
        class AlertAPI:
            def __init__(api_self, db):
                api_self.db = db
            
            async def create_alert(
                api_self,
                symbol: str,
                target_price: float,
                condition: str = "<="
            ) -> int:
                """创建价格提醒"""
                # TODO: 实现价格提醒功能
                return 0
            
            async def get_active_alerts(api_self) -> List[Dict[str, Any]]:
                """获取活跃的提醒"""
                # TODO: 实现价格提醒功能
                return []
            
            async def delete_alert(api_self, alert_id: int) -> None:
                """删除提醒"""
                # TODO: 实现价格提醒功能
                pass
        
        return AlertAPI(self.database)
    
    @property
    def market_api(self):
        """市场数据 API"""
        class MarketAPI:
            async def get_market_data(
                api_self,
                symbols: List[str]
            ) -> Dict[str, Dict[str, Any]]:
                """获取市场数据"""
                # TODO: 集成 AKShare 或其他数据源
                return {}
            
            async def get_historical_data(
                api_self,
                symbol: str,
                days: int = 30
            ) -> List[Dict[str, Any]]:
                """获取历史数据"""
                # TODO: 集成 AKShare 或其他数据源
                return []
        
        return MarketAPI()
    
    @property
    def portfolio_api(self):
        """投资组合 API"""
        class PortfolioAPI:
            def __init__(api_self, db):
                api_self.db = db
            
            async def get_portfolio(api_self, user_id: str = 'default') -> Dict[str, Any]:
                """
                获取用户持仓数据
                
                Args:
                    user_id: 用户ID
                    
                Returns:
                    持仓数据，如果不存在返回默认值
                """
                return await api_self.db.portfolio.get_or_create_default_portfolio(user_id)
            
            async def update_portfolio(
                api_self, 
                portfolio_data: Dict[str, Any],
                user_id: str = 'default'
            ) -> None:
                """
                更新用户持仓数据
                
                Args:
                    portfolio_data: 持仓数据
                    user_id: 用户ID
                    
                Raises:
                    ValueError: 如果数据验证失败
                """
                await api_self.db.portfolio.upsert_user_portfolio(user_id, portfolio_data)
            
            async def delete_portfolio(api_self, user_id: str = 'default') -> bool:
                """
                删除用户持仓数据
                
                Args:
                    user_id: 用户ID
                    
                Returns:
                    是否成功删除
                """
                return await api_self.db.portfolio.delete_user_portfolio(user_id)
            
            async def calculate_summary(api_self, user_id: str = 'default') -> Dict[str, Any]:
                """
                计算持仓汇总数据
                
                Args:
                    user_id: 用户ID
                    
                Returns:
                    汇总数据：
                    - total_value: 总市值
                    - total_gain: 总盈亏
                    - allocation_by_category: 按类别分配
                """
                portfolio = await api_self.db.portfolio.get_or_create_default_portfolio(user_id)
                
                # 计算总市值（包含现金）
                total_value = portfolio['total_asset_value']
                
                # 计算总成本
                total_cost = portfolio['cash_position']  # 现金不算成本
                for holding in portfolio.get('holdings', []):
                    if 'cost_price' in holding and 'quantity' in holding:
                        if holding['cost_price'] and holding['quantity']:
                            total_cost += holding['cost_price'] * holding['quantity']
                
                # 计算总盈亏
                total_gain = total_value - total_cost
                
                # 按类别统计分配
                allocation_by_category: Dict[str, float] = {}
                for holding in portfolio.get('holdings', []):
                    category = holding.get('category', '未分类')
                    market_value = holding.get('market_value', 0.0)
                    allocation_by_category[category] = allocation_by_category.get(category, 0.0) + market_value
                
                # 转换为百分比
                if total_value > 0:
                    allocation_by_category = {
                        k: (v / total_value) * 100 
                        for k, v in allocation_by_category.items()
                    }
                
                return {
                    'total_value': total_value,
                    'total_cost': total_cost,
                    'total_gain': total_gain,
                    'total_gain_percentage': (total_gain / total_cost * 100) if total_cost > 0 else 0,
                    'allocation_by_category': allocation_by_category
                }
        
        return PortfolioAPI(self.database)
