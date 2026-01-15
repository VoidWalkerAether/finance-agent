import { useState, useEffect, useRef } from 'react';
import { WebSocketManager, WebSocketMessage } from './WebSocketManager';

export interface ReportAnalysisData {
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
}

export interface AlertData {
  id: string;
  alert_type: string;
  message: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  triggered_at: string;
  related_symbols?: string[];
  report_id?: string;
}

export const useReportAnalysis = (options?: { autoSubscribe?: boolean }) => {
  const [reportData, setReportData] = useState<ReportAnalysisData[]>([]);
  const [alerts, setAlerts] = useState<AlertData[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [connected, setConnected] = useState<boolean>(false);
  
  const wsManagerRef = useRef<WebSocketManager | null>(null);
  const optionsRef = useRef(options);
  optionsRef.current = options;

  useEffect(() => {
    // 初始化WebSocket连接
    const wsManager = new WebSocketManager({
      url: `ws://localhost:3000/ws`,
      onOpen: () => {
        console.log('报告分析WebSocket连接已建立');
        setConnected(true);
        setError(null);
        
        // 如果设置了自动订阅，则订阅报告分析更新
        if (optionsRef.current?.autoSubscribe !== false) {
          wsManager.subscribeReportAnalysis();
        }
      },
      onClose: () => {
        console.log('报告分析WebSocket连接已关闭');
        setConnected(false);
      },
      onError: (error) => {
        console.error('报告分析WebSocket错误:', error);
        setError('WebSocket连接错误');
      },
      onMessage: (message: WebSocketMessage) => {
        try {
          switch (message.type) {
            case 'report_analysis_update':
              // 处理报告分析更新
              setReportData(prev => {
                const newReportData = message.data as ReportAnalysisData;
                // 检查是否已存在相同ID的报告，如果存在则更新，否则添加
                const existingIndex = prev.findIndex(r => r.id === newReportData.id);
                if (existingIndex >= 0) {
                  const updated = [...prev];
                  updated[existingIndex] = newReportData;
                  return updated;
                } else {
                  return [newReportData, ...prev];
                }
              });
              break;
              
            case 'alert_triggered':
              // 处理预警触发
              const newAlert = message.data as AlertData;
              setAlerts(prev => {
                // 避免重复添加相同的预警
                const exists = prev.some(alert => alert.id === newAlert.id);
                if (!exists) {
                  return [newAlert, ...prev];
                }
                return prev;
              });
              break;
              
            case 'ui_state_update':
              // 处理UI状态更新（如果需要）
              break;
              
            default:
              console.log('收到未处理的消息类型:', message.type);
          }
        } catch (err) {
          console.error('处理WebSocket消息失败:', err);
        }
      }
    });

    wsManagerRef.current = wsManager;
    wsManager.connect();

    // 设置初始加载状态
    setTimeout(() => setLoading(false), 500);

    // 清理函数
    return () => {
      if (wsManagerRef.current) {
        wsManagerRef.current.disconnect();
        wsManagerRef.current = null;
      }
    };
  }, []);

  // 订阅报告分析更新
  const subscribeToReportAnalysis = () => {
    if (wsManagerRef.current) {
      wsManagerRef.current.subscribeReportAnalysis();
    }
  };

  // 取消订阅报告分析更新
  const unsubscribeFromReportAnalysis = () => {
    if (wsManagerRef.current) {
      wsManagerRef.current.unsubscribeReportAnalysis();
    }
  };

  // 发送自定义消息
  const sendMessage = (message: WebSocketMessage) => {
    if (wsManagerRef.current) {
      wsManagerRef.current.send(message);
    } else {
      console.warn('WebSocket连接未建立，无法发送消息:', message);
    }
  };

  return {
    reportData,
    alerts,
    loading,
    error,
    connected,
    subscribeToReportAnalysis,
    unsubscribeFromReportAnalysis,
    sendMessage,
  };
};