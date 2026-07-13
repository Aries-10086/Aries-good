import axios, { type AxiosError, type InternalAxiosRequestConfig } from "axios";

import { useUserStore } from "@/stores/user";
import type { AuthTokens } from "@/types";

type RetryableRequestConfig = InternalAxiosRequestConfig & {
  _retry?: boolean;
};

export const http = axios.create({
  baseURL: "/api/v1",
  timeout: 30_000,
});

const refreshClient = axios.create({
  baseURL: "/api/v1",
  timeout: 30_000,
});

http.interceptors.request.use((config) => {
  const userStore = useUserStore();

  if (userStore.accessToken) {
    config.headers.Authorization = `Bearer ${userStore.accessToken}`;
  }

  return config;
});

http.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const userStore = useUserStore();
    const originalRequest = error.config as RetryableRequestConfig | undefined;

    if (
      error.response?.status !== 401 ||
      !originalRequest ||
      originalRequest._retry ||
      !userStore.refreshToken
    ) {
      return Promise.reject(error);
    }

    originalRequest._retry = true;

    try {
      const { data } = await refreshClient.post<Pick<AuthTokens, "access">>(
        "/auth/refresh",
        { refresh: userStore.refreshToken },
      );
      userStore.setAccessToken(data.access);
      originalRequest.headers.Authorization = `Bearer ${data.access}`;
      return http(originalRequest);
    } catch (refreshError) {
      userStore.logout();
      return Promise.reject(refreshError);
    }
  },
);
