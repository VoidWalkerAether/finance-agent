-- ============================================================================
-- Finance Agent 数据库 Schema
-- 版本：2.0 (基于实际数据优化)
-- 数据库：SQLite + FTS5
-- 设计日期：2025-11-27
-- ============================================================================

-- ============================================================================
-- 1. 报告主表 (reports)
-- 存储策略：基础元数据 + 完整 JSON + 原始文本
-- ============================================================================

CREATE TABLE IF NOT EXISTS reports (
  -- ============ 主键和唯一标识 ============
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  report_id TEXT UNIQUE NOT NULL,           -- 如："analysis_A股与黄金综合策略_20251127_105237"
  
  -- ============ 核心元数据（从 report_info 提取）============
  title TEXT NOT NULL,                      -- 如："A股4000点拉锯与黄金见顶辨析"
  report_type TEXT,                         -- 如："市场策略报告"
  category TEXT,                            -- 如："A股与黄金综合策略"
  date_published TEXT NOT NULL,             -- 如："2025-11"（ISO 格式）
  sources TEXT,                             -- JSON 数组，如：["《财经》记者调研", "华安基金"]
  
  -- ============ 内容字段 ============
  content TEXT,                             -- 原始文本（cleaned.txt 内容）
  
  -- ============ 摘要信息（从 summary 提取）============
  summary_one_sentence TEXT,                -- 一句话总结
  sentiment TEXT,                           -- 情绪："positive" | "neutral" | "negative"
  key_drivers TEXT,                         -- JSON 数组，核心驱动因素
  
  -- ============ 量化评分（从 key_metrics 提取）============
  importance_score INTEGER,                 -- 重要性评分 (1-10)
  urgency_score INTEGER,                    -- 紧急性评分 (1-10)
  reliability_score INTEGER,                -- 可靠性评分 (1-10)
  
  -- ============ 投资建议（从 investment_advice 提取）============
  action TEXT,                              -- 操作建议："buy" | "sell" | "hold" | "watch"
  target_allocation TEXT,                   -- 目标配置描述
  timing TEXT,                              -- 时机建议
  holding_period TEXT,                      -- 持仓周期："short" | "medium" | "long"
  confidence_level TEXT,                    -- 信心水平："low" | "medium" | "high"
  
  -- ============ 完整 JSON 数据 ============
  analysis_json TEXT,                       -- 完整的 JSON 字符串（包含所有结构化数据）
  
  -- ============ 文件信息 ============
  original_file_path TEXT,                  -- 原始文件路径
  file_size INTEGER,                        -- 文件大小（字节）
  
  -- ============ 系统字段 ============
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- 2. 全文搜索表 (reports_fts)
-- FTS5 虚拟表，用于高效全文搜索
-- ============================================================================

CREATE VIRTUAL TABLE IF NOT EXISTS reports_fts USING fts5(
  report_id UNINDEXED,              -- 不索引，用于关联
  title,                            -- 索引标题
  category,                         -- 索引分类
  content,                          -- 索引正文（重点）
  summary_one_sentence,             -- 索引摘要
  tokenize = 'porter unicode61'    -- 支持中英文分词
);

-- ============================================================================
-- 3. 触发器：自动同步到 FTS 表
-- ============================================================================

-- 插入时自动同步到 FTS 表
CREATE TRIGGER IF NOT EXISTS reports_fts_insert
AFTER INSERT ON reports
BEGIN
  INSERT INTO reports_fts(report_id, title, category, content, summary_one_sentence)
  VALUES (NEW.report_id, NEW.title, NEW.category, NEW.content, NEW.summary_one_sentence);
END;

-- 更新时自动同步
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

-- 删除时自动清理
CREATE TRIGGER IF NOT EXISTS reports_fts_delete
AFTER DELETE ON reports
BEGIN
  DELETE FROM reports_fts WHERE report_id = OLD.report_id;
END;

-- ============================================================================
-- 4. 系统核心表（ui_states）
-- 与 Email Agent 完全一致，存储 UI 状态
-- ============================================================================

CREATE TABLE IF NOT EXISTS ui_states (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  state_id TEXT UNIQUE NOT NULL,
  data_json TEXT NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 自动更新时间戳
CREATE TRIGGER IF NOT EXISTS update_ui_states_timestamp
AFTER UPDATE ON ui_states
FOR EACH ROW
BEGIN
  UPDATE ui_states SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- ============================================================================
-- 5. 组件实例表（component_instances）
-- 与 Email Agent 完全一致，管理动态组件
-- ============================================================================

CREATE TABLE IF NOT EXISTS component_instances (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  instance_id TEXT UNIQUE NOT NULL,
  component_id TEXT NOT NULL,
  state_id TEXT NOT NULL,
  session_id TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- 6. 索引策略
-- ============================================================================

-- 核心索引
CREATE INDEX IF NOT EXISTS idx_reports_date ON reports(date_published DESC);
CREATE INDEX IF NOT EXISTS idx_reports_category ON reports(category);
CREATE INDEX IF NOT EXISTS idx_reports_type ON reports(report_type);
CREATE INDEX IF NOT EXISTS idx_reports_action ON reports(action);

-- 评分索引（用于筛选高质量报告）
CREATE INDEX IF NOT EXISTS idx_reports_importance ON reports(importance_score DESC);
CREATE INDEX IF NOT EXISTS idx_reports_urgency ON reports(urgency_score DESC);

-- 复合索引（常见组合查询）
CREATE INDEX IF NOT EXISTS idx_reports_category_date ON reports(category, date_published DESC);
CREATE INDEX IF NOT EXISTS idx_reports_action_date ON reports(action, date_published DESC);

-- 系统表索引
CREATE INDEX IF NOT EXISTS idx_ui_states_state_id ON ui_states(state_id);
CREATE INDEX IF NOT EXISTS idx_ui_states_updated_at ON ui_states(updated_at);
CREATE INDEX IF NOT EXISTS idx_component_instances_instance_id ON component_instances(instance_id);
CREATE INDEX IF NOT EXISTS idx_component_instances_state_id ON component_instances(state_id);
CREATE INDEX IF NOT EXISTS idx_component_instances_session_id ON component_instances(session_id);

-- ============================================================================
-- 7. 视图：简化常用查询
-- ============================================================================

-- 高优先级报告视图（重要性 >= 8）
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

-- 投资建议摘要视图
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

-- ============================================================================
-- 8. 关注列表表（watchlist）
-- 用户关注的标的列表
-- ============================================================================

CREATE TABLE IF NOT EXISTS watchlist (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT DEFAULT 'default',
  target_name TEXT NOT NULL,              -- 标的名称（如：招商银行、上证指数）
  target_type TEXT NOT NULL,              -- 类型：stock/etf/index/industry
  alert_conditions TEXT,                  -- JSON: 提醒条件（可选）
  status TEXT DEFAULT 'active',           -- active/inactive
  notes TEXT,                             -- 备注
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 关注列表索引
CREATE INDEX IF NOT EXISTS idx_watchlist_user ON watchlist(user_id);
CREATE INDEX IF NOT EXISTS idx_watchlist_status ON watchlist(status);
CREATE INDEX IF NOT EXISTS idx_watchlist_target ON watchlist(target_name);

-- 自动更新时间戳
CREATE TRIGGER IF NOT EXISTS update_watchlist_timestamp
AFTER UPDATE ON watchlist
FOR EACH ROW
BEGIN
  UPDATE watchlist SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- ============================================================================
-- 9. 用户持仓表（user_portfolios）
-- 存储用户的投资组合数据
-- ============================================================================

CREATE TABLE IF NOT EXISTS user_portfolios (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT DEFAULT 'default' NOT NULL,
  
  -- ============ 核心数据字段 ============
  total_asset_value REAL NOT NULL,         -- 总资产价值
  cash_position REAL NOT NULL,             -- 现金头寸
  holdings_json TEXT NOT NULL,             -- 持仓明细（JSON格式）
  
  -- ============ 备用扩展字段 ============
  extra_field_1 TEXT,                      -- 备用字段1（可用于存储额外配置）
  extra_field_2 TEXT,                      -- 备用字段2
  extra_field_3 REAL,                      -- 备用数值字段
  
  -- ============ 系统字段 ============
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  
  UNIQUE(user_id)
);

-- 用户持仓索引
CREATE INDEX IF NOT EXISTS idx_user_portfolios_user ON user_portfolios(user_id);
CREATE INDEX IF NOT EXISTS idx_user_portfolios_updated ON user_portfolios(updated_at DESC);

-- 自动更新时间戳
CREATE TRIGGER IF NOT EXISTS update_user_portfolios_timestamp
AFTER UPDATE ON user_portfolios
FOR EACH ROW
BEGIN
  UPDATE user_portfolios SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;
