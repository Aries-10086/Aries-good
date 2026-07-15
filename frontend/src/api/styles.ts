import { http } from "@/api/http";
import type {
  CreateStyleProfilePayload,
  PaginatedResponse,
  StyleProfileDetail,
  StyleProfileSummary,
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
