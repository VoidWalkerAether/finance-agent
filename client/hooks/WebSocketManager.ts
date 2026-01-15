export interface WebSocketMessage {
  type: string;
  [key: string]: any;
}

// 定义定时器类型
type TimeoutHandle = number | null;

export interface WebSocketManagerOptions {
  url: string;
  onOpen?: () => void;
  onClose?: () => void;
  onError?: (error: Event) => void;
  onMessage?: (message: WebSocketMessage) => void;
}

export class WebSocketManager {
  private ws: WebSocket | null = null;
  private url: string;
  private onOpen?: () => void;
  private onClose?: () => void;
  private onError?: (error: Event) => void;
  private onMessage?: (message: WebSocketMessage) => void;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 3000;
  private reconnectTimeout: TimeoutHandle = null;

  constructor(options: WebSocketManagerOptions) {
    this.url = options.url;
    this.onOpen = options.onOpen;
    this.onClose = options.onClose;
    this.onError = options.onError;
    this.onMessage = options.onMessage;
  }

  connect(): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      return;
    }

    try {
      this.ws = new WebSocket(this.url);
      
      this.ws.onopen = () => {
        this.reconnectAttempts = 0; // 重置重连计数
        if (this.onOpen) {
          this.onOpen();
        }
      };

      this.ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          if (this.onMessage) {
            this.onMessage(message);
          }
        } catch (err) {
          console.error('解析WebSocket消息失败:', err);
        }
      };

      this.ws.onclose = () => {
        if (this.onClose) {
          this.onClose();
        }

        // 尝试重连
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
          this.reconnectTimeout = setTimeout(() => {
            this.reconnectAttempts++;
            this.connect();
          }, this.reconnectDelay);
        }
      };

      this.ws.onerror = (error) => {
        if (this.onError) {
          this.onError(error);
        }
      };
    } catch (error) {
      console.error('创建WebSocket连接失败:', error);
      if (this.onError) {
        this.onError(error as Event);
      }
    }
  }

  disconnect(): void {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
    
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  send(message: WebSocketMessage): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket连接未建立，无法发送消息:', message);
    }
  }

  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }

  subscribeReportAnalysis(): void {
    if (this.isConnected()) {
      this.send({
        type: 'subscribe_report_analysis',
      });
    }
  }

  unsubscribeReportAnalysis(): void {
    if (this.isConnected()) {
      this.send({
        type: 'unsubscribe_report_analysis',
      });
    }
  }
}