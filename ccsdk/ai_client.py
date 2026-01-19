"""
AI 客户端 - 与 Claude Agent SDK 交互

对应 TypeScript: email-agent/ccsdk/ai-client.ts

功能:
- 封装 Claude Agent SDK 的 query 方法
- 管理 AI 查询选项
- 提供流式和单次查询接口
"""

import os
import json
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List, AsyncIterable, Union
from dataclasses import dataclass, field

# 强制无缓冲输出（确保 print 日志立即显示）
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# 使用 Claude Agent SDK
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions
from claude_agent_sdk import (
    AssistantMessage as SDKAssistantMsg,
    UserMessage as SDKUserMsg,
    SystemMessage as SDKSystemMsg,
    ResultMessage as SDKResultMsg,
    TextBlock,
    ToolUseBlock,
    ToolResultBlock
)

from .message_types import SDKMessage, SDKUserMessage


@dataclass
class AIQueryOptions:
    """
    AI 查询选项
    
    对应 TypeScript: AIQueryOptions (ai-client.ts 第 8-18 行)
    
    注意: 模型选择由环境变量或 SDK 默认配置决定，无需在此指定
    """
    max_turns: int = 100
    cwd: str = field(default_factory=lambda: str(Path.cwd() / 'agent'))
    allowed_tools: List[str] = field(default_factory=lambda: [
        "mcp__reports__search_reports",  # Finance Agent 自定义工具 - 最高优先级
        "mcp__reports__read_report",     # Finance Agent 自定义工具 - 次优先级
        "Task", "Bash", "Glob", "Grep", "LS", "Read", "Edit", "Write",
        "WebFetch", "TodoWrite", 
        "WebSearch",  # 网络搜索工具 - 最低优先级
        "Skill"
    ])
    system_prompt: str = ""  # 系统提示词（使用 system_prompt 而不是 append_system_prompt）
    mcp_servers: Optional[Dict[str, Any]] = None
    hooks: Optional[Dict[str, Any]] = None
    resume: Optional[str] = None  # SDK session ID for multi-turn
    setting_sources: List[str] = field(default_factory=lambda: ['local', 'project'])


class AIClient:
    """
    AI 客户端
    
    对应 TypeScript: AIClient (ai-client.ts 第 20-114 行)
    
    核心功能:
    - queryStream(): 流式查询 AI
    - querySingle(): 单次查询 AI
    """
    
    def __init__(self, options: Optional[AIQueryOptions] = None):
        """
        初始化 AI 客户端
        
        Args:
            options: 自定义查询选项
        """
        # 加载 Finance Agent 的系统提示词
        finance_prompt_path = Path(__file__).parent / 'finance_agent_prompt.py'
        if finance_prompt_path.exists():
            # 动态导入提示词
            import importlib.util
            spec = importlib.util.spec_from_file_location("finance_agent_prompt", finance_prompt_path)
            if spec and spec.loader:
                prompt_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(prompt_module)
                finance_prompt = getattr(prompt_module, 'FINANCE_AGENT_PROMPT', '')
            else:
                finance_prompt = ''
        else:
            finance_prompt = self._get_default_prompt()
        
        # 默认选项
        default_opts = AIQueryOptions(
            system_prompt=finance_prompt,  # 使用 system_prompt
            mcp_servers=self._get_mcp_servers()
        )
        
        # 合并用户提供的选项
        if options:
            for key, value in options.__dict__.items():
                if value is not None:
                    setattr(default_opts, key, value)
        
        self.default_options = default_opts
    
    def _get_default_prompt(self) -> str:
        """获取默认系统提示词"""
        return """
你是一个基于本地知识库的专业金融分析师。你的核心职责是提取本地研报库中的信息来回答用户问题。

## ！！！最高优先级协议 (CRITICAL PROTOCOL) ！！！
你必须严格遵守以下逻辑流进行操作，任何跳过步骤的行为都是系统错误：

1. **第一步（强制执行）**：
   - 无论用户问什么，必须**首先**调用工具 `search_reports(query=用户问题关键词)`。
   - **绝对禁止**在未执行 `search_reports` 的情况下直接使用 `WebSearch` 或凭记忆回答。

2. **第二步（逻辑判断）**：
   - **情况 A：如果 `search_reports` 返回了结果**：
     - 必须调用 `read_report(report_id=...)` 读取相关度最高的报告全文。
     - 提取字段：`main_points` (主要观点), `core_views` (核心观点), `investment_advice` (投资建议)。
     - 输出回答：必须以"**根据本地报告《[报告标题]》...**"开头。
     - **禁止**在此情况下联网搜索。

   - **情况 B：如果 `search_reports` 返回列表为空**：
     - 仅在此情况下，允许调用 `WebSearch` 搜索网络信息。
     - 输出回答：必须以"**本地报告库中未找到相关内容，根据网络搜索结果...**"开头。

## 回答内容标准
对于找到的本地报告，请按以下结构组织答案，不要啰嗦：
1. **结论**：直接回答用户问题（是/否/趋势）。
2. **核心论据**：基于 `main_points` 和 `core_views`。
3. **投资建议**：基于 `investment_advice`。

---
## 工具调用优先级
1. **最高优先级**：`mcp__reports__search_reports` - 本地报告搜索
2. **次优先级**：`mcp__reports__read_report` - 本地报告读取
3. **最低优先级**：`WebSearch` - 网络搜索（仅在本地无结果时使用）

## 示例演示 (Few-Shot)

**User**: "现在是买入黄金的好时机吗？"

**Model Thinking (隐性思维)**:
1. 用户问黄金。
2. 我必须先查本地库。
3. Action: `search_reports(query="黄金 买入")`

**(Scenario 1: 找到报告)**
**Tool Output**: `[{id: "101", title: "黄金高位震荡分析", score: 0.9}]`
**Model Action**: `read_report(report_id="101")`
**Final Answer**:
"根据本地报告《黄金高位震荡分析》：
目前建议**短期观望**。
- **核心观点**：美联储降息预期已消化，金价处于历史高位。
- **风险提示**：地缘政治溢价正在消退。
- **建议**：等待回调至2000美元附近再考虑配置。"

**(Scenario 2: 没找到报告)**
**Tool Output**: `[]`
**Model Action**: `WebSearch(query="当前黄金投资建议")`
**Final Answer**:
"本地报告库中未找到相关内容。根据网络搜索结果，分析师普遍认为..."
"""

    
    def _get_mcp_servers(self) -> Dict[str, Any]:
        """
        获取 MCP 服务器配置
        
        对应 TypeScript: customServer (custom-tools.ts)
        """
        # Finance Agent 的自定义 MCP 服务器
        custom_tools_path = str(Path(__file__).parent / 'custom_tools.py')
        
        print(f"🔧 [AIClient] MCP 服务器配置信息:")
        print(f"   - custom_tools_path: {custom_tools_path}")
        print(f"   - DATABASE_PATH: {os.environ.get('DATABASE_PATH', './data/finance.db')}")
        
        # 检查 custom_tools.py 文件是否存在
        if not os.path.exists(custom_tools_path):
            print(f"❌ [AIClient] 错误: MCP 服务器脚本不存在: {custom_tools_path}")
            return {}
        
        # 检查文件是否可执行
        if not os.access(custom_tools_path, os.R_OK):
            print(f"❌ [AIClient] 错误: MCP 服务器脚本无读取权限: {custom_tools_path}")
            return {}
            
        # 导入并返回已创建的 MCP 服务器对象
        try:
            import sys
            import importlib.util
            
            # 动态导入 custom_tools 模块
            spec = importlib.util.spec_from_file_location("custom_tools", custom_tools_path)
            if spec and spec.loader:
                custom_tools_module = importlib.util.module_from_spec(spec)
                sys.modules["custom_tools"] = custom_tools_module
                spec.loader.exec_module(custom_tools_module)
                
                # 获取已创建的 MCP 服务器对象
                if hasattr(custom_tools_module, 'custom_server'):
                    mcp_config = {
                        "reports": custom_tools_module.custom_server
                    }
                    print(f"✅ [AIClient] MCP 服务器配置完成: {list(mcp_config.keys())}")
                    return mcp_config
                else:
                    print(f"❌ [AIClient] 错误: custom_tools.py 中未找到 custom_server 对象")
                    return {}
            else:
                print(f"❌ [AIClient] 错误: 无法加载 custom_tools 模块")
                return {}
        except Exception as e:
            print(f"❌ [AIClient] 错误: 导入 custom_tools 模块失败: {e}")
            import traceback
            traceback.print_exc()
            return {}
    
    async def query_stream(
        self,
        prompt: Union[str, AsyncIterable[SDKUserMessage]],
        options: Optional[Dict[str, Any]] = None
    ) -> AsyncIterable[SDKMessage]:
        """
        流式查询 AI
        
        对应 TypeScript: queryStream() (ai-client.ts 第 80-92 行)
        
        Args:
            prompt: 用户提示词或消息流
            options: 查询选项(会与默认选项合并)
        
        Yields:
            SDKMessage: AI 返回的消息流
        """
        print(f"\n🤖 [AIClient] ========== 开始 AI 查询 ==========")
        print(f"📝 [AIClient] Prompt: {str(prompt)[:100]}..." if len(str(prompt)) > 100 else f"📝 [AIClient] Prompt: {prompt}")
        
        # 合并选项（只提取基本类型，避免 JSON 序列化错误）
        merged_options = {}
        
        # 从默认选项中提取基本类型
        for key, value in self.default_options.__dict__.items():
            # 跳过不可序列化的对象
            if key in ['mcp_servers', 'hooks']:
                continue
            # 只保留基本类型
            if isinstance(value, (str, int, bool, list, dict, type(None))):
                merged_options[key] = value
        
        # 合并用户提供的选项
        if options:
            print(f"⚙️  [AIClient] 用户选项: {options}")
            merged_options.update(options)
        
        # 创建 ClaudeAgentOptions
        # 注意: 模型由环境变量配置 (ANTHROPIC_MODEL 或 SDK 默认值)
        print(f"🔧 [AIClient] 创建 Agent 选项...")
        print(f"  - max_turns: {merged_options.get('max_turns', 100)}")
        print(f"  - resume: {merged_options.get('resume', 'None (新会话)')}")
        print(f"  - allowed_tools: {len(merged_options.get('allowed_tools', []))} 个工具")
        print(f"  - mcp_servers: {list(self.default_options.mcp_servers.keys()) if self.default_options.mcp_servers else []}")
        
        # 检查 MCP 服务器配置
        if not self.default_options.mcp_servers:
            print(f"⚠️  [AIClient] 警告: MCP 服务器配置为空")
        else:
            for server_name, server_config in self.default_options.mcp_servers.items():
                print(f"  - MCP 服务器 [{server_name}]: {server_config}")
        
        # 检查系统提示词
        system_prompt = merged_options.get('system_prompt', '')
        if system_prompt:
            prompt_preview = system_prompt[:200].replace('\n', ' ')
            print(f"  - system_prompt: {prompt_preview}...")
            print(f"  - system_prompt 长度: {len(system_prompt)} 字符")
            
            # 检查关键字
            has_search_reports = 'search_reports' in system_prompt
            has_read_report = 'read_report' in system_prompt
            has_priority = '优先使用本地报告' in system_prompt or '优先' in system_prompt
            print(f"  - 包含 'search_reports': {has_search_reports}")
            print(f"  - 包含 'read_report': {has_read_report}")
            print(f"  - 包含 '优先使用': {has_priority}")
        else:
            print(f"  - ⚠️  system_prompt 为空！")
        
        agent_options = ClaudeAgentOptions(
            max_turns=merged_options.get('max_turns', 100),
            allowed_tools=merged_options.get('allowed_tools'),
            #cwd=merged_options.get('cwd'),
            cwd="/Users/caiwei/workbench/claude-agent-sdk-demos/finance-agent",
            system_prompt=system_prompt,  # 系统提示词
            mcp_servers=self.default_options.mcp_servers,  # MCP 服务器配置（包含自定义工具）
            hooks=self.default_options.hooks,  # 钩子函数
            setting_sources=merged_options.get('setting_sources', ['user', 'project']),
            resume=merged_options.get('resume')  # 多轮对话支持
        )
        
        # 使用 ClaudeSDKClient
        print(f"🚀 [AIClient] 启动 ClaudeSDKClient...")
        async with ClaudeSDKClient(options=agent_options) as client:
            print(f"📤 [AIClient] 发送查询到 Claude SDK...")
            await client.query(prompt)
            
            print(f"📡 [AIClient] 开始接收 SDK 响应流...")
            msg_count = 0
            
            # 接收并转换响应
            async for sdk_message in client.receive_response():
                msg_count += 1
                sdk_type = type(sdk_message).__name__
                print(f"📦 [AIClient] SDK 消息 #{msg_count}: {sdk_type}")
                
                self.display_message(sdk_message)
                # 特别检查 SystemMessage
                if sdk_type == 'SystemMessage':
                    print(f"⚙️  [AIClient] SystemMessage 详情: {sdk_message.__dict__}")
                    # 检查 MCP 服务器状态
                    if hasattr(sdk_message, 'data') and sdk_message.data:
                        mcp_servers = sdk_message.data.get('mcp_servers', [])
                        for server in mcp_servers:
                            if server.get('status') == 'failed':
                                print(f"❌ [AIClient] MCP 服务器 [{server.get('name')}] 启动失败")
                                if 'error' in server:
                                    print(f"   错误信息: {server['error']}")
                
                # 将 SDK 消息转换为我们的 SDKMessage 格式
                converted_message = self._convert_sdk_message(sdk_message)
                if converted_message:
                    print(f"✅ [AIClient] 转换成功: {converted_message.type}")
                    yield converted_message
                else:
                    print(f"⚠️  [AIClient] 转换失败或跳过")
            
            print(f"🏁 [AIClient] SDK 响应流结束, 共处理 {msg_count} 条消息")
            print(f"🤖 [AIClient] ========== AI 查询结束 ==========\n")
 
    def display_message(self, msg):
        """Standardized message display function.

        - UserMessage: "User: <content>"
        - AssistantMessage: "Claude: <content>"
        - SystemMessage: ignored
        - ResultMessage: "Result ended" + cost if available
        """
        if isinstance(msg, SDKUserMsg):
            for block in msg.content:
                if isinstance(block, TextBlock):
                    print(f"User: {block.text}")
        elif isinstance(msg, SDKAssistantMsg):
            for block in msg.content:
                if isinstance(block, TextBlock):
                    print(f"Claude: {block.text}")
        elif isinstance(msg, SDKSystemMsg):
            # Ignore system messages
            pass
        elif isinstance(msg, SDKResultMsg):
            print("Result ended")
        
    def _convert_sdk_message(self, sdk_msg: Any) -> Optional[SDKMessage]:
        """
        将 claude_agent_sdk 的消息转换为我们的 SDKMessage 格式
        
        Args:
            sdk_msg: Claude Agent SDK 返回的消息
        
        Returns:
            转换后的 SDKMessage 或 None
        """
        try:
            # AssistantMessage
            if isinstance(sdk_msg, SDKAssistantMsg):
                # 保留完整的 content 结构（支持 text、tool_use、tool_result 等块）
                content = sdk_msg.content
                
                # 如果 content 是 list，转换为字典列表
                if isinstance(content, list):
                    content_blocks = []
                    for block in content:
                        # TextBlock
                        if isinstance(block, TextBlock):
                            content_blocks.append({
                                'type': 'text',
                                'text': block.text
                            })
                        # 已经是字典（已转换）
                        elif isinstance(block, dict):
                            # ⚠️ 检查字典类型，过滤工具相关的块
                            block_type = block.get('type')
                            if block_type in ['tool_use', 'tool_result']:
                                print(f"  🚫 [AIClient] 跳过字典 {block_type} 块，不添加到 content")
                                continue
                            content_blocks.append(block)
                        # ToolUseBlock, ToolResultBlock 等对象
                        elif hasattr(block, 'type'):
                            block_type = block.type
                            
                            # ⚠️ 过滤工具相关的块，不发送到前端
                            if block_type in ['tool_use', 'tool_result']:
                                print(f"  🚫 [AIClient] 跳过 {block_type} 块，不添加到 content")
                                continue
                            
                            block_dict = {'type': block.type}
                            
                            # ToolUseBlock 属性
                            if hasattr(block, 'name'):
                                block_dict['name'] = block.name
                            if hasattr(block, 'id'):
                                block_dict['id'] = block.id
                            if hasattr(block, 'input'):
                                block_dict['input'] = block.input
                            
                            # ToolResultBlock 属性
                            if hasattr(block, 'tool_use_id'):
                                block_dict['tool_use_id'] = block.tool_use_id
                            if hasattr(block, 'is_error'):
                                block_dict['is_error'] = block.is_error
                            
                            # content 可能是字符串、列表或其他类型
                            if hasattr(block, 'content'):
                                content_value = block.content
                                try:
                                    # 如果 content 是列表，转换为字符串或保留列表
                                    if isinstance(content_value, list):
                                        # 尝试提取文本
                                        if content_value and hasattr(content_value[0], 'text'):
                                            block_dict['content'] = content_value[0].text
                                        elif content_value and isinstance(content_value[0], dict) and 'text' in content_value[0]:
                                            block_dict['content'] = content_value[0]['text']
                                        else:
                                            # 转换为 JSON 字符串
                                            block_dict['content'] = json.dumps(content_value)
                                    else:
                                        block_dict['content'] = str(content_value) if content_value is not None else ''
                                except Exception as e:
                                    print(f"⚠️  转换 content 失败: {e}, type: {type(content_value)}")
                                    block_dict['content'] = str(content_value) if content_value is not None else ''
                            
                            content_blocks.append(block_dict)
                    
                    return SDKAssistantMessage(
                        type="assistant",
                        content=content_blocks  # 返回块数组
                    )
                else:
                    # 纯文本内容
                    return SDKAssistantMessage(
                        type="assistant",
                        content=str(content)
                    )
            
            # SystemMessage
            elif isinstance(sdk_msg, SDKSystemMsg):
                print(f"⚙️  [Convert] SystemMessage: subtype={getattr(sdk_msg, 'subtype', '')}")
                session_id = getattr(sdk_msg, 'session_id', None)
                if session_id:
                    print(f"🔑 [Convert] SystemMessage 包含 session_id: {session_id}")
                return SDKSystemMessage(
                    type="system",
                    subtype=getattr(sdk_msg, 'subtype', ''),
                    session_id=session_id
                )
            
            # ResultMessage
            elif isinstance(sdk_msg, SDKResultMsg):
                session_id = getattr(sdk_msg, 'session_id', None)
                if session_id:
                    print(f"🔑 [Convert] ResultMessage 包含 session_id: {session_id}")
                return SDKResultMessage(
                    type="result",
                    subtype="success",
                    result=getattr(sdk_msg, 'result', None),
                    total_cost_usd=getattr(sdk_msg, 'cost', 0.0),
                    duration_ms=getattr(sdk_msg, 'duration', 0),
                    session_id=session_id  # 增加 session_id 提取
                )
            
            # UserMessage (不太常见，但为完整性添加)
            elif isinstance(sdk_msg, SDKUserMsg):
                # 处理 content，可能是列表或字符串
                if isinstance(sdk_msg.content, str):
                    content_text = sdk_msg.content
                elif isinstance(sdk_msg.content, list) and len(sdk_msg.content) > 0:
                    # ⚠️ 过滤工具相关的块，避免显示 ToolResultBlock
                    text_blocks = []
                    for block in sdk_msg.content:
                        # 检查是否是工具块
                        if hasattr(block, 'type'):
                            block_type = block.type
                            if block_type in ['tool_use', 'tool_result']:
                                print(f"  🚫 [AIClient] UserMessage 中跳过 {block_type} 块")
                                continue
                        elif isinstance(block, dict):
                            block_type = block.get('type')
                            if block_type in ['tool_use', 'tool_result']:
                                print(f"  🚫 [AIClient] UserMessage 中跳过字典 {block_type} 块")
                                continue
                        
                        # 提取文本内容
                        if hasattr(block, 'text'):
                            text_blocks.append(block.text)
                        elif isinstance(block, dict) and 'text' in block:
                            text_blocks.append(block['text'])
                        elif isinstance(block, str):
                            text_blocks.append(block)
                    
                    # 合并所有文本块
                    content_text = '\n'.join(text_blocks) if text_blocks else ''
                    
                    # 如果没有提取到任何文本，返回 None（不广播该消息）
                    if not content_text:
                        print(f"  🚫 [AIClient] UserMessage 过滤后无内容，跳过")
                        return None
                else:
                    content_text = str(sdk_msg.content)
                
                return SDKUserMessage(
                    type="user",
                    content=content_text
                )
            
            return None
        
        except Exception as e:
            print(f"⚠️  _convert_sdk_message 错误: {e}, 消息类型: {type(sdk_msg).__name__}")
            import traceback
            traceback.print_exc()
            return None
 
    
    async def query_single(
        self,
        prompt: str,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        单次查询 AI(等待所有消息返回)
        
        对应 TypeScript: querySingle() (ai-client.ts 第 94-113 行)
        
        Args:
            prompt: 用户提示词
            options: 查询选项
        
        Returns:
            dict: {
                'messages': 所有消息列表,
                'cost': 总成本(美元),
                'duration': 持续时间(毫秒)
            }
        """
        messages: List[SDKMessage] = []
        total_cost = 0.0
        duration = 0
        
        async for message in self.query_stream(prompt, options):
            messages.append(message)
            
            if message.type == "result" and message.subtype == "success":
                total_cost = message.total_cost_usd
                duration = message.duration_ms
        
        return {
            'messages': messages,
            'cost': total_cost,
            'duration': duration
        }


# 为了避免循环导入,在这里导入消息类型
from .message_types import (
    SDKSystemMessage,
    SDKAssistantMessage,
    SDKResultMessage
)
