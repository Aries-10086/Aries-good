import { defineStore } from "pinia";

import * as chatApi from "@/api/chat";
import type {
  ChatMessage,
  ChatSession,
  CreateChatSessionPayload,
} from "@/types";

type ChatState = {
  sessions: ChatSession[];
  currentSession: ChatSession | null;
  total: number;
  loading: boolean;
  creating: boolean;
  suggestions: string[];
  suggestionsLoading: boolean;
};

export const useChatStore = defineStore("chat", {
  state: (): ChatState => ({
    sessions: [],
    currentSession: null,
    total: 0,
    loading: false,
    creating: false,
    suggestions: [],
    suggestionsLoading: false,
  }),
  actions: {
    async fetchSessions() {
      this.loading = true;
      try {
        const response = await chatApi.listChatSessions();
        this.sessions = response.results;
        this.total = response.count;
      } finally {
        this.loading = false;
      }
    },
    async createSession(payload: CreateChatSessionPayload) {
      this.creating = true;
      try {
        const session = await chatApi.createChatSession(payload);
        this.currentSession = session;
        this.sessions = [
          session,
          ...this.sessions.filter(
            (item) => item.session_id !== session.session_id,
          ),
        ];
        this.total += 1;
        return session;
      } finally {
        this.creating = false;
      }
    },
    async fetchSession(sessionId: string) {
      this.loading = true;
      try {
        this.currentSession = await chatApi.getChatSession(sessionId);
        return this.currentSession;
      } finally {
        this.loading = false;
      }
    },
    async deleteSession(sessionId: string) {
      await chatApi.deleteChatSession(sessionId);
      this.sessions = this.sessions.filter(
        (item) => item.session_id !== sessionId,
      );
      this.total = Math.max(0, this.total - 1);
      if (this.currentSession?.session_id === sessionId) {
        this.currentSession = null;
      }
    },
    appendMessage(message: ChatMessage) {
      if (!this.currentSession) return;
      this.currentSession.messages = [
        ...this.currentSession.messages,
        message,
      ];
      this.currentSession.message_count = this.currentSession.messages.length;
    },
    replaceLastAssistant(message: ChatMessage) {
      if (!this.currentSession) return;
      const messages = [...this.currentSession.messages];
      if (messages[messages.length - 1]?.role === "assistant") {
        messages[messages.length - 1] = message;
      } else {
        messages.push(message);
      }
      this.currentSession.messages = messages;
      this.currentSession.message_count = messages.length;
    },
    async fetchSuggestions(sessionId: string, regenerate = false) {
      this.suggestionsLoading = true;
      try {
        const response = await chatApi.getChatSuggestions(
          sessionId,
          regenerate,
        );
        this.suggestions = regenerate
          ? [...this.suggestions, ...response.suggestions]
          : response.suggestions;
        return response.suggestions;
      } finally {
        this.suggestionsLoading = false;
      }
    },
    clearSuggestions() {
      this.suggestions = [];
    },
  },
});
