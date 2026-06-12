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

## 2026-06-12 + 排除零库存且零预测销量 SPU

### 任务目标
在角色范围过滤后按 SPU 汇总，将 `总库存` 合计和 `预测日销` 合计同时为 0 的 SPU 排除出报告统计范围。

### 修改文件
- `backend/src/ai_inventory_backend/repository.py`
- `backend/tests/test_repository_report_scope.py`
- `docs/inventory_analysis_skill.md`

### 修改内容
- 报告总览、SPU 健康分布、预警分布和 SKU 证据统一使用相同的 SPU 统计范围。
- 自动选择归属和部门时，按维度与 SPU 汇总后排除零库存且零预测日销的 SPU。
- 仅当两个条件同时为 0 时排除；其中任意一项非 0 的 SPU 继续纳入报告。
- 分析文档同步记录新增统计口径，并补充仓储层测试。

### 未修改范围
- 未修改前端、接口参数、数据结构、数据库表结构、依赖和配置。
- 未修改报告渲染和 LLM 提示词。
- 未修改运行监控的批次异常数和异常列表统计逻辑。
- 未处理工作区中原有的 `.gitignore` 变更。

### 验证方式
- 在 Conda 环境 `inventory_report` 中运行新增仓储测试，结果为 4 个测试全部通过。
- 在 Conda 环境 `inventory_report` 中运行现有 API 测试，结果为 7 个测试全部通过。
- 执行 Python 编译检查和 `git diff --check`，结果通过。
- 使用实际报告结果完成人工测试和评审。

### 风险点
- 排除后的 SPU 数、SKU 数、库存汇总、问题分布和核心影响对象可能发生变化。
- 自动选择的归属或部门可能因排除无效 SPU 而发生变化。

### 评审结论
通过。

## 2026-06-12 + 修改 stocking_inventory_qty 计算口径

### 任务目标
将 `stocking_inventory_qty` 从多个库存字段相加，改为直接使用源表 `lx_ads.ads_lx_kd_inventory_sku_calc` 的 `总库存` 字段。

### 修改文件
- `backend/src/ai_inventory_backend/repository.py`
- `docs/inventory_analysis_skill.md`

### 修改内容
- 角色汇总中的 `stocking_inventory_qty` 直接取聚合后的 `total_inventory`。
- SPU 维度的 `stocking_coverage_days` 改为使用 `总库存 / 预测日销`。
- 分析文档同步记录整体库存的数据计算口径。

### 未修改范围
- 未修改前端和报告中的计算公式展示文案。
- 未修改接口参数、数据结构、数据库表结构、依赖和配置。
- 未修改整体可售天数的 90 至 150 天判断阈值。

### 验证方式
- 执行 Python 编译检查和 `git diff --check`，结果通过。
- 使用修改后的数据计算结果完成人工验收。

### 风险点
- `总库存` 与原分项求和结果可能存在数值差异，会影响整体可售天数及相应的 SPU 健康分类。
- 前端和报告仍展示原计算公式文案，与后端实际取数口径存在差异。

### 评审结论
通过。
