<template>
  <section>
    <div class="page-heading">
      <div>
        <h2 class="page-title">风格档案</h2>
        <p class="page-description">保存不同写作场景的笔风，生成时随时切换。</p>
      </div>
      <el-button type="primary" @click="createVisible = true">创建风格档案</el-button>
    </div>

    <el-skeleton v-if="loading && !profiles.length" :rows="6" animated />

    <div v-else-if="profiles.length" class="profile-grid">
      <StyleProfileCard
        v-for="profile in profiles"
        :key="profile.profile_id"
        :profile="profile"
        @open="openProfile(profile.profile_id)"
      />
    </div>

    <div v-else class="empty-state">
      <div class="empty-state__mark">文</div>
      <h3>还没有风格档案</h3>
      <p>上传 3–5 篇你写过的文章，AI 将学习你的笔风</p>
      <el-button type="primary" @click="createVisible = true">上传写作样本</el-button>
    </div>

    <el-pagination
      v-if="total > pageSize"
      class="pagination"
      background
      layout="prev, pager, next"
      :current-page="page"
      :page-size="pageSize"
      :total="total"
      @current-change="loadProfiles"
    />

    <CreateProfileModal v-model="createVisible" @created="handleCreated" />
  </section>
</template>

<script setup lang="ts">
import { ElMessage } from "element-plus";
import { storeToRefs } from "pinia";
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";

import CreateProfileModal from "@/components/business/CreateProfileModal.vue";
import StyleProfileCard from "@/components/business/StyleProfileCard.vue";
import { useStylesStore } from "@/stores/styles";
import type { StyleProfileDetail } from "@/types";

const router = useRouter();
const stylesStore = useStylesStore();
const { profiles, total, page, pageSize, loading } = storeToRefs(stylesStore);
const createVisible = ref(false);

onMounted(() => loadProfiles(1));

async function loadProfiles(targetPage: number) {
  try {
    await stylesStore.fetchProfiles(targetPage);
  } catch {
    ElMessage.error("风格档案加载失败");
  }
}

function openProfile(profileId: string) {
  router.push({ name: "style-profile-detail", params: { id: profileId } });
}

function handleCreated(profile: StyleProfileDetail) {
  openProfile(profile.profile_id);
}
</script>

<style scoped>
.page-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 28px;
}

.profile-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
  gap: 18px;
}

.empty-state {
  display: grid;
  min-height: 420px;
  place-items: center;
  align-content: center;
  border: 1px dashed #c7d2fe;
  border-radius: 20px;
  background: #fff;
  text-align: center;
}

.empty-state__mark {
  display: grid;
  width: 72px;
  height: 72px;
  place-items: center;
  border-radius: 22px;
  background: #eef2ff;
  color: #4f46e5;
  font-size: 30px;
  font-weight: 700;
}

.empty-state h3 {
  margin: 18px 0 8px;
}

.empty-state p {
  margin: 0 0 22px;
  color: #6b7280;
}

.pagination {
  justify-content: center;
  margin-top: 28px;
}
</style>
