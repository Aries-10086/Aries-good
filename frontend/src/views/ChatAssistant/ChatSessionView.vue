<template>
  <section class="chat-shell">
    <el-skeleton v-if="loading && !session" class="loading-card" :rows="12" animated />

    <el-result
      v-else-if="!session"
      icon="warning"
      title="无法加载会话"
      sub-title="会话可能已删除，或你没有访问权限。"
    >
      <template #extra>
        <el-button type="primary" @click="router.push('/chat')">
          返回沟通助手
        </el-button>
      </template>
    </el-result>

    <template v-else>
      <header class="chat-header">
        <el-button
          circle
          text
          aria-label="返回会话列表"
          @click="router.push('/chat')"
        >
          ←
        </el-button>
        <span class="scene-avatar">{{ scene.icon }}</span>
        <div class="header-copy">
          <strong>{{ scene.title }}</strong>
          <span>{{ session.relationship }} · {{ session.goal }}</span>
        </div>
        <div class="connection-state" :class="{ online: connected }">
          <span />
          {{ connected ? "实时连接" : connecting ? "连接中" : "未连接" }}
        </div>
        <el-popover placement="bottom-end" :width="330" trigger="click">
          <template #reference>
            <el-button text type="primary">查看人设</el-button>
          </template>
          <div class="persona-popover">
            <strong>{{ session.persona.role }}</strong>
            <p>{{ session.persona.relationship }}</p>
            <div>
              <el-tag
                v-for="tone in session.persona.tone"
                :key="tone"
                size="small"
                round
              >
                {{ tone }}
              </el-tag>
            </div>
            <ol>
              <li v-for="strategy in session.persona.strategy" :key="strategy">
                {{ strategy }}
              </li>
            </ol>
          </div>
        </el-popover>
      </header>

      <main ref="messagesContainer" class="message-area">
        <div v-if="!session.messages.length && !generating" class="conversation-empty">
          <span>💭</span>
          <h3>模拟对方说一句话</h3>
          <p>
            把对方刚刚说的内容输入下方，AI 会按照已设定的人设给出可以直接发送的回复。
          </p>
        </div>

        <div
          v-for="(message, index) in session.messages"
          :key="`${message.created_at}-${index}`"
          class="message-row"
          :class="message.role"
        >
          <span v-if="message.role === 'assistant'" class="message-avatar">AI</span>
          <div class="message-wrap">
            <span class="message-label">
              {{ message.role === "assistant" ? "建议回复" : "对方" }}
            </span>
            <div class="message-bubble">{{ message.content }}</div>
            <button
              v-if="message.role === 'assistant'"
              class="bubble-copy"
              type="button"
              @click="copyText(message.content)"
            >
              复制
            </button>
          </div>
        </div>

        <div v-if="generating" class="message-row assistant">
          <span class="message-avatar">AI</span>
          <div class="message-wrap">
            <span class="message-label">正在生成建议</span>
            <div class="message-bubble streaming">
              <template v-if="streamingText">{{ streamingText }}</template>
              <span v-else class="thinking-dots"><i /><i /><i /></span>
              <span class="typing-cursor" />
            </div>
          </div>
        </div>
      </main>

      <section v-if="suggestions.length" class="suggestions-panel">
        <div class="suggestions-heading">
          <div>
            <strong>3 条回复建议</strong>
            <span>选择最适合当前关系的一条</span>
          </div>
          <el-button text @click="chatStore.clearSuggestions()">收起</el-button>
        </div>
        <div class="suggestion-grid">
          <article
            v-for="(suggestion, index) in suggestions"
            :key="`${index}-${suggestion}`"
            class="suggestion-card"
          >
            <span>策略 {{ index + 1 }}</span>
            <p>{{ suggestion }}</p>
            <el-button text type="primary" @click="copyText(suggestion)">
              复制这条
            </el-button>
          </article>
        </div>
      </section>

      <footer class="composer">
        <div v-if="error" class="chat-error">
          {{ error }}
          <el-button v-if="!connected" text type="danger" @click="reconnect">
            重新连接
          </el-button>
        </div>
        <div class="tool-row">
          <el-button
            :loading="suggestionsLoading"
            :disabled="!hasCounterpart || generating"
            @click="generateSuggestions"
          >
            ✨ 生成 3 条建议
          </el-button>
          <el-button
            :disabled="!latestAssistant || generating"
            @click="regenerateReply"
          >
            ↻ 太 AI 了，换一条
          </el-button>
          <el-button
            :disabled="!latestAssistant"
            @click="copyText(latestAssistant?.content ?? '')"
          >
            ⧉ 复制最新回复
          </el-button>
        </div>
        <div class="input-row">
          <el-input
            v-model="counterpartInput"
            type="textarea"
            :autosize="{ minRows: 1, maxRows: 4 }"
            maxlength="2000"
            resize="none"
            placeholder="输入对方说的话…（Enter 发送，Shift + Enter 换行）"
            :disabled="generating"
            @keydown.enter.exact.prevent="sendMessage"
          />
          <el-button
            class="send-button"
            type="primary"
            :disabled="!counterpartInput.trim() || generating"
            @click="sendMessage"
          >
            {{ generating ? "生成中" : "发送" }}
          </el-button>
        </div>
        <p class="composer-tip">
          你输入的是“对方”的话，左侧 AI 气泡是建议你发送的回复。
        </p>
      </footer>
    </template>
  </section>
</template>

<script setup lang="ts">
import { ElMessage } from "element-plus";
import { storeToRefs } from "pinia";
import { computed, nextTick, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import { useChat } from "@/composables/useChat";
import { CHAT_SCENES } from "@/constants/chat";
import { useChatStore } from "@/stores/chat";

const route = useRoute();
const router = useRouter();
const chatStore = useChatStore();
const {
  currentSession,
  loading,
  suggestions,
  suggestionsLoading,
} = storeToRefs(chatStore);
const sessionId = String(route.params.id);
const counterpartInput = ref("");
const messagesContainer = ref<HTMLElement | null>(null);
const session = computed(() =>
  currentSession.value?.session_id === sessionId ? currentSession.value : null,
);
const scene = computed(
  () =>
    CHAT_SCENES.find((item) => item.value === session.value?.scene) ??
    CHAT_SCENES[4]!,
);
const latestAssistant = computed(() =>
  [...(session.value?.messages ?? [])]
    .reverse()
    .find((message) => message.role === "assistant"),
);
const hasCounterpart = computed(() =>
  session.value?.messages.some((message) => message.role === "counterpart"),
);

const {
  connected,
  connecting,
  generating,
  streamingText,
  error,
  connect,
  sendCounterpartMessage,
  regenerate,
} = useChat(sessionId);

onMounted(async () => {
  chatStore.clearSuggestions();
  try {
    await chatStore.fetchSession(sessionId);
    await connect();
    await scrollToBottom();
  } catch {
    if (!session.value) ElMessage.error("会话加载失败");
  }
});

watch(
  () => [session.value?.messages.length, streamingText.value],
  () => scrollToBottom(),
);

async function sendMessage() {
  const content = counterpartInput.value.trim();
  if (!content) return;
  counterpartInput.value = "";
  try {
    await sendCounterpartMessage(content);
  } catch {
    counterpartInput.value = content;
    ElMessage.error("实时连接不可用，请重试");
  }
}

async function regenerateReply() {
  try {
    await regenerate();
  } catch {
    ElMessage.error("重新生成失败，请检查连接");
  }
}

async function generateSuggestions() {
  try {
    await chatStore.fetchSuggestions(sessionId);
    await nextTick();
    scrollToBottom();
  } catch {
    ElMessage.error("建议生成失败，请稍后重试");
  }
}

async function reconnect() {
  try {
    await connect();
    ElMessage.success("实时连接已恢复");
  } catch {
    ElMessage.error("连接失败，请稍后重试");
  }
}

async function copyText(text: string) {
  if (!text) return;
  try {
    await navigator.clipboard.writeText(text);
    ElMessage.success("已复制到剪贴板");
  } catch {
    ElMessage.error("复制失败，请手动选择文本");
  }
}

async function scrollToBottom() {
  await nextTick();
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
  }
}
</script>

<style scoped>
.chat-shell {
  display: flex;
  height: calc(100vh - 136px);
  min-height: 620px;
  overflow: hidden;
  border: 1px solid #e5e7eb;
  border-radius: 18px;
  background: #f7f8fc;
  box-shadow: 0 16px 40px rgb(15 23 42 / 8%);
  flex-direction: column;
}

.loading-card {
  margin: 24px;
}

.chat-header {
  display: flex;
  min-height: 72px;
  align-items: center;
  gap: 12px;
  padding: 12px 18px;
  border-bottom: 1px solid #e5e7eb;
  background: #fff;
}

.scene-avatar,
.message-avatar {
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: #eef2ff;
}

.scene-avatar {
  width: 42px;
  height: 42px;
  flex: 0 0 42px;
  font-size: 21px;
}

.header-copy {
  display: grid;
  min-width: 0;
  flex: 1;
  gap: 3px;
}

.header-copy strong,
.header-copy span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.header-copy strong {
  color: #1f2937;
}

.header-copy span {
  color: #8a94a6;
  font-size: 12px;
}

.connection-state {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #9ca3af;
  font-size: 12px;
}

.connection-state > span {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #cbd5e1;
}

.connection-state.online {
  color: #059669;
}

.connection-state.online > span {
  background: #10b981;
}

.persona-popover p {
  margin: 5px 0 12px;
  color: #8a94a6;
  font-size: 13px;
}

.persona-popover div {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.persona-popover ol {
  margin: 14px 0 0;
  padding-left: 20px;
  color: #4b5563;
  font-size: 13px;
  line-height: 1.7;
}

.message-area {
  flex: 1;
  overflow-y: auto;
  padding: 26px clamp(18px, 5vw, 72px);
  scroll-behavior: smooth;
}

.conversation-empty {
  display: grid;
  height: 100%;
  place-items: center;
  align-content: center;
  text-align: center;
}

.conversation-empty > span {
  font-size: 42px;
}

.conversation-empty h3 {
  margin: 16px 0 8px;
}

.conversation-empty p {
  max-width: 420px;
  margin: 0;
  color: #8a94a6;
  font-size: 13px;
  line-height: 1.7;
}

.message-row {
  display: flex;
  max-width: 78%;
  align-items: flex-start;
  gap: 10px;
  margin-bottom: 20px;
}

.message-row.counterpart {
  margin-left: auto;
  justify-content: flex-end;
}

.message-avatar {
  width: 34px;
  height: 34px;
  flex: 0 0 34px;
  color: #4f46e5;
  font-size: 11px;
  font-weight: 800;
}

.message-wrap {
  display: grid;
  gap: 5px;
}

.counterpart .message-wrap {
  justify-items: end;
}

.message-label {
  color: #9ca3af;
  font-size: 11px;
}

.message-bubble {
  padding: 12px 16px;
  border-radius: 5px 17px 17px;
  background: #fff;
  color: #374151;
  line-height: 1.75;
  white-space: pre-wrap;
  word-break: break-word;
  box-shadow: 0 6px 18px rgb(15 23 42 / 6%);
}

.counterpart .message-bubble {
  border-radius: 17px 5px 17px 17px;
  background: #6366f1;
  color: #fff;
}

.bubble-copy {
  padding: 0;
  border: 0;
  background: transparent;
  color: #818cf8;
  cursor: pointer;
  font-size: 11px;
}

.streaming {
  min-width: 78px;
}

.typing-cursor {
  display: inline-block;
  width: 2px;
  height: 1em;
  margin-left: 3px;
  background: #6366f1;
  vertical-align: -2px;
  animation: blink 0.8s step-end infinite;
}

.thinking-dots {
  display: inline-flex;
  gap: 4px;
}

.thinking-dots i {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: #a5b4fc;
  animation: bounce 1s infinite alternate;
}

.thinking-dots i:nth-child(2) {
  animation-delay: 0.2s;
}

.thinking-dots i:nth-child(3) {
  animation-delay: 0.4s;
}

.suggestions-panel {
  padding: 14px 20px;
  border-top: 1px solid #e5e7eb;
  background: #f8fafc;
}

.suggestions-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.suggestions-heading strong,
.suggestions-heading span {
  display: block;
}

.suggestions-heading span {
  margin-top: 2px;
  color: #9ca3af;
  font-size: 11px;
}

.suggestion-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.suggestion-card {
  padding: 12px;
  border: 1px solid #e0e7ff;
  border-radius: 12px;
  background: #fff;
}

.suggestion-card > span {
  color: #6366f1;
  font-size: 11px;
  font-weight: 700;
}

.suggestion-card p {
  margin: 7px 0 4px;
  color: #4b5563;
  font-size: 12px;
  line-height: 1.6;
}

.composer {
  padding: 12px 18px 10px;
  border-top: 1px solid #e5e7eb;
  background: #fff;
}

.chat-error {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
  padding: 7px 10px;
  border-radius: 8px;
  background: #fef2f2;
  color: #dc2626;
  font-size: 12px;
}

.tool-row {
  display: flex;
  gap: 6px;
  margin-bottom: 9px;
  overflow-x: auto;
}

.tool-row :deep(.el-button + .el-button) {
  margin-left: 0;
}

.input-row {
  display: flex;
  align-items: flex-end;
  gap: 10px;
}

.input-row :deep(.el-textarea__inner) {
  min-height: 42px !important;
  border-radius: 12px;
  box-shadow: 0 0 0 1px #dbe1ea inset;
  line-height: 1.55;
}

.send-button {
  min-width: 76px;
  height: 42px;
  border-radius: 12px;
}

.composer-tip {
  margin: 7px 0 0;
  color: #a0a8b5;
  font-size: 11px;
  text-align: center;
}

@keyframes blink {
  50% {
    opacity: 0;
  }
}

@keyframes bounce {
  to {
    transform: translateY(-4px);
  }
}

@media (max-width: 760px) {
  .chat-shell {
    height: 100vh;
    min-height: 0;
    border: 0;
    border-radius: 0;
  }

  .chat-header {
    min-height: 62px;
    padding: 9px 10px;
  }

  .connection-state,
  .chat-header > :deep(.el-button:last-child) {
    display: none;
  }

  .message-area {
    padding: 18px 12px;
  }

  .message-row {
    max-width: 92%;
  }

  .suggestion-grid {
    display: flex;
    overflow-x: auto;
  }

  .suggestion-card {
    min-width: 250px;
  }

  .composer {
    padding: 9px 10px 8px;
  }

  .tool-row :deep(.el-button) {
    flex: 0 0 auto;
  }

  .composer-tip {
    display: none;
  }
}
</style>
