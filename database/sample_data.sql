-- ============================================================================
-- 示例数据：基于实际的 A股与黄金综合策略报告
-- ============================================================================

-- 插入报告数据
INSERT INTO reports (
  report_id,
  title,
  report_type,
  category,
  date_published,
  sources,
  content,
  summary_one_sentence,
  sentiment,
  key_drivers,
  importance_score,
  urgency_score,
  reliability_score,
  action,
  target_allocation,
  timing,
  holding_period,
  confidence_level,
  analysis_json,
  original_file_path
) VALUES (
  'analysis_A股与黄金综合策略_20251127_105237',
  'A股4000点拉锯与黄金见顶辨析',
  '市场策略报告',
  'A股与黄金综合策略',
  '2025-11',
  '["《财经》记者调研", "华安基金", "汇丰晋信基金", "世界黄金协会", "国家统计局", "伦敦现货黄金"]',
  '进入11月以来，A服上证指数在突破4000点大关后，出现了长达两周的拉锯战...',  -- 完整原文
  'A股4000点仅为年末休整而非终点，黄金短期过热但2026年降息周期下仍有望新高。',
  'neutral',
  '["政策面+基本面仍偏多", "年末流动性偏紧", "央行持续购金", "美联储2026年降息预期"]',
  9,
  8,
  9,
  'watch',
  '防御与进攻平衡：黄金/债券20%-30%，港股跨境20%，A股高端制造与红利股30%-40%，现金<10%',
  '12月会议政策落地前逢低分批布局，黄金回调至3800-3900美元区间再考虑加仓',
  'medium',
  'medium',
  '{...}',  -- 完整的 JSON 对象
  '/Users/caiwei/workbench/claude-agent-sdk-demos/finance-agent/A股4000拉锯要不要买黄金_20251126102506_11_342_cleaned.txt'
);

-- ============================================================================
-- 查询示例
-- ============================================================================

-- 1. 全文搜索：查找包含"黄金"的报告
SELECT 
  r.title,
  r.date_published,
  r.summary_one_sentence,
  r.action
FROM reports r
JOIN reports_fts fts ON r.report_id = fts.report_id
WHERE reports_fts MATCH '黄金'
ORDER BY rank
LIMIT 10;

-- 2. 筛选高优先级且建议观望的报告
SELECT 
  title,
  date_published,
  importance_score,
  urgency_score,
  action,
  summary_one_sentence
FROM reports
WHERE importance_score >= 8
  AND action = 'watch'
ORDER BY date_published DESC;

-- 3. 按分类统计报告数量
SELECT 
  category,
  COUNT(*) as count,
  AVG(importance_score) as avg_importance
FROM reports
GROUP BY category
ORDER BY count DESC;

-- 4. 查找特定时间段的报告
SELECT 
  title,
  date_published,
  sentiment,
  action
FROM reports
WHERE date_published >= '2025-11'
ORDER BY date_published DESC;

-- 5. 搜索投资建议中提到"ETF"的报告
SELECT 
  title,
  target_allocation,
  timing,
  confidence_level
FROM reports
WHERE target_allocation LIKE '%ETF%'
   OR timing LIKE '%ETF%';
