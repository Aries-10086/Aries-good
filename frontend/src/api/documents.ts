import { http } from "@/api/http";
import type {
  DocumentReviewDetail,
  DocumentReviewSummary,
  DocumentReviewTaskResponse,
  PaginatedResponse,
} from "@/types";

export type DocumentReviewPayload = {
  text?: string;
  doc_type: string;
  file?: File | null;
  model_version?: string;
};

export async function submitDocumentReview(payload: DocumentReviewPayload) {
  const formData = new FormData();
  formData.append("doc_type", payload.doc_type);
  if (payload.text?.trim()) {
    formData.append("text", payload.text.trim());
  }
  if (payload.file) {
    formData.append("file", payload.file, payload.file.name);
  }
  if (payload.model_version) {
    formData.append("model_version", payload.model_version);
  }

  const { data } = await http.post<DocumentReviewTaskResponse>(
    "/documents/review",
    formData,
  );
  return data;
}

export async function getDocumentReviewTask(taskId: string) {
  const { data } = await http.get<DocumentReviewTaskResponse>(
    `/documents/review/${taskId}`,
  );
  return data;
}

export async function listDocumentReviews(page = 1, pageSize = 20) {
  const { data } = await http.get<PaginatedResponse<DocumentReviewSummary>>(
    "/documents/reviews",
    { params: { page, page_size: pageSize } },
  );
  return data;
}

export async function getDocumentReview(reviewId: string) {
  const { data } = await http.get<DocumentReviewDetail>(
    `/documents/reviews/${reviewId}`,
  );
  return data;
}

export async function waitForDocumentReviewTask(
  taskId: string,
  options?: { intervalMs?: number; timeoutMs?: number },
) {
  const intervalMs = options?.intervalMs ?? 1500;
  const timeoutMs = options?.timeoutMs ?? 120_000;
  const started = Date.now();

  while (Date.now() - started < timeoutMs) {
    const task = await getDocumentReviewTask(taskId);
    if (task.status === "success") {
      return task;
    }
    if (task.status === "failed") {
      throw new Error(task.error || "文档分析失败");
    }
    await new Promise((resolve) => window.setTimeout(resolve, intervalMs));
  }

  throw new Error("分析超时，请稍后在历史记录中查看。");
}
