<template>
  <section>
    <div class="writer-heading">
      <div>
        <el-button text type="primary" class="back-button" @click="router.push(`/style/${profileId}`)">
          ← 返回风格档案
        </el-button>
        <div class="title-line">
          <h2 class="page-title">风格写作</h2>
          <el-tag v-if="profile" effect="plain">{{ profile.name }}</el-tag>
        </div>
        <p class="page-description">给出内容要点，AI 将沿用这份档案的表达习惯。</p>
      </div>
      <div v-if="generating" class="generation-state">
        <span class="pulse" />
        {{ statusText }}
      </div>
    </div>

    <el-skeleton v-if="loading && !profile" :rows="10" animated />

    <el-result
      v-else-if="!profile"
      icon="warning"
      title="无法加载风格档案"
      sub-title="请返回档案列表后重试。"
    >
      <template #extra>
        <el-button type="primary" @click="router.push('/style')">返回档案列表</el-button>
      </template>
    </el-result>

    <template v-else>
      <div class="workspace">
        <section class="page-card input-panel">
          <div class="panel-heading">
            <span class="step-number">1</span>
            <div>
              <h3>告诉我写什么</h3>
              <p>信息越具体，生成内容越贴近你的预期</p>
            </div>
          </div>

          <el-form label-position="top" @submit.prevent="startGeneration">
            <el-form-item label="主题或写作任务" required>
              <el-input
                v-model="topic"
                type="textarea"
                :rows="4"
                maxlength="2000"
                show-word-limit
                placeholder="例如：写一篇邀请朋友周末来家里吃饭的微信消息"
              />
            </el-form-item>

            <el-form-item label="内容大纲">
              <el-input
                v-model="outline"
                type="textarea"
                :rows="6"
                maxlength="10000"
                show-word-limit
                placeholder="可选：列出要包含的事实、顺序或重点，每行一点"
              />
            </el-form-item>

            <el-form-item label="关键词">
              <el-input
                v-model="keywordText"
                clearable
                placeholder="可选，用逗号分隔，例如：周末，火锅，轻松"
              />
              <div v-if="keywords.length" class="keyword-preview">
                <el-tag v-for="keyword in keywords" :key="keyword" size="small" round>
                  {{ keyword }}
                </el-tag>
              </div>
            </el-form-item>

            <el-form-item>
              <template #label>
                <div class="tone-label">
                  <span>表达语气</span>
                  <strong>{{ toneDescription }}</strong>
                </div>
              </template>
              <div class="tone-control">
                <span>正式克制</span>
                <el-slider v-model="toneSlider" :show-tooltip="false" />
                <span>自然口语</span>
              </div>
            </el-form-item>

            <el-button
              class="generate-button"
              type="primary"
              size="large"
              :loading="generating"
              :disabled="!topic.trim()"
              @click="startGeneration"
            >
              {{ generating ? statusText : result ? "重新生成" : "开始生成" }}
            </el-button>
            <el-button v-if="generating" class="stop-button" text @click="cancel">
              停止生成
            </el-button>
          </el-form>
        </section>

        <section class="page-card result-panel">
          <div class="panel-heading result-heading">
            <div class="result-title">
              <span class="step-number">2</span>
              <div>
                <h3>生成结果</h3>
                <p>{{ resultMeta }}</p>
              </div>
            </div>
            <div class="result-actions">
              <el-button v-if="result" text type="primary" @click="copyResult">
                复制全文
              </el-button>
              <el-button
                v-if="result && !generating"
                text
                type="primary"
                @click="startGeneration"
              >
                重新生成
              </el-button>
            </div>
          </div>

          <div v-if="result || generating" class="result-content">
            <div class="article-text">
              {{ result }}<span v-if="generating" class="typing-cursor" />
            </div>
          </div>
          <div v-else class="result-empty">
            <div class="empty-mark">文</div>
            <h3>成稿会出现在这里</h3>
            <p>填写左侧主题，选择语气后开始生成</p>
          </div>

          <div v-if="error" class="error-message">{{ error }}</div>
          <el-alert
            v-if="result && !generating && quality.accepted === false"
            class="quality-warning"
            type="warning"
            :closable="false"
            show-icon
            title="本次结果未达到风格质量阈值"
            description="系统已完成自动优化，但最终版本仍未达标。建议调整要求后重新生成，使用前请人工确认。"
          />

          <div v-if="result && !generating" class="result-footer">
            <div class="quality-tags">
              <el-tag
                v-if="quality.style_similarity !== undefined"
                size="small"
                type="success"
                effect="plain"
              >
                风格相似度 {{ formatScore(quality.style_similarity) }}
              </el-tag>
              <el-tag
                v-if="quality.ai_flavor_score !== undefined"
                size="small"
                type="info"
                effect="plain"
              >
                AI 痕迹 {{ formatScore(quality.ai_flavor_score) }}
              </el-tag>
              <span v-if="quality.attempt_count && quality.attempt_count > 1">
                已自动优化 {{ quality.attempt_count - 1 }} 次
              </span>
            </div>
            <div v-if="generationId" class="feedback">
              <span>这次生成有帮助吗？</span>
              <el-button
                circle
                :type="currentFeedback === 'up' ? 'primary' : ''"
                :loading="feedbackLoading === 'up'"
                aria-label="有帮助"
                @click="sendFeedback('up')"
              >
                👍
              </el-button>
              <el-button
                circle
                :type="currentFeedback === 'down' ? 'danger' : ''"
                :loading="feedbackLoading === 'down'"
                aria-label="需改进"
                @click="sendFeedback('down')"
              >
                👎
              </el-button>
            </div>
          </div>
        </section>
      </div>

      <section class="page-card history-panel">
        <div class="panel-heading history-heading">
          <div>
            <h3>历史生成记录</h3>
            <p>最近 {{ history.length }} 条使用该风格档案生成的内容</p>
          </div>
          <el-button text type="primary" :loading="historyLoading" @click="loadHistory">
            刷新
          </el-button>
        </div>

        <el-skeleton v-if="historyLoading && !history.length" :rows="3" animated />
        <el-empty v-else-if="!history.length" description="还没有生成记录" :image-size="72" />
        <el-collapse v-else v-model="expandedHistory">
          <el-collapse-item
            v-for="record in history"
            :key="record.generation_id"
            :name="record.generation_id"
          >
            <template #title>
              <div class="history-title">
                <strong>{{ record.quality.topic || "未命名写作任务" }}</strong>
                <span>{{ formatDate(record.created_at) }}</span>
                <el-tag
                  v-if="record.feedback"
                  size="small"
                  :type="record.feedback === 'up' ? 'success' : 'warning'"
                  effect="plain"
                >
                  {{ record.feedback === "up" ? "👍 有帮助" : "👎 需改进" }}
                </el-tag>
              </div>
            </template>
            <div class="history-content">{{ record.result }}</div>
            <div class="history-actions">
              <el-button text type="primary" @click.stop="copyText(record.result)">
                复制
              </el-button>
              <el-button text type="primary" @click.stop="reuseRecord(record)">
                载入主题并再次生成
              </el-button>
            </div>
          </el-collapse-item>
        </el-collapse>
      </section>
    </template>
  </section>
</template>

<script setup lang="ts">
import { ElMessage } from "element-plus";
import { storeToRefs } from "pinia";
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import {
  listGenerationHistory,
  submitGenerationFeedback,
} from "@/api/styles";
import { useStreamGenerate } from "@/composables/useStreamGenerate";
import { useStylesStore } from "@/stores/styles";
import type {
  GenerationFeedback,
  GenerationRecord,
  StyleGenerationPayload,
} from "@/types";

const route = useRoute();
const router = useRouter();
const stylesStore = useStylesStore();
const { currentProfile, loading } = storeToRefs(stylesStore);
const profileId = String(route.params.id);
const profile = computed(() =>
  currentProfile.value?.profile_id === profileId ? currentProfile.value : null,
);

const topic = ref("");
const outline = ref("");
const keywordText = ref("");
const toneSlider = ref(50);
const history = ref<GenerationRecord[]>([]);
const historyLoading = ref(false);
const expandedHistory = ref<string[]>([]);
const currentFeedback = ref<GenerationFeedback>("");
const feedbackLoading = ref<GenerationFeedback>("");

const {
  result,
  generationId,
  quality,
  generating,
  attempt,
  statusText,
  error,
  generate,
  cancel,
} = useStreamGenerate();

const keywords = computed(() =>
  [...new Set(keywordText.value.split(/[,，、\n]/).map((item) => item.trim()).filter(Boolean))].slice(
    0,
    20,
  ),
);

const toneDescription = computed(() => {
  if (toneSlider.value <= 30) return "偏正式";
  if (toneSlider.value >= 70) return "偏口语";
  return "自然平衡";
});

const resultMeta = computed(() => {
  if (generating.value) {
    return attempt.value > 1 ? `第 ${attempt.value} 版优化中` : "正在流式生成";
  }
  if (result.value) return `${result.value.replace(/\s/g, "").length} 字`;
  return "等待开始";
});

onMounted(async () => {
  await Promise.allSettled([loadProfile(), loadHistory()]);
});

async function loadProfile() {
  try {
    await stylesStore.fetchProfile(profileId);
  } catch {
    ElMessage.error("风格档案加载失败");
  }
}

async function loadHistory() {
  historyLoading.value = true;
  try {
    const response = await listGenerationHistory(profileId);
    history.value = response.results;
  } catch {
    ElMessage.error("历史记录加载失败");
  } finally {
    historyLoading.value = false;
  }
}

async function startGeneration() {
  if (!topic.value.trim() || generating.value) return;
  currentFeedback.value = "";
  const payload: StyleGenerationPayload = {
    profile_id: profileId,
    topic: topic.value.trim(),
    outline: outline.value.trim(),
    keywords: keywords.value,
    tone_slider: toneSlider.value,
  };

  try {
    await generate(payload);
    await loadHistory();
  } catch {
    ElMessage.error(error.value || "生成失败，请稍后重试");
  }
}

async function sendFeedback(feedback: Exclude<GenerationFeedback, "">) {
  if (!generationId.value || feedbackLoading.value) return;
  feedbackLoading.value = feedback;
  try {
    const record = await submitGenerationFeedback(generationId.value, feedback);
    currentFeedback.value = record.feedback;
    const index = history.value.findIndex(
      (item) => item.generation_id === generationId.value,
    );
    if (index >= 0) history.value[index] = record;
    ElMessage.success("感谢反馈");
  } catch {
    ElMessage.error("反馈提交失败");
  } finally {
    feedbackLoading.value = "";
  }
}

async function copyResult() {
  await copyText(result.value);
}

async function copyText(text: string) {
  try {
    await navigator.clipboard.writeText(text);
    ElMessage.success("已复制到剪贴板");
  } catch {
    ElMessage.error("复制失败，请手动选择文本");
  }
}

function reuseRecord(record: GenerationRecord) {
  topic.value = record.quality.topic ?? "";
  keywordText.value = (record.quality.keywords ?? []).join("，");
  window.scrollTo({ top: 0, behavior: "smooth" });
  ElMessage.success("已载入历史主题，可调整后重新生成");
}

function formatScore(score: number) {
  return `${Math.round(score * 100)}%`;
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}
</script>

<style scoped>
.writer-heading,
.title-line,
.generation-state,
.panel-heading,
.result-title,
.result-actions,
.tone-label,
.tone-control,
.result-footer,
.quality-tags,
.feedback,
.history-heading,
.history-title,
.history-actions {
  display: flex;
  align-items: center;
}

.writer-heading {
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 24px;
}

.back-button {
  margin: -8px 0 12px -12px;
}

.title-line {
  gap: 12px;
}

.title-line .page-title {
  margin-bottom: 0;
}

.writer-heading .page-description {
  margin-top: 8px;
}

.generation-state {
  flex-shrink: 0;
  gap: 9px;
  padding: 9px 14px;
  border-radius: 999px;
  background: #eef2ff;
  color: #4f46e5;
  font-size: 13px;
  font-weight: 600;
}

.pulse {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #6366f1;
  box-shadow: 0 0 0 0 rgb(99 102 241 / 45%);
  animation: pulse 1.4s infinite;
}

.workspace {
  display: grid;
  grid-template-columns: minmax(320px, 0.85fr) minmax(420px, 1.4fr);
  gap: 20px;
  align-items: stretch;
}

.input-panel,
.result-panel {
  min-height: 650px;
}

.panel-heading {
  gap: 12px;
  margin-bottom: 24px;
}

.panel-heading h3,
.panel-heading p {
  margin: 0;
}

.panel-heading p {
  margin-top: 5px;
  color: #8a94a6;
  font-size: 13px;
}

.step-number {
  display: inline-grid;
  width: 32px;
  height: 32px;
  flex-shrink: 0;
  place-items: center;
  border-radius: 10px;
  background: #eef2ff;
  color: #4f46e5;
  font-weight: 700;
}

.keyword-preview {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 9px;
}

.tone-label {
  width: 100%;
  justify-content: space-between;
  gap: 12px;
}

.tone-label strong {
  color: #4f46e5;
  font-size: 13px;
}

.tone-control {
  width: 100%;
  gap: 14px;
}

.tone-control > span {
  flex-shrink: 0;
  color: #6b7280;
  font-size: 12px;
}

.tone-control :deep(.el-slider) {
  flex: 1;
}

.generate-button {
  width: 100%;
  margin-top: 8px;
}

.stop-button {
  width: 100%;
  margin: 8px 0 0;
}

.result-panel {
  display: flex;
  flex-direction: column;
}

.result-heading,
.history-heading {
  justify-content: space-between;
}

.result-title {
  gap: 12px;
}

.result-actions {
  gap: 2px;
}

.result-actions :deep(.el-button + .el-button) {
  margin-left: 0;
}

.result-content {
  flex: 1;
  overflow: hidden;
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  background: #fcfcfd;
}

.article-text {
  height: 100%;
  max-height: 580px;
  overflow: auto;
  padding: 26px 28px;
  color: #273142;
  font-size: 16px;
  line-height: 1.95;
  white-space: pre-wrap;
  word-break: break-word;
}

.typing-cursor {
  display: inline-block;
  width: 2px;
  height: 1.15em;
  margin-left: 3px;
  background: #4f46e5;
  vertical-align: -2px;
  animation: blink 0.8s step-end infinite;
}

.result-empty {
  display: grid;
  flex: 1;
  place-items: center;
  align-content: center;
  color: #8a94a6;
  text-align: center;
}

.empty-mark {
  display: grid;
  width: 68px;
  height: 68px;
  place-items: center;
  border-radius: 20px;
  background: #f1f5f9;
  color: #94a3b8;
  font-size: 28px;
  font-weight: 700;
}

.result-empty h3 {
  margin: 16px 0 6px;
  color: #475569;
}

.result-empty p {
  margin: 0;
  font-size: 13px;
}

.error-message {
  margin-top: 12px;
  padding: 10px 12px;
  border-radius: 8px;
  background: #fef2f2;
  color: #dc2626;
  font-size: 13px;
}

.quality-warning {
  margin-top: 12px;
}

.result-footer {
  justify-content: space-between;
  gap: 16px;
  margin-top: 16px;
}

.quality-tags {
  flex-wrap: wrap;
  gap: 7px;
}

.quality-tags > span {
  color: #8a94a6;
  font-size: 12px;
}

.feedback {
  flex-shrink: 0;
  gap: 8px;
}

.feedback > span {
  color: #6b7280;
  font-size: 13px;
}

.feedback :deep(.el-button + .el-button) {
  margin-left: 0;
}

.history-panel {
  margin-top: 20px;
}

.history-title {
  width: calc(100% - 20px);
  gap: 16px;
  padding-right: 14px;
  text-align: left;
}

.history-title strong {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.history-title span {
  flex-shrink: 0;
  color: #8a94a6;
  font-size: 13px;
}

.history-content {
  max-height: 320px;
  overflow: auto;
  padding: 18px;
  border-radius: 10px;
  background: #f8fafc;
  color: #374151;
  line-height: 1.8;
  white-space: pre-wrap;
}

.history-actions {
  justify-content: flex-end;
  margin-top: 8px;
}

@keyframes blink {
  50% {
    opacity: 0;
  }
}

@keyframes pulse {
  70% {
    box-shadow: 0 0 0 7px rgb(99 102 241 / 0%);
  }
  100% {
    box-shadow: 0 0 0 0 rgb(99 102 241 / 0%);
  }
}

@media (max-width: 1080px) {
  .workspace {
    grid-template-columns: 1fr;
  }

  .input-panel,
  .result-panel {
    min-height: auto;
  }

  .result-panel {
    min-height: 600px;
  }
}

@media (max-width: 720px) {
  .writer-heading,
  .result-footer {
    align-items: flex-start;
    flex-direction: column;
  }

  .generation-state {
    align-self: flex-start;
  }

  .result-heading {
    align-items: flex-start;
  }

  .result-actions {
    flex-direction: column;
    align-items: flex-end;
  }

  .article-text {
    padding: 20px;
  }

  .history-title {
    display: grid;
    grid-template-columns: 1fr auto;
    gap: 4px 12px;
  }
}
</style>
