"""
智能搜索服务

功能：
- 意图识别：判断用户查询是金融相关还是通用问题
- 智能路由：根据意图选择本地数据库搜索或网络搜索
"""

import json
import re
from typing import Dict, Any
from ccsdk.ai_client import AIClient


class SearchService:
    """智能搜索服务"""
    
    def __init__(self, database_manager):
        """
        初始化搜索服务
        
        Args:
            database_manager: 数据库管理器实例
        """
        self.db = database_manager
        self.ai_client = AIClient()
    
    async def classify_intent(self, query: str) -> Dict[str, Any]:
        """
        识别用户查询意图
        
        Args:
            query: 用户查询语句
            
        Returns:
            Dict: 包含 intent (FINANCE/GENERAL), reason, confidence
        """
        prompt = f"""
        你是一个智能金融助手。请分析以下用户查询，并将其分类为以下两类之一：
        1. FINANCE: 关于股票、基金、市场分析、投资建议、黄金、宏观经济或具体金融报告的深度查询。
        2. GENERAL: 关于常识、天气、非金融新闻、闲聊或通用的网络信息查询。

        用户查询: "{query}"

        请仅返回一个 JSON 对象，格式如下：
        {{
          "intent": "FINANCE" | "GENERAL",
          "reason": "分类理由的简短说明",
          "confidence": 0.0 到 1.0 之间的置信度
        }}
        """
        
        try:
            # 使用较轻量的配置进行单次意图识别
            options = {
                "system_prompt": "你是一个专业的意图识别助手。请严格按要求的 JSON 格式输出。",
                "allowed_tools": []  # 意图识别不需要工具
            }
            
            result = await self.ai_client.query_single(prompt, options=options)
            
            # 提取 AI 返回的文本并解析 JSON
            for msg in result.get('messages', []):
                if msg.type == 'assistant':
                    # 尝试从文本中提取 JSON
                    text = ""
                    if isinstance(msg.content, list):
                        for block in msg.content:
                            if block.get('type') == 'text':
                                text += block.get('text', '')
                    else:
                        text = str(msg.content)
                    
                    json_match = re.search(r'\{.*\}', text, re.DOTALL)
                    if json_match:
                        try:
                            return json.loads(json_match.group())
                        except json.JSONDecodeError:
                            continue
            
            return {"intent": "GENERAL", "reason": "无法解析 AI 响应", "confidence": 0.0}
            
        except Exception as e:
            print(f"[SearchService] ⚠️ 意图识别失败: {e}")
            return {"intent": "GENERAL", "reason": str(e), "confidence": 0.0}
    
    async def smart_search(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """
        智能搜索：根据意图选择搜索方式
        
        Args:
            query: 用户查询
            limit: 结果数量
            
        Returns:
            Dict: 搜索结果及元数据
        """
        # 1. 意图识别
        intent_data = await self.classify_intent(query)
        intent = intent_data.get("intent", "GENERAL")
        
        print(f"[SearchService] 🔍 意图识别结果: {intent} (置信度: {intent_data.get('confidence')})")
        
        results = []
        search_type = "unknown"
        
        # 2. 根据意图执行不同的搜索
        if intent == "FINANCE":
            # 金融意图：执行本地数据库搜索
            print(f"[SearchService] 🏦 执行本地数据库搜索...")
            results = await self.db.smart_search_reports(query=query, limit=limit)
            search_type = "local_database"
        else:
            # 通用意图：执行网络搜索
            print(f"[SearchService] 🌐 执行网络搜索...")
            # 使用较通用的提示词，允许直接网络搜索
            options = {
                "system_prompt": "你是一个通用的AI助手。请通过网络搜索回答用户的问题。不要尝试在本地数据库中搜索。",
                "allowed_tools": ["WebSearch", "WebFetch"]
            }
            search_result = await self.ai_client.query_single(query, options=options)
            
            # 提取回答内容作为搜索结果
            for msg in search_result.get('messages', []):
                if msg.type == 'assistant':
                    text = ""
                    if isinstance(msg.content, list):
                        for block in msg.content:
                            if block.get('type') == 'text':
                                text += block.get('text', '')
                    else:
                        text = str(msg.content)
                    
                    if text:
                        results.append({
                            "title": "网络搜索结果",
                            "content": text,
                            "type": "web_search"
                        })
            search_type = "web"
            
        return {
            "query": query,
            "intent": intent_data,
            "search_type": search_type,
            "results": results
        }
