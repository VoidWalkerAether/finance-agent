import React from 'react';
import { ComponentProps } from '../ComponentRegistry';
import { useReportAnalysis } from '../../hooks/useReportAnalysis';

interface PortfolioHolding {
  id: string;
  name: string;
  symbol: string;
  type: string;
  quantity: number;
  current_price: number;
  purchase_price: number;
  current_value: number;
  gain: number;
  gain_percentage: number;
  allocation: number; // 百分比
}

interface PortfolioState {
  total_value: number;
  cash_balance: number;
  total_gain: number;
  total_gain_percentage: number;
  holdings: PortfolioHolding[];
  allocation_summary: Record<string, number>; // 按类型分配
  performance_chart_data?: Array<{
    date: string;
    value: number;
  }>;
}

export const PortfolioDashboard: React.FC<ComponentProps<PortfolioState>> = ({
  state,
  onAction
}) => {
  const { reportData, alerts, loading, error, connected } = useReportAnalysis({ autoSubscribe: true });

  // 计算总览数据
  const totalValue = state.total_value || 0;
  const cashBalance = state.cash_balance || 0;
  const totalGain = state.total_gain || 0;
  const totalGainPercentage = state.total_gain_percentage || 0;

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-2xl font-bold mb-4">投资组合仪表盘</h2>
      
      {/* 连接状态 */}
      <div className="mb-4 p-2 rounded-lg text-sm "
        style={{ backgroundColor: connected ? '#d4edda' : '#f8d7da', color: connected ? '#155724' : '#721c24' }}>
        连接状态: <span>{connected ? '已连接' : '未连接'}</span>
        {loading && <span> (加载中...)</span>}
        {error && <span> (错误: {error})</span>}
      </div>
      
      {/* 投资组合概览 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-blue-50 p-4 rounded-lg">
          <h3 className="text-sm text-gray-500">总资产</h3>
          <p className="text-xl font-bold">¥{totalValue.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</p>
        </div>
        <div className="bg-green-50 p-4 rounded-lg">
          <h3 className="text-sm text-gray-500">现金余额</h3>
          <p className="text-xl font-bold">¥{cashBalance.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</p>
        </div>
        <div className={`p-4 rounded-lg ${totalGain >= 0 ? 'bg-green-50' : 'bg-red-50'}`}>
          <h3 className="text-sm text-gray-500">总盈亏</h3>
          <p className={`text-xl font-bold ${totalGain >= 0 ? 'text-green-600' : 'text-red-600'}`}>
            {totalGain >= 0 ? '+' : ''}¥{Math.abs(totalGain).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </p>
        </div>
        <div className={`p-4 rounded-lg ${totalGainPercentage >= 0 ? 'bg-green-50' : 'bg-red-50'}`}>
          <h3 className="text-sm text-gray-500">总盈亏率</h3>
          <p className={`text-xl font-bold ${totalGainPercentage >= 0 ? 'text-green-600' : 'text-red-600'}`}>
            {totalGainPercentage >= 0 ? '+' : ''}{totalGainPercentage.toFixed(2)}%
          </p>
        </div>
      </div>
      
      {/* 持仓列表 */}
      <div className="mb-6">
        <h3 className="text-lg font-semibold mb-2">持仓详情</h3>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  标的
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  类型
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  数量
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  当前价格
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  当前价值
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  盈亏
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  盈亏率
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  配置比例
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {(state.holdings || []).map((holding, index) => (
                <tr key={holding.id || index}>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="font-medium">{holding.name}</div>
                    <div className="text-sm text-gray-500">{holding.symbol}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    {holding.type}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    {holding.quantity}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    ¥{holding.current_price.toFixed(2)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    ¥{holding.current_value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </td>
                  <td className={`px-6 py-4 whitespace-nowrap ${holding.gain >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {holding.gain >= 0 ? '+' : ''}¥{Math.abs(holding.gain).toFixed(2)}
                  </td>
                  <td className={`px-6 py-4 whitespace-nowrap ${holding.gain_percentage >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {holding.gain_percentage >= 0 ? '+' : ''}{holding.gain_percentage.toFixed(2)}%
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    {holding.allocation.toFixed(2)}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      
      {/* 资产配置 */}
      <div className="mb-6">
        <h3 className="text-lg font-semibold mb-2">资产配置</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {Object.entries(state.allocation_summary || {}).map(([type, percentage], index) => (
            <div key={index} className="border rounded-lg p-3 text-center">
              <div className="text-lg font-bold">{percentage.toFixed(2)}%</div>
              <div className="text-sm text-gray-600">{type}</div>
            </div>
          ))}
        </div>
      </div>
      
      {/* 相关报告分析 */}
      {reportData.length > 0 && (
        <div className="mb-6">
          <h3 className="text-lg font-semibold mb-2">相关报告分析</h3>
          <div className="space-y-3 max-h-64 overflow-y-auto">
            {reportData.slice(0, 3).map((report, index) => (
              <div key={report.id || index} className="border rounded-lg p-3 bg-blue-50">
                <div className="flex justify-between">
                  <h4 className="font-medium">{report.title}</h4>
                  <span className="text-xs text-gray-500">{new Date(report.timestamp).toLocaleDateString()}</span>
                </div>
                <p className="text-sm text-gray-700 mt-1">{report.summary}</p>
                {report.trends && report.trends.length > 0 && (
                  <div className="mt-2">
                    <h5 className="text-xs font-medium text-gray-600">趋势:</h5>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {report.trends.slice(0, 3).map((trend, idx) => (
                        <span key={idx} className={`text-xs px-2 py-1 rounded ${
                          trend.change >= 0 ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                        }`}>
                          {trend.indicator}: {trend.change >= 0 ? '+' : ''}{trend.change} ({trend.change_percent.toFixed(2)}%)
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
      
      {/* 预警信息 */}
      {alerts.length > 0 && (
        <div className="mb-6">
          <h3 className="text-lg font-semibold mb-2">预警信息</h3>
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {alerts.slice(0, 5).map((alert, index) => (
              <div 
                key={alert.id || index} 
                className="p-3 rounded-lg border-l-4"
                style={{
                  borderLeftColor: 
                    alert.severity === 'critical' ? '#dc3545' : 
                    alert.severity === 'high' ? '#fd7e14' : 
                    alert.severity === 'medium' ? '#ffc107' : '#17a2b8'
                }}
              >
                <div className="flex justify-between">
                  <span className="font-medium">{alert.message}</span>
                  <span className="text-xs text-gray-500">{new Date(alert.triggered_at).toLocaleString()}</span>
                </div>
                <div className="text-xs mt-1">
                  类型: {alert.alert_type} | 严重程度: {alert.severity}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
      
      {/* 操作按钮 */}
      <div className="flex flex-wrap gap-4">
        <button
          onClick={() => onAction && onAction('refresh_portfolio', {})}
          className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
        >
          刷新数据
        </button>
        <button
          onClick={() => onAction && onAction('rebalance_portfolio', {})}
          className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600"
        >
          重新平衡
        </button>
        <button
          onClick={() => onAction && onAction('add_position', {})}
          className="px-4 py-2 bg-purple-500 text-white rounded hover:bg-purple-600"
        >
          添加持仓
        </button>
      </div>
    </div>
  );
};