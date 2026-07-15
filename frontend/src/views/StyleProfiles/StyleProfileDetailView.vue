<template>
  <section>
    <el-button text type="primary" class="back-button" @click="$router.push('/style')">
      ← 返回风格档案
    </el-button>

    <el-skeleton v-if="loading && !currentProfile" :rows="8" animated />

    <template v-else-if="currentProfile">
      <div class="page-heading">
        <div>
          <h2 class="page-title">{{ currentProfile.name }}</h2>
          <p class="page-description">{{ currentProfile.description }}</p>
        </div>
        <el-tag type="info">{{ currentProfile.sample_count }} 篇样本</el-tag>
      </div>

      <div class="detail-grid">
        <section class="page-card">
          <h3>风格特征</h3>
          <dl class="feature-list">
            <template v-for="(value, key) in currentProfile.features" :key="key">
              <dt>{{ featureLabel(key) }}</dt>
              <dd>{{ formatFeature(value) }}</dd>
            </template>
          </dl>
        </section>

        <section class="page-card">
          <h3>样本概况</h3>
          <p>已提取 {{ currentProfile.vector_dimension }} 维风格向量。</p>
          <p>最近更新：{{ formatDate(currentProfile.updated_at) }}</p>
        </section>
      </div>
    </template>
  </section>
</template>

<script setup lang="ts">
import { ElMessage } from "element-plus";
import { storeToRefs } from "pinia";
import { onMounted } from "vue";
import { useRoute } from "vue-router";

import { useStylesStore } from "@/stores/styles";

const route = useRoute();
const stylesStore = useStylesStore();
const { currentProfile, loading } = storeToRefs(stylesStore);

onMounted(async () => {
  try {
    await stylesStore.fetchProfile(String(route.params.id));
  } catch {
    ElMessage.error("风格档案加载失败");
  }
});

function featureLabel(value: string) {
  const labels: Record<string, string> = {
    average_sentence_length: "平均句长",
    sentence_length_std: "句长波动",
    tone_particles: "语气词",
    punctuation_habits: "标点习惯",
    top_words: "高频词",
  };
  return labels[value] ?? value;
}

function formatFeature(value: unknown) {
  if (typeof value === "string" || typeof value === "number") {
    return String(value);
  }
  return JSON.stringify(value, null, 2);
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
  margin-bottom: 28px;
}

.detail-grid {
  display: grid;
  grid-template-columns: minmax(0, 2fr) minmax(260px, 1fr);
  gap: 20px;
}

.page-card h3 {
  margin-top: 0;
}

.feature-list {
  display: grid;
  grid-template-columns: minmax(120px, 180px) 1fr;
  gap: 14px 20px;
  margin: 0;
}

.feature-list dt {
  color: #6b7280;
  font-weight: 600;
}

.feature-list dd {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
}

@media (max-width: 800px) {
  .detail-grid {
    grid-template-columns: 1fr;
  }
}
</style>
