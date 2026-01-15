import React from 'react';
import { ComponentProps } from '../ComponentRegistry';
import { useReportAnalysis } from '../../hooks/useReportAnalysis';

interface WatchlistItem {
  id: string;
  name: string;
  symbol: string;
  type: string; // ETF/stock/index/industry
  current_price?: number;
  target_price?: number;
  alert_condition?: string; // <=/>=/between
  status: 'active' | 'triggered' | 'disabled';
  notes?: string;
  last_updated?: string;
}

interface RelatedReport {
  id: string;
  title: string;
  summary: string;
  relevance: number; // 0-1
  published_at: string;
}

interface WatchlistState {
  items: WatchlistItem[];
  alerts: Array<{
    id: number;
    symbol: string;
    condition: string;
    target_price: number;
    current_price: number;
    status: 'active' | 'triggered';
  }>;
  related_reports?: RelatedReport[];
}

export const WatchlistTable: React.FC<ComponentProps<WatchlistState>> = ({
  state,
  onAction
}) => {
  const { reportData, alerts: reportAlerts, loading, error, connected } = useReportAnalysis({ autoSubscribe: true });

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-2xl font-bold mb-4">关注列表</h2>
      
      {/* 连接状态 */}
      <div className="mb-4 p-2 rounded-lg text-sm "
        style={{ backgroundColor: connected ? '#d4edda' : '#f8d7da', color: connected ? '#155724' : '#721c24' }}>
        连接状态: <span>{connected ? '已连接' : '未连接'}</span>
        {loading && <span> (加载中...)</span>}
        {error && <span> (错误: {error})</span>}
      </div>
      
      {/* 关注列表表格 */}
      <div className="mb-6">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold">关注标的</h3>
          <button
            onClick={() => onAction && onAction('add_watchlist_item', {})}
            className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
          >
            添加标的
          </button>
        </div>
        
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  名称
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  代码
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  类型
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  当前价格
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  目标价格
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  提醒条件
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  状态
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  操作
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {(state.items || []).map((item, index) => (
                <tr key={item.id || index}>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="font-medium">{item.name}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    {item.symbol}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    {item.type}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    {item.current_price ? `¥${item.current_price.toFixed(2)}` : '-'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    {item.target_price ? `¥${item.target_price.toFixed(2)}` : '-'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    {item.alert_condition || '-'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full
                      ${item.status === 'active' ? 'bg-green-100 text-green-800' : 
                        item.status === 'triggered' ? 'bg-yellow-100 text-yellow-800' : 
                        'bg-gray-100 text-gray-800'}`}>
                      {item.status === 'active' ? '活跃' : 
                       item.status === 'triggered' ? '已触发' : '已禁用'}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    <div className="flex space-x-2">
                      <button
                        onClick={() => onAction && onAction('edit_watchlist_item', { id: item.id })}
                        className="text-blue-600 hover:text-blue-900"
                      >
                        编辑
                      </button>
                      <button
                        onClick={() => onAction && onAction('remove_watchlist_item', { id: item.id })}
                        className="text-red-600 hover:text-red-900"
                      >
                        删除
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      
      {/* 已触发提醒 */}
      {state.alerts && state.alerts.length > 0 && (
        <div className="mb-6">
          <h3 className="text-lg font-semibold mb-2">已触发提醒</h3>
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <ul className="space-y-2">
              {state.alerts.map((alert, index) => (
                <li key={index} className="flex justify-between items-center p-2 bg-white rounded">
                  <span>{alert.symbol}: 价格 {alert.current_price?.toFixed(2)} 已{alert.condition}目标 {alert.target_price}</span>
                  <button
                    onClick={() => onAction && onAction('acknowledge_alert', { id: alert.id })}
                    className="px-3 py-1 bg-yellow-500 text-white rounded text-sm"
                  >
                    确认
                  </button>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
      
      {/* 相关报告 */}
      {(state.related_reports && state.related_reports.length > 0) || (reportData.length > 0) ? (
        <div className="mb-6">
          <h3 className="text-lg font-semibold mb-2">相关报告分析</h3>
          <div className="space-y-3 max-h-64 overflow-y-auto">
            {(reportData.length > 0 ? reportData : state.related_reports || []).map((report, index) => (
              <div key={report.id || index} className="border rounded-lg p-3 bg-blue-50">
                <div className="flex justify-between">
                  <h4 className="font-medium">{report.title}</h4>
                  <span className="text-xs text-gray-500">{new Date(report.published_at || report.timestamp).toLocaleDateString()}</span>
                </div>
                <p className="text-sm text-gray-700 mt-1">{report.summary}</p>
                {(report as any).relevance && (
                  <div className="mt-1">
                    <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">
                      相关度: {((report as any).relevance * 100).toFixed(0)}%
                    </span>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      ) : null}
      
      {/* 操作按钮 */}
      <div className="flex space-x-4">
        <button
          onClick={() => onAction && onAction('refresh_watchlist', {})}
          className="px-4 py-2 bg-gray-500 text-white rounded hover:bg-gray-600"
        >
          刷新列表
        </button>
        <button
          onClick={() => onAction && onAction('export_watchlist', {})}
          className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600"
        >
          导出列表
        </button>
      </div>
    </div>
  );
};