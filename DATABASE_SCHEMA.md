# 数据库结构详解

> **文档目的**:记录 Email Agent 的数据库实现细节,**明确区分系统核心表和业务表**,指导 Finance Agent 复刻。
> **数据来源**:`email-agent/database/database-manager.ts` 和 `email-agent/database/schema.sql`
> **原则**:系统核心表必须保留,业务表根据金融报告数据定制。

---

## 📋 目录

1. [表分类总览](#表分类总览)
2. [系统核心表(所有Agent必需)](#系统核心表所有agent必需)
3. [Email Agent业务表](#email-agent业务表)
4. [Finance Agent业务表设计](#finance-agent业务表设计)
5. [DatabaseManager核心方法](#databasemanager核心方法)
6. [Python复刻要点](#python复刻要点)

---

## 🗂️ 表分类总览

### **分类原则**

```
📦 系统核心表 (所有 Agent 通用)
├── ui_states                  ✅ 必需 - 存储 Listeners/Actions 的 UI 状态
└── component_instances        ✅ 必需 - 跟踪组件实例

📧 Email Agent 业务表
├── emails                     🔵 邮件主表 - 存储邮件内容
├── emails_fts                 🔍 全文搜索 - FTS5 虚拟表
├── attachments                📎 Email专用 - 附件记录
└── (其他可选表)             ⚠️ contacts, threads, search_history

📈 Finance Agent 业务表 (基于实际数据设计)
├── reports                    🔵 报告主表 - 存储金融分析报告
└── reports_fts                🔍 全文搜索 - 中文分词支持
```

### **关键区别**

| 特性 | 系统核心表 | Email 业务表 | Finance 业务表 |
|------|----------|-----------|-------------|
| **是否必需** | ✅ 所有 Agent 必需 | ⚠️ Email 专用 | ⚠️ Finance 专用 |
| **复刻方式** | 完全复制结构 | 参考改造 | 基于实际数据设计 |
| **数据示例** | UI 组件状态 | 邮件文本 | A股黄金报告 |
| **主要字段** | `state_id`, `data_json` | `subject`, `body_text` | `title`, `content`, `analysis_json` |

---

## ✅ 系统核心表(所有Agent必需)

> **重要提示**:这两张表是插件系统的**基础架构**,Finance Agent **必须完全复制**结构和功能。

### **1. ui_states - UI 状态存储**

**TypeScript 实现** (`database-manager.ts` 第 213-221 行):

```typescript
this.db.exec(`
  CREATE TABLE IF NOT EXISTS ui_states (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    state_id TEXT UNIQUE NOT NULL,
    data_json TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
  )
`);
```

**字段说明**:

| 字段 | 类型 | 约束 | 说明 | Finance Agent 示例 |
|------|------|------|------|-----------------|
| `id` | INTEGER | PRIMARY KEY | 自增主键 | 1, 2, 3... |
| `state_id` | TEXT | UNIQUE NOT NULL | 状态标识 | `"financial_dashboard"`, `"report_list"` |
| `data_json` | TEXT | NOT NULL | JSON 序列化数据 | `{"reports":[{"title":"A股黄金报告","score":9}]}` |
| `created_at` | DATETIME | DEFAULT | 创建时间 | `2025-11-27 10:00:00` |
| `updated_at` | DATETIME | DEFAULT | 最后更新时间 | `2025-11-27 15:30:00` |

**索引** (`database-manager.ts` 第 236-237 行):

```typescript
CREATE INDEX IF NOT EXISTS idx_ui_states_state_id ON ui_states(state_id)
CREATE INDEX IF NOT EXISTS idx_ui_states_updated_at ON ui_states(updated_at)
```

**触发器** (`database-manager.ts` 第 249-256 行):

```typescript
CREATE TRIGGER IF NOT EXISTS update_ui_states_timestamp
AFTER UPDATE ON ui_states
FOR EACH ROW
BEGIN
  UPDATE ui_states SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END
```

**Finance Agent 使用场景**:

```json
// state_id: "report_dashboard"
{
  "high_priority_reports": [
    {
      "report_id": "analysis_A股与黄金综合策略_20251127_105237",
      "title": "A股4000点拉锯与黄金见顶辨析",
      "importance_score": 9,
      "action": "watch",
      "date_published": "2025-11"
    }
  ],
  "stats": {
    "total_reports": 150,
    "this_month": 12,
    "avg_importance": 7.5
  }
}
```

---

### **2. component_instances - 组件实例跟踪**

**TypeScript 实现** (`database-manager.ts` 第 224-232 行):

```typescript
this.db.exec(`
  CREATE TABLE IF NOT EXISTS component_instances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    instance_id TEXT UNIQUE NOT NULL,
    component_id TEXT NOT NULL,
    state_id TEXT NOT NULL,
    session_id TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
  )
`);
```

**字段说明**:

| 字段 | 类型 | 说明 | Email Agent 示例 | Finance Agent 示例 |
|------|------|------|-----------------|-----------------|
| `instance_id` | TEXT | 实例唯一标识 | `comp_1737123456789` | `comp_1732689237000` |
| `component_id` | TEXT | 组件模板 ID | `financial_dashboard` | `report_dashboard` |
| `state_id` | TEXT | 绑定的 UI 状态 | `financial_dashboard` | `report_dashboard` |
| `session_id` | TEXT | 所属会话 | `session-xyz-123` | `session-abc-456` |

**索引** (`database-manager.ts` 第 238-241 行):

```typescript
CREATE INDEX IF NOT EXISTS idx_component_instances_instance_id ON component_instances(instance_id)
CREATE INDEX IF NOT EXISTS idx_component_instances_state_id ON component_instances(state_id)
CREATE INDEX IF NOT EXISTS idx_component_instances_session_id ON component_instances(session_id)
```

**为什么必需**:
- ✅ 跟踪 Action 返回的组件实例
- ✅ 支持按会话查询组件列表
- ✅ 支持组件生命周期管理

---

## 📧 Email Agent业务表

> **参考文件**: `email-agent/database/database-manager.ts` (90-172行), `email-agent/database/schema.sql`

### **1. emails - 邮件主表**

**TypeScript 实现** (`database-manager.ts` 第 90-125 行):

```typescript
this.db.exec(`
  CREATE TABLE IF NOT EXISTS emails (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    messageId TEXT UNIQUE NOT NULL,
    threadId TEXT,
    inReplyTo TEXT,
    emailReferences TEXT,
    dateSent DATETIME NOT NULL,
    dateReceived DATETIME DEFAULT CURRENT_TIMESTAMP,
    subject TEXT,
    fromAddress TEXT NOT NULL,
    fromName TEXT,
    toAddresses TEXT,
    ccAddresses TEXT,
    bccAddresses TEXT,
    replyTo TEXT,
    bodyText TEXT,
    bodyHtml TEXT,
    snippet TEXT,
    isRead BOOLEAN DEFAULT 0,
    isStarred BOOLEAN DEFAULT 0,
    isImportant BOOLEAN DEFAULT 0,
    isDraft BOOLEAN DEFAULT 0,
    isSent BOOLEAN DEFAULT 0,
    isTrash BOOLEAN DEFAULT 0,
    isSpam BOOLEAN DEFAULT 0,
    sizeBytes INTEGER DEFAULT 0,
    hasAttachments BOOLEAN DEFAULT 0,
    attachmentCount INTEGER DEFAULT 0,
    folder TEXT DEFAULT 'INBOX',
    labels TEXT,
    rawHeaders TEXT,
    createdAt DATETIME DEFAULT CURRENT_TIMESTAMP,
    updatedAt DATETIME DEFAULT CURRENT_TIMESTAMP
  )
`);
```

**关键字段分类**:

| 分类 | 字段 | 说明 | Finance Agent 对应 |
|------|------|------|-----------------|
| **唯一标识** | `messageId` | 邮件唯一 ID | `report_id` |
| **时间信息** | `dateSent`, `dateReceived` | 发送/接收时间 | `date_published`, `created_at` |
| **元数据** | `subject`, `fromAddress`, `fromName` | 主题、发件人 | `title`, `sources`, `category` |
| **内容字段** | `bodyText`, `bodyHtml`, `snippet` | 正文、预览 | `content`, `summary_one_sentence` |
| **状态标志** | `isRead`, `isStarred`, `isImportant` | 已读、标记 | `is_read`, `is_flagged` |
| **分类信息** | `folder`, `labels` | 文件夹、标签 | `category`, `tags` |

**索引** (`database-manager.ts` 第 157-167 行):

```typescript
const indexes = [
  "CREATE INDEX IF NOT EXISTS idx_emails_date_sent ON emails(date_sent DESC)",
  "CREATE INDEX IF NOT EXISTS idx_emails_from_address ON emails(from_address)",
  "CREATE INDEX IF NOT EXISTS idx_emails_thread_id ON emails(thread_id)",
  "CREATE INDEX IF NOT EXISTS idx_emails_message_id ON emails(message_id)",
  "CREATE INDEX IF NOT EXISTS idx_emails_is_read ON emails(is_read)",
  "CREATE INDEX IF NOT EXISTS idx_emails_is_starred ON emails(is_starred)",
  "CREATE INDEX IF NOT EXISTS idx_emails_folder ON emails(folder)",
  "CREATE INDEX IF NOT EXISTS idx_emails_has_attachments ON emails(has_attachments)",
  "CREATE INDEX IF NOT EXISTS idx_attachments_email_id ON attachments(email_id)"
];
```

---

### **2. emails_fts - 全文搜索表**

**TypeScript 实现** (`database-manager.ts` 第 142-154 行):

```typescript
this.db.exec(`
  CREATE VIRTUAL TABLE IF NOT EXISTS emails_fts USING fts5(
    messageId UNINDEXED,
    subject,
    fromAddress,
    fromName,
    bodyText,
    toAddresses,
    ccAddresses,
    attachment_names,
    tokenize = 'porter unicode61'
  )
`);
```

**为什么需要 FTS5**:
- ✅ 支持全文搜索(如 `"buy gold"` 匹配邮件内容)
- ✅ 性能优化(比 `LIKE '%keyword%'` 快 10-100 倍)
- ✅ 支持分词和相关性排序

**触发器同步** (`database-manager.ts` 第 174-210 行):

```typescript
// 插入时同步
CREATE TRIGGER IF NOT EXISTS emails_fts_insert
AFTER INSERT ON emails
BEGIN
  INSERT INTO emails_fts(
    messageId, subject, fromAddress, fromName, bodyText,
    toAddresses, ccAddresses
  )
  VALUES (
    NEW.messageId, NEW.subject, NEW.fromAddress, NEW.fromName,
    NEW.bodyText, NEW.toAddresses, NEW.ccAddresses
  );
END

// 更新时同步
CREATE TRIGGER IF NOT EXISTS emails_fts_update
AFTER UPDATE ON emails
BEGIN
  UPDATE emails_fts
  SET subject = NEW.subject,
      from_address = NEW.from_address,
      from_name = NEW.from_name,
      body_text = NEW.body_text,
      to_addresses = NEW.to_addresses,
      cc_addresses = NEW.cc_addresses
  WHERE message_id = NEW.message_id;
END

// 删除时清理
CREATE TRIGGER IF NOT EXISTS emails_fts_delete
AFTER DELETE ON emails
BEGIN
  DELETE FROM emails_fts WHERE message_id = OLD.message_id;
END
```

---

### **3. attachments - 附件表** (❌ Finance Agent 不需要)

**TypeScript 实现** (`database-manager.ts` 第 128-139 行):

```typescript
this.db.exec(`
  CREATE TABLE IF NOT EXISTS attachments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email_id INTEGER NOT NULL,
    filename TEXT NOT NULL,
    content_type TEXT,
    size_bytes INTEGER,
    content_id TEXT,
    is_inline BOOLEAN DEFAULT 0,
    FOREIGN KEY (email_id) REFERENCES emails(id) ON DELETE CASCADE
  )
`);
```

**Finance Agent 是否需要**: ❌ 不需要(除非报告需要附加 PDF 文件)

---

## 📈 Finance Agent业务表设计

> **基于实际数据**: `analysis_A股与黄金综合策略_20251127_105237.json` 和 `A股4000拉锯要不要买黄金_20251126102506_11_342_cleaned.txt`
> **设计理念**:混合存储策略 - 高频字段提取 + 完整 JSON + 原始文本

### **核心设计决策**

```
📊 混合存储策略可视化

├── 提取到列 (高频查询字段)
│   ├── title: "A股4000点拉锯与黄金见顶辨析"
│   ├── category: "A股与黄金综合策略"
│   ├── date_published: "2025-11"
│   ├── action: "watch"
│   ├── importance_score: 9
│   ├── urgency_score: 8
│   └── sentiment: "neutral"
│
├── 原始文本 (FTS5 索引)
│   └── content: 3000+ 字原文
│
└── 完整 JSON (保留细节)
    └── analysis_json: {
            "investment_targets": [...],
            "risk_warnings": [...],
            "timeline_events": [...],
            "key_data": {...},
            ...
        }
```

**为什么不完全规范化?**
- ❌ 需要 10+ 张表 (`investment_targets`, `risk_warnings`, `timeline_events`, `key_data` 等)
- ❌ 复杂的 JOIN 查询
- ❌ 过度工程化(MVP 阶段)
- ❌ JSON 结构可能频繁变化

**为什么提取部分字段?**
- ✅ 80/20 原则: 20% 字段处理 80% 查询
- ✅ 高频查询: `WHERE action = 'watch' AND importance_score >= 8`
- ✅ 索引优化: 列索引比 JSON 提取快

---

### **1. reports - 报告主表**

**完整 Schema** (已在 `database/schema.sql` 中实现):

```sql
CREATE TABLE IF NOT EXISTS reports (
  -- ============ 主键和唯一标识 ============
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  report_id TEXT UNIQUE NOT NULL,           -- "analysis_A股与黄金综合策略_20251127_105237"
  
  -- ============ 核心元数据 ============
  title TEXT NOT NULL,                      -- "A股4000点拉锯与黄金见顶辨析"
  report_type TEXT,                         -- "市场策略报告"
  category TEXT,                            -- "A股与黄金综合策略"
  date_published TEXT NOT NULL,             -- "2025-11"
  sources TEXT,                             -- JSON: ["《财经》记者调研", ...]
  
  -- ============ 内容字段 ============
  content TEXT,                             -- 3000+ 字原始文本
  
  -- ============ 摘要信息 ============
  summary_one_sentence TEXT,                -- "一句话总结"
  sentiment TEXT,                           -- "positive" | "neutral" | "negative"
  key_drivers TEXT,                         -- JSON: ["政策面+基本面偏多", ...]
  
  -- ============ 量化评分 ============
  importance_score INTEGER,                 -- 9 (重要性)
  urgency_score INTEGER,                    -- 8 (紧急性)
  reliability_score INTEGER,                -- 9 (可靠性)
  
  -- ============ 投资建议 ============
  action TEXT,                              -- "buy" | "sell" | "hold" | "watch"
  target_allocation TEXT,                   -- "防御与进攻平衡..."
  timing TEXT,                              -- "12月会议政策落地前..."
  holding_period TEXT,                      -- "short" | "medium" | "long"
  confidence_level TEXT,                    -- "low" | "medium" | "high"
  
  -- ============ 完整 JSON 数据 ============
  analysis_json TEXT,                       -- 完整 207 行 JSON
  
  -- ============ 文件信息 ============
  original_file_path TEXT,
  file_size INTEGER,
  
  -- ============ 系统字段 ============
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**实际数据示例** (基于用户提供的文件):

| 字段 | 实际数据 |
|------|--------|
| `report_id` | `analysis_A股与黄金综合策略_20251127_105237` |
| `title` | `A股4000点拉锯与黄金见顶辨析` |
| `category` | `A股与黄金综合策略` |
| `action` | `watch` |
| `importance_score` | `9` |
| `sentiment` | `neutral` |
| `content` | `进入11月以来，A服上证指数在突破4000点大关后...` (3000+ 字) |
| `analysis_json` | `{"report_info":{...}, "summary":{...}, "key_data":{...}, ...}` (207 行) |

**与 Email Agent 对比**:

| Email Agent | Finance Agent | 数据类型 |
|-------------|---------------|---------|
| `messageId` | `report_id` | TEXT UNIQUE |
| `subject` | `title` | TEXT |
| `fromAddress` | `sources` (JSON 数组) | TEXT |
| `bodyText` | `content` | TEXT (原始文本) |
| `snippet` | `summary_one_sentence` | TEXT |
| `isStarred` | `importance_score >= 8` | BOOLEAN → INTEGER |
| `folder` | `category` | TEXT |
| `labels` (JSON) | `key_drivers` (JSON) | TEXT |
| ❌ 无 | `action`, `sentiment`, `*_score` | 新增字段 |

---

### **2. reports_fts - 全文搜索表**

**Schema** (`database/schema.sql` 第 62-69 行):

```sql
CREATE VIRTUAL TABLE IF NOT EXISTS reports_fts USING fts5(
  report_id UNINDEXED,              -- 不索引,用于关联
  title,                            -- 索引标题
  category,                         -- 索引分类
  content,                          -- 索引正文(重点)
  summary_one_sentence,             -- 索引摘要
  tokenize = 'porter unicode61'    -- 支持中英文分词
);
```

**使用场景**:

```python
# 查询 1: 搜索包含 "黄金" 和 "A股" 的报告
SELECT r.* FROM reports r
JOIN reports_fts fts ON r.report_id = fts.report_id
WHERE reports_fts MATCH '黄金 A股'
ORDER BY r.date_published DESC;

# 查询 2: 搜索分类为 "ETF" 的高优先级报告
SELECT r.* FROM reports r
JOIN reports_fts fts ON r.report_id = fts.report_id
WHERE reports_fts MATCH 'ETF'
  AND r.importance_score >= 8
ORDER BY r.importance_score DESC;
```

**触发器同步** (`database/schema.sql` 第 76-100 行):

```sql
-- 插入时同步
CREATE TRIGGER IF NOT EXISTS reports_fts_insert
AFTER INSERT ON reports
BEGIN
  INSERT INTO reports_fts(report_id, title, category, content, summary_one_sentence)
  VALUES (NEW.report_id, NEW.title, NEW.category, NEW.content, NEW.summary_one_sentence);
END;

-- 更新时同步
CREATE TRIGGER IF NOT EXISTS reports_fts_update
AFTER UPDATE ON reports
BEGIN
  UPDATE reports_fts
  SET title = NEW.title,
      category = NEW.category,
      content = NEW.content,
      summary_one_sentence = NEW.summary_one_sentence
  WHERE report_id = NEW.report_id;
END;

-- 删除时清理
CREATE TRIGGER IF NOT EXISTS reports_fts_delete
AFTER DELETE ON reports
BEGIN
  DELETE FROM reports_fts WHERE report_id = OLD.report_id;
END;
```

**与 Email Agent 对比**:

| 特性 | Email Agent | Finance Agent |
|------|-------------|---------------|
| **FTS 表名** | `emails_fts` | `reports_fts` |
| **索引字段** | `subject`, `bodyText`, `fromAddress` | `title`, `content`, `category` |
| **分词器** | `porter unicode61` | `porter unicode61` (相同) |
| **同步机制** | INSERT/UPDATE/DELETE 触发器 | 完全相同 |

---

### **3. 视图：简化常用查询**

**高优先级报告视图** (`database/schema.sql` 第 167-179 行):

```sql
CREATE VIEW IF NOT EXISTS high_priority_reports AS
SELECT 
  report_id,
  title,
  category,
  date_published,
  importance_score,
  urgency_score,
  action,
  summary_one_sentence
FROM reports
WHERE importance_score >= 8
ORDER BY date_published DESC;
```

**投资建议摘要视图**:

```sql
CREATE VIEW IF NOT EXISTS investment_recommendations AS
SELECT 
  report_id,
  title,
  date_published,
  action,
  target_allocation,
  timing,
  confidence_level,
  sentiment
FROM reports
WHERE action IN ('buy', 'hold', 'watch')
ORDER BY date_published DESC;
```

---

## 🔧 DatabaseManager核心方法

> **参考文件**: `email-agent/database/database-manager.ts`

### **1. 初始化数据库** (`database-manager.ts` 第 73-79 行)

**TypeScript 实现**:

```typescript
private constructor(dbPath: string = DATABASE_PATH) {
  this.dbPath = dbPath;
  this.db = new Database(dbPath);
  this.db.exec("PRAGMA journal_mode = WAL");  // 写入后台日志模式
  this.db.exec("PRAGMA foreign_keys = ON");    // 启用外键约束
  this.initializeDatabase();
}
```

**Python 等价实现**:

```python
import sqlite3
import aiosqlite
from pathlib import Path

class DatabaseManager:
    def __init__(self, db_path: str = "finance_agent.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # 同步初始化
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA foreign_keys = ON")
        conn.close()
        
        # 初始化表结构
        self._initialize_database()
    
    def _initialize_database(self):
        """Execute schema.sql to create tables"""
        with open('database/schema.sql', 'r') as f:
            schema = f.read()
        
        conn = sqlite3.connect(self.db_path)
        conn.executescript(schema)
        conn.close()
```

**关键点**:
- ✅ `PRAGMA journal_mode = WAL`: 启用 Write-Ahead Logging,提高并发性能
- ✅ `PRAGMA foreign_keys = ON`: 启用外键约束,保证数据一致性

---

### **2. Upsert 操作** (`database-manager.ts` 第 260-392 行)

**TypeScript 实现** (邮件插入/更新):

```typescript
public upsertEmail(email: EmailRecord, attachments: Attachment[] = []): number {
  const upsertEmail = this.db.prepare(`
    INSERT INTO emails (
      message_id, thread_id, in_reply_to, email_references,
      date_sent, date_received, subject, from_address, from_name,
      to_addresses, cc_addresses, bcc_addresses, reply_to,
      body_text, body_html, snippet,
      is_read, is_starred, is_important, is_draft, is_sent,
      is_trash, is_spam, size_bytes, has_attachments,
      attachment_count, folder, labels, raw_headers
    ) VALUES (
      $messageId, $threadId, $inReplyTo, $references,
      $dateSent, $dateReceived, $subject, $fromAddress, $fromName,
      $toAddresses, $ccAddresses, $bccAddresses, $replyTo,
      $bodyText, $bodyHtml, $snippet,
      $isRead, $isStarred, $isImportant, $isDraft, $isSent,
      $isTrash, $isSpam, $sizeBytes, $hasAttachments,
      $attachmentCount, $folder, $labels, $rawHeaders
    )
    ON CONFLICT(message_id) DO UPDATE SET
      thread_id = excluded.thread_id,
      subject = excluded.subject,
      body_text = excluded.body_text,
      is_read = excluded.is_read,
      updated_at = CURRENT_TIMESTAMP
    RETURNING id
  `);

  // 使用事务保证原子性
  const upsertTransaction = this.db.transaction(() => {
    const result = upsertEmail.get({ /* parameters */ });
    // ... 处理附件
    return result.id;
  });

  return upsertTransaction() as number;
}
```

**Python 等价实现** (Finance Agent 报告插入):

```python
import json
from typing import Dict, Any

def upsert_report(self, report_data: Dict[str, Any]) -> int:
    """
    插入或更新报告
    
    Args:
        report_data: {
            'report_id': 'analysis_...',
            'title': 'A股4000点...',
            'content': '3000+ 字原文',
            'analysis_json': {...},  # dict 将自动序列化
            ...
        }
    
    Returns:
        int: 报告的自增 ID
    """
    # 序列化 JSON 字段
    if isinstance(report_data.get('analysis_json'), dict):
        report_data['analysis_json'] = json.dumps(report_data['analysis_json'], ensure_ascii=False)
    if isinstance(report_data.get('sources'), list):
        report_data['sources'] = json.dumps(report_data['sources'], ensure_ascii=False)
    if isinstance(report_data.get('key_drivers'), list):
        report_data['key_drivers'] = json.dumps(report_data['key_drivers'], ensure_ascii=False)
    
    conn = sqlite3.connect(self.db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
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
                content = excluded.content,
                analysis_json = excluded.analysis_json,
                updated_at = CURRENT_TIMESTAMP
        """, report_data)
        
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()
```

**关键点**:
- ✅ `ON CONFLICT ... DO UPDATE`: SQLite 3.24+ 支持
- ✅ JSON 字段需要手动序列化 (`json.dumps`)
- ✅ `ensure_ascii=False`: 保留中文字符

---

### **3. 搜索方法** (`database-manager.ts` 第 396-500 行)

**TypeScript 实现** (复杂查询):

```typescript
public searchEmails(criteria: SearchCriteria): EmailRecord[] {
  let whereClauses: string[] = [];
  let params: any = {};

  // 全文搜索
  if (criteria.query) {
    whereClauses.push(`e.id IN (
      SELECT e2.id FROM emails e2
      JOIN emails_fts fts ON e2.message_id = fts.message_id
      WHERE emails_fts MATCH $query
    )`);
    params.$query = criteria.query;
  }

  // 发件人筛选
  if (criteria.from) {
    whereClauses.push('e.from_address = $from');
    params.$from = criteria.from;
  }

  // 日期范围
  if (criteria.dateRange) {
    whereClauses.push('e.date_sent BETWEEN $startDate AND $endDate');
    params.$startDate = criteria.dateRange.start;
    params.$endDate = criteria.dateRange.end;
  }

  const whereClause = whereClauses.length > 0 ? 'WHERE ' + whereClauses.join(' AND ') : '';
  const query = `SELECT * FROM emails e ${whereClause} ORDER BY e.date_sent DESC LIMIT $limit`;
  
  return this.db.prepare(query).all({ ...params, $limit: criteria.limit || 30 });
}
```

**Python 等价实现** (Finance Agent 报告搜索):

```python
from typing import Optional, List, Dict, Any
from datetime import datetime

def search_reports(
    self,
    query: Optional[str] = None,
    category: Optional[str] = None,
    action: Optional[str] = None,
    min_importance: Optional[int] = None,
    date_range: Optional[tuple] = None,
    limit: int = 30
) -> List[Dict[str, Any]]:
    """
    搜索报告
    
    Args:
        query: 全文搜索关键词
        category: 分类筛选
        action: 投资建议 ('buy', 'sell', 'hold', 'watch')
        min_importance: 最小重要性评分
        date_range: (start_date, end_date)
        limit: 返回数量
    
    Returns:
        List[Dict]: 报告列表
    """
    where_clauses = []
    params = {}
    
    # 全文搜索
    if query:
        where_clauses.append("""
            r.id IN (
                SELECT r2.id FROM reports r2
                JOIN reports_fts fts ON r2.report_id = fts.report_id
                WHERE reports_fts MATCH :query
            )
        """)
        params['query'] = query
    
    # 分类筛选
    if category:
        where_clauses.append('r.category = :category')
        params['category'] = category
    
    # 投资建议筛选
    if action:
        where_clauses.append('r.action = :action')
        params['action'] = action
    
    # 重要性评分
    if min_importance:
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
        ORDER BY r.date_published DESC
        LIMIT :limit
    """
    params['limit'] = limit
    
    conn = sqlite3.connect(self.db_path)
    conn.row_factory = sqlite3.Row  # 返回字典
    cursor = conn.cursor()
    
    try:
        cursor.execute(query_sql, params)
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()
```

**关键点**:
- ✅ FTS5 搜索使用 `MATCH` 关键词
- ✅ 动态构建 WHERE 子句
- ✅ `sqlite3.Row`: 返回字典而非元组

---

### **4. UI State 管理** (新增方法)

**Python 实现**:

```python
def get_ui_state(self, state_id: str) -> Optional[Dict[str, Any]]:
    """获取 UI 状态"""
    conn = sqlite3.connect(self.db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "SELECT data_json FROM ui_states WHERE state_id = ?",
            (state_id,)
        )
        row = cursor.fetchone()
        return json.loads(row[0]) if row else None
    finally:
        conn.close()

def set_ui_state(self, state_id: str, data: Dict[str, Any]) -> None:
    """设置 UI 状态"""
    data_json = json.dumps(data, ensure_ascii=False)
    
    conn = sqlite3.connect(self.db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO ui_states (state_id, data_json)
            VALUES (?, ?)
            ON CONFLICT(state_id) DO UPDATE SET
                data_json = excluded.data_json,
                updated_at = CURRENT_TIMESTAMP
        """, (state_id, data_json))
        conn.commit()
    finally:
        conn.close()
```

---



## 🐍 Python复刻要点

### **1. 技术选型**

| 组件 | TypeScript (Email Agent) | Python (Finance Agent) | 说明 |
|------|----------------------|-------------------|---------|
| **数据库驱动** | `bun:sqlite` | `sqlite3` / `aiosqlite` | 内置库 |
| **ORM** | 无 (SQL 原生语句) | `SQLAlchemy` (可选) | 可选使用 |
| **异步** | `bun` 内置支持 | `asyncio` + `aiosqlite` | 建议异步 |
| **JSON 序列化** | `JSON.stringify()` | `json.dumps(ensure_ascii=False)` | 保留中文 |

---

### **2. 异步 DatabaseManager 实现**

```python
import aiosqlite
import json
from typing import Optional, Dict, Any, List
from pathlib import Path

class DatabaseManager:
    """Finance Agent 数据库管理器 (异步)"""
    
    def __init__(self, db_path: str = "data/finance.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._initialize_sync()
    
    def _initialize_sync(self):
        """Synchronous initialization for schema"""
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA foreign_keys = ON")
        
        # Execute schema.sql
        with open('database/schema.sql', 'r', encoding='utf-8') as f:
            conn.executescript(f.read())
        
        conn.close()
    
    async def upsert_report(self, report_data: Dict[str, Any]) -> int:
        """异步插入/更新报告"""
        # JSON 序列化
        for key in ['analysis_json', 'sources', 'key_drivers']:
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
                    content = excluded.content,
                    analysis_json = excluded.analysis_json,
                    updated_at = CURRENT_TIMESTAMP
            """, report_data)
            
            await db.commit()
            return cursor.lastrowid
    
    async def search_reports(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        action: Optional[str] = None,
        min_importance: Optional[int] = None,
        limit: int = 30
    ) -> List[Dict[str, Any]]:
        """异步搜索报告"""
        where_clauses = []
        params = {}
        
        if query:
            where_clauses.append("""
                r.id IN (
                    SELECT r2.id FROM reports r2
                    JOIN reports_fts fts ON r2.report_id = fts.report_id
                    WHERE reports_fts MATCH :query
                )
            """)
            params['query'] = query
        
        if category:
            where_clauses.append('r.category = :category')
            params['category'] = category
        
        if action:
            where_clauses.append('r.action = :action')
            params['action'] = action
        
        if min_importance:
            where_clauses.append('r.importance_score >= :min_importance')
            params['min_importance'] = min_importance
        
        where_clause = ' AND '.join(where_clauses) if where_clauses else '1=1'
        query_sql = f"""
            SELECT * FROM reports r
            WHERE {where_clause}
            ORDER BY r.date_published DESC
            LIMIT :limit
        """
        params['limit'] = limit
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(query_sql, params)
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    async def get_ui_state(self, state_id: str) -> Optional[Dict[str, Any]]:
        """获取 UI 状态"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT data_json FROM ui_states WHERE state_id = ?",
                (state_id,)
            )
            row = await cursor.fetchone()
            return json.loads(row[0]) if row else None
    
    async def set_ui_state(self, state_id: str, data: Dict[str, Any]) -> None:
        """设置 UI 状态"""
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
```

---

### **3. 实际数据导入示例**

基于用户提供的 JSON 和 TXT 文件:

```python
import json
from pathlib import Path

async def import_actual_report():
    """导入用户提供的实际报告"""
    db = DatabaseManager()
    
    # 1. 读取 JSON 分析文件
    json_path = Path('analysis_A股与黄金综合策略_20251127_105237.json')
    with open(json_path, 'r', encoding='utf-8') as f:
        analysis = json.load(f)
    
    # 2. 读取原始文本文件
    txt_path = Path('A股4000拉锯要不要买黄金_20251126102506_11_342_cleaned.txt')
    with open(txt_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 3. 构建 report_data
    report_data = {
        'report_id': json_path.stem,  # 'analysis_A股与黄金综合策略_20251127_105237'
        
        # 从 JSON 中提取元数据
        'title': analysis['report_info']['title'],
        'report_type': analysis['report_info']['type'],
        'category': analysis['report_info']['category'],
        'date_published': analysis['report_info']['date'],
        'sources': analysis['report_info']['sources'],  # 将自动转 JSON
        
        # 原始文本
        'content': content,
        
        # 从 summary 提取
        'summary_one_sentence': analysis['summary']['one_sentence'],
        'sentiment': analysis['summary']['sentiment'],
        'key_drivers': analysis['summary']['key_drivers'],
        
        # 从 key_metrics 提取
        'importance_score': analysis['key_metrics']['importance_score'],
        'urgency_score': analysis['key_metrics']['urgency_score'],
        'reliability_score': analysis['key_metrics']['reliability_score'],
        
        # 从 investment_advice 提取
        'action': analysis['investment_advice']['action'],
        'target_allocation': analysis['investment_advice']['target_allocation'],
        'timing': analysis['investment_advice']['timing'],
        'holding_period': analysis['investment_advice']['holding_period'],
        'confidence_level': analysis['investment_advice']['confidence_level'],
        
        # 完整 JSON
        'analysis_json': analysis,  # 将自动转 JSON
        
        # 文件信息
        'original_file_path': str(txt_path.absolute()),
        'file_size': txt_path.stat().st_size
    }
    
    # 4. 插入数据库
    report_id = await db.upsert_report(report_data)
    print(f"✅ 成功导入报告 ID: {report_id}")
    
    # 5. 验证 FTS5 搜索
    results = await db.search_reports(query='黄金 A股', limit=5)
    print(f"🔍 搜索 '黄金 A股' 找到 {len(results)} 条结果")

# 运行
import asyncio
asyncio.run(import_actual_report())
```

**输出示例**:
```
✅ 成功导入报告 ID: 1
🔍 搜索 '黄金 A股' 找到 1 条结果
```

---

### **4. 关键差异对比**

| 特性 | TypeScript (Email Agent) | Python (Finance Agent) | 注意事项 |
|------|----------------------|-------------------|---------|
| **数据库连接** | `new Database(path)` | `aiosqlite.connect(path)` | Python 需要 `async with` |
| **参数化查询** | `$param` | `:param` 或 `?` | SQLite 参数化语法 |
| **JSON 序列化** | `JSON.stringify(obj)` | `json.dumps(obj, ensure_ascii=False)` | **必须** `ensure_ascii=False` |
| **事务处理** | `db.transaction(() => {...})` | `async with db: ... await db.commit()` | 自动回滚 |
| **返回字典** | 默认 Object | `db.row_factory = aiosqlite.Row` | 需要手动设置 |
| **FTS5 中文** | `unicode61` | `unicode61` (相同) | SQLite 3.9+ 内置支持 |

---

### **5. 完整目录结构**

```
finance-agent/
├── database/
│   ├── schema.sql                 # 完整表结构 (已完成)
│   ├── sample_data.sql            # 示例数据 (已完成)
│   ├── database_manager.py        # ✅ 待实现
│   └── README.md                  # 设计说明 (已完成)
├── ccsdk/
│   ├── session.py                 # ✅ 待实现 (Phase 2.1)
│   ├── listeners_manager.py       # ✅ 待实现
│   └── actions_manager.py         # ✅ 待实现
├── scripts/
│   └── import_report.py           # ✅ 待创建 (导入实际数据)
└── data/
    └── finance.db                 # SQLite 数据库文件
```

---

## ✅ 复刻检查清单

### **系统核心表**
- [x] `ui_states` - 已在 `schema.sql` 中定义
- [x] `component_instances` - 已在 `schema.sql` 中定义
- [ ] `get_ui_state()` / `set_ui_state()` - 待在 `database_manager.py` 实现

### **业务数据表**
- [x] `reports` - 已根据实际数据设计
- [x] `reports_fts` - FTS5 全文搜索表
- [ ] `upsert_report()` - 待实现
- [ ] `search_reports()` - 待实现

### **索引和触发器**
- [x] 10 个索引 - 已在 `schema.sql` 中定义
- [x] FTS 同步触发器 - INSERT/UPDATE/DELETE
- [x] 时间戳自动更新触发器

### **测试验证**
- [ ] 创建数据库: `sqlite3 data/finance.db < database/schema.sql`
- [ ] 导入实际数据: `python scripts/import_report.py`
- [ ] 测试 FTS5 搜索: `SELECT * FROM reports_fts WHERE reports_fts MATCH '黄金'`
- [ ] 测试视图查询: `SELECT * FROM high_priority_reports`

---

## 📚 相关文档

- **ARCHITECTURE_ACTUAL.md** - 整体架构
- **SESSION_FLOW.md** - 会话流程
- **TS_TO_PYTHON_MAP.md** - TypeScript → Python 映射
- **IMPLEMENTATION_CHECKLIST.md** - 实现清单 (Phase 2.0 已完成)
- **database/README.md** - 数据库设计详解
- **database/schema.sql** - 完整表结构
- **database/sample_data.sql** - 示例数据

---

## 📊 表结构对比总结

| 表名 | Email Agent | Finance Agent | 分类 | 是否必需 |
|------|-------------|---------------|------|---------|
| `ui_states` | ✅ | ✅ | 系统核心 | ✅ 必需 |
| `component_instances` | ✅ | ✅ | 系统核心 | ✅ 必需 |
| `emails` | ✅ | ❌ | 业务表 | - |
| `reports` | ❌ | ✅ | 业务表 | ✅ 必需 |
| `emails_fts` | ✅ | ❌ | 全文搜索 | - |
| `reports_fts` | ❌ | ✅ | 全文搜索 | ✅ 推荐 |
| `attachments` | ✅ | ❌ | Email专用 | ❌ 不需要 |
| `recipients` | ✅ | ❌ | Email专用 | ❌ 不需要 |
| `contacts` | ⚠️ 可选 | ❌ | 辅助表 | ❌ 不需要 |
| `threads` | ⚠️ 可选 | ❌ | 辅助表 | ❌ 不需要 |

---

## ✨ 核心亮点

1. **系统核心表完全一致**: `ui_states` 和 `component_instances` 的结构完全相同
2. **混合存储策略**: 基于实际 JSON 数据设计,高频字段提取 + 完整 JSON 保留
3. **FTS5 中文支持**: `tokenize = 'porter unicode61'` 支持中文分词
4. **异步设计**: 使用 `aiosqlite` 实现异步数据库操作
5. **实际数据驱动**: 基于用户提供的 A股黄金报告设计

## ✅ 复刻检查清单

### **系统核心表**
- [ ] `ui_states` - UI 状态存储
- [ ] `component_instances` - 组件实例跟踪

### **数据源表（根据业务调整）**
- [ ] Email Agent: `emails` 表
- [ ] Finance Agent: `transactions` 表（替代 emails）

### **辅助表（可选）**
- [ ] 全文搜索表（FTS5）
- [ ] 缓存表（contacts → merchants）
- [ ] 搜索历史表

### **索引和触发器**
- [ ] 时间戳索引（查询优化）
- [ ] 外键索引（JOIN 优化）
- [ ] 自动更新时间戳触发器
- [ ] FTS 同步触发器

---

## 📊 表结构对比总结

| Email Agent | Finance Agent | 分类 | 是否必需 |
|-------------|---------------|------|---------|
| `ui_states` | `ui_states` | 系统核心 | ✅ 必需 |
| `component_instances` | `component_instances` | 系统核心 | ✅ 必需 |
| `emails` | `transactions` | 数据源 | ✅ 必需（结构调整） |
| `emails_fts` | `transactions_fts` | 辅助 | ⚠️ 推荐 |
| `contacts` | `merchants` | 辅助 | ⚠️ 可选 |
| `search_history` | `search_history` | 辅助 | ⚠️ 可选 |
| `threads` | ❌ 不需要 | 业务 | ❌ 不需要 |
| `recipients` | ❌ 不需要 | 业务 | ❌ 不需要 |
| `attachments` | ❌ 不需要 | 业务 | ❌ 不需要 |

---

## 📚 相关文档

- **ARCHITECTURE_ACTUAL.md** - 整体架构
- **SESSION_FLOW.md** - 会话流程
- **PLUGIN_LOADING.md** - 插件加载机制
- **WEBSOCKET_MESSAGES.md** - WebSocket 消息格式
