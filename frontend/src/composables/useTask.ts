import { http } from "@/api/http";
import type { AsyncTask } from "@/types";

export async function fetchTask(taskId: string) {
  const { data } = await http.get<AsyncTask>(`/tasks/${taskId}/`);
  return data;
}
