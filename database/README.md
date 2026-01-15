# Finance Agent 数据库设计说明

> **版本**：2.0 (基于实际数据优化)  
> **最后更新**：2025-11-27

---

## 📊 设计概述

### 核心设计思路：**混合存储策略**

```
┌─────────────────────────────────────────────────────────────┐
│                     reports 表（主表）                       │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌───────────────────┐  │
│  │ 核心元数据  │  │ 提取字段    │  │  完整 JSON 存储   │  │
│  │ - title     │  │ - action    │  │  analysis_json    │  │
│  │ - category  │  │ - sentiment │  │  (所有细节)       │  │
│  │ - date      │  │ - scores    │  │                   │  │
│  └─────────────┘  └─────────────┘  └───────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                           │
                           ├──────┐
                           ↓      ↓
           ┌────────────────────┐  ┌───────────────────┐
           │ reports_fts (FTS5) │  │ 原始文本 content  │
           │  全文搜索索引      │  │  (3000+ 字)       │
           └────────────────────┘  └───────────────────┘
```

---

## 🎯 为什么采用这种设计？

### 问题 1：为什么不把 JSON 全部展开成独立表？

#### ❌ 完全规范化的方案（不推荐）
```sql
-- 需要创建 10+ 张表
reports
├── investment_targets (推荐标的表)
├── cautious_targets (谨慎标的表)
├── risk_warnings (风险预警表)
├── timeline_events (时间线事件表)
├── key_data (关键数据表)
└── ...
```

**缺点**：
- 🔴 查询复杂（需要多次 JOIN）
- 🔴 插入数据繁琐（事务复杂）
- 🔴 JSON 结构变化时需要修改表结构
- 🔴 过度设计（MVP 不需要）

#### ✅ 混合存储方案（推荐）
```sql
-- 只需要 3 张核心表
reports (主表，存储完整 JSON)
reports_fts (FTS5 搜索)
ui_states (系统表)
```

**优点**：
- ✅ **灵活性**：JSON 结构变化不影响数据库
- ✅ **简单性**：插入一条记录即可
- ✅ **性能**：高频查询字段已提取到列（action, scores, sentiment）
- ✅ **完整性**：analysis_json 保留所有细节

---

### 问题 2：为什么要提取部分字段到列？

**实际查询需求分析**：

#### 高频查询（需要独立列）
```sql
-- 这些查询很常见，需要索引支持
SELECT * FROM reports WHERE action = 'buy';
SELECT * FROM reports WHERE importance_score >= 8;
SELECT * FROM reports WHERE date_published > '2025-11';
```

#### 低频查询（JSON 存储即可）
```python
# 这些查询不频繁，可以在应用层处理
report = db.get_report(report_id)
analysis = json.loads(report.analysis_json)
timeline_events = analysis['timeline_events']  # Python 解析
investment_targets = analysis['investment_targets']['recommended']
```

**设计原则**：
- ✅ **80/20 原则**：20% 的字段满足 80% 的查询
- ✅ **提取字段**：action, scores, sentiment, date_published, category
- ✅ **JSON 存储**：timeline_events, investment_targets, risk_warnings

---

## 📋 表结构设计

### 1. **reports 表**（主表）

```sql
CREATE TABLE reports (
  -- 核心元数据（高频查询）
  report_id TEXT UNIQUE NOT NULL,
  title TEXT NOT NULL,
  category TEXT,
  date_published TEXT NOT NULL,
  
  -- 提取的关键字段（用于筛选和排序）
  action TEXT,                    -- 'buy' | 'sell' | 'hold' | 'watch'
  sentiment TEXT,                 -- 'positive' | 'neutral' | 'negative'
  importance_score INTEGER,
  urgency_score INTEGER,
  reliability_score INTEGER,
  
  -- 原始文本（用于全文搜索）
  content TEXT,
  
  -- 完整 JSON 数据（保留所有细节）
  analysis_json TEXT              -- 完整的结构化数据
);
```

### 2. **reports_fts 表**（FTS5 全文搜索）

```sql
CREATE VIRTUAL TABLE reports_fts USING fts5(
  report_id UNINDEXED,
  title,
  content,                        -- 索引 3000+ 字的原文
  summary_one_sentence,
  tokenize = 'porter unicode61'   -- 中英文分词
);
```

### 3. **ui_states 表**（系统核心表）

与 Email Agent 完全一致，用于存储动态 UI 组件状态。

---

## 🔍 典型查询场景

### 场景 1：全文搜索 + 筛选

```sql
-- 查找包含"黄金"且重要性 >= 8 的报告
SELECT 
  r.title,
  r.date_published,
  r.importance_score,
  r.summary_one_sentence
FROM reports r
JOIN reports_fts fts ON r.report_id = fts.report_id
WHERE reports_fts MATCH '黄金'
  AND r.importance_score >= 8
ORDER BY rank
LIMIT 10;
```

### 场景 2：按投资建议筛选

```sql
-- 查找所有建议"观望"的报告
SELECT 
  title,
  action,
  target_allocation,
  timing,
  confidence_level
FROM reports
WHERE action = 'watch'
ORDER BY date_published DESC;
```

### 场景 3：获取完整分析数据

```python
# Python 代码示例
report = db.query("SELECT analysis_json FROM reports WHERE report_id = ?", [report_id])
analysis = json.loads(report['analysis_json'])

# 访问投资标的
recommended_targets = analysis['investment_targets']['recommended']
for target in recommended_targets:
    print(f"{target['name']}: {target['reason']}")

# 访问风险预警
risk_warnings = analysis['risk_warnings']
for risk in risk_warnings:
    print(f"{risk['risk_type']}: {risk['description']}")
```

---

## 📈 性能优化

### 索引策略

```sql
-- 核心索引（支持高频查询）
CREATE INDEX idx_reports_date ON reports(date_published DESC);
CREATE INDEX idx_reports_category ON reports(category);
CREATE INDEX idx_reports_action ON reports(action);
CREATE INDEX idx_reports_importance ON reports(importance_score DESC);

-- 复合索引（支持组合查询）
CREATE INDEX idx_reports_category_date ON reports(category, date_published DESC);
CREATE INDEX idx_reports_action_date ON reports(action, date_published DESC);
```

### 性能预估

| 数据量 | FTS5 搜索速度 | JSON 解析速度 | 数据库文件大小 |
|--------|--------------|--------------|---------------|
| 100 份报告 | < 10ms | < 1ms | ~10MB |
| 1,000 份报告 | < 20ms | < 1ms | ~100MB |
| 10,000 份报告 | < 50ms | < 1ms | ~1GB |

---

## 🆚 与 Email Agent 的对比

| 维度 | Email Agent | Finance Agent |
|------|-------------|---------------|
| **主表** | `emails` | `reports` |
| **核心字段** | subject, bodyText | title, content |
| **分类方式** | folder, labels | category, sentiment, action |
| **结构化数据** | 简单元数据 | **复杂 JSON**（投资建议、风险预警） |
| **FTS5** | ✅ emails_fts | ✅ reports_fts |
| **系统表** | ui_states, component_instances | ✅ 完全相同 |
| **索引策略** | date, folder, from | date, category, action, scores |

**结论**：架构 95% 相似，只需调整业务字段！

---

## 🚀 实现建议

### MVP 阶段（Week 1-2）

1. ✅ **只实现 3 张核心表**
   - reports
   - reports_fts
   - ui_states

2. ✅ **核心功能**
   - 插入报告（文本 + JSON）
   - 全文搜索
   - 按分类/日期查询

3. ⏭️ **暂不实现**
   - 独立的 investment_targets 表
   - 独立的 risk_warnings 表
   - 复杂的统计视图

### 扩展阶段（Week 3+）

如果发现性能瓶颈或查询复杂度过高，再考虑：

```sql
-- 可选：投资标的独立表
CREATE TABLE investment_targets (
  id INTEGER PRIMARY KEY,
  report_id TEXT REFERENCES reports(report_id),
  target_name TEXT,
  target_type TEXT,
  action TEXT,  -- 'recommended' | 'cautious'
  reason TEXT,
  key_metrics TEXT
);
```

---

## 📝 数据插入示例

```python
import json
import sqlite3

# 读取原始文件
with open('A股4000拉锯要不要买黄金.txt', 'r') as f:
    content = f.read()

# 读取 JSON 分析
with open('analysis_A股与黄金综合策略.json', 'r') as f:
    analysis = json.load(f)

# 插入数据库
conn = sqlite3.connect('finance.db')
cursor = conn.cursor()

cursor.execute('''
INSERT INTO reports (
  report_id,
  title,
  category,
  date_published,
  content,
  summary_one_sentence,
  sentiment,
  importance_score,
  urgency_score,
  reliability_score,
  action,
  target_allocation,
  analysis_json
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
''', (
  'analysis_A股与黄金综合策略_20251127_105237',
  analysis['report_info']['title'],
  analysis['report_info']['category'],
  analysis['report_info']['date'],
  content,
  analysis['summary']['one_sentence'],
  analysis['summary']['sentiment'],
  analysis['key_metrics']['importance_score'],
  analysis['key_metrics']['urgency_score'],
  analysis['key_metrics']['reliability_score'],
  analysis['investment_advice']['action'],
  analysis['investment_advice']['target_allocation'],
  json.dumps(analysis, ensure_ascii=False)
))

conn.commit()
```

---

## ✅ Phase 2.0 评审通过标准

- [x] 表结构清晰合理
- [x] 支持全文搜索
- [x] 支持结构化查询
- [x] 索引策略完整
- [x] 兼容 Email Agent 架构
- [x] 基于实际数据验证
- [x] 提供示例查询和插入代码

**评审结论**：✅ **数据库设计已完成，可以开始 Phase 2.1（Session 类实现）**

---

## 📚 相关文件

- [`schema.sql`](schema.sql) - 完整的表结构定义
- [`sample_data.sql`](sample_data.sql) - 示例数据和查询
- [`ER_DIAGRAM.md`](ER_DIAGRAM.md) - 详细的设计文档
