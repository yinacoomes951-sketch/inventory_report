from .schemas import ExceptionRow, InventoryRun, ReportDetail, ReportRow, RunSummary


SUMMARY = RunSummary(
    latestBatch="2026-W23",
    reportCount=86,
    pushSuccessRate=96.5,
    clickRate=71.3,
    exceptionCount=3,
)

RUNS = [
    InventoryRun(
        id="run-2026-w23",
        batchKey="2026-W23",
        startedAt="2026-06-01 09:00",
        finishedAt="2026-06-01 09:18",
        status="completed",
        reportCount=86,
        pushSuccessRate=96.5,
        clickRate=71.3,
        exceptionCount=3,
    ),
    InventoryRun(
        id="run-2026-w22",
        batchKey="2026-W22",
        startedAt="2026-05-25 09:00",
        finishedAt="2026-05-25 09:14",
        status="completed",
        reportCount=82,
        pushSuccessRate=100,
        clickRate=77,
        exceptionCount=0,
    ),
    InventoryRun(
        id="run-2026-w21",
        batchKey="2026-W21",
        startedAt="2026-05-18 09:00",
        finishedAt="2026-05-18 09:22",
        status="partial_failed",
        reportCount=79,
        pushSuccessRate=88.6,
        clickRate=58.2,
        exceptionCount=8,
    ),
]

REPORTS = [
    ReportRow(
        id="report-owner-zhangsan",
        objectName="张三",
        level="运营个人",
        reportStatus="generated",
        pushStatus="success",
        clickStatus="clicked",
        clickCount=4,
        lastClickedAt="2026-06-01 10:32",
    ),
    ReportRow(
        id="report-dept-home",
        objectName="家居战队",
        level="战队/部门",
        reportStatus="generated",
        pushStatus="success",
        clickStatus="not_clicked",
        clickCount=0,
        lastClickedAt=None,
    ),
    ReportRow(
        id="report-director-a",
        objectName="运营总监A",
        level="总监范围",
        reportStatus="generated",
        pushStatus="failed",
        clickStatus="not_clicked",
        clickCount=0,
        lastClickedAt=None,
    ),
]

EXCEPTIONS = [
    ExceptionRow(
        id="ex-1",
        createdAt="2026-06-01 09:16",
        objectName="运营总监A",
        type="推送失败",
        reason="企微用户映射缺失",
        suggestion="补齐对象与企微UserID映射后重试",
    ),
    ExceptionRow(
        id="ex-2",
        createdAt="2026-06-01 09:18",
        objectName="李四",
        type="报告异常",
        reason="库存数据为空或未匹配SKU",
        suggestion="检查本周库存表insert_time批次数据",
    ),
]

REPORT_DETAIL = ReportDetail(
    id="report-owner-zhangsan",
    title="张三 / 欧洲 / 2026-W23 库存诊断报告",
    objectName="张三",
    level="运营个人",
    batchKey="2026-W23",
    riskLevel="high",
    htmlContent="""
<section class="report-html">
  <h2>核心结论</h2>
  <p>本周需要优先处理FBA可售不足与国内库龄积压并存的问题。</p>
  <h2>关键建议</h2>
  <ul>
    <li>SKU-A001可售天数低于建议可售天数，建议优先安排FBA补货。</li>
    <li>SKU-B117总库存充足但近30天销量回落，建议暂停新增备货。</li>
  </ul>
  <h2>SKU证据</h2>
  <table>
    <thead><tr><th>SKU</th><th>可售天数</th><th>建议可售天数</th><th>建议动作</th></tr></thead>
    <tbody>
      <tr><td>SKU-A001</td><td>12</td><td>35</td><td>优先发货到FBA</td></tr>
      <tr><td>SKU-B117</td><td>96</td><td>45</td><td>暂停新增备货</td></tr>
    </tbody>
  </table>
</section>
""".strip(),
)
