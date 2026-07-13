import { defineStore } from "pinia";

import type { AuthTokens, UserInfo } from "@/types";

const ACCESS_TOKEN_KEY = "wenmo.access_token";
const REFRESH_TOKEN_KEY = "wenmo.refresh_token";
const USER_INFO_KEY = "wenmo.user_info";

type UserState = {
  accessToken: string;
  refreshToken: string;
  userInfo: UserInfo | null;
};

export const useUserStore = defineStore("user", {
  state: (): UserState => ({
    accessToken: localStorage.getItem(ACCESS_TOKEN_KEY) ?? "",
    refreshToken: localStorage.getItem(REFRESH_TOKEN_KEY) ?? "",
    userInfo: readStoredUserInfo(),
  }),
  getters: {
    isAuthenticated: (state) => Boolean(state.accessToken && state.refreshToken),
    email: (state) => state.userInfo?.email ?? "",
  },
  actions: {
    setTokens(tokens: AuthTokens) {
      this.accessToken = tokens.access;
      this.refreshToken = tokens.refresh;
      localStorage.setItem(ACCESS_TOKEN_KEY, tokens.access);
      localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh);
    },
    setAccessToken(accessToken: string) {
      this.accessToken = accessToken;
      localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
    },
    setUserInfo(userInfo: UserInfo) {
      this.userInfo = userInfo;
      localStorage.setItem(USER_INFO_KEY, JSON.stringify(userInfo));
    },
    logout() {
      this.accessToken = "";
      this.refreshToken = "";
      this.userInfo = null;
      localStorage.removeItem(ACCESS_TOKEN_KEY);
      localStorage.removeItem(REFRESH_TOKEN_KEY);
      localStorage.removeItem(USER_INFO_KEY);
    },
  },
});

function readStoredUserInfo() {
  const raw = localStorage.getItem(USER_INFO_KEY);

  if (!raw) {
    return null;
  }

  try {
    return JSON.parse(raw) as UserInfo;
  } catch {
    localStorage.removeItem(USER_INFO_KEY);
    return null;
  }
}
