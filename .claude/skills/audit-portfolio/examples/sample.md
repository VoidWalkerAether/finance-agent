# 示例：审计结果输出

## 场景 1：完全合规 (OK)
**总体状态**: ok
**违规/警告**: 无

## 场景 2：存在违规 (VIOLATED)
**总体状态**: violated
**违规项**:
- **single_position_max_extreme**: 某股票占比 25% 超过极限 20%
- **target_position_count_min**: 持仓数量 3 低于下限 5

## 场景 3：存在警告 (WARNING)
**总体状态**: warning
**警告项**:
- **liquidity**: 现金占比 4% 略低于下限 5%
