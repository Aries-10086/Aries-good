<template>
  <main v-if="isAuthLayout" class="auth-shell">
    <RouterView />
  </main>

  <el-container v-else class="app-shell">
    <el-aside class="app-sidebar" width="240px">
      <div class="brand">
        <span class="brand-mark">W</span>
        <div>
          <strong>文墨</strong>
          <small>Wenmo</small>
        </div>
      </div>

      <el-menu router :default-active="$route.path" class="nav-menu">
        <el-menu-item v-for="item in navItems" :key="item.path" :index="item.path">
          <span>{{ item.title }}</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="app-header">
        <div>
          <span class="eyebrow">AI 写作与沟通助手</span>
          <h1>{{ currentTitle }}</h1>
        </div>
        <div class="header-actions">
          <span class="user-email">{{ displayName }}</span>
          <el-button text type="primary" @click="logout">退出登录</el-button>
        </div>
      </el-header>

      <el-main class="app-main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useRoute } from "vue-router";

import { useAuth } from "@/composables/useAuth";

const route = useRoute();
const { displayName, logout } = useAuth();

const navItems = [
  { path: "/", title: "首页" },
  { path: "/style-writer", title: "风格写作" },
  { path: "/chat", title: "聊天" },
  { path: "/documents", title: "文案检索" },
  { path: "/settings", title: "设置" },
];

const currentTitle = computed(() => String(route.meta.title ?? "首页"));
const isAuthLayout = computed(() => Boolean(route.meta.authLayout));
</script>

<style scoped>
.app-shell {
  min-height: 100vh;
}

.auth-shell {
  min-height: 100vh;
  padding: 32px;
  background:
    radial-gradient(circle at top left, rgb(99 102 241 / 16%), transparent 30%),
    #f5f7fb;
}

.app-sidebar {
  border-right: 1px solid #e5e7eb;
  background: #111827;
  color: #ffffff;
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  height: 72px;
  padding: 0 20px;
}

.brand-mark {
  display: inline-grid;
  width: 40px;
  height: 40px;
  place-items: center;
  border-radius: 12px;
  background: #6366f1;
  font-weight: 800;
}

.brand strong,
.brand small {
  display: block;
}

.brand small {
  color: #9ca3af;
}

.nav-menu {
  border-right: 0;
  background: transparent;
}

.nav-menu :deep(.el-menu-item) {
  color: #d1d5db;
}

.nav-menu :deep(.el-menu-item.is-active),
.nav-menu :deep(.el-menu-item:hover) {
  background: rgb(99 102 241 / 18%);
  color: #ffffff;
}

.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 72px;
  border-bottom: 1px solid #e5e7eb;
  background: #ffffff;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.user-email {
  color: #4b5563;
  font-size: 14px;
}

.eyebrow {
  color: #6366f1;
  font-size: 13px;
  font-weight: 600;
}

.app-header h1 {
  margin: 4px 0 0;
  font-size: 22px;
}

.app-main {
  padding: 32px;
}
</style>
