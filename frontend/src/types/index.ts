export type AsyncTaskStatus = "pending" | "running" | "success" | "failed" | "canceled";

export type UserInfo = {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  is_active: boolean;
  date_joined: string;
};

export type AuthTokens = {
  access: string;
  refresh: string;
};

export type LoginPayload = {
  email: string;
  password: string;
};

export type RegisterPayload = {
  email: string;
  password: string;
  first_name?: string;
  last_name?: string;
};

export type PaginatedResponse<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};

export type StyleProfileSummary = {
  profile_id: string;
  name: string;
  sample_count: number;
  description: string;
  created_at: string;
  updated_at: string;
};

export type StyleProfileDetail = StyleProfileSummary & {
  samples: string[];
  style_vector: number[];
  vector_dimension: number;
  features: Record<string, unknown>;
};

export type CreateStyleProfilePayload = {
  name: string;
  samples: string[];
  files: File[];
};

export type AsyncTask = {
  id: string;
  task_id: string;
  type: string;
  status: AsyncTaskStatus;
  result: Record<string, unknown>;
  error: string;
  created_at: string;
  updated_at: string;
};
