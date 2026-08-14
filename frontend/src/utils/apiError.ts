import axios from "axios";

export function formatApiError(error: unknown, fallback: string): string {
  if (!axios.isAxiosError(error)) {
    return fallback;
  }

  if (!error.response) {
    return "网络连接失败，请稍后重试";
  }

  const detail = error.response.data?.detail;
  if (typeof detail === "string" && detail.trim()) {
    return detail;
  }

  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0];
    if (typeof first === "string") {
      return first;
    }
  }

  if (error.response.status === 401) {
    return "邮箱或密码错误";
  }

  return fallback;
}
