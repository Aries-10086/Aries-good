<template>
  <el-dialog
    :model-value="modelValue"
    :title="scene ? `新建对话 · ${scene.title}` : '新建对话'"
    width="min(620px, 92vw)"
    :close-on-click-modal="!creating"
    :close-on-press-escape="!creating"
    @close="close"
    @closed="reset"
  >
    <div v-if="scene" class="selected-scene">
      <span
        class="selected-scene__icon"
        :style="{ backgroundColor: `${scene.accent}18`, color: scene.accent }"
      >
        {{ scene.icon }}
      </span>
      <div>
        <strong>{{ scene.title }}</strong>
        <p>{{ scene.description }}</p>
      </div>
    </div>

    <el-form label-position="top" @submit.prevent="submit">
      <el-form-item label="你和对方的关系" required>
        <el-select
          v-model="relationship"
          class="full-width"
          filterable
          allow-create
          default-first-option
          placeholder="选择或输入关系"
        >
          <el-option
            v-for="option in RELATIONSHIP_OPTIONS"
            :key="option"
            :label="option"
            :value="option"
          />
        </el-select>
      </el-form-item>

      <el-form-item label="这次想达到什么目标？" required>
        <el-input
          v-model="goal"
          type="textarea"
          :rows="4"
          maxlength="255"
          show-word-limit
          placeholder="例如：邀请很久没见的朋友周六晚上一起吃火锅，语气轻松，不要让对方有压力"
        />
      </el-form-item>

      <el-form-item label="绑定风格档案（可选）">
        <el-select
          v-model="styleProfileId"
          class="full-width"
          clearable
          :loading="stylesLoading"
          placeholder="不绑定，使用默认表达风格"
        >
          <el-option
            v-for="profile in profiles"
            :key="profile.profile_id"
            :label="`${profile.name} · ${profile.sample_count} 篇样本`"
            :value="profile.profile_id"
          />
        </el-select>
        <p class="field-tip">
          绑定后，人设和后续回复会参考该档案的表达习惯。
        </p>
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button :disabled="creating" @click="close">取消</el-button>
      <el-button
        type="primary"
        :loading="creating"
        :disabled="!canSubmit"
        @click="submit"
      >
        {{ creating ? "正在生成人设…" : "创建并开始聊天" }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ElMessage } from "element-plus";
import { storeToRefs } from "pinia";
import { computed, ref, watch } from "vue";

import { RELATIONSHIP_OPTIONS, type ChatSceneOption } from "@/constants/chat";
import { useChatStore } from "@/stores/chat";
import { useStylesStore } from "@/stores/styles";
import type { ChatSession } from "@/types";

const props = defineProps<{
  modelValue: boolean;
  scene: ChatSceneOption | null;
}>();

const emit = defineEmits<{
  "update:modelValue": [value: boolean];
  created: [session: ChatSession];
}>();

const chatStore = useChatStore();
const stylesStore = useStylesStore();
const { profiles, loading: stylesLoading } = storeToRefs(stylesStore);
const { creating } = storeToRefs(chatStore);

const relationship = ref("");
const goal = ref("");
const styleProfileId = ref("");
const canSubmit = computed(
  () => Boolean(props.scene && relationship.value.trim() && goal.value.trim()),
);

watch(
  () => [props.modelValue, props.scene] as const,
  async ([visible, scene]) => {
    if (!visible || !scene) return;
    if (!goal.value && scene.prompt) goal.value = scene.prompt;
    if (!profiles.value.length) {
      try {
        await stylesStore.fetchProfiles(1);
      } catch {
        ElMessage.warning("风格档案加载失败，仍可使用默认风格创建");
      }
    }
  },
  { immediate: true },
);

function close() {
  if (!creating.value) emit("update:modelValue", false);
}

function reset() {
  relationship.value = "";
  goal.value = "";
  styleProfileId.value = "";
}

async function submit() {
  if (!props.scene || !canSubmit.value) return;
  try {
    const session = await chatStore.createSession({
      scene: props.scene.value,
      relationship: relationship.value.trim(),
      goal: goal.value.trim(),
      style_profile_id: styleProfileId.value || null,
    });
    ElMessage.success("对话已创建，人设准备完成");
    emit("created", session);
    emit("update:modelValue", false);
  } catch {
    ElMessage.error("创建失败，请检查模型服务后重试");
  }
}
</script>

<style scoped>
.selected-scene {
  display: flex;
  align-items: center;
  gap: 14px;
  margin: -4px 0 22px;
  padding: 14px;
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  background: #f8fafc;
}

.selected-scene__icon {
  display: grid;
  width: 48px;
  height: 48px;
  flex: 0 0 48px;
  place-items: center;
  border-radius: 14px;
  font-size: 24px;
}

.selected-scene strong,
.selected-scene p {
  display: block;
  margin: 0;
}

.selected-scene p,
.field-tip {
  color: #8a94a6;
  font-size: 13px;
}

.selected-scene p {
  margin-top: 4px;
}

.full-width {
  width: 100%;
}

.field-tip {
  margin: 7px 0 0;
  line-height: 1.5;
}
</style>
