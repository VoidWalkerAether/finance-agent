"""
类型定义

对应 TypeScript: email-agent/ccsdk/types.ts
"""

from typing import Any, Dict, Optional, Literal, Union
from dataclasses import dataclass
from typing import Protocol


# ============================================================================
# WebSocket 相关类型
# ============================================================================

class WSClient(Protocol):
    """
    WebSocket 客户端协议
    
    对应 TypeScript: ServerWebSocket<{ sessionId: string }>
    """
    session_id: Optional[str]
    
    async def send(self, message: str) -> None:
        """发送消息到客户端"""
        ...
    
    async def close(self) -> None:
        """关闭连接"""
        ...


# ============================================================================
# WebSocket 消息类型
# ============================================================================

@dataclass
class ChatMessage:
    """
    聊天消息
    
    对应 TypeScript: ChatMessage
    """
    type: Literal["chat"] = "chat"
    content: str = ""
    session_id: Optional[str] = None
    new_conversation: bool = False


@dataclass
class SubscribeMessage:
    """
    订阅会话消息
    
    对应 TypeScript: SubscribeMessage
    """
    type: Literal["subscribe"] = "subscribe"
    session_id: str = ""


@dataclass
class UnsubscribeMessage:
    """
    取消订阅消息
    
    对应 TypeScript: UnsubscribeMessage
    """
    type: Literal["unsubscribe"] = "unsubscribe"
    session_id: str = ""


@dataclass
class RequestReportsMessage:
    """
    请求报告列表消息
    
    对应 Email Agent 的 RequestInboxMessage
    """
    type: Literal["request_reports"] = "request_reports"


@dataclass
class SubscribeReportAnalysisMessage:
    """
    订阅报告分析消息
    """
    type: Literal["subscribe_report_analysis"] = "subscribe_report_analysis"
    sessionId: str = ""


@dataclass
class UnsubscribeReportAnalysisMessage:
    """
    取消订阅报告分析消息
    """
    type: Literal["unsubscribe_report_analysis"] = "unsubscribe_report_analysis"
    sessionId: str = ""


# ============================================================================
# 智能搜索相关消息类型
# ============================================================================

@dataclass
class WSSearchMessage:
    """
    搜索请求消息
    
    客户端发送此消息发起搜索查询
    """
    type: Literal["search"] = "search"
    query: str = ""
    session_id: Optional[str] = None
    limit: int = 10


@dataclass
class WSSearchStatusMessage:
    """
    搜索状态消息
    
    服务端发送此消息通知搜索进度
    """
    type: Literal["search_status"] = "search_status"
    status: str = ""  # "recognizing_intent", "searching_local", "searching_web"
    message: str = ""


@dataclass
class WSSearchIntentMessage:
    """
    意图识别结果消息
    
    服务端发送意图识别结果
    """
    type: Literal["search_intent"] = "search_intent"
    intent: str = ""  # "FINANCE" or "GENERAL"
    reason: str = ""
    confidence: float = 0.0


@dataclass
class WSSearchResultMessage:
    """
    搜索结果消息
    
    服务端发送本地数据库搜索结果
    """
    type: Literal["search_result"] = "search_result"
    search_type: str = ""  # "local_database" or "web"
    results: list = None
    
    def __post_init__(self):
        if self.results is None:
            self.results = []


@dataclass
class WSSearchChunkMessage:
    """
    流式搜索文本块消息
    
    服务端流式发送 AI 回复的文本片段
    """
    type: Literal["search_chunk"] = "search_chunk"
    text: str = ""


@dataclass
class WSSearchCompleteMessage:
    """
    搜索完成消息
    
    服务端发送此消息表示搜索已完成
    """
    type: Literal["search_complete"] = "search_complete"
    cost: float = 0.0
    duration_ms: int = 0
    session_id: Optional[str] = None


@dataclass
class WSSearchErrorMessage:
    """
    搜索错误消息
    
    服务端发送此消息表示搜索失败
    """
    type: Literal["search_error"] = "search_error"
    error: str = ""
    message: str = ""


# 所有传入消息的联合类型
IncomingMessage = Union[
    ChatMessage, 
    SubscribeMessage, 
    UnsubscribeMessage, 
    RequestReportsMessage, 
    SubscribeReportAnalysisMessage, 
    UnsubscribeReportAnalysisMessage,
    WSSearchMessage  # ✅ 添加搜索消息类型
]


# ============================================================================
# SDK 消息类型
# ============================================================================

@dataclass
class SDKUserMessage:
    """
    SDK 用户消息
    
    对应 TypeScript: @anthropic-ai/claude-agent-sdk SDKUserMessage
    """
    type: Literal["user"] = "user"
    content: str = ""


@dataclass
class SDKAssistantMessage:
    """SDK 助手消息"""
    type: Literal["assistant"] = "assistant"
    content: Union[str, list] = ""


@dataclass
class SDKSystemMessage:
    """SDK 系统消息"""
    type: Literal["system"] = "system"
    subtype: str = ""
    session_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


@dataclass
class SDKResultMessage:
    """SDK 结果消息"""
    type: Literal["result"] = "result"
    subtype: str = "success"  # "success" | "error" | ...
    result: Optional[Any] = None
    total_cost_usd: float = 0.0
    duration_ms: int = 0
    error: Optional[str] = None
    session_id: Optional[str] = None  # 增加 session_id 字段


# SDK 消息联合类型
SDKMessage = Union[SDKUserMessage, SDKAssistantMessage, SDKSystemMessage, SDKResultMessage]


# ============================================================================
# WebSocket 发送消息类型
# ============================================================================

@dataclass
class WSAssistantMessage:
    """发送给 WebSocket 客户端的助手消息"""
    type: Literal["assistant_message"] = "assistant_message"
    content: str = ""
    session_id: str = ""


@dataclass
class WSToolUseMessage:
    """工具使用消息"""
    type: Literal["tool_use"] = "tool_use"
    tool_name: str = ""
    tool_id: str = ""
    tool_input: Dict[str, Any] = None
    session_id: str = ""


@dataclass
class WSToolResultMessage:
    """工具结果消息"""
    type: Literal["tool_result"] = "tool_result"
    tool_use_id: str = ""
    content: Any = None
    is_error: bool = False
    session_id: str = ""


@dataclass
class WSResultMessage:
    """查询结果消息"""
    type: Literal["result"] = "result"
    success: bool = True
    result: Optional[Any] = None
    cost: float = 0.0
    duration: int = 0
    error: Optional[str] = None
    session_id: str = ""


@dataclass
class WSSystemMessage:
    """系统消息"""
    type: Literal["system"] = "system"
    subtype: str = ""
    session_id: str = ""
    data: Optional[Dict[str, Any]] = None


@dataclass
class WSUserMessage:
    """用户消息回显"""
    type: Literal["user_message"] = "user_message"
    content: str = ""
    session_id: str = ""


@dataclass
class WSErrorMessage:
    """错误消息"""
    type: Literal["error"] = "error"
    error: str = ""
    session_id: str = ""


@dataclass
class WSSessionInfo:
    """会话信息"""
    type: Literal["session_info"] = "session_info"
    session_id: str = ""
    message_count: int = 0
    is_active: bool = False


# ============================================================================
# UI State 相关类型
# ============================================================================

@dataclass
class UIStateTemplate:
    """
    UI State 模板定义
    对应 TypeScript: UIStateTemplate<T>
    """
    id: str                         # 唯一标识符
    name: str                       # 人类可读名称
    description: str = ""           # 描述
    initialState: Any = None        # 初始状态数据


@dataclass
class UIStateLogEntry:
    """
    UI State 日志条目（JSONL 格式）
    对应 TypeScript: UIStateLogEntry
    """
    timestamp: str                  # ISO 格式时间戳
    stateId: str                    # 状态 ID
    action: str                     # 操作类型 (update/delete)
    dataSize: int = 0               # 数据大小（字节）


@dataclass
class WSUIStateUpdateMessage:
    """
    UI State 更新消息（WebSocket）
    对应 TypeScript: ui_state_update 消息
    """
    type: Literal["ui_state_update"] = "ui_state_update"
    stateId: str = ""
    data: Any = None
    timestamp: str = ""


# ============================================================================
# Components 相关类型
# ============================================================================

@dataclass
class ComponentTemplate:
    """
    Component 模板定义
    """
    id: str                         # 唯一标识符
    name: str                       # 人类可读名称
    description: str = ""           # 描述
    stateId: str = ""               # 关联的UI状态ID


@dataclass
class ComponentInstance:
    """
    Component 实例
    """
    instanceId: str                 # 实例唯一 ID
    componentId: str                # 组件模板 ID
    stateId: str = ""               # 关联的UI状态ID
    sessionId: str = ""             # 所属会话
    props: Optional[Dict[str, Any]] = None  # 组件属性
    createdAt: str = ""             # 创建时间


@dataclass
class ComponentLogEntry:
    """
    Component 日志条目（JSONL 格式）
    """
    timestamp: str                  # ISO 格式时间戳
    instanceId: str                 # 实例 ID
    componentId: str                # 组件 ID
    sessionId: str                  # 会话 ID
    action: str                     # 操作类型 (create/update/delete)
    dataSize: int = 0               # 数据大小（字节）


@dataclass
class WSComponentInstanceMessage:
    """
    Component 实例消息（WebSocket）
    对应 TypeScript: component_instance 消息
    """
    type: Literal["component_instance"] = "component_instance"
    instance: ComponentInstance = None
    sessionId: str = ""


@dataclass
class WSComponentUpdateMessage:
    """
    Component 更新消息（WebSocket）
    """
    type: Literal["component_update"] = "component_update"
    instanceId: str = ""
    data: Any = None
    sessionId: str = ""


@dataclass
class WSReportAnalysisUpdateMessage:
    """
    报告分析更新消息（WebSocket）
    """
    type: Literal["report_analysis_update"] = "report_analysis_update"
    reportId: str = ""
    title: str = ""
    analysis: Any = None
    timestamp: str = ""
    sessionId: str = ""


@dataclass
class WSAlertTriggeredMessage:
    """
    预警触发消息（WebSocket）
    """
    type: Literal["alert_triggered"] = "alert_triggered"
    alertId: str = ""
    title: str = ""
    message: str = ""
    severity: str = "info"  # info, warning, danger
    data: Any = None
    timestamp: str = ""
    sessionId: str = ""


# 所有发送给客户端的消息类型
OutgoingMessage = Union[
    WSAssistantMessage,
    WSToolUseMessage,
    WSToolResultMessage,
    WSResultMessage,
    WSSystemMessage,
    WSUserMessage,
    WSErrorMessage,
    WSSessionInfo,
    WSUIStateUpdateMessage,
    WSComponentInstanceMessage,
    WSComponentUpdateMessage,
    WSReportAnalysisUpdateMessage,
    WSAlertTriggeredMessage
]


# ============================================================================
# Listeners 相关类型
# ============================================================================

EventType = Literal[
    "report_received",      # 新报告上传
    "report_analyzed",      # 报告分析完成
    "price_alert",          # 价格触发预警
    "daily_summary",        # 每日定时任务
    "user_query"            # 用户提问
]


@dataclass
class ListenerConfig:
    """
    Listener 配置
    对应 TypeScript: ListenerConfig
    """
    id: str                         # 唯一标识符
    name: str                       # 人类可读名称
    description: str = ""           # 描述
    enabled: bool = True            # 是否启用
    event: EventType = "report_received"  # 监听的事件类型


@dataclass
class NotifyOptions:
    """通知选项"""
    priority: Literal["low", "normal", "high"] = "normal"


@dataclass
class ListenerResult:
    """
    Listener 执行结果
    对应 TypeScript: ListenerResult
    """
    executed: bool                  # 是否执行了操作
    reason: str                     # 原因说明
    actions: Optional[list[str]] = None  # 执行的操作列表
    components: Optional[list] = None    # 可选：要渲染的组件实例


@dataclass
class ListenerLogEntry:
    """
    Listener 日志条目（JSONL 格式）
    对应 TypeScript: ListenerLogEntry
    """
    timestamp: str                  # ISO 格式时间戳
    report_id: str                  # 报告 ID
    report_title: str               # 报告标题
    executed: bool                  # 是否执行
    reason: str                     # 原因
    actions: Optional[list[str]] = None
    execution_time_ms: int = 0      # 执行时间（毫秒）
    error: Optional[str] = None     # 错误信息（如果失败）


# ============================================================================
# Actions 相关类型
# ============================================================================

@dataclass
class ActionTemplate:
    """
    Action 模板定义
    对应 TypeScript: ActionTemplate
    """
    id: str                         # 唯一标识符
    name: str                       # 人类可读名称
    description: str = ""           # 描述
    icon: str = "🚀"                # 图标（emoji）
    parameterSchema: Dict[str, Any] = None  # JSON Schema 参数定义


@dataclass
class ActionInstance:
    """
    Action 实例
    由 Agent 在对话中创建，通过参数实例化模板
    对应 TypeScript: ActionInstance
    """
    instanceId: str                 # 实例唯一 ID
    templateId: str                 # 模板 ID
    label: str                      # 按钮显示文本
    description: str = ""           # 可选描述
    params: Dict[str, Any] = None   # 参数
    style: Literal["primary", "secondary", "danger"] = "primary"  # 按钮样式
    sessionId: str = ""             # 所属会话
    createdAt: str = ""             # 创建时间


@dataclass
class ActionResult:
    """
    Action 执行结果
    对应 TypeScript: ActionResult
    """
    success: bool                   # 是否成功
    message: str                    # 结果消息
    data: Optional[Dict[str, Any]] = None       # 可选数据
    components: Optional[list] = None           # 可选：创建的组件实例


@dataclass
class ActionLogEntry:
    """
    Action 执行日志条目（JSONL 格式）
    对应 TypeScript: ActionLogEntry
    """
    timestamp: str                  # ISO 格式时间戳
    instanceId: str                 # 实例 ID
    templateId: str                 # 模板 ID
    sessionId: str                  # 会话 ID
    params: Dict[str, Any]          # 参数
    result: ActionResult            # 执行结果
    duration: int                   # 执行时间（毫秒）
    error: Optional[str] = None     # 错误信息


