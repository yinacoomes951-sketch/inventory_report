<template>
  <div class="monitor-page">
    <t-alert
      class="scope-alert"
      theme="info"
      message="MVP1提示"
      description="推送成功率和点击率当前允许由预留/模拟状态承接；真实企微推送与点击追踪进入MVP2。"
    />
    <t-alert
      v-if="loadError"
      class="scope-alert"
      theme="error"
      message="API连接异常"
      :description="loadError"
    />

    <div class="metric-grid">
      <t-card v-for="item in metrics" :key="item.label" class="metric-card" :bordered="false">
        <div class="metric-label">{{ item.label }}</div>
        <div class="metric-value" :class="item.className">{{ item.value }}</div>
      </t-card>
    </div>

    <t-card title="历史执行记录" class="section-card">
      <template #actions>
        <t-space>
          <t-tag>最近8周</t-tag>
          <t-tag>只读</t-tag>
        </t-space>
      </template>
      <t-table
        row-key="id"
        :columns="runColumns"
        :data="runs"
        :loading="loading"
        empty="暂无执行记录"
        size="small"
        bordered
      />
    </t-card>

    <t-card title="本周对象明细" class="section-card">
      <t-table
        row-key="id"
        :columns="reportColumns"
        :data="reports"
        :loading="loading"
        empty="暂无对象明细"
        size="small"
        bordered
      />
    </t-card>

    <t-card title="异常记录" class="section-card">
      <t-table
        row-key="id"
        :columns="exceptionColumns"
        :data="exceptions"
        :loading="loading"
        empty="暂无异常记录"
        size="small"
        bordered
      />
    </t-card>
  </div>
</template>

<script setup lang="ts">
import { computed, h, onMounted, ref, resolveComponent } from 'vue';
import { useRouter } from 'vue-router';
import { fetchExceptions, fetchLatestSummary, fetchReports, fetchRuns } from '../api/inventory';
import type { ExceptionRow, InventoryRun, ReportRow, RunSummary } from '../types';

const router = useRouter();
const loading = ref(false);
const summary = ref<RunSummary | null>(null);
const runs = ref<InventoryRun[]>([]);
const reports = ref<ReportRow[]>([]);
const exceptions = ref<ExceptionRow[]>([]);
const loadError = ref("");

const metrics = computed(() => [
  { label: '最近执行', value: summary.value?.latestBatch ?? '-', className: '' },
  { label: '生成报告', value: summary.value?.reportCount ?? '-', className: '' },
  { label: '推送成功率', value: formatPercent(summary.value?.pushSuccessRate), className: 'success' },
  { label: '点击率', value: formatPercent(summary.value?.clickRate), className: 'primary' },
  { label: '异常数', value: summary.value?.exceptionCount ?? '-', className: 'warning' },
]);

const runColumns = [
  { colKey: 'batchKey', title: '批次', width: 110 },
  { colKey: 'startedAt', title: '开始时间', width: 160 },
  { colKey: 'finishedAt', title: '完成时间', width: 160 },
  {
    colKey: 'status',
    title: '状态',
    cell: (_: unknown, { row }: { row: InventoryRun }) => renderRunStatus(row.status),
    width: 110,
  },
  { colKey: 'reportCount', title: '报告数', width: 90 },
  {
    colKey: 'pushSuccessRate',
    title: '推送成功率',
    cell: (_: unknown, { row }: { row: InventoryRun }) => renderRate(row.pushSuccessRate),
    width: 160,
  },
  {
    colKey: 'clickRate',
    title: '点击率',
    cell: (_: unknown, { row }: { row: InventoryRun }) => renderRate(row.clickRate),
    width: 160,
  },
  { colKey: 'exceptionCount', title: '异常', width: 90 },
];

const reportColumns = [
  { colKey: 'objectName', title: '对象', width: 130 },
  { colKey: 'level', title: '层级', width: 110 },
  {
    colKey: 'reportStatus',
    title: '报告状态',
    cell: (_: unknown, { row }: { row: ReportRow }) => renderReportStatus(row.reportStatus),
    width: 110,
  },
  {
    colKey: 'pushStatus',
    title: '推送状态',
    cell: (_: unknown, { row }: { row: ReportRow }) => renderPushStatus(row.pushStatus),
    width: 110,
  },
  {
    colKey: 'clickStatus',
    title: '点击状态',
    cell: (_: unknown, { row }: { row: ReportRow }) => renderClickStatus(row.clickStatus),
    width: 110,
  },
  { colKey: 'clickCount', title: '点击次数', width: 90 },
  {
    colKey: 'lastClickedAt',
    title: '最近点击',
    cell: (_: unknown, { row }: { row: ReportRow }) => row.lastClickedAt || '-',
    width: 160,
  },
  {
    colKey: 'action',
    title: '报告',
    cell: (_: unknown, { row }: { row: ReportRow }) =>
      h(
        resolveComponent('t-button'),
        {
          theme: 'primary',
          variant: 'text',
          onClick: () => router.push(`/reports/${row.id}`),
        },
        () => '打开',
      ),
    width: 90,
  },
];

const exceptionColumns = [
  { colKey: 'createdAt', title: '时间', width: 160 },
  { colKey: 'objectName', title: '对象', width: 130 },
  { colKey: 'type', title: '类型', width: 120 },
  { colKey: 'reason', title: '原因' },
  { colKey: 'suggestion', title: '处理建议' },
];

onMounted(async () => {
  loading.value = true;
  loadError.value = "";
  try {
    const [summaryData, runData] = await Promise.all([fetchLatestSummary(), fetchRuns()]);
    summary.value = summaryData;
    runs.value = runData;
    const currentRunId = runData[0]?.id ?? 'latest';
    const [reportData, exceptionData] = await Promise.all([
      fetchReports(currentRunId),
      fetchExceptions(currentRunId),
    ]);
    reports.value = reportData;
    exceptions.value = exceptionData;
  } catch (error) {
    loadError.value = error instanceof Error ? error.message : '接口请求失败，请检查后端服务是否可用。';
    summary.value = null;
    runs.value = [];
    reports.value = [];
    exceptions.value = [];
  } finally {
    loading.value = false;
  }
});

function formatPercent(value?: number) {
  return typeof value === 'number' ? `${value.toFixed(1)}%` : '-';
}

function renderRate(value: number) {
  const theme = value >= 95 ? 'success' : value >= 70 ? 'warning' : 'danger';
  return h(
    'div',
    { class: 'rate-cell' },
    [
      h(resolveComponent('t-progress'), { percentage: value, theme: 'line', color: theme }),
      h('span', formatPercent(value)),
    ],
  );
}

function renderRunStatus(status: InventoryRun['status']) {
  const map = {
    completed: ['success', '已完成'],
    partial_failed: ['warning', '部分失败'],
    failed: ['danger', '失败'],
    running: ['primary', '执行中'],
  } as const;
  const [theme, text] = map[status];
  return h(resolveComponent('t-tag'), { theme }, () => text);
}

function renderReportStatus(status: ReportRow['reportStatus']) {
  const map = {
    generated: ['success', '已生成'],
    failed: ['danger', '失败'],
    data_insufficient: ['warning', '数据不足'],
  } as const;
  const [theme, text] = map[status];
  return h(resolveComponent('t-tag'), { theme }, () => text);
}

function renderPushStatus(status: ReportRow['pushStatus']) {
  const map = {
    not_integrated: ['default', '未集成'],
    pending: ['primary', '待推送'],
    success: ['success', '已推送'],
    failed: ['danger', '推送失败'],
  } as const;
  const [theme, text] = map[status];
  return h(resolveComponent('t-tag'), { theme }, () => text);
}

function renderClickStatus(status: ReportRow['clickStatus']) {
  const map = {
    not_tracked: ['default', '未追踪'],
    not_clicked: ['warning', '未点击'],
    clicked: ['success', '已点击'],
  } as const;
  const [theme, text] = map[status];
  return h(resolveComponent('t-tag'), { theme }, () => text);
}
</script>
