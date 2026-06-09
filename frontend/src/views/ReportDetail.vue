<template>
  <div class="report-detail-page">
    <t-card>
      <template #title>
        <t-space align="center">
          <t-button theme="default" variant="text" @click="router.back()">返回</t-button>
          <span>{{ report?.title || '报告详情' }}</span>
        </t-space>
      </template>

      <t-loading :loading="loading">
        <t-alert v-if="loadError" theme="error" message="API连接异常" :description="loadError" />
        <template v-if="report">
          <div class="report-meta">
            <t-tag theme="primary">{{ report.batchKey }}</t-tag>
            <t-tag>{{ report.level }}</t-tag>
            <t-tag :theme="riskTheme">{{ riskText }}</t-tag>
            <span class="muted">报告对象：{{ report.objectName }}</span>
          </div>
          <div class="html-card" v-html="report.htmlContent" />
        </template>
        <t-alert v-else theme="warning" message="报告不存在或尚未生成" />
      </t-loading>
    </t-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { fetchReportDetail } from '../api/inventory';
import type { ReportDetail } from '../types';

const props = defineProps<{ reportId: string }>();
const router = useRouter();
const loading = ref(false);
const report = ref<ReportDetail | null>(null);
const loadError = ref("");

const riskTheme = computed(() => {
  if (report.value?.riskLevel === 'high') return 'danger';
  if (report.value?.riskLevel === 'medium') return 'warning';
  return 'success';
});

const riskText = computed(() => {
  if (report.value?.riskLevel === 'high') return '高风险';
  if (report.value?.riskLevel === 'medium') return '中风险';
  return '低风险';
});

onMounted(async () => {
  loading.value = true;
  loadError.value = "";
  try {
    report.value = await fetchReportDetail(props.reportId);
  } catch (error) {
    loadError.value = error instanceof Error ? error.message : '报告接口请求失败，请检查后端服务是否可用。';
    report.value = null;
  } finally {
    loading.value = false;
  }
});
</script>
