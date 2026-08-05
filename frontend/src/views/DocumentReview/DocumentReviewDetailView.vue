<template>
  <section>
    <el-button text type="primary" class="back-button" @click="router.push('/documents')">
      ← 返回文案检索
    </el-button>

    <el-skeleton v-if="loading && !review" :rows="12" animated />

    <el-result
      v-else-if="!review"
      icon="warning"
      title="无法加载分析报告"
      sub-title="记录可能已删除，或你没有访问权限。"
    >
      <template #extra>
        <el-button type="primary" @click="router.push('/documents')">返回列表</el-button>
      </template>
    </el-result>

    <template v-else>
      <div class="page-heading">
        <div>
          <h2 class="page-title">分析报告</h2>
          <p class="page-description">
            {{ docTypeLabel(review.doc_type) }} · {{ review.risks.length }} 个风险点 ·
            模型 {{ review.model_version || "baseline" }}
          </p>
        </div>
        <div class="heading-actions">
          <el-button @click="copyReport">复制报告</el-button>
          <el-button type="primary" @click="exportMarkdown">导出 Markdown</el-button>
        </div>
      </div>

      <div class="detail-layout">
        <section class="page-card report-panel">
          <div class="panel-heading">
            <div>
              <h3>自然语言报告</h3>
              <p>基于结构化风险点生成的可读解读</p>
            </div>
          </div>
          <article class="report-content">{{ review.report || "暂无报告内容。" }}</article>
        </section>

        <aside class="page-card sidebar">
          <div class="panel-heading">
            <div>
              <h3>风险列表</h3>
              <p>点击条目查看对应原文位置</p>
            </div>
          </div>

          <div v-if="review.risks.length" class="risk-list">
            <button
              v-for="(risk, index) in review.risks"
              :key="`${risk.start}-${risk.end}-${index}`"
              class="risk-item"
              :class="{ 'risk-item--active': activeRiskIndex === index }"
              type="button"
              @click="activeRiskIndex = index"
            >
              <div class="risk-item__head">
                <strong>{{ risk.type }}</strong>
                <el-tag size="small" :type="levelTagType(risk.level)" effect="plain">
                  {{ risk.level }}
                </el-tag>
              </div>
              <p>{{ risk.quote || review.raw_text.slice(risk.start, risk.end) }}</p>
              <small>{{ risk.reason }}</small>
            </button>
          </div>
          <el-empty v-else description="未检测到明确风险" :image-size="72" />
        </aside>
      </div>

      <section class="page-card source-panel">
        <div class="panel-heading">
          <div>
            <h3>原文高亮</h3>
            <p>高 / 中 / 低风险分别使用红 / 黄 / 蓝底色标记</p>
          </div>
        </div>
        <RiskHighlight :text="review.raw_text" :risks="highlightRisks" />
      </section>
    </template>
  </section>
</template>

<script setup lang="ts">
import { ElMessage } from "element-plus";
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import { getDocumentReview } from "@/api/documents";
import RiskHighlight from "@/components/business/RiskHighlight.vue";
import type { DocumentReviewDetail, DocumentReviewDocType } from "@/types";

const DOC_TYPE_LABELS: Record<DocumentReviewDocType, string> = {
  contract: "合同",
  report: "报告",
  testimony: "口供",
  general: "通用",
};

const route = useRoute();
const router = useRouter();
const review = ref<DocumentReviewDetail | null>(null);
const loading = ref(false);
const activeRiskIndex = ref(0);

const reviewId = computed(() => String(route.params.id ?? ""));

const highlightRisks = computed(() => {
  if (!review.value?.risks.length) return [];
  const active = review.value.risks[activeRiskIndex.value];
  return active ? [active] : review.value.risks;
});

watch(reviewId, loadReview, { immediate: true });

onMounted(loadReview);

async function loadReview() {
  if (!reviewId.value) return;
  loading.value = true;
  try {
    review.value = await getDocumentReview(reviewId.value);
    activeRiskIndex.value = 0;
  } catch {
    review.value = null;
    ElMessage.error("分析报告加载失败");
  } finally {
    loading.value = false;
  }
}

function docTypeLabel(value: DocumentReviewDocType) {
  return DOC_TYPE_LABELS[value] ?? "通用";
}

function levelTagType(level: string) {
  if (level === "高") return "danger";
  if (level === "低") return "info";
  return "warning";
}

async function copyReport() {
  if (!review.value?.report) return;
  await navigator.clipboard.writeText(review.value.report);
  ElMessage.success("报告已复制");
}

function exportMarkdown() {
  if (!review.value) return;
  const lines = [
    `# 文案检索报告`,
    ``,
    `- 文档类型：${docTypeLabel(review.value.doc_type)}`,
    `- 风险数量：${review.value.risks.length}`,
    `- 模型版本：${review.value.model_version || "baseline"}`,
    ``,
    review.value.report,
    ``,
    `## 风险列表`,
    ...review.value.risks.map(
      (risk, index) =>
        `${index + 1}. [${risk.level}] ${risk.type}：${risk.quote || ""}\n   建议：${risk.suggestion || ""}`,
    ),
  ];
  const blob = new Blob([lines.join("\n")], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `document-review-${review.value.review_id}.md`;
  anchor.click();
  URL.revokeObjectURL(url);
}
</script>

<style scoped>
.back-button {
  margin-bottom: 12px;
}

.page-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 20px;
}

.heading-actions {
  display: flex;
  gap: 10px;
}

.detail-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(280px, 0.8fr);
  gap: 20px;
  margin-bottom: 20px;
}

.report-panel,
.sidebar,
.source-panel {
  padding: 24px;
}

.panel-heading {
  margin-bottom: 16px;
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

.report-content {
  white-space: pre-wrap;
  line-height: 1.85;
  color: #334155;
}

.risk-list {
  display: grid;
  gap: 10px;
  max-height: 520px;
  overflow: auto;
}

.risk-item {
  display: grid;
  gap: 6px;
  width: 100%;
  padding: 14px;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  background: #fff;
  text-align: left;
  cursor: pointer;
}

.risk-item--active {
  border-color: #6366f1;
  box-shadow: 0 10px 24px rgb(99 102 241 / 10%);
}

.risk-item__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.risk-item p,
.risk-item small {
  margin: 0;
  color: #64748b;
  font-size: 12px;
  line-height: 1.6;
}

@media (max-width: 960px) {
  .page-heading,
  .detail-layout {
    grid-template-columns: 1fr;
    display: grid;
  }

  .page-heading {
    display: block;
  }

  .heading-actions {
    margin-top: 12px;
  }
}
</style>
