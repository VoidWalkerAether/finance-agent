"""
Finance Agent 数据库管理器

基于 Email Agent 的 database-manager.ts 复刻
参考文件: email-agent/database/database-manager.ts

功能:
- 初始化数据库 (执行 schema.sql)
- 报告的 CRUD 操作 (upsert_report, search_reports)
- UI State 管理 (get_ui_state, set_ui_state)
- Component Instance 管理
- FTS5 全文搜索
"""

import aiosqlite
import sqlite3
import json
import os
import chromadb
from chromadb.utils import embedding_functions
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
from datetime import datetime

# 导入 Repository 层
from .repositories import WatchlistRepository, PortfolioRepository


class DatabaseManager:
    """Finance Agent 数据库管理器 (异步)"""
    
    _instance = None  # 单例模式
    
    def __new__(cls, db_path: str = "data/finance.db"):
        """单例模式: 确保只有一个数据库连接实例"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, db_path: str = "data/finance.db"):
        """
        初始化数据库管理器
        
        Args:
            db_path: 数据库文件路径
        """
        if self._initialized:
            return
        
        self.db_path = db_path
        
        # 确保目录存在
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # 同步初始化数据库结构
        self._initialize_sync()
        
        # 初始化 Repository 层
        self._watchlist_repo = WatchlistRepository(db_path)
        self._portfolio_repo = PortfolioRepository(db_path)
        
        # 新增：ChromaDB 初始化（受环境变量控制）
        use_chromadb = os.getenv('USE_CHROMADB', 'false').lower() == 'true'
        print(f"[DEBUG] USE_CHROMADB 环境变量: {use_chromadb}")
        if use_chromadb:
            self._init_chromadb()
        
        self._initialized = True
    
    def _initialize_sync(self):
        """
        同步初始化数据库 (PRAGMA + schema.sql)
        
        对应 TypeScript: database-manager.ts 第 73-79 行
        """
        conn = sqlite3.connect(self.db_path)
        
        try:
            # 启用 WAL 模式 (提高并发性能)
            conn.execute("PRAGMA journal_mode = WAL")
            
            # 启用外键约束
            conn.execute("PRAGMA foreign_keys = ON")
            
            # 执行 schema.sql
            schema_path = Path(__file__).parent / 'schema.sql'
            if schema_path.exists():
                with open(schema_path, 'r', encoding='utf-8') as f:
                    conn.executescript(f.read())
                print(f"✅ 数据库初始化成功: {self.db_path}")
            else:
                print(f"⚠️ schema.sql 未找到: {schema_path}")
        
        finally:
            conn.close()
    
    def _init_chromadb(self):
        """初始化 ChromaDB 客户端"""
        try:
            # 初始化 ChromaDB 客户端
            chroma_db_path = os.getenv('CHROMA_DB_PATH', './chroma_db')
            print(f"[DEBUG] ChromaDB 路径: {chroma_db_path}")
            self.chroma_client = chromadb.PersistentClient(path=chroma_db_path)
            print("[DEBUG] ChromaDB 客户端创建成功")
            
            # 尝试使用 SentenceTransformer 嵌入函数
            try:
                embedding_model = os.getenv('EMBEDDING_MODEL', 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
                print(f"[DEBUG] 嵌入模型: {embedding_model}")
                self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
                    model_name=embedding_model
                )
                print("[DEBUG] SentenceTransformer 嵌入函数创建成功")
            except Exception as embed_error:
                print(f"⚠️  SentenceTransformer 嵌入函数不可用: {embed_error}")
                # 使用默认嵌入函数
                self.embedding_function = None
            
            # 获取或创建集合
            # 使用更安全的方法处理集合创建以避免嵌入函数冲突
            collection_name = "reports"
            
            # 首先尝试获取现有集合，如果获取失败（说明不存在），则创建新集合
            collection_args = {"name": collection_name}
            if self.embedding_function:
                collection_args["embedding_function"] = self.embedding_function
            
            try:
                # 尝试获取现有集合
                self.reports_collection = self.chroma_client.get_collection(
                    name=collection_name,
                    embedding_function=self.embedding_function
                )
                print(f"[DEBUG] 成功获取已存在的集合 {collection_name}")
            except:
                # 如果获取失败（集合不存在或配置不匹配），则创建新集合
                print(f"[DEBUG] 集合 {collection_name} 不存在或配置不匹配，创建新集合")
                self.reports_collection = self.chroma_client.create_collection(**collection_args)
            
            print("✅ ChromaDB 初始化成功")
        except Exception as e:
            print(f"❌ ChromaDB 初始化失败: {e}")
            import traceback
            traceback.print_exc()
            self.chroma_client = None
    
    # ============================================================================
    # 报告管理 (Reports CRUD)
    # ============================================================================
    
    async def upsert_report(self, report_data: Dict[str, Any]) -> int:
        """
        插入或更新报告
        
        对应 TypeScript: database-manager.ts 第 260-392 行 (upsertEmail)
        
        Args:
            report_data: {
                'report_id': 'analysis_...',
                'title': 'A股4000点...',
                'content': '3000+ 字原文',
                'analysis_json': {...},  # dict 将自动序列化
                'sources': [...],        # list 将自动序列化
                'key_drivers': [...],
                ...
            }
        
        Returns:
            int: 报告的自增 ID
        """
        # JSON 字段序列化
        json_fields = ['analysis_json', 'sources', 'key_drivers']
        for key in json_fields:
            if key in report_data and isinstance(report_data[key], (dict, list)):
                report_data[key] = json.dumps(report_data[key], ensure_ascii=False)
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO reports (
                    report_id, title, report_type, category, date_published, sources,
                    content, summary_one_sentence, sentiment, key_drivers,
                    importance_score, urgency_score, reliability_score,
                    action, target_allocation, timing, holding_period, confidence_level,
                    analysis_json, original_file_path, file_size
                ) VALUES (
                    :report_id, :title, :report_type, :category, :date_published, :sources,
                    :content, :summary_one_sentence, :sentiment, :key_drivers,
                    :importance_score, :urgency_score, :reliability_score,
                    :action, :target_allocation, :timing, :holding_period, :confidence_level,
                    :analysis_json, :original_file_path, :file_size
                )
                ON CONFLICT(report_id) DO UPDATE SET
                    title = excluded.title,
                    report_type = excluded.report_type,
                    category = excluded.category,
                    content = excluded.content,
                    summary_one_sentence = excluded.summary_one_sentence,
                    sentiment = excluded.sentiment,
                    key_drivers = excluded.key_drivers,
                    importance_score = excluded.importance_score,
                    urgency_score = excluded.urgency_score,
                    reliability_score = excluded.reliability_score,
                    action = excluded.action,
                    target_allocation = excluded.target_allocation,
                    timing = excluded.timing,
                    holding_period = excluded.holding_period,
                    confidence_level = excluded.confidence_level,
                    analysis_json = excluded.analysis_json,
                    updated_at = CURRENT_TIMESTAMP
            """, report_data)
            
            await db.commit()
            
            # 新增：如果启用了 ChromaDB，同时保存到向量数据库
            print(f"[DEBUG] 检查 ChromaDB 是否可用: hasattr={hasattr(self, 'chroma_client')}, chroma_client={getattr(self, 'chroma_client', 'NOT_SET')}")
            if hasattr(self, 'chroma_client') and self.chroma_client:
                try:
                    print(f"[DEBUG] 正在保存到 ChromaDB: {report_data.get('report_id')}")
                    await self._save_to_chromadb(report_data)
                    print(f"[DEBUG] 成功保存到 ChromaDB: {report_data.get('report_id')}")
                except Exception as e:
                    print(f"⚠️  保存到 ChromaDB 失败: {e}")
                    import traceback
                    traceback.print_exc()
            
            return cursor.lastrowid
    
    async def _save_to_chromadb(self, report_data):
        """保存报告到 ChromaDB"""
        print(f"[DEBUG] [数据库管理器] [_save_to_chromadb] 开始保存报告到ChromaDB, report_id={report_data['report_id']}, title='{report_data.get('title', 'N/A')}'")
        
        # 构建用于向量搜索的合成语义文本
        from .relationship_analyzer import ReportRelationshipAnalyzer
        analyzer = ReportRelationshipAnalyzer(self)
        embedding_text = analyzer._prepare_embedding_text(report_data)
        print(f"[DEBUG] [数据库管理器] [_save_to_chromadb] 合成语义文本长度: {len(embedding_text)}")
        
        # 使用合成语义文本作为文档内容，以便更好地进行语义搜索
        documents = [embedding_text]
        print(f"[DEBUG] [数据库管理器] [_save_to_chromadb] 文档内容长度: {len(documents[0]) if documents[0] else 0}")
        
        metadatas = [{
            "report_id": report_data['report_id'],
            "title": report_data['title'],
            "category": report_data.get('category', ''),
            "action": report_data.get('action', ''),
            "importance_score": report_data.get('importance_score', 0),
            "summary_one_sentence": report_data.get('summary_one_sentence', ''),
            "sentiment": report_data.get('sentiment', ''),
            "date_published": report_data.get('date_published', ''),
            "original_content_length": len(report_data.get('content', ''))  # 记录原始内容长度
        }]
        ids = [report_data['report_id']]
        
        print(f"[DEBUG] [数据库管理器] [_save_to_chromadb] 准备执行upsert操作")
    
        self.reports_collection.upsert(
            documents=documents,  # 使用合成语义文本
            metadatas=metadatas,
            ids=ids
        )
        
        print(f"[INFO] [数据库管理器] [_save_to_chromadb] 成功保存报告到ChromaDB, report_id={report_data['report_id']}")
    
    async def get_report(self, report_id: str) -> Optional[Dict[str, Any]]:
        """
        根据 report_id 获取报告
        
        Args:
            report_id: 报告唯一标识
        
        Returns:
            Dict: 报告数据 (JSON 字段已反序列化)
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM reports WHERE report_id = ?",
                (report_id,)
            )
            row = await cursor.fetchone()
            
            if row:
                report = dict(row)
                # 反序列化 JSON 字段
                for key in ['analysis_json', 'sources', 'key_drivers']:
                    if report.get(key):
                        try:
                            report[key] = json.loads(report[key])
                        except json.JSONDecodeError:
                            pass
                return report
            
            return None
    
    async def search_reports(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        action: Optional[str] = None,
        min_importance: Optional[int] = None,
        date_range: Optional[Tuple[str, str]] = None,
        limit: int = 30,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        搜索报告 (支持全文搜索 + 多条件筛选)
        
        对应 TypeScript: database-manager.ts 第 396-500 行 (searchEmails)
        
        Args:
            query: FTS5 全文搜索关键词 (如 "黄金 A股")
            category: 分类筛选
            action: 投资建议筛选 ('buy', 'sell', 'hold', 'watch')
            min_importance: 最小重要性评分
            date_range: 日期范围 (start_date, end_date)
            limit: 返回数量
            offset: 偏移量
        
        Returns:
            List[Dict]: 报告列表 (JSON 字段已反序列化)
        """
        where_clauses = []
        params = {}
        
        # FTS5 全文搜索 - 处理中文搜索问题
        if query:
            # 对于中文搜索，使用通配符来提高匹配率
            # 根据经验教训，SQLite FTS5的unicode61分词器对纯中文支持有限
            fts_query = query
            # 如果查询包含中文字符，添加通配符
            if any('\u4e00' <= char <= '\u9fff' for char in query):
                # 将查询词用通配符包装
                words = query.split()
                fts_words = [f"{word}*" if any('\u4e00' <= char <= '\u9fff' for char in word) else word for word in words]
                # 对于多词查询，使用AND连接以提高准确性
                if len(fts_words) > 1:
                    fts_query = " OR ".join(fts_words)
                else:
                    fts_query = fts_words[0]
            
            where_clauses.append("""
                r.report_id IN (
                    SELECT report_id FROM reports_fts
                    WHERE reports_fts MATCH :query
                )
            """)
            params['query'] = fts_query
        
        # 分类筛选
        if category:
            where_clauses.append('r.category = :category')
            params['category'] = category
        
        # 投资建议筛选
        if action:
            where_clauses.append('r.action = :action')
            params['action'] = action
        
        # 重要性评分
        if min_importance is not None:
            where_clauses.append('r.importance_score >= :min_importance')
            params['min_importance'] = min_importance
        
        # 日期范围
        if date_range:
            where_clauses.append('r.date_published BETWEEN :start_date AND :end_date')
            params['start_date'] = date_range[0]
            params['end_date'] = date_range[1]
        
        where_clause = ' AND '.join(where_clauses) if where_clauses else '1=1'
        query_sql = f"""
            SELECT * FROM reports r
            WHERE {where_clause}
            ORDER BY r.date_published DESC, r.importance_score DESC
            LIMIT :limit OFFSET :offset
        """
        params['limit'] = limit
        params['offset'] = offset
        
        # 添加调试信息
        print(f"[DEBUG] 执行查询: {query_sql}")
        print(f"[DEBUG] 查询参数: {params}")
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(query_sql, params)
            rows = await cursor.fetchall()
            
            # 添加调试信息
            print(f"[DEBUG] 查询返回 {len(rows)} 条记录")
            
            results = []
            for row in rows:
                report = dict(row)
                # 反序列化 JSON 字段
                for key in ['analysis_json', 'sources', 'key_drivers']:
                    if report.get(key):
                        try:
                            report[key] = json.loads(report[key])
                        except json.JSONDecodeError:
                            pass
                results.append(report)
            
            return results
    
    async def smart_search_reports(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        action: Optional[str] = None,
        min_importance: Optional[int] = None,
        limit: int = 30,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        智能搜索报告：根据环境变量决定使用哪种搜索方式
        """
        # 检查是否启用 ChromaDB
        if hasattr(self, 'chroma_client') and self.chroma_client and os.getenv('USE_CHROMADB', 'false').lower() == 'true':
            return await self._chroma_search_reports(query, category, action, min_importance, limit, offset)
        else:
            # 回退到原有的 FTS5 搜索
            return await self.search_reports(query, category, action, min_importance, limit, offset)
    
    async def _chroma_search_reports(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        action: Optional[str] = None,
        min_importance: Optional[int] = None,
        limit: int = 30,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        使用 ChromaDB 进行向量搜索
        """
        # 1. 如果只有语义搜索（无结构化筛选条件）
        if query and not (category or action or min_importance):
            # 不需要构建where条件，因为没有结构化筛选条件
            print(f"[DEBUG] [数据库管理器] [_chroma_search_reports] 执行纯向量搜索, query={query}, limit={limit}")
            
            # 确保查询文本不为空
            if not query.strip():
                print("[DEBUG] 查询文本为空，返回空结果")
                return []
                
            # 获取比请求更多的结果，以便过滤距离
            results = self.reports_collection.query(
                query_texts=[query],
                n_results=limit * 3  # 获取更多结果以允许过滤
            )
            
            # 检查是否返回了结果
            if not results['ids'] or len(results['ids'][0]) == 0:
                print("[DEBUG] 未找到任何匹配结果")
                return []
            
            # 从返回的 metadata 中构建报告信息，只包括距离小于0.5的结果
            reports = []
            for i, doc_id in enumerate(results['ids'][0]):
                # 检查距离，只包括距离小于0.5的结果
                if 'distances' in results and len(results['distances'][0]) > i:
                    distance = results['distances'][0][i]
                    if distance >= 0.5:  # 跳过距离大于等于0.5的结果
                        continue
                
                if len(reports) >= limit:  # 确保不超过请求的限制
                    break
                    
                metadata = results['metadatas'][0][i]
                reports.append({
                    'report_id': metadata['report_id'],
                    'title': metadata['title'],
                    'category': metadata['category'],
                    'importance_score': metadata['importance_score'],
                    'action': metadata['action'],
                    'summary_one_sentence': metadata.get('summary_one_sentence', ''),
                    'sentiment': metadata.get('sentiment', ''),
                    'date_published': metadata.get('date_published', ''),
                    'content': results['documents'][0][i] if results['documents'] and len(results['documents']) > 0 and i < len(results['documents'][0]) else '',
                    'similarity_distance': results['distances'][0][i] if 'distances' in results and i < len(results['distances'][0]) else None
                })
            
            print(f"[DEBUG] [数据库管理器] [_chroma_search_reports] 过滤后返回 {len(reports)} 个高相似度结果")
            return reports
        
        # 2. 如果有结构化筛选条件，需要混合搜索
        else:
            # 先用 ChromaDB 做语义搜索，加入where条件
            where_conditions = {}
            if category:
                where_conditions["category"] = category
            if action:
                where_conditions["action"] = action
            if min_importance is not None:
                where_conditions["importance_score"] = {"$gte": min_importance}
            print(f"[DEBUG] [混合搜索] [_chroma_search_reports] 执行向量搜索, query={query}, where_conditions={where_conditions}, limit={limit}")
            if query:
                # 获取更多结果用于距离过滤
                chroma_results = self.reports_collection.query(
                    query_texts=[query],
                    where=where_conditions if where_conditions else None,
                    n_results=limit * 3  # 获取更多结果以允许距离过滤
                )
                
                # 过滤距离大于等于0.5的结果
                filtered_candidate_ids = []
                if 'distances' in chroma_results:
                    for i, doc_id in enumerate(chroma_results['ids'][0]):
                        if i < len(chroma_results['distances'][0]):
                            distance = chroma_results['distances'][0][i]
                            if distance < 0.5:  # 只保留距离小于0.5的结果
                                filtered_candidate_ids.append(doc_id)
                else:
                    # 如果没有距离信息，使用原始结果
                    filtered_candidate_ids = chroma_results['ids'][0]
                
                candidate_ids = filtered_candidate_ids[:limit]  # 限制返回数量
            else:
                # 如果没有语义搜索，获取所有候选文档
                all_docs = self.reports_collection.get(where=where_conditions if where_conditions else None)
                candidate_ids = all_docs['ids']
            
            # 再用 SQLite 进行结构化筛选
            where_clauses = []
            params = []
            
            if candidate_ids:
                placeholders = ','.join(['?' for _ in candidate_ids])
                where_clauses.append(f"report_id IN ({placeholders})")
                params.extend(candidate_ids)
            
            if category:
                where_clauses.append("category = ?")
                params.append(category)
                
            if action:
                where_clauses.append("action = ?")
                params.append(action)
                
            if min_importance is not None:
                where_clauses.append("importance_score >= ?")
                params.append(min_importance)
            
            where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"
            
            sql = f"""
                SELECT * FROM reports 
                WHERE {where_clause}
                ORDER BY date_published DESC, importance_score DESC
                LIMIT ? OFFSET ?
            """
            params.append(limit)
            params.append(offset)
            
            # 执行 SQLite 查询
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(sql, params)
                rows = await cursor.fetchall()
                
                results = []
                for row in rows:
                    report = dict(row)
                    # 反序列化 JSON 字段
                    for key in ['analysis_json', 'sources', 'key_drivers']:
                        if report.get(key):
                            try:
                                report[key] = json.loads(report[key])
                            except json.JSONDecodeError:
                                pass
                    results.append(report)
                
                return results
    
    async def list_all_reports(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        列出所有报告（用于调试）
        
        Args:
            limit: 返回数量限制
            
        Returns:
            List[Dict]: 报告列表
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT report_id, title, category, date_published, content, summary_one_sentence
                FROM reports
                ORDER BY date_published DESC
                LIMIT ?
            """, (limit,))
            rows = await cursor.fetchall()
            
            print(f"[DEBUG] 列出所有报告，返回 {len(rows)} 条记录")
            
            results = []
            for row in rows:
                results.append(dict(row))
            
            return results
    
    async def get_high_priority_reports(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取高优先级报告 (importance_score >= 8)
        
        使用视图: high_priority_reports (schema.sql 第 167-179 行)
        
        Args:
            limit: 返回数量
        
        Returns:
            List[Dict]: 高优先级报告列表
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM high_priority_reports LIMIT ?",
                (limit,)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    # ============================================================================
    # UI State 管理
    # ============================================================================
    
    async def get_ui_state(self, state_id: str) -> Optional[Dict[str, Any]]:
        """
        获取 UI 状态
        
        对应 TypeScript: 新增方法 (TypeScript 中未实现,但系统需要)
        
        Args:
            state_id: 状态唯一标识 (如 "report_dashboard")
        
        Returns:
            Dict: 状态数据 (已反序列化)
        """
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT data_json FROM ui_states WHERE state_id = ?",
                (state_id,)
            )
            row = await cursor.fetchone()
            
            if row and row[0]:
                try:
                    return json.loads(row[0])
                except json.JSONDecodeError:
                    return None
            
            return None
    
    async def set_ui_state(self, state_id: str, data: Dict[str, Any]) -> None:
        """
        设置 UI 状态
        
        对应 TypeScript: 新增方法 (TypeScript 中未实现,但系统需要)
        
        Args:
            state_id: 状态唯一标识
            data: 状态数据 (将自动序列化)
        """
        data_json = json.dumps(data, ensure_ascii=False)
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO ui_states (state_id, data_json)
                VALUES (?, ?)
                ON CONFLICT(state_id) DO UPDATE SET
                    data_json = excluded.data_json,
                    updated_at = CURRENT_TIMESTAMP
            """, (state_id, data_json))
            await db.commit()
    
    async def delete_ui_state(self, state_id: str) -> None:
        """删除 UI 状态"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM ui_states WHERE state_id = ?", (state_id,))
            await db.commit()
    
    # ============================================================================
    # Component Instance 管理
    # ============================================================================
    
    async def create_component_instance(
        self,
        instance_id: str,
        component_id: str,
        state_id: str,
        session_id: Optional[str] = None
    ) -> int:
        """
        创建组件实例
        
        Args:
            instance_id: 实例唯一标识 (如 "comp_1732689237000")
            component_id: 组件模板 ID (如 "report_dashboard")
            state_id: 绑定的 UI 状态 ID
            session_id: 所属会话 ID
        
        Returns:
            int: 自增 ID
        """
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO component_instances (instance_id, component_id, state_id, session_id)
                VALUES (?, ?, ?, ?)
            """, (instance_id, component_id, state_id, session_id))
            await db.commit()
            return cursor.lastrowid
    
    async def get_component_instances_by_session(
        self,
        session_id: str
    ) -> List[Dict[str, Any]]:
        """
        根据会话 ID 获取组件实例列表
        
        Args:
            session_id: 会话 ID
        
        Returns:
            List[Dict]: 组件实例列表
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM component_instances WHERE session_id = ? ORDER BY created_at DESC",
                (session_id,)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    # ============================================================================
    # 统计和分析
    # ============================================================================
    
    async def get_report_stats(self) -> Dict[str, Any]:
        """
        获取报告统计信息
        
        Returns:
            Dict: {
                'total_reports': 总报告数,
                'by_category': {分类: 数量},
                'by_action': {投资建议: 数量},
                'avg_importance': 平均重要性评分
            }
        """
        async with aiosqlite.connect(self.db_path) as db:
            # 总报告数
            cursor = await db.execute("SELECT COUNT(*) FROM reports")
            total_reports = (await cursor.fetchone())[0]
            
            # 按分类统计
            cursor = await db.execute("""
                SELECT category, COUNT(*) as count
                FROM reports
                WHERE category IS NOT NULL
                GROUP BY category
                ORDER BY count DESC
            """)
            by_category = {row[0]: row[1] for row in await cursor.fetchall()}
            
            # 按投资建议统计
            cursor = await db.execute("""
                SELECT action, COUNT(*) as count
                FROM reports
                WHERE action IS NOT NULL
                GROUP BY action
                ORDER BY count DESC
            """)
            by_action = {row[0]: row[1] for row in await cursor.fetchall()}
            
            # 平均重要性评分
            cursor = await db.execute("""
                SELECT AVG(importance_score)
                FROM reports
                WHERE importance_score IS NOT NULL
            """)
            avg_importance = (await cursor.fetchone())[0]
            
            return {
                'total_reports': total_reports,
                'by_category': by_category,
                'by_action': by_action,
                'avg_importance': round(avg_importance, 2) if avg_importance else 0
            }
    
    # ============================================================================
    # UI State 管理
    # ============================================================================
    
    def get_ui_state(self, state_id: str) -> Optional[Any]:
        """
        获取 UI 状态 (同步方法，供 UIStateManager 使用)
        
        对应 TypeScript: database-manager.ts getUIState()
        
        Args:
            state_id: 状态唯一标识符
        
        Returns:
            Any: 状态数据 (已反序列化 JSON)
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        try:
            cursor = conn.execute(
                "SELECT data_json FROM ui_states WHERE state_id = ?",
                (state_id,)
            )
            row = cursor.fetchone()
            
            if row:
                try:
                    return json.loads(row['data_json'])
                except json.JSONDecodeError:
                    return None
            
            return None
        finally:
            conn.close()
    
    async def set_ui_state(self, state_id: str, data: Any) -> None:
        """
        设置/更新 UI 状态
        
        对应 TypeScript: database-manager.ts setUIState()
        
        Args:
            state_id: 状态 ID
            data: 状态数据 (将自动序列化为 JSON)
        """
        json_data = json.dumps(data, ensure_ascii=False)
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO ui_states (state_id, data_json)
                VALUES (?, ?)
                ON CONFLICT(state_id) DO UPDATE SET
                    data_json = excluded.data_json,
                    updated_at = CURRENT_TIMESTAMP
            """, (state_id, json_data))
            
            await db.commit()
    
    async def list_ui_states(self) -> List[Dict[str, str]]:
        """
        列出所有 UI 状态
        
        对应 TypeScript: database-manager.ts listUIStates()
        
        Returns:
            List[Dict]: [{'stateId': '...', 'updatedAt': '...'}]
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT state_id as stateId, updated_at as updatedAt
                FROM ui_states
                ORDER BY updated_at DESC
            """)
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    async def delete_ui_state(self, state_id: str) -> None:
        """
        删除 UI 状态
        
        对应 TypeScript: database-manager.ts deleteUIState()
        
        Args:
            state_id: 状态 ID
        """
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "DELETE FROM ui_states WHERE state_id = ?",
                (state_id,)
            )
            await db.commit()
    
    # ============================================================================
    # 工具方法
    # ============================================================================
    
    async def execute_raw_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """
        执行原始 SQL 查询
        
        Args:
            query: SQL 查询语句
            params: 查询参数
        
        Returns:
            List[Dict]: 查询结果
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    async def execute_raw_command(self, query: str, params: tuple = ()) -> int:
        """
        执行原始 SQL 命令 (INSERT/UPDATE/DELETE)
        
        Args:
            query: SQL 命令语句
            params: 命令参数
        
        Returns:
            int: 受影响的行数
        """
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(query, params)
            await db.commit()
            return cursor.rowcount
    
    def close(self):
        """关闭数据库连接 (单例模式下通常不需要显式调用)"""
        # aiosqlite 使用 async with 自动管理连接,无需手动关闭
        pass
    
    # ============================================================================
    # Repository 层访问属性
    # ============================================================================
    
    @property
    def watchlist(self) -> WatchlistRepository:
        """
        获取关注列表 Repository
        
        Returns:
            WatchlistRepository: 关注列表数据访问层
        """
        return self._watchlist_repo
    
    @property
    def portfolio(self) -> PortfolioRepository:
        """
        获取持仓数据 Repository
        
        Returns:
            PortfolioRepository: 持仓数据访问层
        """
        return self._portfolio_repo
    
    # ============================================================================
    # 关注列表管理 (弃用，请使用 db.watchlist.xxx)
    # 保留为兼容性方法，将来会移除
    # ============================================================================
    
    async def add_watchlist_item(self, *args, **kwargs) -> int:
        """弃用: 请使用 db.watchlist.add_item()"""
        return await self._watchlist_repo.add_item(*args, **kwargs)
    
    async def get_watchlist(self, *args, **kwargs) -> List[Dict[str, Any]]:
        """弃用: 请使用 db.watchlist.get_list()"""
        return await self._watchlist_repo.get_list(*args, **kwargs)
    
    async def get_watchlist_item(self, *args, **kwargs) -> Optional[Dict[str, Any]]:
        """弃用: 请使用 db.watchlist.get_item()"""
        return await self._watchlist_repo.get_item(*args, **kwargs)
    
    async def update_watchlist_item(self, *args, **kwargs) -> bool:
        """弃用: 请使用 db.watchlist.update_item()"""
        return await self._watchlist_repo.update_item(*args, **kwargs)
    
    async def remove_watchlist_item(self, *args, **kwargs) -> bool:
        """弃用: 请使用 db.watchlist.remove_item()"""
        return await self._watchlist_repo.remove_item(*args, **kwargs)
    
    async def delete_watchlist_item(self, *args, **kwargs) -> bool:
        """弃用: 请使用 db.watchlist.delete_item()"""
        return await self._watchlist_repo.delete_item(*args, **kwargs)
    
    async def test_fts5_search(self, query: str) -> List[Dict[str, Any]]:
        """
        测试FTS5全文搜索功能
        
        Args:
            query: 搜索关键词
            
        Returns:
            List[Dict]: 搜索结果
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            # 直接查询FTS5表
            cursor = await db.execute("""
                SELECT * FROM reports_fts
                WHERE reports_fts MATCH ?
            """, (query,))
            rows = await cursor.fetchall()
            
            print(f"[DEBUG] FTS5搜索 '{query}' 返回 {len(rows)} 条记录")
            
            results = []
            for row in rows:
                results.append(dict(row))
            
            return results
    
    async def get_report_relationships(self, source_report_id: str) -> List[Dict[str, Any]]:
        """
        获取指定报告的关联关系
        
        Args:
            source_report_id: 源报告ID
            
        Returns:
            List[Dict]: 关联关系列表
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM report_relationships
                WHERE source_report_id = ?
                ORDER BY similarity_score DESC
            """, (source_report_id,))
            rows = await cursor.fetchall()
            
            results = []
            for row in rows:
                result = dict(row)
                # 尝试解析analysis_json字段
                if result.get('analysis_json'):
                    try:
                        result['analysis_json'] = json.loads(result['analysis_json'])
                    except json.JSONDecodeError:
                        pass  # 如果解析失败，保留原始字符串
                results.append(result)
            
            return results
    
    async def get_reverse_report_relationships(self, target_report_id: str) -> List[Dict[str, Any]]:
        """
        获取指定报告被其他报告关联的关系（反向关联）
        
        Args:
            target_report_id: 目标报告ID
            
        Returns:
            List[Dict]: 关联关系列表
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM report_relationships
                WHERE target_report_id = ?
                ORDER BY similarity_score DESC
            """, (target_report_id,))
            rows = await cursor.fetchall()
            
            results = []
            for row in rows:
                result = dict(row)
                # 尝试解析analysis_json字段
                if result.get('analysis_json'):
                    try:
                        result['analysis_json'] = json.loads(result['analysis_json'])
                    except json.JSONDecodeError:
                        pass  # 如果解析失败，保留原始字符串
                results.append(result)
            
            return results
    
    async def delete_report_relationships(self, source_report_id: str = None, target_report_id: str = None) -> int:
        """
        删除报告关联关系
        
        Args:
            source_report_id: 源报告ID（可选）
            target_report_id: 目标报告ID（可选）
            
        Returns:
            int: 删除的记录数
        """
        async with aiosqlite.connect(self.db_path) as db:
            if source_report_id and target_report_id:
                # 删除特定的关联关系
                cursor = await db.execute("""
                    DELETE FROM report_relationships
                    WHERE source_report_id = ? AND target_report_id = ?
                """, (source_report_id, target_report_id))
            elif source_report_id:
                # 删除指定源报告的所有关联关系
                cursor = await db.execute("""
                    DELETE FROM report_relationships
                    WHERE source_report_id = ?
                """, (source_report_id,))
            elif target_report_id:
                # 删除指向指定目标报告的所有关联关系
                cursor = await db.execute("""
                    DELETE FROM report_relationships
                    WHERE target_report_id = ?
                """, (target_report_id,))
            else:
                # 删除所有关联关系
                cursor = await db.execute("""
                    DELETE FROM report_relationships
                """, ())
            
            await db.commit()
            return cursor.rowcount
    
    async def get_all_report_relationships(self) -> List[Dict[str, Any]]:
        """
        获取所有报告关联关系
        
        Returns:
            List[Dict]: 所有关联关系列表
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM report_relationships
                ORDER BY created_at DESC
            """, ())
            rows = await cursor.fetchall()
            
            results = []
            for row in rows:
                result = dict(row)
                # 尝试解析analysis_json字段
                if result.get('analysis_json'):
                    try:
                        result['analysis_json'] = json.loads(result['analysis_json'])
                    except json.JSONDecodeError:
                        pass  # 如果解析失败，保留原始字符串
                results.append(result)
            
            return results


# ============================================================================
# 便捷函数
# ============================================================================

def get_database_manager(db_path: str = "data/finance.db") -> DatabaseManager:
    """
    获取 DatabaseManager 单例实例
    
    Args:
        db_path: 数据库文件路径
    
    Returns:
        DatabaseManager: 数据库管理器实例
    """
    return DatabaseManager(db_path)
