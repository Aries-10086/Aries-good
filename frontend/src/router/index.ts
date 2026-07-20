import { createRouter, createWebHistory } from "vue-router";

import { useAuth } from "@/composables/useAuth";
import { useUserStore } from "@/stores/user";

const routes = [
  {
    path: "/login",
    name: "login",
    component: () => import("@/views/Auth/LoginView.vue"),
    meta: { title: "登录", public: true, authLayout: true },
  },
  {
    path: "/register",
    name: "register",
    component: () => import("@/views/Auth/RegisterView.vue"),
    meta: { title: "注册", public: true, authLayout: true },
  },
  {
    path: "/",
    name: "home",
    component: () => import("@/views/Home/HomeView.vue"),
    meta: { title: "首页" },
  },
  {
    path: "/style",
    name: "style-profiles",
    component: () => import("@/views/StyleProfiles/StyleProfilesView.vue"),
    meta: { title: "风格档案" },
  },
  {
    path: "/style/:id",
    name: "style-profile-detail",
    component: () => import("@/views/StyleProfiles/StyleProfileDetailView.vue"),
    meta: { title: "风格档案详情" },
  },
  {
    path: "/style/:id/write",
    name: "style-profile-write",
    component: () => import("@/views/StyleWriter/StyleWriterView.vue"),
    meta: { title: "风格写作" },
  },
  {
    path: "/style-writer",
    redirect: "/style",
  },
  {
    path: "/chat",
    name: "chat",
    component: () => import("@/views/ChatAssistant/ChatAssistantView.vue"),
    meta: { title: "聊天" },
  },
  {
    path: "/chat/:id",
    name: "chat-session",
    component: () => import("@/views/ChatAssistant/ChatSessionView.vue"),
    meta: { title: "聊天会话" },
  },
  {
    path: "/documents",
    name: "documents",
    component: () => import("@/views/DocumentReview/DocumentReviewView.vue"),
    meta: { title: "文案检索" },
  },
  {
    path: "/settings",
    name: "settings",
    component: () => import("@/views/Settings/SettingsView.vue"),
    meta: { title: "设置" },
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.beforeEach(async (to) => {
  const userStore = useUserStore();

  if (to.meta.public) {
    if (userStore.isAuthenticated && (to.name === "login" || to.name === "register")) {
      return { name: "home" };
    }

    return true;
  }

  if (!userStore.isAuthenticated) {
    return { name: "login", query: { redirect: to.fullPath } };
  }

  if (!userStore.userInfo) {
    try {
      const { loadMe } = useAuth();
      await loadMe();
    } catch {
      userStore.logout();
      return { name: "login", query: { redirect: to.fullPath } };
    }
  }

  return true;
});

export default router;
