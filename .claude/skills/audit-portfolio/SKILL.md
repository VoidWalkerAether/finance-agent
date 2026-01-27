---
name: audit-portfolio
description: 审计投资组合与投资原则的一致性。当用户询问组合是否合规、检查持仓风险或生成投资建议前使用。
argument-hint: [user-id]
---

# audit-portfolio

投资组合与原则一致性检查技能。此技能通过运行底层 Python 审计脚本，检查用户的投资持仓是否符合其预设的投资原则约束。

## 任务

1. **执行审计**: 运行 `scripts/audit.py` 获取组合的结构化审计数据（JSON 格式）。
2. **分析结果**: 提取违规项（violations）并根据 `template.md` 生成易读的中文报告。
3. **给出建议**: 针对违反的规则（如仓位超限、现金不足等），提供具体的调整建议。

## 执行指南

- **调用命令**: 
  ```bash
  python .claude/skills/audit-portfolio/scripts/audit.py [user-id]
  ```
  *(注意：[user-id] 默认使用 "default")*
- **处理报错**: 如果脚本返回 `error` 字段，请检查 `debug_info` 并在解决后重试。

## 规则定义

- **仓位上限**: 单一标的权重检查（常规/极限）。
- **持仓数量**: 总体分散度检查。
- **流动性**: 现金占比检查。

## 示例

参考 `examples/sample.md` 了解预期输出格式。
