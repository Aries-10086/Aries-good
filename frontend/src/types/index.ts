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
