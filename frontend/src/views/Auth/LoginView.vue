<template>
  <section class="auth-page">
    <el-card class="auth-card" shadow="never">
      <template #header>
        <div>
          <h2>登录文墨</h2>
          <p>继续使用风格写作、聊天和文案检索。</p>
        </div>
      </template>

      <el-form label-position="top" @submit.prevent="submit">
        <el-form-item label="邮箱">
          <el-input v-model="form.email" type="email" autocomplete="email" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input
            v-model="form.password"
            type="password"
            autocomplete="current-password"
            show-password
          />
        </el-form-item>
        <el-button type="primary" native-type="submit" :loading="loading" class="auth-submit">
          登录
        </el-button>
      </el-form>

      <p class="auth-footer">
        还没有账号？
        <RouterLink to="/register">立即注册</RouterLink>
      </p>
    </el-card>
  </section>
</template>

<script setup lang="ts">
import { ElMessage } from "element-plus";
import { reactive } from "vue";
import { useRoute } from "vue-router";

import { useAuth } from "@/composables/useAuth";

const route = useRoute();
const { loading, login } = useAuth();

const form = reactive({
  email: String(route.query.email ?? ""),
  password: "",
});

async function submit() {
  if (!form.email || !form.password) {
    ElMessage.warning("请输入邮箱和密码");
    return;
  }

  await login(form, String(route.query.redirect ?? "/"));
}
</script>

<style scoped>
.auth-page {
  display: grid;
  min-height: calc(100vh - 64px);
  place-items: center;
}

.auth-card {
  width: min(420px, 100%);
  border-radius: 18px;
}

.auth-card h2 {
  margin: 0 0 8px;
}

.auth-card p {
  margin: 0;
  color: #6b7280;
}

.auth-submit {
  width: 100%;
}

.auth-footer {
  margin-top: 20px;
  text-align: center;
}

.auth-footer a {
  color: #6366f1;
  font-weight: 600;
}
</style>
