## 2026-06-12 + 修改 overseas_ready_qty 计算口径

### 任务目标
将 `overseas_ready_qty` 从多个库存明细字段相加，改为直接使用源表 `lx_ads.ads_lx_kd_inventory_sku_calc` 的 `国外合计` 字段。

### 修改文件
- `backend/src/ai_inventory_backend/repository.py`
- `backend/src/ai_inventory_backend/source_fields.py`
- `backend/tests/test_api.py`

### 修改内容
- 角色汇总、SPU 汇总和 SKU 明细中的 `overseas_ready_qty` 均改为使用 `国外合计`，空值按 0 处理。
- SPU 海外覆盖天数和整体库存覆盖天数同步使用新口径。
- 将 `国外合计` 加入源数据必需字段契约，并补充接口测试断言。

### 未修改范围
- 未修改前端、数据库表结构、依赖和配置。
- 未修改覆盖天数阈值、诊断逻辑和报告文案。
- 未处理工作区中原有的无关变更。

### 验证方式
- 在 Conda 环境 `inventory_report` 中运行 `tests/test_api.py`，结果为 7 个测试全部通过。
- 检查旧的 7 字段计算公式已从相关 SQL 中移除。
- 执行 Python 语法解析和 `git diff --check`，结果通过。
- 使用真实数据库生成报告并完成人工验证。

### 风险点
- `国外合计` 与旧公式可能存在数值差异，会影响海外覆盖天数、整体库存覆盖天数及相应风险分类。

### 评审结论
通过。
