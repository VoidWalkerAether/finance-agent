import { useState, useEffect } from 'react';

/**
 * UI状态类型定义
 */
export interface UIState {
  [key: string]: any;
}

/**
 * UI状态管理Hook
 * 用于同步前端组件与后端UI状态管理器的状态
 */
export const useUIState = (stateId: string, initialState: UIState = {}) => {
  const [state, setState] = useState<UIState>(initialState);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // 初始化时从后端获取状态
  useEffect(() => {
    const fetchState = async () => {
      try {
        setLoading(true);
        // 这里应该通过WebSocket或API获取状态
        // 模拟获取状态的逻辑
        const response = await fetch(`/api/ui-state/${stateId}`);
        if (response.ok) {
          const data = await response.json();
          setState(data);
        } else {
          setState(initialState);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : '获取状态失败');
        setState(initialState);
      } finally {
        setLoading(false);
      }
    };

    fetchState();

    // 设置WebSocket监听器以接收状态更新
    const ws = new WebSocket(`ws://localhost:3000/ws`);
    ws.onopen = () => {
      console.log('WebSocket连接已建立');
    };

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        if (message.type === 'ui_state_update' && message.stateId === stateId) {
          setState(message.data);
        }
      } catch (err) {
        console.error('解析WebSocket消息失败:', err);
      }
    };

    ws.onclose = () => {
      console.log('WebSocket连接已关闭');
    };

    ws.onerror = (error) => {
      console.error('WebSocket错误:', error);
    };

    // 清理函数
    return () => {
      ws.close();
    };
  }, [stateId]);

  // 更新状态并发送到后端
  const updateState = async (newState: UIState | ((prevState: UIState) => UIState)) => {
    const updatedState = typeof newState === 'function' ? newState(state) : newState;
    
    setState(updatedState);

    try {
      // 发送到后端UI状态管理器
      await fetch(`/api/ui-state/${stateId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(updatedState),
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : '更新状态失败');
      // 如果更新失败，回滚到之前的状态
      setState(state);
    }
  };

  return {
    state,
    loading,
    error,
    updateState,
  };
};