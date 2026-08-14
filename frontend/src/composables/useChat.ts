import {
  computed,
  onScopeDispose,
  ref,
  toValue,
  watch,
  type MaybeRefOrGetter,
} from "vue";

import { createChatWebSocketTicket } from "@/api/chat";
import { useChatStore } from "@/stores/chat";
import type { ChatSocketEvent } from "@/types";

export function useChat(sessionIdSource: MaybeRefOrGetter<string>) {
  const sessionId = computed(() => toValue(sessionIdSource));
  const chatStore = useChatStore();
  const connected = ref(false);
  const connecting = ref(false);
  const generating = ref(false);
  const streamingText = ref("");
  const error = ref("");
  const latestEmotion = ref<"negative" | "neutral" | null>(null);
  let socket: WebSocket | null = null;
  let connectionPromise: Promise<void> | null = null;
  let pendingRegenerate = false;

  watch(sessionId, (next, prev) => {
    if (prev && next !== prev) {
      disconnect();
    }
  });

  async function connect() {
    if (connectionPromise) {
      return connectionPromise;
    }

    if (socket?.readyState === WebSocket.OPEN) {
      return;
    }

    connecting.value = true;
    error.value = "";
    const activeSessionId = sessionId.value;
    connectionPromise = (async () => {
      const { ticket } = await createChatWebSocketTicket(activeSessionId);
      await openSocket(activeSessionId, ticket);
    })().catch((reason: unknown) => {
      const message =
        reason instanceof Error ? reason.message : "无法连接实时对话服务";
      error.value = message;
      connecting.value = false;
      connectionPromise = null;
      throw reason instanceof Error ? reason : new Error(message);
    });

    return connectionPromise;
  }

  function openSocket(activeSessionId: string, ticket: string) {
    return new Promise<void>((resolve, reject) => {
      socket = new WebSocket(websocketUrl(activeSessionId, ticket));
      socket.onopen = () => {
        connected.value = true;
        connecting.value = false;
        connectionPromise = null;
        resolve();
      };
      socket.onmessage = (event) => {
        handleEvent(JSON.parse(String(event.data)) as ChatSocketEvent);
      };
      socket.onerror = () => {
        const reason = new Error("无法连接实时对话服务");
        error.value = reason.message;
        connecting.value = false;
        connectionPromise = null;
        reject(reason);
      };
      socket.onclose = (event) => {
        connected.value = false;
        connecting.value = false;
        connectionPromise = null;
        if (generating.value) {
          generating.value = false;
          error.value =
            event.code === 4401 ? "登录状态已失效，请重新登录" : "实时连接已中断";
        }
      };
    });
  }

  async function sendCounterpartMessage(content: string) {
    const normalized = content.trim();
    if (!normalized || generating.value) return;
    await ensureConnected();

    pendingRegenerate = false;
    streamingText.value = "";
    error.value = "";
    generating.value = true;
    chatStore.clearSuggestions();
    chatStore.appendMessage({
      role: "counterpart",
      content: normalized,
      created_at: new Date().toISOString(),
    });
    socket!.send(
      JSON.stringify({
        action: "message",
        content: normalized,
      }),
    );
  }

  async function regenerate() {
    if (generating.value) return;
    await ensureConnected();

    pendingRegenerate = true;
    streamingText.value = "";
    error.value = "";
    generating.value = true;
    socket!.send(JSON.stringify({ action: "regenerate" }));
  }

  function handleEvent(event: ChatSocketEvent) {
    if (event.event === "start") {
      generating.value = true;
      latestEmotion.value = event.emotion;
    } else if (event.event === "token") {
      streamingText.value += event.text;
    } else if (event.event === "complete") {
      if (pendingRegenerate) {
        chatStore.replaceLastAssistant(event.message);
      } else {
        chatStore.appendMessage(event.message);
      }
      streamingText.value = "";
      generating.value = false;
      pendingRegenerate = false;
    } else if (event.event === "error") {
      error.value = event.detail;
      generating.value = false;
      streamingText.value = "";
      pendingRegenerate = false;
    }
  }

  async function ensureConnected() {
    if (socket?.readyState !== WebSocket.OPEN) {
      await connect();
    }
  }

  function disconnect() {
    socket?.close(1000, "page closed");
    socket = null;
    connectionPromise = null;
    connected.value = false;
    connecting.value = false;
    generating.value = false;
    streamingText.value = "";
    pendingRegenerate = false;
  }

  onScopeDispose(disconnect);

  return {
    connected,
    connecting,
    generating,
    streamingText,
    error,
    latestEmotion,
    connect,
    disconnect,
    sendCounterpartMessage,
    regenerate,
  };
}

function websocketUrl(sessionId: string, ticket: string) {
  const configuredBase = import.meta.env.VITE_WS_BASE_URL?.replace(/\/$/, "");
  const base =
    configuredBase ||
    `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.host}`;
  return `${base}/ws/chat/${sessionId}/?ticket=${encodeURIComponent(ticket)}`;
}
