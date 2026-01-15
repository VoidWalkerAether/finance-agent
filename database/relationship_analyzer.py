"""
报告关联性分析服务
基于ChromaDB向量搜索和LLM深度分析实现报告间关联性识别
"""

import json
import asyncio
import re
from typing import Dict, List, Optional, Any
from pathlib import Path

# 项目内部导入
from .database_manager import DatabaseManager


class ReportRelationshipAnalyzer:
    """报告关联性分析器"""
    
    def __init__(self, db_manager: DatabaseManager):
        """
        初始化关联分析器
        
        Args:
            db_manager: 数据库管理器实例
        """
        self.db = db_manager
        # 确保ChromaDB客户端可用
        if hasattr(self.db, 'chroma_client') and self.db.chroma_client:
            self.chroma_client = self.db.chroma_client
            self.reports_collection = self.db.reports_collection
        else:
            self.chroma_client = None
            self.reports_collection = None
        
        # 初始化关联关系表
        try:
            asyncio.create_task(self._initialize_relationships_table())
        except RuntimeError:
            # 如果不在事件循环中，使用同步方式初始化
            import threading
            if threading.current_thread() is threading.main_thread():
                import asyncio as async_module
                loop = async_module.new_event_loop()
                async_module.set_event_loop(loop)
                loop.run_until_complete(self._initialize_relationships_table())
            else:
                # 在非主线程中，简单记录日志
                print(f"[WARNING] [关系分析器] [__init__] 无法在当前上下文中初始化关联关系表")
    
    async def _initialize_relationships_table(self):
        """
        初始化关联关系表
        """
        try:
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS report_relationships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_report_id TEXT NOT NULL,
                target_report_id TEXT NOT NULL,
                relation_type TEXT NOT NULL,
                similarity_score REAL,
                summary TEXT,
                evidence TEXT,
                analysis_json TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
            await self.db.execute_raw_query(create_table_sql)
            
            # 创建索引以提高查询性能
            index_queries = [
                "CREATE INDEX IF NOT EXISTS idx_report_relationships_source ON report_relationships(source_report_id);",
                "CREATE INDEX IF NOT EXISTS idx_report_relationships_target ON report_relationships(target_report_id);",
                "CREATE INDEX IF NOT EXISTS idx_report_relationships_type ON report_relationships(relation_type);",
                "CREATE INDEX IF NOT EXISTS idx_report_relationships_created_at ON report_relationships(created_at);",
                "CREATE INDEX IF NOT EXISTS idx_report_relationships_score ON report_relationships(similarity_score);",
            ]
            
            for sql in index_queries:
                try:
                    await self.db.execute_raw_query(sql)
                except Exception as e:
                    # 索引创建失败通常不影响功能，只记录日志
                    print(f"[WARNING] [关系分析器] [_initialize_relationships_table] 创建索引失败: {e}")
            
            print(f"[INFO] [关系分析器] [_initialize_relationships_table] 关联关系表初始化完成")
        except Exception as e:
            print(f"[ERROR] [关系分析器] [_initialize_relationships_table] 初始化关联关系表失败: {e}")
            import traceback
            traceback.print_exc()
    
    def _prepare_embedding_text(self, report_data: Dict[str, Any]) -> str:
        """
        构建用于向量化的合成语义文本
        
        Args:
            report_data: 报告数据
            
        Returns:
            str: 合成语义文本
        """
        print(f"[DEBUG] [关系分析器] [_prepare_embedding_text] 开始构建合成语义文本, report_id={report_data.get('report_id', 'N/A')}")
        
        # 解析JSON数据
        analysis_json = report_data.get('analysis_json', {})
        if isinstance(analysis_json, str):
            try:
                print(f"[DEBUG] [关系分析器] [_prepare_embedding_text] 解析analysis_json字符串")
                analysis_json = json.loads(analysis_json)
            except json.JSONDecodeError:
                print(f"[WARNING] [关系分析器] [_prepare_embedding_text] analysis_json解析失败，使用空字典")
                analysis_json = {}
        
        report_info = analysis_json.get('report_info', {})
        summary = analysis_json.get('summary', {})
        text_summary = analysis_json.get('text_summary', {})
        risk_warnings = analysis_json.get('risk_warnings', [])
        
        # 构建合成语义文本
        title = report_info.get('title', report_data.get('title', ''))
        category = report_data.get('category', '')
        one_sentence = summary.get('one_sentence', '')
        core_views = '; '.join(text_summary.get('core_views', [])[:10])
        key_drivers = '; '.join(summary.get('key_drivers', [])[:5])
        risks = '; '.join([r.get('description', '') for r in risk_warnings][:5])
        action = analysis_json.get('investment_advice', {}).get('action', '')
        holding_period = analysis_json.get('investment_advice', {}).get('holding_period', '')
        
        print(f"[DEBUG] [关系分析器] [_prepare_embedding_text] 构建文本字段 - 标题: {title[:50]}..., 分类: {category}, 摘要: {one_sentence[:30]}...")
        
        embedding_text = f"""
标题: {title}
分类: {category}
摘要: {one_sentence}
核心观点: {core_views}
关键驱动因素: {key_drivers}
风险: {risks}
投资建议: {action}
时间范围: {holding_period}
"""
        
        print(f"[DEBUG] [关系分析器] [_prepare_embedding_text] 合成语义文本构建完成, 长度={len(embedding_text)}")
        return embedding_text.strip()
    
    async def find_related_reports(self, new_report_id: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        查找关联报告
        
        Args:
            new_report_id: 新报告ID
            max_results: 最大返回结果数
            
        Returns:
            List[Dict]: 关联报告列表
        """
        print(f"[DEBUG] [关系分析器] [find_related_reports] 开始查找关联报告, new_report_id={new_report_id}, max_results={max_results}")
        
        if not self.chroma_client or not self.reports_collection:
            print("[警告] [关系分析器] [find_related_reports] ChromaDB未启用，无法进行关联分析")
            return []
        
        try:
            # 获取新报告
            print(f"[DEBUG] [关系分析器] [find_related_reports] 正在获取新报告 {new_report_id}")
            new_report = await self.db.get_report(new_report_id)
            if not new_report:
                print(f"[警告] [关系分析器] [find_related_reports] 未找到报告 {new_report_id}")
                return []
            
            print(f"[DEBUG] [关系分析器] [find_related_reports] 成功获取报告数据, title='{new_report.get('title', 'N/A')}', category='{new_report.get('category', 'N/A')}'")
            
            # 构建新报告的embedding文本
            query_text = self._prepare_embedding_text(new_report)
            print(f"[DEBUG] [关系分析器] [find_related_reports] 构建embedding文本完成, 长度={len(query_text)}")
            
            # 使用metadata过滤排除自身报告
            where_conditions = {
                "report_id": {"$ne": new_report_id}  # 排除自身
            }
            
            print(f"[DEBUG] [关系分析器] [find_related_reports] 开始执行向量搜索")
            # 执行向量搜索，不限制分类，让语义匹配决定相关性
            results = self.reports_collection.query(
                query_texts=[query_text],
                where=where_conditions,
                n_results=max_results
            )
            print(f"[DEBUG] [关系分析器] [find_related_reports] 向量搜索完成, 找到 {len(results['ids'][0])} 个结果")
            
            # 处理结果
            related_reports = []
            for i, doc_id in enumerate(results['ids'][0]):
                if i >= max_results:
                    print(f"[DEBUG] [关系分析器] [find_related_reports] 达到最大结果数限制，停止处理")
                    break
                    
                # 获取相似度得分
                distance = results['distances'][0][i] if 'distances' in results and results['distances'] else 0
                
                # 只有距离小于0.6的报告才被认为是相关的
                if distance >= 0.6:
                    print(f"[DEBUG] [关系分析器] [find_related_reports] 距离 {distance} >= 0.6，跳过此结果")
                    continue
                
                # 转换为相似度得分（0-100，越大越相似）
                similarity_score = max(0, min(100, (1 - distance) * 100))
                
                # 获取元数据
                metadata = results['metadatas'][0][i] if 'metadatas' in results and results['metadatas'] else {}
                
                related_reports.append({
                    "related_report_id": doc_id,
                    "similarity_score": round(similarity_score, 2),
                    "distance": distance  # 添加距离信息便于调试
                })
            
            # 按相似度排序
            related_reports.sort(key=lambda x: x['similarity_score'], reverse=True)
            
            print(f"[INFO] [关系分析器] [find_related_reports] 成功找到 {len(related_reports)} 个关联报告")
            return related_reports
            
        except Exception as e:
            print(f"[ERROR] [关系分析器] [find_related_reports] 查找关联报告失败: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _build_relationship_analysis_prompt(self, new_report: Dict[str, Any], 
                                          historical_reports: List[Dict[str, Any]]) -> str:
        """
        构建关联性分析Prompt
        
        Args:
            new_report: 新报告数据
            historical_reports: 历史报告列表
            
        Returns:
            str: Prompt文本
        """
        print(f"[DEBUG] [关系分析器] [_build_relationship_analysis_prompt] 开始构建关联性分析Prompt, 新报告ID={new_report.get('report_id', 'N/A')}, 历史报告数量={len(historical_reports)}")
        
        # 准备新报告JSON
        new_report_json = new_report.get('analysis_json', {})
        if isinstance(new_report_json, str):
            try:
                print(f"[DEBUG] [关系分析器] [_build_relationship_analysis_prompt] 解析新报告JSON")
                new_report_json = json.loads(new_report_json)
            except json.JSONDecodeError:
                print(f"[WARNING] [关系分析器] [_build_relationship_analysis_prompt] 新报告JSON解析失败，使用空字典")
                new_report_json = {}
        
        # 准备历史报告摘要
        historical_summaries = []
        print(f"[DEBUG] [关系分析器] [_build_relationship_analysis_prompt] 开始处理 {len(historical_reports)} 个历史报告")
        for i, report in enumerate(historical_reports):
            print(f"[DEBUG] [关系分析器] [_build_relationship_analysis_prompt] 处理历史报告 {i+1}/{len(historical_reports)}, ID={report['report_id']}")
            report_json = report.get('analysis_json', {})
            if isinstance(report_json, str):
                try:
                    report_json = json.loads(report_json)
                except json.JSONDecodeError:
                    report_json = {}
                    
            summary = {
                "report_id": report['report_id'],
                "title": report['title'],
                "category": report.get('category', ''),
                "date_published": report.get('date_published', ''),
                "summary_one_sentence": report.get('summary_one_sentence', ''),
                "action": report.get('action', ''),
                "sentiment": report.get('sentiment', ''),
                "importance_score": report.get('importance_score', 0),
                "key_entities": report.get('key_entities', []),
                "investment_targets": report_json.get('investment_targets', {}),
                "key_drivers": report_json.get('summary', {}).get('key_drivers', []),
                "core_views": report_json.get('text_summary', {}).get('core_views', [])[:3],
                "risk_warnings": report_json.get('risk_warnings', [])[:3],
                "key_data_sample": dict(list(report_json.get('key_data', {}).items())[:5]) if report_json.get('key_data') else {}
            }
            historical_summaries.append(summary)
        
        print(f"[DEBUG] [关系分析器] [_build_relationship_analysis_prompt] 历史报告摘要构建完成")
        
        prompt = f"""
你是一个金融投资研报分析专家。你的任务是分析一份"新报告"与"历史报告列表"之间的逻辑关联。

请基于以下维度分析新报告与历史报告的关联性，并输出分析结果：

1. **延续性验证**：新报告的实际数据是否验证或推翻了历史报告的预测？
2. **观点演进**：核心观点发生了什么变化？
3. **标的追踪**：对共同提及的投资标的，策略有何调整？

---
【新报告数据】：
{json.dumps(new_report_json, ensure_ascii=False, indent=2)}

---
【历史参考报告列表】：
{json.dumps(historical_summaries, ensure_ascii=False, indent=2)}

---
请以 JSON 格式输出结果，格式如下：
{{
  "relations": [
    {{
      "target_report_id": "历史报告ID",
      "relation_type": "验证 | 反转 | 补充 | 冲突",
      "summary": "简述关联内容",
      "evidence": "引用具体的字段值对比",
      "score": 0.9
    }}
  ]
}}
"""
        
        print(f"[DEBUG] [关系分析器] [_build_relationship_analysis_prompt] Prompt构建完成, 长度={len(prompt)}")
        return prompt
    
    async def analyze_report_relationships(self, new_report_id: str, max_candidates: int = 5) -> Dict[str, Any]:
        """
        分析报告间的关联关系
        
        Args:
            new_report_id: 新报告ID
            max_candidates: 最大候选报告数
            
        Returns:
            Dict: 关联分析结果
        """
        print(f"[INFO] [关系分析器] [analyze_report_relationships] 开始分析报告 {new_report_id} 的关联关系, max_candidates={max_candidates}")
        
        # 1. 查找候选关联报告
        print(f"[DEBUG] [关系分析器] [analyze_report_relationships] 步骤1: 查找候选关联报告")
        candidate_results = await self.find_related_reports(new_report_id, max_candidates)
        if not candidate_results:
            print(f"[DEBUG] [关系分析器] [analyze_report_relationships] 未找到候选关联报告")
            return {"relations": []}
        else:
            print(f"[DEBUG] [关系分析器] [analyze_report_relationships] 找到 {len(candidate_results)} 个候选关联报告")
        
        # 2. 获取新报告完整数据
        print(f"[DEBUG] [关系分析器] [analyze_report_relationships] 步骤2: 获取新报告完整数据")
        new_report = await self.db.get_report(new_report_id)
        if not new_report:
            print(f"[ERROR] [关系分析器] [analyze_report_relationships] 无法获取新报告 {new_report_id}")
            return {"relations": []}
        print(f"[DEBUG] [关系分析器] [analyze_report_relationships] 成功获取新报告数据")
        
        # 3. 获取历史报告数据列表
        print(f"[DEBUG] [关系分析器] [analyze_report_relationships] 步骤3: 获取历史报告数据列表")
        historical_reports = []
        for i, relation in enumerate(candidate_results):
            print(f"[DEBUG] [关系分析器] [analyze_report_relationships] 获取历史报告 {relation['related_report_id']}, 进度 {i+1}/{len(candidate_results)}")
            report_data = await self.db.get_report(relation['related_report_id'])
            if report_data:
                print(f"[DEBUG] [关系分析器] [analyze_report_relationships] 成功获取历史报告 {relation['related_report_id']}, title='{report_data.get('title', 'N/A')}'")
                historical_reports.append(report_data)
            else:
                print(f"[WARNING] [关系分析器] [analyze_report_relationships] 无法获取历史报告 {relation['related_report_id']}")
        
        if not historical_reports:
            print(f"[WARNING] [关系分析器] [analyze_report_relationships] 未获取到任何历史报告数据")
            return {"relations": []}
        else:
            print(f"[DEBUG] [关系分析器] [analyze_report_relationships] 成功获取 {len(historical_reports)} 个历史报告数据")
        
        # 4. 构建分析Prompt
        print(f"[DEBUG] [关系分析器] [analyze_report_relationships] 步骤4: 构建分析Prompt")
        prompt = self._build_relationship_analysis_prompt(new_report, historical_reports)
        print(f"[DEBUG] [关系分析器] [analyze_report_relationships] Prompt构建完成, 长度={len(prompt)}")
        
        # 5. 调用LLM进行深度分析
        print(f"[DEBUG] [关系分析器] [analyze_report_relationships] 步骤5: 调用LLM进行深度分析")
        try:
            # 初始化AI客户端
            import sys
            import os
            sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
            from ccsdk.ai_client import AIClient
            
            # 创建AI客户端实例
            print(f"[DEBUG] [关系分析器] [analyze_report_relationships] 初始化AI客户端")
            ai_client = AIClient()
            
            # 执行LLM查询
            print(f"[DEBUG] [关系分析器] [analyze_report_relationships] 执行LLM查询")
            result = await ai_client.query_single(prompt)
            print(f"[DEBUG] [关系分析器] [analyze_report_relationships] LLM查询完成, 共收到 {len(result['messages'])} 条消息")
            
            # 提取AI响应内容
            assistant_message = None
            for msg in result['messages']:
                if hasattr(msg, 'type') and msg.type == 'assistant':
                    assistant_message = msg
                    break
            
            if assistant_message and hasattr(assistant_message, 'content'):
                # 处理响应内容
                content = assistant_message.content
                
                # 如果content是列表，尝试找到JSON部分
                if isinstance(content, list):
                    text_content = ""
                    for block in content:
                        if isinstance(block, dict) and block.get('type') == 'text':
                            text_content += block.get('text', '')
                        elif isinstance(block, str):
                            text_content += block
                    content = text_content
                elif not isinstance(content, str):
                    content = str(content)
                
                # 从响应中提取JSON部分
                import re
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    json_str = json_match.group()
                    try:
                        llm_result = json.loads(json_str)
                        
                        # 提取relations部分
                        relations = llm_result.get('relations', [])
                        
                        print(f"[INFO] [关系分析器] [analyze_report_relationships] LLM分析完成，找到 {len(relations)} 个关联关系")
                    except json.JSONDecodeError as e:
                        print(f"[ERROR] [关系分析器] [analyze_report_relationships] 解析LLM返回的JSON失败: {e}")
                        print(f"[DEBUG] [关系分析器] [analyze_report_relationships] LLM返回内容: {json_str[:500]}...")
                        # 如果解析失败，使用基于相似度的模拟结果
                        relations = self._generate_fallback_relations(candidate_results, historical_reports)
                else:
                    print(f"[WARNING] [关系分析器] [analyze_report_relationships] 未在LLM响应中找到JSON格式结果")
                    # 如果没有找到JSON，使用基于相似度的模拟结果
                    relations = self._generate_fallback_relations(candidate_results, historical_reports)
            else:
                print(f"[WARNING] [关系分析器] [analyze_report_relationships] LLM未返回有效内容，使用模拟结果")
                # 如果没有有效响应，使用基于相似度的模拟结果
                relations = self._generate_fallback_relations(candidate_results, historical_reports)
        
        except Exception as e:
            print(f"[ERROR] [关系分析器] [analyze_report_relationships] LLM调用失败: {e}")
            import traceback
            traceback.print_exc()
            
            # 如果LLM调用失败，使用基于相似度的模拟结果
            relations = self._generate_fallback_relations(candidate_results, historical_reports)
        
        result = {"relations": relations}
        
        # 6. 存储分析结果到数据库
        print(f"[DEBUG] [关系分析器] [analyze_report_relationships] 步骤6: 存储分析结果到数据库")
        await self._store_relationship_analysis(new_report_id, result)
        
        print(f"[INFO] [关系分析器] [analyze_report_relationships] 关联分析完成，找到 {len(relations)} 个关联关系")
        return result
    
    async def _store_relationship_analysis(self, source_report_id: str, analysis_result: Dict[str, Any]) -> None:
        """
        存储关联分析结果到数据库
        
        Args:
            source_report_id: 源报告ID
            analysis_result: 分析结果
        """
        print(f"[DEBUG] [关系分析器] [_store_relationship_analysis] 开始存储关联分析结果, source_report_id={source_report_id}, relations_count={len(analysis_result.get('relations', []))}")
        
        try:
            # 存储每个关联关系
            insert_sql = """
            INSERT OR REPLACE INTO report_relationships 
            (source_report_id, target_report_id, relation_type, similarity_score, summary, evidence, analysis_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            
            # 执行数据库操作
            relations = analysis_result.get('relations', [])
            print(f"[DEBUG] [关系分析器] [_store_relationship_analysis] 准备存储 {len(relations)} 个关联关系")
            
            for i, relation in enumerate(relations):
                print(f"[DEBUG] [关系分析器] [_store_relationship_analysis] 存储关联关系 {i+1}/{len(relations)}, target_report_id={relation['target_report_id']}")
                await self.db.execute_raw_command(insert_sql, (
                    source_report_id,
                    relation['target_report_id'],
                    relation['relation_type'],
                    relation['score'],
                    relation['summary'],
                    relation['evidence'],
                    json.dumps(relation, ensure_ascii=False)
                ))
                print(f"[DEBUG] [关系分析器] [_store_relationship_analysis] 成功存储关联关系 {i+1}/{len(relations)}")
            
            print(f"[INFO] [关系分析器] [_store_relationship_analysis] 已成功存储 {len(analysis_result.get('relations', []))} 个关联关系")
            
        except Exception as e:
            print(f"[ERROR] [关系分析器] [_store_relationship_analysis] 存储关联分析结果失败: {e}")
            import traceback
            traceback.print_exc()
    
    async def get_report_relationships(self, source_report_id: str) -> List[Dict[str, Any]]:
        """
        获取指定报告的关联关系
        
        Args:
            source_report_id: 源报告ID
            
        Returns:
            List[Dict]: 关联关系列表
        """
        print(f"[DEBUG] [关系分析器] [get_report_relationships] 获取报告 {source_report_id} 的关联关系")
        try:
            relationships = await self.db.get_report_relationships(source_report_id)
            print(f"[INFO] [关系分析器] [get_report_relationships] 找到 {len(relationships)} 个关联关系")
            return relationships
        except Exception as e:
            print(f"[ERROR] [关系分析器] [get_report_relationships] 获取关联关系失败: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    async def get_reverse_report_relationships(self, target_report_id: str) -> List[Dict[str, Any]]:
        """
        获取指定报告被其他报告关联的关系（反向关联）
        
        Args:
            target_report_id: 目标报告ID
            
        Returns:
            List[Dict]: 关联关系列表
        """
        print(f"[DEBUG] [关系分析器] [get_reverse_report_relationships] 获取被报告 {target_report_id} 关联的报告")
        try:
            relationships = await self.db.get_reverse_report_relationships(target_report_id)
            print(f"[INFO] [关系分析器] [get_reverse_report_relationships] 找到 {len(relationships)} 个反向关联关系")
            return relationships
        except Exception as e:
            print(f"[ERROR] [关系分析器] [get_reverse_report_relationships] 获取反向关联关系失败: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _generate_fallback_relations(self, candidate_results: List[Dict[str, Any]], historical_reports: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        生成备用关联关系（当LLM调用失败时使用）
        
        Args:
            candidate_results: 候选关联报告列表
            historical_reports: 历史报告列表
            
        Returns:
            List[Dict]: 关联关系列表
        """
        print(f"[DEBUG] [关系分析器] [_generate_fallback_relations] 生成备用关联关系, candidate_results={len(candidate_results)}, historical_reports={len(historical_reports)}")
        
        relations = []
        for i, relation in enumerate(candidate_results):
            print(f"[DEBUG] [关系分析器] [_generate_fallback_relations] 处理候选关联 {i+1}/{len(candidate_results)}, related_report_id={relation['related_report_id']}")
            # 基于相似度得分生成关联类型，使用新的阈值标准（距离<0.6对应相似度>40%）
            score = relation['similarity_score']
            distance = relation.get('distance', 1.0 - score/100.0)  # 计算距离值
            
            # 将距离转换为百分比相似度进行判断
            percentage_similarity = (1 - distance) * 100
            
            if percentage_similarity >= 60:  # 对应距离 <= 0.4
                relation_type = "验证"
                print(f"[DEBUG] [关系分析器] [_generate_fallback_relations] 相似度 {percentage_similarity:.1f}% -> 验证")
            elif percentage_similarity >= 50:  # 对应距离 <= 0.5
                relation_type = "补充"
                print(f"[DEBUG] [关系分析器] [_generate_fallback_relations] 相似度 {percentage_similarity:.1f}% -> 补充")
            elif percentage_similarity >= 40:  # 对应距离 <= 0.6
                relation_type = "冲突"
                print(f"[DEBUG] [关系分析器] [_generate_fallback_relations] 相似度 {percentage_similarity:.1f}% -> 冲突")
            else:
                relation_type = "相关"
                print(f"[DEBUG] [关系分析器] [_generate_fallback_relations] 相似度 {percentage_similarity:.1f}% -> 相关")
            
            # 从历史报告中获取标题和分类信息
            target_report = next((hr for hr in historical_reports if hr['report_id'] == relation['related_report_id']), None)
            target_title = target_report['title'] if target_report else "未知报告"
            target_category = target_report.get('category', '') if target_report else ""
            target_action = target_report.get('action', '') if target_report else ""
            
            relation_data = {
                "target_report_id": relation['related_report_id'],
                "relation_type": relation_type,
                "summary": f"与'{target_title}'在{target_category}领域具有{percentage_similarity:.1f}%的相似度",
                "evidence": f"共同关注{target_category}，投资建议均为{target_action}",
                "score": percentage_similarity / 100.0
            }
            relations.append(relation_data)
            print(f"[DEBUG] [关系分析器] [_generate_fallback_relations] 添加关联关系: {relation_data['relation_type']}, score={relation_data['score']}")
        
        print(f"[INFO] [关系分析器] [_generate_fallback_relations] 备用关联关系生成完成, 共生成 {len(relations)} 个关联")
        return relations


# 便捷函数
def get_relationship_analyzer(db_path: str = "data/finance.db") -> ReportRelationshipAnalyzer:
    """
    获取关联分析器实例
    
    Args:
        db_path: 数据库路径
        
    Returns:
        ReportRelationshipAnalyzer: 关联分析器实例
    """
    db_manager = DatabaseManager(db_path)
    analyzer = ReportRelationshipAnalyzer(db_manager)
    return analyzer


async def get_relationship_analyzer_async(db_path: str = "data/finance.db") -> ReportRelationshipAnalyzer:
    """
    异步获取关联分析器实例并等待初始化完成
    
    Args:
        db_path: 数据库路径
        
    Returns:
        ReportRelationshipAnalyzer: 关联分析器实例
    """
    db_manager = DatabaseManager(db_path)
    analyzer = ReportRelationshipAnalyzer(db_manager)
    # 等待表初始化完成
    import asyncio
    await asyncio.sleep(0.1)  # 给异步初始化一些时间
    return analyzer