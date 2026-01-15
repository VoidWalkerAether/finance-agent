"""
搜索会话管理 - 支持多轮对话和流式输出

功能：
1. 管理单个搜索会话的生命周期
2. 保持 SDK session_id 实现多轮对话
3. 流式输出 AI 回复
4. 智能路由（本地数据库 vs 网络搜索）
"""

import json
import time
from typing import Optional, Any, Dict
from .message_types import WSClient


class SearchSession:
    """
    搜索会话类
    
    管理单个 WebSocket 连接的搜索会话，支持多轮对话
    """
    
    def __init__(
        self,
        websocket: WSClient,
        search_service: Any,
        session_id: str,
        resume_id: Optional[str] = None  # 增加可选参数，用于多轮对话
    ):
        """
        初始化搜索会话
        
        Args:
            websocket: WebSocket 客户端连接
            search_service: SearchService 实例
            session_id: 会话 ID
            resume_id: SDK session_id，用于恢复多轮对话
        """
        self.websocket = websocket
        self.search_service = search_service
        self.session_id = session_id
        self.resume_id: Optional[str] = resume_id  # SDK session_id（多轮对话关键）
        self.created_at = time.time()
        
        if resume_id:
            print(f"⚙️  [SearchSession] 恢复搜索会话: {session_id} (resume: {resume_id})")
        else:
            print(f"✅ [SearchSession] 创建搜索会话: {session_id}")
    
    async def handle_query(self, query: str, limit: int = 10):
        """
        处理用户查询（主入口）
        
        Args:
            query: 用户查询语句
            limit: 结果数量限制
        """
        try:
            print(f"🔍 [SearchSession {self.session_id}] 处理查询: {query}")
            
            # 1. 发送状态：正在识别意图
            await self._send_status("recognizing_intent", "正在识别查询意图...")
            
            # 2. 意图识别
            intent_data = await self._classify_intent(query)
            intent = intent_data.get("intent", "GENERAL")
            
            # 3. 发送意图识别结果
            await self._send_intent(intent_data)
            
            # 4. 根据意图执行搜索
            if intent == "FINANCE":
                await self._search_local(query, limit)
            else:
                await self._search_web_stream(query)
            
        except Exception as e:
            print(f"❌ [SearchSession {self.session_id}] 查询失败: {e}")
            await self._send_error(str(e), "搜索过程中发生错误")
    
    async def _classify_intent(self, query: str) -> Dict[str, Any]:
        """
        识别用户查询意图
        
        Args:
            query: 用户查询
            
        Returns:
            Dict: 意图识别结果
        """
        try:
            result = await self.search_service.classify_intent(query)
            print(f"💡 [SearchSession {self.session_id}] 意图: {result.get('intent')} (置信度: {result.get('confidence')})")
            return result
        except Exception as e:
            print(f"⚠️  [SearchSession {self.session_id}] 意图识别失败: {e}")
            return {"intent": "GENERAL", "reason": str(e), "confidence": 0.0}
    
    async def _search_local(self, query: str, limit: int):
        """
        执行本地数据库搜索并生成 AI 回答
        
        Args:
            query: 查询语句
            limit: 结果数量
        """
        try:
            # 发送状态
            await self._send_status("searching_local", "正在搜索本地数据库...")
            
            # 执行搜索
            results = await self.search_service.db.smart_search_reports(query=query, limit=limit)
            
            print(f"📊 [SearchSession {self.session_id}] 本地搜索返回 {len(results)} 条结果")
            
            if not results:
                # 未找到结果
                await self._send_chunk("抱歉，未找到相关的金融报告。请尝试使用其他关键词搜索。")
                await self._send_complete(0.0, 0)
                return
            
            # 发送状态：正在分析
            await self._send_status("analyzing", f"找到 {len(results)} 条相关报告，正在分析...")
            
            # 构造报告信息（传递给 AI）
            report_ids = [r['report_id'] for r in results[:3]]  # 只取前3条
            report_info = "\n\n".join([
                f"**报告 {i+1}: {r['title']}**\n"
                f"核心观点: {r.get('summary_one_sentence', '')}\n"
                f"关键驱动力: {', '.join(r.get('key_drivers', []))}\n"
                f"投资建议: {r.get('action', '')}"
                for i, r in enumerate(results[:3])
            ])
            
            # 调用 AI 生成回答
            ai_prompt = f"""用户问题：{query}

我已为您找到以下相关的金融报告：

{report_info}

请基于以上报告内容，回答用户的问题。请使用 search_reports 和 read_report 工具获取详细内容，给出具体的投资建议和分析。"""
            
            options = {
                "system_prompt": "你是一个专业的金融分析师。请优先使用本地报告数据库回答问题，给出具体、有数据支撑的投资建议。",
                "allowed_tools": ["mcp__reports__search_reports", "mcp__reports__read_report"],
                "max_turns": 10,
                "resume": self.resume_id
            }
            
            print(f"🤖 [SearchSession {self.session_id}] 开始 AI 分析 (resume: {self.resume_id})")
            
            total_cost = 0.0
            duration_ms = 0
            
            # 流式输出 AI 回答
            async for message in self.search_service.ai_client.query_stream(ai_prompt, options):
                print(f"📨 [SearchSession {self.session_id}] 收到消息类型: {message.type}")  # 增加调试
                
                # 系统消息：提取 session_id
                if message.type == "system":
                    if hasattr(message, 'session_id') and message.session_id:
                        self.resume_id = message.session_id
                        print(f"🔑 [SearchSession {self.session_id}] 保存 SDK session_id: {self.resume_id}")
                
                # 助手消息：流式发送文本
                elif message.type == "assistant":
                    print(f"🤖 [SearchSession {self.session_id}] AssistantMessage content 类型: {type(message.content)}")  # 调试
                    if isinstance(message.content, list):
                        print(f"📝 [SearchSession {self.session_id}] content 列表长度: {len(message.content)}")  # 调试
                        for block in message.content:
                            print(f"   block 类型: {type(block)}, 内容: {block if isinstance(block, dict) else 'not dict'}")  # 调试
                            if isinstance(block, dict) and block.get('type') == 'text':
                                text = block.get('text', '')
                                if text:
                                    print(f"✅ [SearchSession {self.session_id}] 发送文本块，长度: {len(text)}")  # 调试
                                    await self._send_chunk(text)
                            else:
                                print(f"⚠️  [SearchSession {self.session_id}] 跳过非文本块: {block.get('type') if isinstance(block, dict) else 'unknown'}")  # 调试
                    elif isinstance(message.content, str):
                        print(f"✅ [SearchSession {self.session_id}] 发送字符串内容，长度: {len(message.content)}")  # 调试
                        await self._send_chunk(message.content)
                    else:
                        print(f"⚠️  [SearchSession {self.session_id}] 未知 content 类型: {type(message.content)}")  # 调试
                
                # 结果消息：提取成本、耗时和 session_id
                elif message.type == "result":
                    total_cost = getattr(message, 'total_cost_usd', 0.0)
                    duration_ms = getattr(message, 'duration_ms', 0)
                    
                    result_session_id = getattr(message, 'session_id', None)
                    if result_session_id:
                        self.resume_id = result_session_id
                        print(f"🔑 [SearchSession {self.session_id}] 从 ResultMessage 保存 SDK session_id: {self.resume_id}")
            
            # 发送完成消息
            await self._send_complete(total_cost, duration_ms)
            print(f"✅ [SearchSession {self.session_id}] 本地搜索完成 (成本: ${total_cost:.6f})")
            
        except Exception as e:
            print(f"❌ [SearchSession {self.session_id}] 本地搜索失败: {e}")
            import traceback
            traceback.print_exc()
            await self._send_error(str(e), "本地数据库搜索失败")
    
    async def _search_web_stream(self, query: str):
        """
        执行流式网络搜索
        
        Args:
            query: 查询语句
        """
        try:
            # 发送状态
            await self._send_status("searching_web", "正在进行网络搜索...")
            
            # 准备 AI 查询选项
            options = {
                "system_prompt": "你是一个通用的AI助手。请通过网络搜索回答用户的问题。",
                "allowed_tools": ["WebSearch", "WebFetch"],
                "mcp_servers": {},  # 禁用 MCP 服务器
                "max_turns": 10,
                "resume": self.resume_id  # ✅ 多轮对话关键
            }
            
            print(f"🌐 [SearchSession {self.session_id}] 开始流式网络搜索 (resume: {self.resume_id})")
            
            total_cost = 0.0
            duration_ms = 0
            
            # 使用 query_stream 实现流式输出
            async for message in self.search_service.ai_client.query_stream(query, options):
                print(f"📨 [SearchSession {self.session_id}] 收到消息类型: {message.type}")
                
                # 系统消息：提取 session_id
                if message.type == "system":
                    print(f"⚙️  [SearchSession {self.session_id}] SystemMessage 详情: {message.__dict__ if hasattr(message, '__dict__') else 'No __dict__'}")
                    if hasattr(message, 'session_id') and message.session_id:
                        self.resume_id = message.session_id
                        print(f"🔑 [SearchSession {self.session_id}] 保存 SDK session_id: {self.resume_id}")
                    else:
                        print(f"⚠️  [SearchSession {self.session_id}] SystemMessage 没有 session_id 或为 None")
                
                # 助手消息：流式发送文本
                elif message.type == "assistant":
                    if isinstance(message.content, list):
                        for block in message.content:
                            if block.get('type') == 'text':
                                text = block.get('text', '')
                                if text:
                                    await self._send_chunk(text)
                    elif isinstance(message.content, str):
                        await self._send_chunk(message.content)
                
                # 结果消息：提取成本、耗时和 session_id
                elif message.type == "result":
                    total_cost = getattr(message, 'total_cost_usd', 0.0)
                    duration_ms = getattr(message, 'duration_ms', 0)
                    
                    # 提取 session_id
                    result_session_id = getattr(message, 'session_id', None)
                    if result_session_id:
                        self.resume_id = result_session_id
                        print(f"🔑 [SearchSession {self.session_id}] 从 ResultMessage 保存 SDK session_id: {self.resume_id}")
                    else:
                        print(f"⚠️  [SearchSession {self.session_id}] ResultMessage 没有 session_id")
            
            # 发送完成消息
            await self._send_complete(total_cost, duration_ms)
            print(f"✅ [SearchSession {self.session_id}] 网络搜索完成 (成本: ${total_cost:.6f})")
            
        except Exception as e:
            print(f"❌ [SearchSession {self.session_id}] 网络搜索失败: {e}")
            import traceback
            traceback.print_exc()
            await self._send_error(str(e), "网络搜索失败")
    
    # ========== 消息发送方法 ==========
    
    async def _send_status(self, status: str, message: str):
        """发送状态消息"""
        await self.websocket.send_text(json.dumps({
            "type": "search_status",
            "status": status,
            "message": message
        }))
    
    async def _send_intent(self, intent_data: Dict[str, Any]):
        """发送意图识别结果"""
        await self.websocket.send_text(json.dumps({
            "type": "search_intent",
            "intent": intent_data.get("intent", ""),
            "reason": intent_data.get("reason", ""),
            "confidence": intent_data.get("confidence", 0.0)
        }))
    
    async def _send_result(self, search_type: str, results: list):
        """发送搜索结果"""
        try:
            print(f"📦 [SearchSession {self.session_id}] 准备发送 {len(results)} 条结果")
            
            # 转换结果为 JSON 可序列化的格式
            serializable_results = []
            for result in results:
                if isinstance(result, dict):
                    # 处理 datetime 对象
                    clean_result = {}
                    for key, value in result.items():
                        if hasattr(value, 'isoformat'):  # datetime 对象
                            clean_result[key] = value.isoformat()
                        else:
                            clean_result[key] = value
                    serializable_results.append(clean_result)
                else:
                    serializable_results.append(result)
            
            message = json.dumps({
                "type": "search_result",
                "search_type": search_type,
                "results": serializable_results
            }, ensure_ascii=False)
            
            print(f"✅ [SearchSession {self.session_id}] 结果序列化成功，消息长度: {len(message)}")
            await self.websocket.send_text(message)
            print(f"✅ [SearchSession {self.session_id}] 结果发送成功")
            
        except Exception as e:
            print(f"❌ [SearchSession {self.session_id}] 发送结果失败: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    async def _send_chunk(self, text: str):
        """发送流式文本块"""
        await self.websocket.send_text(json.dumps({
            "type": "search_chunk",
            "text": text
        }))
    
    async def _send_complete(self, cost: float, duration_ms: int):
        """发送搜索完成消息"""
        try:
            print(f"🏁 [SearchSession {self.session_id}] 准备发送完成消息 (resume_id: {self.resume_id})")
            await self.websocket.send_text(json.dumps({
                "type": "search_complete",
                "cost": cost,
                "duration_ms": duration_ms,
                "session_id": self.resume_id  # 返回 SDK session_id 供客户端保存
            }))
            print(f"✅ [SearchSession {self.session_id}] 完成消息发送成功")
        except Exception as e:
            print(f"❌ [SearchSession {self.session_id}] 发送完成消息失败: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    async def _send_error(self, error: str, message: str):
        """发送错误消息"""
        await self.websocket.send_text(json.dumps({
            "type": "search_error",
            "error": error,
            "message": message
        }))
    
    async def cleanup(self):
        """清理会话资源"""
        print(f"🧹 [SearchSession {self.session_id}] 清理会话")
        # 未来可以添加更多清理逻辑
