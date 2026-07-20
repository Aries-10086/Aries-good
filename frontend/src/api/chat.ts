import { http } from "@/api/http";
import type {
  ChatSession,
  ChatSuggestionResponse,
  CreateChatSessionPayload,
  PaginatedResponse,
} from "@/types";

export async function listChatSessions(page = 1, pageSize = 30) {
  const { data } = await http.get<PaginatedResponse<ChatSession>>(
    "/chat/sessions",
    { params: { page, page_size: pageSize } },
  );
  return data;
}

export async function createChatSession(payload: CreateChatSessionPayload) {
  const { data } = await http.post<ChatSession>("/chat/sessions", payload);
  return data;
}

export async function getChatSession(sessionId: string) {
  const { data } = await http.get<ChatSession>(`/chat/sessions/${sessionId}`);
  return data;
}

export async function deleteChatSession(sessionId: string) {
  await http.delete(`/chat/sessions/${sessionId}`);
}

export async function getChatSuggestions(
  sessionId: string,
  regenerate = false,
) {
  const { data } = await http.post<ChatSuggestionResponse>(
    `/chat/sessions/${sessionId}/suggestions`,
    { regenerate },
  );
  return data;
}
