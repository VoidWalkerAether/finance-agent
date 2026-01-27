# 投资组合一致性审计报告

**用户 ID**: {{user_id}}
**审计时间**: {{audit_time}}
**总体状态**: {{overall_status}}

## 审计概览
- **违规项数量**: {{violation_count}}
- **警告项数量**: {{warning_count}}

## 详细检查结果
{{#violations}}
### {{rule}}
- **状态**: {{status}}
- **详情**: {{details}}
{{/violations}}

---
*本报告由 finance-agent 自动生成*
