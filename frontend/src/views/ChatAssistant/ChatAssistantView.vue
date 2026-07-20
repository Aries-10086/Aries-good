<template>
  <section>
    <div class="page-heading">
      <div>
        <h2 class="page-title">沟通助手</h2>
        <p class="page-description">
          选择一个沟通场景，告诉我你们的关系和目标，获得更自然的回复建议。
        </p>
      </div>
    </div>

    <div class="chat-entry-layout">
      <aside class="page-card history-sidebar">
        <div class="sidebar-heading">
          <div>
            <h3>历史会话</h3>
            <span>{{ total }} 个会话</span>
          </div>
          <el-button
            circle
            text
            :loading="loading"
            aria-label="刷新会话"
            @click="loadSessions"
          >
            ↻
          </el-button>
        </div>

        <el-skeleton v-if="loading && !sessions.length" :rows="5" animated />
        <div v-else-if="sessions.length" class="session-list">
          <button
            v-for="session in sessions"
            :key="session.session_id"
            class="session-item"
            type="button"
            @click="openSession(session.session_id)"
          >
            <span class="session-item__icon">
              {{ sceneFor(session.scene).icon }}
            </span>
            <span class="session-item__body">
              <strong>{{ session.goal }}</strong>
              <span>
                {{ session.relationship }} · {{ sceneFor(session.scene).title }}
              </span>
              <small>{{ relativeDate(session.updated_at) }}</small>
            </span>
            <span class="session-item__arrow">›</span>
          </button>
        </div>
        <div v-else class="history-empty">
          <span>💬</span>
          <strong>还没有历史会话</strong>
          <p>从右侧选择场景，开始第一次沟通演练。</p>
        </div>
      </aside>

      <main class="scene-section">
        <div class="section-heading">
          <div>
            <span class="eyebrow">选择场景</span>
            <h3>今天想解决什么沟通问题？</h3>
          </div>
          <p>每个场景都会生成匹配关系距离和目标的人设卡片。</p>
        </div>

        <div class="scene-grid">
          <button
            v-for="scene in CHAT_SCENES"
            :key="scene.value"
            class="scene-card"
            :class="{ 'scene-card--custom': scene.value === 'custom' }"
            type="button"
            @click="selectScene(scene)"
          >
            <span
              class="scene-card__icon"
              :style="{
                backgroundColor: `${scene.accent}16`,
                color: scene.accent,
              }"
            >
              {{ scene.icon }}
            </span>
            <span class="scene-card__copy">
              <strong>{{ scene.title }}</strong>
              <span>{{ scene.description }}</span>
            </span>
            <span class="scene-card__arrow">→</span>
          </button>
        </div>

        <div class="privacy-note">
          <span>🔒</span>
          <p>
            对话内容仅用于生成本次建议。请避免输入身份证号、住址等敏感信息。
          </p>
        </div>
      </main>
    </div>

    <CreateChatSessionModal
      v-model="createVisible"
      :scene="selectedScene"
      @created="handleCreated"
    />
  </section>
</template>

<script setup lang="ts">
import { ElMessage } from "element-plus";
import { storeToRefs } from "pinia";
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";

import CreateChatSessionModal from "@/components/business/CreateChatSessionModal.vue";
import {
  CHAT_SCENES,
  type ChatSceneOption,
} from "@/constants/chat";
import { useChatStore } from "@/stores/chat";
import type { ChatScene, ChatSession } from "@/types";

const router = useRouter();
const chatStore = useChatStore();
const { sessions, total, loading } = storeToRefs(chatStore);
const createVisible = ref(false);
const selectedScene = ref<ChatSceneOption | null>(null);

onMounted(loadSessions);

async function loadSessions() {
  try {
    await chatStore.fetchSessions();
  } catch {
    ElMessage.error("历史会话加载失败");
  }
}

function selectScene(scene: ChatSceneOption) {
  selectedScene.value = scene;
  createVisible.value = true;
}

function sceneFor(scene: ChatScene): ChatSceneOption {
  return CHAT_SCENES.find((item) => item.value === scene) ?? CHAT_SCENES[4]!;
}

function openSession(sessionId: string) {
  router.push({ name: "chat-session", params: { id: sessionId } });
}

function handleCreated(session: ChatSession) {
  openSession(session.session_id);
}

function relativeDate(value: string) {
  const date = new Date(value);
  const diff = Date.now() - date.getTime();
  const minutes = Math.floor(diff / 60_000);
  if (minutes < 1) return "刚刚";
  if (minutes < 60) return `${minutes} 分钟前`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} 小时前`;
  return new Intl.DateTimeFormat("zh-CN", {
    month: "short",
    day: "numeric",
  }).format(date);
}
</script>

<style scoped>
.page-heading {
  margin-bottom: 26px;
}

.chat-entry-layout {
  display: grid;
  grid-template-columns: minmax(260px, 320px) minmax(0, 1fr);
  gap: 22px;
  align-items: start;
}

.history-sidebar {
  position: sticky;
  top: 24px;
  padding: 20px;
}

.sidebar-heading,
.section-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
}

.sidebar-heading {
  align-items: center;
  margin-bottom: 16px;
}

.sidebar-heading h3,
.section-heading h3 {
  margin: 0;
  color: #1f2937;
}

.sidebar-heading span {
  display: block;
  margin-top: 4px;
  color: #9ca3af;
  font-size: 12px;
}

.session-list {
  display: grid;
  gap: 7px;
  max-height: calc(100vh - 250px);
  overflow: auto;
}

.session-item {
  display: flex;
  width: 100%;
  align-items: center;
  gap: 10px;
  padding: 12px 10px;
  border: 0;
  border-radius: 12px;
  background: transparent;
  color: inherit;
  cursor: pointer;
  text-align: left;
  transition: background 0.18s ease;
}

.session-item:hover,
.session-item:focus-visible {
  outline: none;
  background: #f3f4f6;
}

.session-item__icon {
  display: grid;
  width: 36px;
  height: 36px;
  flex: 0 0 36px;
  place-items: center;
  border-radius: 10px;
  background: #f1f5f9;
}

.session-item__body {
  display: grid;
  min-width: 0;
  flex: 1;
  gap: 3px;
}

.session-item__body strong,
.session-item__body span,
.session-item__body small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.session-item__body strong {
  color: #374151;
  font-size: 13px;
}

.session-item__body span,
.session-item__body small {
  color: #9ca3af;
  font-size: 11px;
}

.session-item__arrow {
  color: #a5b4fc;
  font-size: 20px;
}

.history-empty {
  display: grid;
  min-height: 260px;
  place-items: center;
  align-content: center;
  text-align: center;
}

.history-empty > span {
  font-size: 30px;
}

.history-empty strong {
  margin-top: 12px;
  color: #4b5563;
}

.history-empty p {
  margin: 7px 12px 0;
  color: #9ca3af;
  font-size: 12px;
  line-height: 1.6;
}

.scene-section {
  min-width: 0;
}

.section-heading {
  margin-bottom: 20px;
}

.section-heading h3 {
  margin-top: 6px;
  font-size: 22px;
}

.section-heading > p {
  max-width: 300px;
  margin: 2px 0 0;
  color: #8a94a6;
  font-size: 13px;
  line-height: 1.6;
  text-align: right;
}

.eyebrow {
  color: #6366f1;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.scene-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.scene-card {
  display: flex;
  min-height: 138px;
  align-items: flex-start;
  gap: 16px;
  padding: 24px;
  border: 1px solid #e5e7eb;
  border-radius: 18px;
  background: #fff;
  color: inherit;
  cursor: pointer;
  text-align: left;
  transition:
    border-color 0.2s ease,
    box-shadow 0.2s ease,
    transform 0.2s ease;
}

.scene-card:hover,
.scene-card:focus-visible {
  border-color: #a5b4fc;
  outline: none;
  box-shadow: 0 14px 34px rgb(15 23 42 / 9%);
  transform: translateY(-2px);
}

.scene-card--custom {
  grid-column: 1 / -1;
  min-height: 112px;
  border-style: dashed;
  background:
    linear-gradient(100deg, rgb(238 242 255 / 70%), transparent 60%),
    #fff;
}

.scene-card__icon {
  display: grid;
  width: 52px;
  height: 52px;
  flex: 0 0 52px;
  place-items: center;
  border-radius: 15px;
  font-size: 25px;
}

.scene-card__copy {
  display: grid;
  min-width: 0;
  flex: 1;
  gap: 8px;
}

.scene-card__copy strong {
  color: #1f2937;
  font-size: 17px;
}

.scene-card__copy span {
  color: #6b7280;
  font-size: 13px;
  line-height: 1.65;
}

.scene-card__arrow {
  align-self: center;
  color: #a5b4fc;
  font-size: 21px;
}

.privacy-note {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 18px;
  padding: 12px 16px;
  border-radius: 12px;
  background: #f8fafc;
  color: #8491a3;
  font-size: 12px;
}

.privacy-note p {
  margin: 0;
}

@media (max-width: 980px) {
  .chat-entry-layout {
    grid-template-columns: 1fr;
  }

  .history-sidebar {
    position: static;
  }

  .session-list {
    max-height: 280px;
  }
}

@media (max-width: 680px) {
  .section-heading {
    display: block;
  }

  .section-heading > p {
    margin-top: 8px;
    text-align: left;
  }

  .scene-grid {
    grid-template-columns: 1fr;
  }

  .scene-card--custom {
    grid-column: auto;
  }
}
</style>
