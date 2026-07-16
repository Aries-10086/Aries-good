import { http } from "@/api/http";
import type {
  CreateStyleProfilePayload,
  GenerationFeedback,
  GenerationRecord,
  PaginatedResponse,
  StyleProfileDetail,
  StyleProfileSummary,
  UpdateStyleProfilePayload,
} from "@/types";

export async function listStyleProfiles(page = 1, pageSize = 20) {
  const { data } = await http.get<PaginatedResponse<StyleProfileSummary>>(
    "/styles/profiles",
    { params: { page, page_size: pageSize } },
  );
  return data;
}

export async function getStyleProfile(profileId: string) {
  const { data } = await http.get<StyleProfileDetail>(
    `/styles/profiles/${profileId}`,
  );
  return data;
}

export async function createStyleProfile(payload: CreateStyleProfilePayload) {
  const formData = new FormData();
  formData.append("name", payload.name);
  payload.samples.forEach((sample) => formData.append("samples", sample));
  payload.files.forEach((file) => formData.append("files", file, file.name));

  const { data } = await http.post<StyleProfileDetail>(
    "/styles/profiles",
    formData,
  );
  return data;
}

export async function updateStyleProfile(
  profileId: string,
  payload: UpdateStyleProfilePayload,
) {
  const formData = new FormData();
  if (payload.name !== undefined) {
    formData.append("name", payload.name);
  }
  payload.samples?.forEach((sample) => formData.append("samples", sample));
  payload.files?.forEach((file) => formData.append("files", file, file.name));

  const { data } = await http.put<StyleProfileDetail>(
    `/styles/profiles/${profileId}`,
    formData,
  );
  return data;
}

export async function deleteStyleProfile(profileId: string) {
  await http.delete(`/styles/profiles/${profileId}`);
}

export async function listGenerationHistory(profileId: string, pageSize = 20) {
  const { data } = await http.get<PaginatedResponse<GenerationRecord>>(
    "/styles/generations",
    { params: { profile_id: profileId, page_size: pageSize } },
  );
  return data;
}

export async function submitGenerationFeedback(
  generationId: string,
  feedback: Exclude<GenerationFeedback, "">,
) {
  const { data } = await http.post<GenerationRecord>(
    `/styles/generations/${generationId}/feedback`,
    { feedback },
  );
  return data;
}
