<template>
  <article class="profile-card" tabindex="0" @click="$emit('open')" @keydown.enter="$emit('open')">
    <div class="profile-card__mark">{{ profile.name.slice(0, 1) }}</div>
    <div class="profile-card__body">
      <h3>{{ profile.name }}</h3>
      <p>{{ profile.description || "风格特征已提取，可用于定向生成。" }}</p>
      <div class="profile-card__meta">
        <span>{{ profile.sample_count }} 篇样本</span>
        <span>更新于 {{ formatDate(profile.updated_at) }}</span>
      </div>
    </div>
    <span class="profile-card__arrow">→</span>
  </article>
</template>

<script setup lang="ts">
import type { StyleProfileSummary } from "@/types";

defineProps<{
  profile: StyleProfileSummary;
}>();

defineEmits<{
  open: [];
}>();

function formatDate(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "short",
    day: "numeric",
  }).format(new Date(value));
}
</script>

<style scoped>
.profile-card {
  display: flex;
  align-items: center;
  gap: 18px;
  border: 1px solid #e5e7eb;
  border-radius: 16px;
  background: #fff;
  padding: 22px;
  cursor: pointer;
  transition:
    border-color 0.2s ease,
    transform 0.2s ease,
    box-shadow 0.2s ease;
}

.profile-card:hover,
.profile-card:focus-visible {
  border-color: #a5b4fc;
  outline: none;
  transform: translateY(-2px);
  box-shadow: 0 14px 32px rgb(15 23 42 / 8%);
}

.profile-card__mark {
  display: grid;
  flex: 0 0 48px;
  height: 48px;
  place-items: center;
  border-radius: 14px;
  background: #eef2ff;
  color: #4f46e5;
  font-size: 20px;
  font-weight: 700;
}

.profile-card__body {
  min-width: 0;
  flex: 1;
}

.profile-card h3 {
  margin: 0 0 8px;
  color: #111827;
}

.profile-card p {
  display: -webkit-box;
  overflow: hidden;
  margin: 0 0 14px;
  color: #6b7280;
  line-height: 1.6;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.profile-card__meta {
  display: flex;
  gap: 18px;
  color: #9ca3af;
  font-size: 13px;
}

.profile-card__arrow {
  color: #6366f1;
  font-size: 22px;
}
</style>
