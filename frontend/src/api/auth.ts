import { http } from "@/api/http";
import type { AuthTokens, LoginPayload, RegisterPayload, UserInfo } from "@/types";

export async function register(payload: RegisterPayload) {
  const { data } = await http.post<UserInfo>("/auth/register", payload);
  return data;
}

export async function login(payload: LoginPayload) {
  const { data } = await http.post<AuthTokens>("/auth/login", payload);
  return data;
}

export async function refresh(refreshToken: string) {
  const { data } = await http.post<Pick<AuthTokens, "access">>("/auth/refresh", {
    refresh: refreshToken,
  });
  return data;
}

export async function me() {
  const { data } = await http.get<UserInfo>("/auth/me");
  return data;
}
