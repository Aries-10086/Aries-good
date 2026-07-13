import { ElMessage } from "element-plus";
import { storeToRefs } from "pinia";
import { computed, ref } from "vue";
import { useRouter } from "vue-router";

import * as authApi from "@/api/auth";
import { useUserStore } from "@/stores/user";
import type { LoginPayload, RegisterPayload } from "@/types";

export function useAuth() {
  const router = useRouter();
  const userStore = useUserStore();
  const { userInfo, isAuthenticated } = storeToRefs(userStore);
  const loading = ref(false);
  const displayName = computed(() => {
    if (!userInfo.value) {
      return "";
    }

    return (
      [userInfo.value.first_name, userInfo.value.last_name].filter(Boolean).join(" ") ||
      userInfo.value.email
    );
  });

  async function login(payload: LoginPayload, redirect = "/") {
    loading.value = true;

    try {
      const tokens = await authApi.login(payload);
      userStore.setTokens(tokens);
      const currentUser = await authApi.me();
      userStore.setUserInfo(currentUser);
      ElMessage.success("登录成功");
      await router.push(redirect);
    } finally {
      loading.value = false;
    }
  }

  async function register(payload: RegisterPayload) {
    loading.value = true;

    try {
      await authApi.register(payload);
      ElMessage.success("注册成功，请登录");
      await router.push({ name: "login", query: { email: payload.email } });
    } finally {
      loading.value = false;
    }
  }

  async function loadMe() {
    if (!userStore.accessToken) {
      return null;
    }

    const currentUser = await authApi.me();
    userStore.setUserInfo(currentUser);
    return currentUser;
  }

  async function logout() {
    userStore.logout();
    await router.push({ name: "login" });
  }

  return {
    displayName,
    isAuthenticated,
    loading,
    login,
    logout,
    loadMe,
    register,
    userInfo,
  };
}
