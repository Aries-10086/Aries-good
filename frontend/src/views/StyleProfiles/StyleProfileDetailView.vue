<template>
  <section>
    <el-button text type="primary" class="back-button" @click="router.push('/style')">
      ← 返回风格档案
    </el-button>

    <el-skeleton v-if="loading && !profile" :rows="10" animated />

    <el-result
      v-else-if="!profile"
      icon="warning"
      title="无法加载风格档案"
      sub-title="档案可能已删除，或你没有访问权限。"
    >
      <template #extra>
        <el-button type="primary" @click="router.push('/style')">返回档案列表</el-button>
      </template>
    </el-result>

    <template v-else>
      <div class="page-heading">
        <div class="heading-copy">
          <div class="title-row">
            <h2 class="page-title">{{ profile.name }}</h2>
            <el-button text type="primary" :disabled="actionLoading" @click="editName">
              编辑名称
            </el-button>
          </div>
          <p class="page-description">{{ profile.description || "暂无风格描述" }}</p>
        </div>
        <div class="heading-actions">
          <el-button :disabled="actionLoading" @click="appendVisible = true">
            追加样本
          </el-button>
          <el-button
            type="primary"
            @click="router.push({ name: 'style-profile-write', params: { id: profileId } })"
          >
            开始写作
          </el-button>
          <el-button type="danger" plain :loading="deleting" @click="removeProfile">
            删除
          </el-button>
        </div>
      </div>

      <div class="summary-strip">
        <div>
          <strong>{{ profile.sample_count }}</strong>
          <span>篇写作样本</span>
        </div>
        <div>
          <strong>{{ profile.features.char_count ?? "—" }}</strong>
          <span>分析字符</span>
        </div>
        <div>
          <strong>{{ profile.vector_dimension }}</strong>
          <span>维风格向量</span>
        </div>
        <div>
          <strong>{{ formatDate(profile.updated_at) }}</strong>
          <span>最近更新</span>
        </div>
      </div>

      <div class="feature-grid">
        <section class="page-card word-card">
          <div class="card-heading">
            <div>
              <h3>高频词云</h3>
              <p>字体越大，词语在样本中出现越频繁</p>
            </div>
          </div>
          <div v-if="wordCloud.length" class="word-cloud">
            <span
              v-for="item in wordCloud"
              :key="item.word"
              class="word"
              :style="{ fontSize: `${item.size}px`, opacity: item.opacity }"
              :title="`${item.word}：${item.count} 次`"
            >
              {{ item.word }}
            </span>
          </div>
          <el-empty v-else description="暂无词频数据" :image-size="68" />
        </section>

        <section class="page-card">
          <div class="card-heading">
            <div>
              <h3>句长特征</h3>
              <p>样本句子的平均长度与波动幅度</p>
            </div>
          </div>
          <div class="bar-chart">
            <div v-for="metric in sentenceMetrics" :key="metric.label" class="bar-row">
              <span class="bar-label">{{ metric.label }}</span>
              <div class="bar-track">
                <div class="bar-fill" :style="{ width: `${metric.percent}%` }" />
              </div>
              <strong>{{ metric.value }}</strong>
            </div>
          </div>
          <p class="chart-note">单位：字符 / 句</p>
        </section>

        <section class="page-card tone-card">
          <div class="card-heading">
            <div>
              <h3>语气词标签</h3>
              <p>每 100 字使用频率，帮助识别表达习惯</p>
            </div>
          </div>
          <div v-if="toneParticles.length" class="tone-tags">
            <el-tag
              v-for="item in toneParticles"
              :key="item.particle"
              round
              effect="light"
              :type="item.count > 2 ? 'primary' : 'info'"
            >
              {{ item.particle }} · {{ item.per100 }}/百字
            </el-tag>
          </div>
          <el-empty v-else description="样本中未发现常见语气词" :image-size="68" />
        </section>

        <section class="page-card punctuation-card">
          <div class="card-heading">
            <div>
              <h3>标点习惯</h3>
              <p>感叹与省略表达的使用情况</p>
            </div>
          </div>
          <div class="punctuation-stats">
            <div>
              <strong>{{ punctuation.exclamation_count ?? 0 }}</strong>
              <span>感叹号</span>
            </div>
            <div>
              <strong>{{ percentage(punctuation.exclamation_ratio) }}</strong>
              <span>感叹占比</span>
            </div>
            <div>
              <strong>{{ punctuation.ellipsis_count ?? 0 }}</strong>
              <span>省略号</span>
            </div>
            <div>
              <strong>{{ percentage(punctuation.ellipsis_ratio) }}</strong>
              <span>省略占比</span>
            </div>
          </div>
        </section>
      </div>

      <section class="page-card samples-card">
        <div class="card-heading samples-heading">
          <div>
            <h3>写作样本</h3>
            <p>展开可查看用于提取风格的原文</p>
          </div>
          <el-tag type="info">{{ profile.samples.length }} 篇</el-tag>
        </div>
        <el-collapse v-model="expandedSamples">
          <el-collapse-item
            v-for="(sample, index) in profile.samples"
            :key="index"
            :name="String(index)"
          >
            <template #title>
              <div class="sample-title">
                <strong>样本 {{ index + 1 }}</strong>
                <span>{{ sample.replace(/\s/g, "").length }} 字</span>
                <span>{{ samplePreview(sample) }}</span>
              </div>
            </template>
            <div class="sample-content">{{ sample }}</div>
          </el-collapse-item>
        </el-collapse>
      </section>
    </template>

    <el-dialog
      v-model="appendVisible"
      title="追加写作样本"
      width="min(680px, 92vw)"
      :close-on-click-modal="!appending"
      @closed="resetAppendForm"
    >
      <p class="dialog-tip">可粘贴文本或上传文件，每篇样本至少 100 个非空白字符。</p>
      <div class="append-list">
        <div v-for="(_, index) in appendedSamples" :key="index" class="append-item">
          <el-input
            v-model="appendedSamples[index]"
            type="textarea"
            :rows="5"
            resize="vertical"
            :placeholder="`粘贴第 ${index + 1} 篇新样本`"
          />
          <el-button
            v-if="appendedSamples.length > 1"
            text
            type="danger"
            @click="appendedSamples.splice(index, 1)"
          >
            移除
          </el-button>
        </div>
      </div>
      <el-button text type="primary" @click="appendedSamples.push('')">+ 再添加一篇</el-button>
      <el-upload
        v-model:file-list="fileList"
        class="append-upload"
        drag
        multiple
        :auto-upload="false"
        accept=".txt,.md,.docx"
      >
        <strong>拖入或选择 txt / md / docx 文件</strong>
        <p>单个文件不超过 2MB</p>
      </el-upload>
      <template #footer>
        <el-button :disabled="appending" @click="appendVisible = false">取消</el-button>
        <el-button type="primary" :loading="appending" @click="appendSamples">
          {{ appending ? "正在重新分析…" : "追加并分析" }}
        </el-button>
      </template>
    </el-dialog>
  </section>
</template>

<script setup lang="ts">
import {
  ElMessage,
  ElMessageBox,
  type UploadUserFile,
} from "element-plus";
import { storeToRefs } from "pinia";
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import { useStylesStore } from "@/stores/styles";

const route = useRoute();
const router = useRouter();
const stylesStore = useStylesStore();
const { currentProfile, loading } = storeToRefs(stylesStore);

const profileId = String(route.params.id);
const profile = computed(() =>
  currentProfile.value?.profile_id === profileId ? currentProfile.value : null,
);
const expandedSamples = ref<string[]>([]);
const appendVisible = ref(false);
const appendedSamples = ref([""]);
const fileList = ref<UploadUserFile[]>([]);
const appending = ref(false);
const deleting = ref(false);
const actionLoading = computed(() => appending.value || deleting.value);

const wordCloud = computed(() => {
  const words = profile.value?.features.top_words ?? [];
  const highestCount = Math.max(...words.map((item) => item.count), 1);
  return words.slice(0, 30).map((item) => ({
    ...item,
    size: Math.round(14 + (item.count / highestCount) * 20),
    opacity: String(0.58 + (item.count / highestCount) * 0.42),
  }));
});

const sentenceMetrics = computed(() => {
  const average = Number(profile.value?.features.average_sentence_length ?? 0);
  const deviation = Number(profile.value?.features.sentence_length_std ?? 0);
  const maximum = Math.max(average, deviation, 1);
  return [
    {
      label: "平均句长",
      value: average.toFixed(1),
      percent: Math.max((average / maximum) * 100, average ? 4 : 0),
    },
    {
      label: "句长波动",
      value: deviation.toFixed(1),
      percent: Math.max((deviation / maximum) * 100, deviation ? 4 : 0),
    },
  ];
});

const toneParticles = computed(() =>
  Object.entries(profile.value?.features.tone_particles ?? {})
    .filter(([, data]) => data.count > 0)
    .map(([particle, data]) => ({
      particle,
      count: data.count,
      per100: data.per_100_chars,
    }))
    .sort((left, right) => right.count - left.count),
);

const punctuation = computed(
  () =>
    profile.value?.features.punctuation_habits ?? {
      total: 0,
      ellipsis_count: 0,
      ellipsis_ratio: 0,
      exclamation_count: 0,
      exclamation_ratio: 0,
    },
);

onMounted(async () => {
  try {
    await stylesStore.fetchProfile(profileId);
  } catch {
    ElMessage.error("风格档案加载失败");
  }
});

async function editName() {
  if (!profile.value) return;
  try {
    const { value } = await ElMessageBox.prompt("输入新的档案名称", "编辑名称", {
      inputValue: profile.value.name,
      inputPlaceholder: "档案名称",
      inputPattern: /\S+/,
      inputErrorMessage: "名称不能为空",
      confirmButtonText: "保存",
      cancelButtonText: "取消",
    });
    const name = value.trim();
    if (name === profile.value.name) return;
    await stylesStore.updateProfile(profileId, { name });
    ElMessage.success("档案名称已更新");
  } catch (error) {
    if (error !== "cancel" && error !== "close") {
      ElMessage.error("名称更新失败");
    }
  }
}

async function appendSamples() {
  const samples = appendedSamples.value.map((item) => item.trim()).filter(Boolean);
  const files = fileList.value.flatMap((item) => (item.raw ? [item.raw] : []));

  if (!samples.length && !files.length) {
    ElMessage.warning("请粘贴或上传至少一篇样本");
    return;
  }
  if (samples.some((sample) => sample.replace(/\s/g, "").length < 100)) {
    ElMessage.warning("每篇粘贴样本至少需要 100 个非空白字符");
    return;
  }

  appending.value = true;
  try {
    await stylesStore.updateProfile(profileId, { samples, files });
    appendVisible.value = false;
    ElMessage.success("样本已追加，风格特征已重新分析");
  } catch {
    ElMessage.error("追加失败，请检查样本格式后重试");
  } finally {
    appending.value = false;
  }
}

async function removeProfile() {
  if (!profile.value) return;
  try {
    await ElMessageBox.confirm(
      `删除“${profile.value.name}”后无法恢复，是否继续？`,
      "删除风格档案",
      {
        type: "warning",
        confirmButtonText: "确认删除",
        cancelButtonText: "取消",
      },
    );
    deleting.value = true;
    await stylesStore.deleteProfile(profileId);
    ElMessage.success("风格档案已删除");
    await router.replace("/style");
  } catch (error) {
    if (error !== "cancel" && error !== "close") {
      ElMessage.error("删除失败，请稍后重试");
    }
  } finally {
    deleting.value = false;
  }
}

function resetAppendForm() {
  appendedSamples.value = [""];
  fileList.value = [];
}

function samplePreview(sample: string) {
  const normalized = sample.replace(/\s+/g, " ").trim();
  return normalized.length > 42 ? `${normalized.slice(0, 42)}…` : normalized;
}

function percentage(value: number | undefined) {
  return `${((value ?? 0) * 100).toFixed(1)}%`;
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}
</script>

<style scoped>
.back-button {
  margin: -8px 0 18px;
}

.page-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 24px;
}

.heading-copy {
  min-width: 0;
}

.title-row,
.heading-actions,
.card-heading,
.samples-heading {
  display: flex;
  align-items: center;
}

.title-row {
  gap: 8px;
}

.title-row .page-title {
  margin-bottom: 0;
}

.heading-copy .page-description {
  max-width: 720px;
  margin-top: 10px;
}

.heading-actions {
  flex-shrink: 0;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
}

.heading-actions :deep(.el-button + .el-button) {
  margin-left: 0;
}

.summary-strip {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  margin-bottom: 20px;
  overflow: hidden;
  border: 1px solid #e5e7eb;
  border-radius: 16px;
  background: #fff;
}

.summary-strip > div {
  display: grid;
  gap: 5px;
  padding: 18px 22px;
  border-right: 1px solid #eef0f3;
}

.summary-strip > div:last-child {
  border-right: 0;
}

.summary-strip strong {
  color: #111827;
  font-size: 21px;
}

.summary-strip span,
.card-heading p,
.chart-note,
.dialog-tip {
  color: #8a94a6;
  font-size: 13px;
}

.feature-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 20px;
}

.page-card {
  min-width: 0;
}

.card-heading {
  justify-content: space-between;
  margin-bottom: 22px;
}

.card-heading h3 {
  margin: 0;
  color: #1f2937;
}

.card-heading p {
  margin: 6px 0 0;
}

.word-cloud {
  display: flex;
  min-height: 180px;
  align-content: center;
  align-items: baseline;
  justify-content: center;
  flex-wrap: wrap;
  gap: 8px 18px;
  padding: 14px;
}

.word {
  color: #4f46e5;
  font-weight: 650;
  line-height: 1.2;
  transition: transform 0.2s ease;
}

.word:nth-child(3n) {
  color: #0891b2;
}

.word:nth-child(3n + 1) {
  color: #7c3aed;
}

.word:hover {
  transform: scale(1.08);
}

.bar-chart {
  display: grid;
  gap: 24px;
  min-height: 150px;
  align-content: center;
}

.bar-row {
  display: grid;
  grid-template-columns: 80px minmax(100px, 1fr) 50px;
  align-items: center;
  gap: 14px;
}

.bar-label {
  color: #4b5563;
  font-size: 14px;
}

.bar-track {
  height: 22px;
  overflow: hidden;
  border-radius: 8px;
  background: #eef2ff;
}

.bar-fill {
  height: 100%;
  min-width: 0;
  border-radius: inherit;
  background: linear-gradient(90deg, #818cf8, #4f46e5);
}

.bar-row:nth-child(2) .bar-fill {
  background: linear-gradient(90deg, #67e8f9, #0891b2);
}

.bar-row strong {
  color: #374151;
  text-align: right;
}

.chart-note {
  margin: 4px 0 0;
  text-align: right;
}

.tone-tags {
  display: flex;
  min-height: 110px;
  align-content: center;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}

.tone-tags :deep(.el-tag) {
  padding: 16px 13px;
}

.punctuation-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  min-height: 110px;
  align-items: center;
}

.punctuation-stats > div {
  display: grid;
  gap: 7px;
  text-align: center;
}

.punctuation-stats strong {
  color: #4f46e5;
  font-size: 24px;
}

.punctuation-stats span {
  color: #6b7280;
  font-size: 13px;
}

.samples-card {
  margin-top: 20px;
}

.samples-heading {
  justify-content: space-between;
}

.sample-title {
  display: grid;
  width: calc(100% - 20px);
  grid-template-columns: 90px 70px minmax(0, 1fr);
  align-items: center;
  gap: 12px;
  padding-right: 16px;
  text-align: left;
}

.sample-title span {
  overflow: hidden;
  color: #8a94a6;
  font-size: 13px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sample-content {
  max-height: 420px;
  overflow: auto;
  padding: 18px;
  border-radius: 10px;
  background: #f8fafc;
  color: #374151;
  line-height: 1.85;
  white-space: pre-wrap;
  word-break: break-word;
}

.dialog-tip {
  margin: -6px 0 16px;
}

.append-list {
  display: grid;
  gap: 12px;
}

.append-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.append-upload {
  margin-top: 18px;
}

.append-upload p {
  margin: 6px 0 0;
  color: #9ca3af;
  font-size: 12px;
}

@media (max-width: 960px) {
  .page-heading {
    display: grid;
  }

  .heading-actions {
    justify-content: flex-start;
  }

  .summary-strip {
    grid-template-columns: repeat(2, 1fr);
  }

  .summary-strip > div:nth-child(2) {
    border-right: 0;
  }

  .summary-strip > div:nth-child(-n + 2) {
    border-bottom: 1px solid #eef0f3;
  }
}

@media (max-width: 720px) {
  .feature-grid,
  .summary-strip {
    grid-template-columns: 1fr;
  }

  .summary-strip > div {
    border-right: 0;
    border-bottom: 1px solid #eef0f3;
  }

  .summary-strip > div:last-child {
    border-bottom: 0;
  }

  .punctuation-stats {
    grid-template-columns: repeat(2, 1fr);
    gap: 24px;
  }

  .sample-title {
    grid-template-columns: 80px 1fr;
  }

  .sample-title span:last-child {
    display: none;
  }
}
</style>
