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

## 2026-06-12 + 预测日销小于 0.5 按 0 处理

### 任务目标
在报告诊断中，将角色范围内 SPU 汇总后的预测日销严格小于 0.5 的情况按 0 处理，并统一应用于报告统计和诊断。

### 修改文件
- `backend/src/ai_inventory_backend/repository.py`
- `backend/tests/test_repository_report_scope.py`
- `docs/inventory_analysis_skill.md`

### 修改内容
- 新增预测日销零值阈值 0.5；SPU 汇总预测日销小于 0.5 时标准化为 0，等于 0.5 时保留原值。
- 双零 SPU 排除、自动选择归属和部门、报告汇总、SPU 覆盖天数及无动销判断统一使用标准化后的预测日销。
- SKU 证据中的源预测日销字段保持不变。
- 补充 0、0.49、0.5 边界值以及低预测日销呆滞判断测试，并同步更新分析口径文档。

### 未修改范围
- 未修改前端、接口参数、接口返回结构、数据库表结构、依赖和配置。
- 未修改报告渲染、LLM 提示词和运行监控异常统计。
- 未处理工作区中原有的 `.gitignore` 和 `AGENTS.md` 变更。

### 验证方式
- 在 Conda 环境 `inventory_report` 中运行仓储与边界测试，结果为 12 个测试全部通过。
- 在 Conda 环境 `inventory_report` 中运行 API 与报告渲染回归测试，结果为 9 个测试全部通过。
- 执行 Python 编译检查和 `git diff --check`，结果通过。
- 完成实际报告结果的人工验证和代码评审。

### 验证结论
已实际运行并通过。

### 风险点
- 有库存且 SPU 汇总预测日销小于 0.5 的对象可能进入无动销或呆滞分类。
- 相关 SPU 的覆盖天数不再按极低预测日销计算，报告汇总、问题分布及自动选择的归属或部门可能变化。

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

## 2026-06-12 + 调整核心影响 SPU 分类排序与表格展示

### 任务目标
让核心影响 SPU 按各业务分类的风险指标独立排序，并优化明细表格的指标列、列宽和横向滚动体验。

### 修改文件
- `backend/src/ai_inventory_backend/repository.py`
- `backend/src/ai_inventory_backend/report_renderer.py`
- `backend/tests/test_repository_report_scope.py`
- `backend/tests/test_report_renderer.py`
- `frontend/src/styles.css`

### 修改内容
- 保留综合影响分用于全局 TOP SPU，新增备货不足、备货过量、发货不足、发货过量和无动销/呆滞五类独立 TOP 8 排序。
- 分类明细不再受全局前 30 截断，同一 SPU 可同时进入多个问题分类。
- 备货不足和发货不足展示预测日销，其他分类保留 90 天以上库龄；预测日销保持一位小数。
- 将表头“影响分”改为“综合影响分”，明确其仅作为辅助参考。
- 核心影响 SPU 表格增加横向滚动并冻结第一列，表头保持单行；产品列宽为 200px，本组关注点列宽为 240px。

### 未修改范围
- 未修改综合影响分公式、健康状态、问题数量和产品名称选取规则。
- 未修改前端组件、接口参数、数据库结构、依赖、配置和 LLM 增强逻辑。
- 未处理工作区中原有的 `.gitignore` 变更。

### 验证方式
- 在 Conda 环境 `inventory_report` 中运行后端完整测试，结果为 17 个测试全部通过。
- 执行 Python 编译检查和 `git diff --check`，结果通过。
- 完成报告分类排序、动态指标列、冻结首列及列宽的人工验证和评审。

### 风险点
- 分类明细与全局综合影响分的排序结果可能不同，这是按业务风险独立排序后的预期行为。
- 窄屏查看核心影响 SPU 表格时需要横向滚动，第一列 SPU 会保持冻结。

### 评审结论
通过。

## 2026-06-13 + 增加核心影响 SPU 分类排序备注

### 任务目标
在核心影响 SPU 的五个业务分类中展示实际排序逻辑，方便报告使用者理解每组 SPU 的优先级。

### 修改文件
- `backend/src/ai_inventory_backend/report_renderer.py`
- `backend/tests/test_report_renderer.py`

### 修改内容
- 在备货不足、备货过量、发货不足、发货过量和无动销/呆滞模块的业务说明下增加“排序规则”备注。
- 排序文案与仓储层现有多级排序保持一致，并随各模块配置集中维护。
- 补充渲染测试，逐一验证五个模块展示各自对应的排序说明。

### 未修改范围
- 未修改 SPU 筛选、排序实现、Top 8 数量和综合影响分公式。
- 未修改前端样式、接口结构、数据库查询、依赖和配置。
- 未处理工作区中原有的 `.gitignore` 变更及其他已有修改。

### 验证方式
- 在 Conda 环境 `inventory_report` 中运行渲染器测试，结果为 3 个测试全部通过。
- 在 Conda 环境 `inventory_report` 中运行后端完整测试，结果为 22 个测试全部通过。
- 执行 Python 编译检查和 `git diff --check`，结果通过。
- 完成人工验证和评审。

### 风险点
- 后续若调整分类排序实现，需要同步更新对应模块的排序备注。

### 评审结论
通过。

## 2026-06-13 + 无动销呆滞 SPU 增加 12 个月以上库龄

### 任务目标
在“核心影响SPU”的“无动销/呆滞SPU”模块中增加 12 个月以上库龄展示，并将其放在 90 天以上库龄之前。

### 修改文件
- `backend/src/ai_inventory_backend/report_renderer.py`
- `backend/tests/test_report_renderer.py`

### 修改内容
- 扩展核心影响 SPU 表格渲染逻辑，使业务分类可以配置可选的第二指标列。
- 仅在“无动销/呆滞SPU”模块展示“12个月+库龄”和“90天+库龄”两列。
- 将“12个月+库龄”放在“90天+库龄”之前，并展示已有的 `aged_12m_qty` 数据。
- 补充测试断言，验证新增列的标题、数值和显示顺序，同时确认其他分类不展示该列。

### 未修改范围
- 未修改 SQL、接口参数、接口返回结构、数据库结构和指标计算口径。
- 未修改无动销/呆滞 SPU 的筛选与排序逻辑。
- 未修改前端样式、依赖和配置。
- 未处理工作区中原有的 `.gitignore` 变更。

### 验证方式
- 直接执行 3 个渲染器测试函数，结果全部通过。
- 执行 `git diff --check`，结果通过。
- 当前 Python 环境未安装 `pytest`，未通过 pytest 测试框架运行。

### 验证结论
已实际运行并通过。

### 风险点
- 无动销/呆滞 SPU 表格增加一列后占用宽度增大，窄屏查看时可能需要更多横向滚动。
- 后续调整通用表格指标配置时，需要继续保证其他四个分类不出现“12个月+库龄”列。

### 评审结论
通过。

## 2026-06-13 + 调整呆滞与清仓风险表格列宽

### 任务目标
调整 HTML 诊断报告“呆滞与清仓风险”明细表格，避免表头换行，并优化各列宽度和窄屏查看体验。

### 修改文件
- `backend/src/ai_inventory_backend/report_renderer.py`
- `frontend/src/styles.css`
- `backend/tests/test_report_renderer.py`

### 修改内容
- 为“呆滞与清仓风险”表格增加独立容器和样式类。
- 设置表格最小宽度和横向滚动，保持表头不换行。
- 参考“核心影响SPU”模块固定首列 SPU，并保留对应背景和阴影效果。
- 将产品列宽度调整为 280px，建议列宽度调整为 220px，数值列保持紧凑。
- 补充渲染测试，验证专用表格容器和空数据行结构。

### 未修改范围
- 未修改表格字段、字段顺序、数据口径和筛选逻辑。
- 未修改接口参数、接口返回、数据库结构、依赖和配置。
- 未调整其他报告模块样式。
- 未处理工作区中原有的 `.gitignore` 变更。

### 验证方式
- 执行 Python 编译检查，结果通过。
- 执行 `git diff --check`，结果通过，仅存在 LF/CRLF 行尾提示。
- 使用现有 Python 按文件加载渲染器并执行等价渲染断言，命令退出码为 0。
- 完成表头、列宽、横向滚动和首列固定效果的人工验证。
- 当前 Python 环境缺少 `pytest` 和 `fastapi`，未通过 pytest 测试框架运行。

### 验证结论
需要人工验证；人工验证已通过。

### 风险点
- 窄屏查看时会出现横向滚动，这是保持表头不换行的预期行为。
- 产品名称较长时仍可能在单元格内换行，以控制表格整体宽度。

### 评审结论
通过。

## 2026-06-24 + 暂停整篇 LLM 报告改写并增加调用观测

### 任务目标
暂停普通报告详情链路中的整篇 HTML LLM 改写，让 `/api/inventory-reports/{report_id}` 稳定返回规则 HTML；同时保留 LLM 调用观测能力，便于后续排查和改造为独立 AI 区块链路。

### 修改文件
- `backend/src/ai_inventory_backend/repository.py`
- `backend/src/ai_inventory_backend/llm_report.py`
- `backend/tests/test_repository_report_scope.py`
- `backend/tests/test_llm_report.py`

### 修改内容
- 在 `_build_report_detail()` 中保留原 `enhance_html()` 调用代码但注释掉实际调用，改为返回 `report_renderer.render_html()` 生成的规则 HTML。
- 在注释中说明暂停原因：整篇 LLM HTML 改写容易输出过长并被截断，导致 `invalid_html` 回退；后续 AI 能力应改为独立 AI 区块。
- 为 `enhance_html()` 增加调用日志、失败原因日志和 HTML 来源注释标记，用于判断 LLM 是否被调用、是否成功采用、或是否回退规则 HTML。
- `invalid_html` 仅保留简短失败日志，不输出 LLM 返回内容预览，避免日志暴露报告片段。
- 补充单元测试，覆盖 LLM disabled、调用成功、请求失败、非法 HTML、缺少闭合 `</section>`，以及普通报告详情不再调用 LLM 改写。

### 未修改范围
- 未新增接口。
- 未修改接口入参、返回结构和 `ReportDetail` schema。
- 未修改 SQL、数据库结构、数据口径和诊断规则。
- 未修改 LLM prompt、配置项、依赖和 lock 文件。
- 未修改前端页面、路由和样式。
- 未处理工作区中既有的 `.gitignore` 变更。

### 验证方式
- 在 Conda 环境 `inventory_report` 中显式设置 UTF-8、`PYTHONPATH=backend\src` 和 `AI_INVENTORY_USE_MOCK_DATA=true` 后运行后端测试：

```powershell
$env:PYTHONPATH='backend\src'
$env:PYTHONUTF8='1'
$env:AI_INVENTORY_USE_MOCK_DATA='true'
conda run -n inventory_report pytest backend\tests -q -o cache_dir=.ai_tmp\pytest_cache
```

### 验证结论
- 已实际运行并通过。
- 测试结果：`29 passed in 1.38s`。
- 用户已确认验证通过。

### 风险点
- `/api/inventory-llm/status` 仍会展示 LLM 配置状态，但普通报告详情接口已不再调用 LLM 改写整篇 HTML。
- `llm_report.py` 仍保留整篇 HTML 改写能力和测试，后续若改为 AI 区块链路，需要重新梳理调用入口和日志含义。
- `htmlContent` 不再产生 LLM 改写版内容，依赖 LLM 改写效果的临时验证流程需要改为查看规则 HTML 或后续 AI 区块接口。

### 评审结论
通过。
## 2026-06-24 规则 HTML 内嵌现有样式

### 任务目标
让 `/api/inventory-reports/{report_id}` 返回的规则 HTML 自带报告样式，使导出的单个 HTML 文件发给他人后不再依赖 `frontend/src/styles.css`。

### 修改文件
- `backend/src/ai_inventory_backend/report_renderer.py`
- `backend/tools/export_reports.py`
- `backend/tests/test_report_renderer.py`
- `backend/tests/test_export_reports.py`

### 修改内容
- 在规则报告 `render_html()` 输出前增加 `<style data-inventory-report-style>` 样式块。
- 样式内容优先读取项目现有 `frontend/src/styles.css`。
- 当样式文件读取失败时，使用后端内置最小兜底 CSS，保证卡片、表格、网格、状态标签和柱状图有基础样式。
- 导出脚本移除对 `../frontend/src/styles.css` 的外部引用，保留导出页外层布局样式。
- 补充 renderer 和导出页面测试，验证样式内嵌顺序和导出 HTML 不再依赖外部 CSS。

### 未修改范围
- 未修改接口路径、接口入参和 `ReportDetail` schema。
- 未修改 SQL、数据库结构、数据口径和诊断规则。
- 未恢复普通报告详情中的整篇 LLM HTML 改写。
- 未修改 LLM prompt、LLM 配置和依赖。
- 未处理工作区中既有的 `.gitignore` 变更。

### 验证方式
在 Conda 环境 `inventory_report` 中显式设置 UTF-8、`PYTHONPATH=backend\src` 和 `AI_INVENTORY_USE_MOCK_DATA=true` 后运行后端测试：

```powershell
$env:PYTHONPATH='backend\src'
$env:PYTHONUTF8='1'
$env:AI_INVENTORY_USE_MOCK_DATA='true'
conda run -n inventory_report pytest backend\tests -q -o cache_dir=.ai_tmp\pytest_cache
```

### 验证结论
- 已实际运行并通过。
- 测试结果：`31 passed in 1.30s`。
- 用户已确认验证通过。

### 风险点
- 完整注入 `frontend/src/styles.css` 后，前端 `v-html` 场景可能受到同源全局样式影响，后续如发现影响可收敛为报告专用 CSS 子集。
- 若后续导出 HTML 需要更严格的视觉一致性，建议抽取真实报告文件做浏览器人工检查。

### 评审结论
通过。
