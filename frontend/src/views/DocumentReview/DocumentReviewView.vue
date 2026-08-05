<template>
  <section>
    <div class="page-heading">
      <div>
        <h2 class="page-title">文案检索</h2>
        <p class="page-description">
          上传或粘贴文案，系统将识别潜在风险并生成可读的分析报告。
        </p>
      </div>
    </div>

    <div class="review-layout">
      <section class="page-card input-panel">
        <div class="panel-heading">
          <div>
            <h3>提交待审文案</h3>
            <p>支持粘贴文本或上传 txt / md / docx，单次不超过 20,000 字</p>
          </div>
        </div>

        <el-form label-position="top" @submit.prevent="submitReview">
          <el-form-item label="文档类型">
            <el-select v-model="docType" class="full-width">
              <el-option
                v-for="option in DOC_TYPE_OPTIONS"
                :key="option.value"
                :label="option.label"
                :value="option.value"
              />
            </el-select>
          </el-form-item>

          <el-form-item label="文本内容">
            <el-input
              v-model="text"
              type="textarea"
              :rows="14"
              maxlength="20000"
              show-word-limit
              placeholder="粘贴合同条款、报告段落或口供内容..."
            />
          </el-form-item>

          <el-form-item label="或上传文件">
            <el-upload
              v-model:file-list="fileList"
              drag
              :auto-upload="false"
              accept=".txt,.md,.docx"
              :limit="1"
              @change="handleFileChange"
            >
              <strong>拖入或选择 txt / md / docx</strong>
              <p>上传后会与文本框内容二选一提交</p>
            </el-upload>
          </el-form-item>

          <el-button
            type="primary"
            size="large"
            :loading="submitting"
            :disabled="!canSubmit"
            @click="submitReview"
          >
            {{ submitting ? progressText : "开始分析" }}
          </el-button>
        </el-form>

        <el-progress
          v-if="submitting"
          class="progress-bar"
          :percentage="progress"
          :stroke-width="10"
          striped
          striped-flow
        />
      </section>

      <aside class="page-card history-panel">
        <div class="panel-heading">
          <div>
            <h3>历史记录</h3>
            <p>{{ total }} 次分析</p>
          </div>
          <el-button circle text :loading="loadingHistory" @click="loadHistory">
            ↻
          </el-button>
        </div>

        <el-skeleton v-if="loadingHistory && !history.length" :rows="4" animated />
        <div v-else-if="history.length" class="history-list">
          <button
            v-for="item in history"
            :key="item.review_id"
            class="history-item"
            type="button"
            @click="openReview(item.review_id)"
          >
            <strong>{{ docTypeLabel(item.doc_type) }}</strong>
            <span>{{ item.risk_count }} 个风险点</span>
            <small>{{ formatDate(item.created_at) }}</small>
          </button>
        </div>
        <el-empty v-else description="还没有分析记录" :image-size="72" />
      </aside>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ElMessage } from "element-plus";
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";

import {
  listDocumentReviews,
  submitDocumentReview,
  waitForDocumentReviewTask,
} from "@/api/documents";
import type { DocumentReviewDocType, DocumentReviewSummary } from "@/types";

const DOC_TYPE_OPTIONS = [
  { value: "contract", label: "合同" },
  { value: "report", label: "报告" },
  { value: "testimony", label: "口供" },
  { value: "general", label: "通用" },
] as const;

const router = useRouter();
const docType = ref<DocumentReviewDocType>("contract");
const text = ref("");
const fileList = ref<{ raw?: File }[]>([]);
const submitting = ref(false);
const progress = ref(8);
const progressText = ref("正在提交...");
const history = ref<DocumentReviewSummary[]>([]);
const total = ref(0);
const loadingHistory = ref(false);

const canSubmit = computed(
  () => Boolean(text.value.trim() || fileList.value[0]?.raw) && !submitting.value,
);

onMounted(loadHistory);

async function loadHistory() {
  loadingHistory.value = true;
  try {
    const data = await listDocumentReviews();
    history.value = data.results;
    total.value = data.count;
  } catch {
    ElMessage.error("历史记录加载失败");
  } finally {
    loadingHistory.value = false;
  }
}

function handleFileChange() {
  if (fileList.value.length > 1) {
    fileList.value = fileList.value.slice(-1);
  }
}

async function submitReview() {
  if (!canSubmit.value) return;

  submitting.value = true;
  progress.value = 12;
  progressText.value = "正在提交...";

  try {
    const task = await submitDocumentReview({
      text: text.value,
      doc_type: docType.value,
      file: fileList.value[0]?.raw ?? null,
    });
    progress.value = 28;
    progressText.value = "正在识别风险...";

    const timer = window.setInterval(() => {
      progress.value = Math.min(progress.value + 6, 92);
    }, 1200);

    try {
      await waitForDocumentReviewTask(task.task_id);
    } finally {
      window.clearInterval(timer);
    }

    progress.value = 100;
    progressText.value = "分析完成";
    ElMessage.success("分析完成");
    await loadHistory();
    router.push({ name: "document-review-detail", params: { id: task.review_id } });
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : "分析失败");
  } finally {
    submitting.value = false;
    progress.value = 8;
    progressText.value = "正在提交...";
  }
}

function openReview(reviewId: string) {
  router.push({ name: "document-review-detail", params: { id: reviewId } });
}

function docTypeLabel(value: DocumentReviewDocType) {
  return DOC_TYPE_OPTIONS.find((item) => item.value === value)?.label ?? "通用";
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}
</script>

<style scoped>
.page-heading {
  margin-bottom: 24px;
}

.review-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(280px, 0.8fr);
  gap: 20px;
  align-items: start;
}

.input-panel,
.history-panel {
  padding: 24px;
}

.panel-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.panel-heading h3 {
  margin: 0 0 6px;
  color: #1f2937;
}

.panel-heading p {
  margin: 0;
  color: #94a3b8;
  font-size: 13px;
}

.full-width {
  width: 100%;
}

.progress-bar {
  margin-top: 18px;
}

.history-list {
  display: grid;
  gap: 10px;
}

.history-item {
  display: grid;
  gap: 4px;
  width: 100%;
  padding: 14px;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  background: #fff;
  text-align: left;
  cursor: pointer;
}

.history-item:hover,
.history-item:focus-visible {
  border-color: #a5b4fc;
  outline: none;
}

.history-item strong {
  color: #1f2937;
}

.history-item span,
.history-item small {
  color: #94a3b8;
  font-size: 12px;
}

@media (max-width: 960px) {
  .review-layout {
    grid-template-columns: 1fr;
  }
}
</style>
