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
  features: StyleFeatures;
};

export type CreateStyleProfilePayload = {
  name: string;
  samples: string[];
  files: File[];
};

export type UpdateStyleProfilePayload = {
  name?: string;
  samples?: string[];
  files?: File[];
};

export type StyleWordFeature = {
  word: string;
  count: number;
};

export type ToneParticleFeature = {
  count: number;
  per_100_chars: number;
};

export type StyleFeatures = {
  sample_count?: number;
  char_count?: number;
  top_words?: StyleWordFeature[];
  average_sentence_length?: number;
  sentence_length_std?: number;
  tone_particles?: Record<string, ToneParticleFeature>;
  punctuation_habits?: {
    total: number;
    ellipsis_count: number;
    ellipsis_ratio: number;
    exclamation_count: number;
    exclamation_ratio: number;
  };
  [key: string]: unknown;
};

export type GenerationFeedback = "" | "up" | "down";

export type GenerationQuality = {
  ai_flavor_score?: number;
  style_similarity?: number;
  accepted?: boolean;
  attempt_count?: number;
  topic?: string;
  keywords?: string[];
  ai_flavor_hits?: Array<Record<string, unknown>>;
};

export type GenerationRecord = {
  generation_id: string;
  profile_id: string;
  profile_name: string;
  result: string;
  model_name: string;
  quality: GenerationQuality;
  feedback: GenerationFeedback;
  created_at: string;
};

export type StyleGenerationPayload = {
  profile_id: string;
  topic: string;
  outline: string;
  keywords: string[];
  tone_slider: number;
};

export type ChatScene =
  | "invite_dinner"
  | "persuade_game"
  | "comfort"
  | "urge"
  | "custom";

export type ChatPersona = {
  role: string;
  relationship: string;
  tone: string[];
  strategy: string[];
  boundaries: string[];
  preferred_phrases: string[];
  avoid_phrases: string[];
  success_signal: string;
};

export type ChatMessage = {
  role: "counterpart" | "assistant";
  content: string;
  created_at: string;
  emotion?: "negative" | "neutral";
};

export type ChatSession = {
  session_id: string;
  scene: ChatScene;
  scene_label: string;
  relationship: string;
  goal: string;
  persona: ChatPersona;
  messages: ChatMessage[];
  message_count: number;
  style_profile_id: string | null;
  style_profile_name: string;
  status: "active" | "archived" | "closed";
  created_at: string;
  updated_at: string;
};

export type CreateChatSessionPayload = {
  scene: ChatScene;
  relationship: string;
  goal: string;
  style_profile_id?: string | null;
};

export type ChatSuggestionResponse = {
  suggestions: string[];
  regenerate: boolean;
};

export type ChatSocketEvent =
  | {
      event: "start";
      regenerate: boolean;
      emotion: "negative" | "neutral" | null;
    }
  | { event: "token"; text: string }
  | { event: "complete"; message: ChatMessage }
  | { event: "error"; detail: string };

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
