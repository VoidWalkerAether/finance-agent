"""Agent Tools - 提供 AI 能力给 Actions 和 Listeners
对应 TypeScript: websocket-handler.ts 中的 callAgent() 方法

核心功能:
1. callAgent() - 使用 Claude Agent SDK 调用 Claude 获取结构化输出
2. 使用 Tool Use 强制结构化输出
3. 模型选择由环境变量配置，无需代码指定

参考: https://github.com/anthropics/claude-agent-sdk-python/blob/main/examples/streaming_mode.py
"""

import os
import json
from typing import Any, Dict, Optional, Literal

from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions
from claude_agent_sdk.types import AssistantMessage, ToolUseBlock


class AgentTools:
    """
    Agent 工具类 - 提供 AI 调用能力
    对应 TypeScript: ActionContext.callAgent() (websocket-handler.ts 第 553-599 行)
    
    使用 Claude Agent SDK 而非直接使用 Anthropic SDK
    
    注意: 模型选择由环境变量 (ANTHROPIC_MODEL) 或 SDK 默认配置决定
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        初始化 Agent Tools
        
        Args:
            api_key: Anthropic API Key (如果为 None，从环境变量读取)
        """
        self.api_key = api_key or os.environ.get("ANTHROPIC_AUTH_TOKEN")
        if not self.api_key:
            raise ValueError("ANTHROPIC_AUTH_TOKEN not found in environment variables")
        
        # Claude Agent SDK 会自动从环境变量读取 API Key
        # 不需要手动创建客户端
    
    async def call_agent(
        self,
        prompt: str,
        schema: Dict[str, Any]
    ) -> Any:
        """
        调用 Claude 获取结构化输出
        对应 TypeScript: callAgent() (websocket-handler.ts 第 553-599 行)
        
        工作原理:
        1. 使用 Claude Agent SDK 的 ClaudeSDKClient
        2. 定义一个名为 "respond" 的工具，input_schema 为用户提供的 schema
        3. 使用 tool_choice 强制 Claude 调用这个工具
        4. 从流式响应中提取 tool_use block
        
        注意: 模型选择由环境变量或 SDK 配置决定，无需在代码中指定
        
        Args:
            prompt: 用户提示词
            schema: JSON Schema 定义期望的输出结构
        
        Returns:
            结构化输出数据 (dict)
        
        Example:
            >>> tools = AgentTools()
            >>> schema = {
            ...     "type": "object",
            ...     "properties": {
            ...         "category": {"type": "string"},
            ...         "sentiment": {"type": "string", "enum": ["positive", "negative", "neutral"]}
            ...     },
            ...     "required": ["category", "sentiment"]
            ... }
            >>> result = await tools.call_agent(
            ...     prompt="分析这条报告：A股市场表现强劲",
            ...     schema=schema
            ... )
            >>> print(result)
            {'category': '股票市场', 'sentiment': 'positive'}
        """
        print(f"[AgentTools] callAgent() called:")
        print(f"  - Prompt length: {len(prompt)} chars")
        print(f"  - Schema: {json.dumps(schema, ensure_ascii=False)[:100]}...")
        
        try:
            # 定义工具（用于强制结构化输出）
            tools = [
                {
                    "name": "respond",
                    "description": "Respond with structured data matching the schema",
                    "input_schema": schema
                }
            ]
            
            # 配置选项
            options = ClaudeAgentOptions(
                max_tokens=4096,
                max_turns=1,  # 单次调用
                tools=tools,
                tool_choice={"type": "tool", "name": "respond"}  # 强制使用工具
            )
            
            # 使用 ClaudeSDKClient (对应官方示例)
            tool_use_block = None
            async with ClaudeSDKClient() as client:
                await client.query(prompt, options=options)
                
                # 接收响应并查找 ToolUseBlock
                async for message in client.receive_response():
                    if isinstance(message, AssistantMessage):
                        for block in message.content:
                            if isinstance(block, ToolUseBlock):
                                tool_use_block = block
                                break
                        if tool_use_block:
                            break
            
            if not tool_use_block:
                raise ValueError("Agent did not return structured response (no tool_use block)")
            
            # 返回结构化输出
            result = tool_use_block.input
            print(f"[AgentTools] callAgent() completed successfully")
            print(f"  - Result: {json.dumps(result, ensure_ascii=False)[:200]}...")
            
            return result
            
        except Exception as e:
            print(f"❌ [AgentTools] callAgent() failed: {e}")
            raise


# 全局单例 (可选)
_agent_tools_instance: Optional[AgentTools] = None


def get_agent_tools() -> AgentTools:
    """
    获取 AgentTools 单例
    
    Returns:
        AgentTools 实例
    """
    global _agent_tools_instance
    if _agent_tools_instance is None:
        _agent_tools_instance = AgentTools()
    return _agent_tools_instance
