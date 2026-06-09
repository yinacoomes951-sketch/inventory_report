<template>
  <t-layout class="app-shell">
    <t-aside class="app-aside" width="220px">
      <div class="brand">AI 库存诊断</div>
      <t-menu theme="dark" :value="activePath" @change="onMenuChange">
        <t-menu-item value="/">执行监控</t-menu-item>
      </t-menu>
    </t-aside>
    <t-layout>
      <t-header class="app-header">
        <div>
          <div class="page-title">AI库存诊断执行监控</div>
          <div class="page-subtitle">极简版：历史执行记录、推送成功率、点击率和异常记录。</div>
        </div>
      </t-header>
      <t-content class="app-content">
        <router-view />
      </t-content>
    </t-layout>
  </t-layout>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';

const route = useRoute();
const router = useRouter();
const activePath = computed(() => route.path);

function onMenuChange(value: string) {
  router.push(value);
}
</script>
