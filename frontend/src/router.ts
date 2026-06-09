import { createRouter, createWebHistory } from 'vue-router';
import ExecutionMonitor from './views/ExecutionMonitor.vue';
import ReportDetail from './views/ReportDetail.vue';

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      component: ExecutionMonitor,
    },
    {
      path: '/reports/:reportId',
      component: ReportDetail,
      props: true,
    },
  ],
});
