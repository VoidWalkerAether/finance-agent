import React from 'react';
import { ComponentProps } from './ComponentRegistry';
import { useReportAnalysis } from '../../hooks/useReportAnalysis';

interface ReportAnalysisState {
  reports: {
    id: string;
    title: string;
    summary: string;
    key_metrics: Record<string, any>;
    trends: Array<{
      indicator: string;
      value: number;
      change: number;
      change_percent: number;
    }>;
    recommendations: string[];
    timestamp: string;
    source: string;
  }[];
  alerts: {
    id: string;
    alert_type: string;
    message: string;
    severity: 'low' | 'medium' | 'high' | 'critical';
    triggered_at: string;
    related_symbols?: string[];
    report_id?: string;
  }[];
}

export const MarketMonitor: React.FC<ComponentProps<ReportAnalysisState>> = ({
  state,
  onAction
}) => {
  const { reportData, alerts, loading, error, connected } = useReportAnalysis({ autoSubscribe: true });
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-2xl font-bold mb-4">市场监控</h2>
      
      {/* 连接状态 */}
      <div className="mb-4 p-2 rounded-lg text-sm "
        style={{ backgroundColor: connected ? '#d4edda' : '#f8d7da', color: connected ? '#155724' : '#721c24' }}>
        连接状态: <span>{connected ? '已连接' : '未连接'}</span>
        {loading && <span> (加载中...)</span>}
        {error && <span> (错误: {error})</span>}
      </div>
      
      {/* 报告分析更新 */}
      <div className="mb-6">
        <h3 className="text-lg font-semibold mb-2">报告分析更新</h3>
        <div className="space-y-4 max-h-96 overflow-y-auto">
          {(reportData.length > 0 ? reportData : state.reports || []).map((report, index) => (
            <div key={report.id || index} className="border rounded-lg p-4 bg-gray-50">
              <div className="flex justify-between items-start">
                <h4 className="font-medium text-lg">{report.title}</h4>
                <span className="text-xs text-gray-500">{new Date(report.timestamp).toLocaleString()}</span>
              </div>
              <p className="text-gray-700 my-2">{report.summary}</p>
              
              {/* 关键指标 */}
              {report.key_metrics && Object.keys(report.key_metrics).length > 0 && (
                <div className="mt-2">
                  <h5 className="font-medium text-sm mb-1">关键指标:</h5>
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(report.key_metrics).map(([key, value], idx) => (
                      <span key={idx} className="bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded">
                        {key}: {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              
              {/* 趋势分析 */}
              {report.trends && report.trends.length > 0 && (
                <div className="mt-2">
                  <h5 className="font-medium text-sm mb-1">趋势分析:</h5>
                  <div className="space-y-1">
                    {report.trends.map((trend, idx) => (
                      <div key={idx} className="flex justify-between text-sm">
                        <span>{trend.indicator}</span>
                        <span className={trend.change >= 0 ? 'text-green-600' : 'text-red-600'}>
                          {trend.change >= 0 ? '+' : ''}{trend.change} ({trend.change_percent >= 0 ? '+' : ''}{trend.change_percent}%)
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              
              {/* 投资建议 */}
              {report.recommendations && report.recommendations.length > 0 && (
                <div className="mt-2">
                  <h5 className="font-medium text-sm mb-1">投资建议:</h5>
                  <ul className="list-disc pl-5 text-sm space-y-1">
                    {report.recommendations.map((rec, idx) => (
                      <li key={idx}>{rec}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ))}
          
          {(reportData.length === 0 && (!state.reports || state.reports.length === 0)) && (
            <p className="text-gray-500 text-center py-4">暂无报告分析数据</p>
          )}
        </div>
      </div>
      
      {/* 预警信息 */}
      <div className="mb-6">
        <h3 className="text-lg font-semibold mb-2">预警信息</h3>
        <div className="space-y-2 max-h-48 overflow-y-auto">
          {(alerts.length > 0 ? alerts : state.alerts || []).map((alert, index) => (
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
                {alert.related_symbols && alert.related_symbols.length > 0 && 
                  ` | 相关标的: ${alert.related_symbols.join(', ')}`}
              </div>
            </div>
          ))}
          
          {(alerts.length === 0 && (!state.alerts || state.alerts.length === 0)) && (
            <p className="text-gray-500 text-center py-2">暂无预警信息</p>
          )}
        </div>
      </div>
      
      {/* 操作按钮 */}
      <div className="flex space-x-4">
        <button
          onClick={() => onAction && onAction('refresh_report_analysis', {})}
          className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
        >
          刷新分析
        </button>
        <button
          onClick={() => onAction && onAction('generate_report', {})}
          className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600"
        >
          生成报告
        </button>
      </div>
    </div>
  );
};