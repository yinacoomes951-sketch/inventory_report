# Amazon AI 库存查询与诊断

这是一个独立于原 NexusBI 的库存诊断项目。它读取 Amazon 库存结构化数据，按运营个人、战队/部门、运营总监三个角色范围生成 SPU 优先的库存健康报告，并为后续企微推送、点击追踪和周期任务提供基础。

> 当前定位：报告 MVP 已可运行，业务口径仍在校准，企微集成尚未开始。请不要把当前聚合口径直接视为最终生产结论。

## 1. 项目目标

每周自动完成以下流程：

1. 从库存数据表读取最新批次。
2. 按运营负责人、战队/部门、运营总监切分数据。
3. 先由确定性规则计算库存事实和风险，再由 LLM 根据分析 Skill 与表达 Skill 润色报告。
4. 生成可审计的 HTML 库存健康报告。
5. 后续通过企微定向推送，并记录发送成功率、点击率和历史执行记录。

## 2. 当前进度

| 模块 | 状态 | 说明 |
| --- | --- | --- |
| PostgreSQL 真实数据读取 | 已完成 | 读取 `lx_ads.ads_lx_kd_inventory_sku_calc` 最新 `insert_time` 批次 |
| 三类角色报告 | 已完成 | 运营个人、战队/部门、运营总监 |
| SPU 健康诊断 | 已完成初版 | 报告正文以 SPU 为主，SKU 作为后续 BI 下钻证据 |
| 库龄与呆滞分析 | 已完成初版 | 关注 90 天以上库龄及 12 个月以上严重库龄 |
| HTML 报告 | 已完成初版 | 包含结论、概览、图表、问题分组、行动清单 |
| LLM 报告增强 | 已接通 | OpenAI-compatible API；无密钥时自动回退规则报告 |
| 运行记录前端 | 已完成 MVP | 可查看运行、报告、异常和报告详情 |
| 报告历史持久化 | 未完成 | 当前主要读取最新数据并即时生成 |
| BI 下钻链接 | 待开发 | 应按角色、SPU、问题类型携带筛选参数 |
| 周期调度 | 待开发 | 已引入 APScheduler，尚未形成生产任务 |
| 企微推送 | 未开始 | 需要应用消息接口、人员映射、重试和审计 |
| 点击追踪 | 未开始 | 前端成功率和点击率目前为占位指标 |
| 生产权限与部署 | 未完成 | 需要鉴权、数据范围、密钥管理和部署方案 |

## 3. 已确认的业务口径

### 3.1 分析粒度

- 报告先判断角色范围整体是否健康。
- 前半部分只展示 SPU 分布和核心影响 SPU，避免直接堆 SKU。
- SKU 不在正文大面积展开；需要排查时跳转 BI，并自动带入筛选条件。
- 数据表中的“备货预警”只是原业务判断标准之一，不直接作为 AI 报告标题或最终结论。

### 3.2 需求与库存范围

日销统一使用 `预测日销`。

整体库存覆盖用于采购/备货判断：

```text
整体库存 = 海外在途及可售 + 国内库存 + 采购在途 + 采购计划
整体库存覆盖天数 = 整体库存 / 预测日销
关注区间 = 90 至 150 天
```

海外覆盖用于发货判断：

```text
海外覆盖库存 = 海外在途及可售
海外覆盖天数 = 海外覆盖库存 / 预测日销
关注区间 = 60 至 100 天
```

低于下限和高于上限都需要关注，但动作不同：

- 整体库存不足：进一步判断采购补货。
- 整体库存过量：控制新增采购并检查库龄、动销。
- 海外覆盖不足：优先确认国内可发库存并安排发货。
- 海外覆盖过量：控制继续发货，检查海外库龄与销售趋势。

### 3.3 库龄与呆滞

- 90 天以上库龄进入重点观察。
- 12 个月以上库存单独标识严重风险。
- 有动销 SPU 的长库龄属于局部清理问题。
- 无动销且仍有库存的 SPU 才进入呆滞、清仓或坏账风险判断。

## 4. 当前高优先级校准项

以下内容尚未最终验收，接手者应先处理：

1. **聚合覆盖天数可能失真。** 当前角色层总库存除以总预测日销可能被低销量大库存 SPU 拉高，例如出现 220 天以上。角色总览应优先展示 SPU 分布、中位数、分位数或加权合理性，而不是只展示一个总体比值。
2. **健康状态需避免分类重叠。** 同一 SPU 可以同时命中备货、发货和库龄问题，但主健康状态必须唯一，问题标签可以多选。
3. **无动销口径需严格。** 不能仅因某个 SKU 无销量就把整个 SPU 判为无动销；需结合 SPU 汇总销量、预测日销、在售状态和库存。
4. **动作建议必须按库存链路决策。** 国内缓冲不足不等于需要采购；只有整体库存不足时才进入采购判断。
5. **报告术语继续业务化。** 使用“整体库存覆盖天数”“海外在途及可售覆盖天数”，避免“备货天数”“发货天数”等容易误解的名称。

## 5. AI 如何参与

AI 不直接对原始明细自由发挥，而是位于可审计流程的最后一层：

```text
数据库最新批次
  -> 角色数据范围
  -> Python/SQL 确定性指标
  -> SPU 健康分类与问题标签
  -> 结构化 diagnosis JSON
  -> inventory_analysis_skill.md
  -> inventory_report_skill.md
  -> LLM 表达增强
  -> 必备章节校验
  -> HTML 报告
```

- **数据机制**：SQL/Python 负责事实、计算和阈值，LLM 不计算核心数字。
- **分析 Skill**：规定库存链路、诊断顺序、事实与推断边界。
- **报告 Skill**：规定 SPU 优先、图表优先、概念注释和行动导向。
- **LLM 对接**：支持 DeepSeek 等 OpenAI-compatible API；调用失败自动返回规则版报告。
- **安全边界**：LLM 不得新增输入中不存在的数字、SKU、原因或外部事实。

## 6. 技术结构

```text
ai_inventory/
├─ backend/
│  ├─ src/ai_inventory_backend/  FastAPI、数据访问、诊断与报告渲染
│  ├─ tests/                     后端接口测试
│  └─ tools/                     启动、导出、数据核对工具
├─ frontend/
│  └─ src/                       Vue 3 + TDesign 运行监控页面
├─ docs/
│  ├─ inventory_analysis_skill.md
│  └─ inventory_report_skill.md
├─ generated_reports/            本地报告，不提交 Git
├─ .env.example
└─ README.md
```

后端：Python 3.10+、FastAPI、SQLAlchemy、PostgreSQL。

前端：Vue 3、TypeScript、Vite、TDesign。

## 7. 本地启动

### 7.1 后端

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item ..\.env.example ..\.env
```

在项目根目录 `.env` 中填写数据库连接。仅看界面时可保持：

```env
AI_INVENTORY_USE_MOCK_DATA=true
AI_INVENTORY_LLM_ENABLED=false
```

启动规则版：

```powershell
.\tools\start_real_backend.ps1
```

启用 LLM：

```powershell
.\tools\start_llm_backend.ps1
```

API 地址：

- 健康检查：`http://127.0.0.1:8001/health`
- OpenAPI：`http://127.0.0.1:8001/docs`

### 7.2 前端

```powershell
cd frontend
Copy-Item .env.example .env
npm install
npm run dev
```

访问 `http://127.0.0.1:5174`。

### 7.3 测试

```powershell
cd backend
$env:PYTHONPATH = (Resolve-Path .\src)
python -m pytest tests -q

cd ..\frontend
npm run build
```

## 8. 配置说明

| 变量 | 必填 | 说明 |
| --- | --- | --- |
| `AI_INVENTORY_DATABASE_URL` | 真实数据必填 | PostgreSQL SQLAlchemy URL |
| `AI_INVENTORY_USE_MOCK_DATA` | 否 | `true` 时不连接真实数据库 |
| `AI_INVENTORY_LLM_ENABLED` | 否 | 是否启用 LLM 表达增强 |
| `AI_INVENTORY_LLM_API_KEY` | LLM 必填 | 不得提交 Git |
| `AI_INVENTORY_LLM_BASE_URL` | 否 | OpenAI-compatible API 地址 |
| `AI_INVENTORY_LLM_MODEL` | 否 | 模型名 |
| `VITE_API_BASE_URL` | 否 | 前端 API 地址 |

## 9. 下一阶段建议

建议按以下顺序推进：

1. 完成覆盖天数聚合口径校准，并补充 SPU 级基准样本测试。
2. 冻结 diagnosis JSON 契约和健康状态/问题标签定义。
3. 接入 BI 下钻链接，先做到“报告发现问题 -> 点击查看筛选后的 SPU/SKU”。
4. 建立运行、报告、收件人和点击事件持久化表。
5. 增加每周调度、幂等批次和失败重试。
6. 接入企微应用消息，完成负责人/战队经理/总监人员映射。
7. 增加鉴权、数据范围、审计和生产部署。

## 10. 最近验证

验证日期：2026-06-09。

- 后端接口测试：`7 passed`。
- Python 源码与工具编译检查：通过。
- 前端 TypeScript 检查与 Vite 生产构建：通过。
- 硬编码工作区路径扫描：未发现残留个人绝对路径。
- 常见密钥形态扫描：未发现真实密钥。
- Git 忽略验证：真实报告、Excel、截图、日志、`.env`、构建产物和依赖目录均不进入提交。
- 已知非阻塞项：TDesign 构建块约 1.3 MB，后续可通过按需加载和路由拆包优化。

## 11. AI 接手提示词

新同事可以把下面内容直接交给编码 AI：

```text
请先阅读 README.md、docs/inventory_analysis_skill.md、
docs/inventory_report_skill.md，再检查 git status 和现有测试。

这是一个独立的 Amazon AI 库存诊断项目，不依赖原 NexusBI。
当前报告 MVP 已可运行，但聚合覆盖天数、无动销 SPU 和健康分类仍需校准。
请不要直接改阈值或报告文案，先用真实 SPU 样本复现问题，并保证：
1. 日销使用预测日销；
2. 整体库存包含海外在途及可售、国内库存、采购在途、采购计划；
3. 发货判断只看海外在途及可售；
4. 报告以 SPU 为主，SKU 通过 BI 下钻；
5. 事实计算由 SQL/Python 完成，LLM 只做受约束的分析表达；
6. 不提交 .env、真实报告、数据库导出或业务截图。

完成代码后运行后端测试和前端构建，并在 README 当前进度中更新结果、
遗留问题和下一步。
```

## 12. 数据与安全

- `.env`、数据库凭据、模型密钥不得提交。
- `generated_reports/`、Excel 核对文件、业务截图不得提交。
- 数据库访问按只读账号设计。
- GitHub 仓库建议设为私有，确认脱敏后再扩大可见范围。
