import { ElMessage } from "element-plus";
import { storeToRefs } from "pinia";
import { computed, ref } from "vue";
import { useRouter } from "vue-router";

import * as authApi from "@/api/auth";
import { useChatStore } from "@/stores/chat";
import { useStylesStore } from "@/stores/styles";
import { useUserStore } from "@/stores/user";
import type { LoginPayload, RegisterPayload } from "@/types";
import { formatApiError } from "@/utils/apiError";

export function useAuth() {
  const router = useRouter();
  const userStore = useUserStore();
  const chatStore = useChatStore();
  const stylesStore = useStylesStore();
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
    } catch (error) {
      ElMessage.error(formatApiError(error, "登录失败，请稍后重试"));
      throw error;
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
    } catch (error) {
      ElMessage.error(formatApiError(error, "注册失败，请稍后重试"));
      throw error;
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
    chatStore.$reset();
    stylesStore.$reset();
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
