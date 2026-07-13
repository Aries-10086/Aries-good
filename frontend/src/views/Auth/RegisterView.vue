<template>
  <section class="auth-page">
    <el-card class="auth-card" shadow="never">
      <template #header>
        <div>
          <h2>注册文墨</h2>
          <p>创建账号后即可登录使用全部模块。</p>
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
            autocomplete="new-password"
            show-password
          />
        </el-form-item>
        <el-form-item label="名">
          <el-input v-model="form.first_name" autocomplete="given-name" />
        </el-form-item>
        <el-form-item label="姓">
          <el-input v-model="form.last_name" autocomplete="family-name" />
        </el-form-item>
        <el-button type="primary" native-type="submit" :loading="loading" class="auth-submit">
          注册
        </el-button>
      </el-form>

      <p class="auth-footer">
        已有账号？
        <RouterLink to="/login">去登录</RouterLink>
      </p>
    </el-card>
  </section>
</template>

<script setup lang="ts">
import { ElMessage } from "element-plus";
import { reactive } from "vue";

import { useAuth } from "@/composables/useAuth";

const { loading, register } = useAuth();

const form = reactive({
  email: "",
  password: "",
  first_name: "",
  last_name: "",
});

async function submit() {
  if (!form.email || !form.password) {
    ElMessage.warning("请输入邮箱和密码");
    return;
  }

  await register(form);
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
