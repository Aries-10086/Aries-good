<template>
  <el-dialog
    :model-value="modelValue"
    title="创建风格档案"
    width="min(680px, 92vw)"
    :close-on-click-modal="!creating"
    :close-on-press-escape="!creating"
    @close="close"
    @closed="reset"
  >
    <el-form label-position="top" @submit.prevent="submit">
      <el-form-item label="档案名称">
        <el-input
          v-model="name"
          maxlength="120"
          show-word-limit
          placeholder="例如：我的公众号文风"
        />
      </el-form-item>

      <div class="section-heading">
        <div>
          <strong>粘贴写作样本</strong>
          <span>每篇至少 100 字，文本与文件合计至少 3 篇</span>
        </div>
        <el-button text type="primary" @click="addSample">添加一篇</el-button>
      </div>

      <div class="sample-list">
        <div v-for="(_, index) in samples" :key="index" class="sample-item">
          <el-input
            v-model="samples[index]"
            type="textarea"
            :rows="4"
            resize="vertical"
            :placeholder="`粘贴第 ${index + 1} 篇文章`"
          />
          <el-button
            v-if="samples.length > 1"
            text
            type="danger"
            @click="removeSample(index)"
          >
            删除
          </el-button>
        </div>
      </div>

      <el-form-item label="或上传文件">
        <el-upload
          v-model:file-list="fileList"
          drag
          multiple
          :auto-upload="false"
          accept=".txt,.md,.docx"
        >
          <div class="upload-copy">
            <strong>拖入或选择 txt / docx 文件</strong>
            <span>单个文件不超过 2MB</span>
          </div>
        </el-upload>
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button :disabled="creating" @click="close">取消</el-button>
      <el-button type="primary" :loading="creating" @click="submit">
        {{ creating ? "正在学习你的笔风…" : "创建并分析" }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ElMessage, type UploadUserFile } from "element-plus";
import { ref } from "vue";

import { useStylesStore } from "@/stores/styles";
import type { StyleProfileDetail } from "@/types";

defineProps<{
  modelValue: boolean;
}>();

const emit = defineEmits<{
  "update:modelValue": [value: boolean];
  created: [profile: StyleProfileDetail];
}>();

const stylesStore = useStylesStore();
const creating = ref(false);
const name = ref("");
const samples = ref(["", "", ""]);
const fileList = ref<UploadUserFile[]>([]);

function addSample() {
  samples.value.push("");
}

function removeSample(index: number) {
  samples.value.splice(index, 1);
}

function close() {
  if (!creating.value) {
    emit("update:modelValue", false);
  }
}

function reset() {
  name.value = "";
  samples.value = ["", "", ""];
  fileList.value = [];
}

async function submit() {
  const textSamples = samples.value.map((sample) => sample.trim()).filter(Boolean);
  const files = fileList.value.flatMap((item) => (item.raw ? [item.raw] : []));

  if (!name.value.trim()) {
    ElMessage.warning("请输入档案名称");
    return;
  }
  if (textSamples.length + files.length < 3) {
    ElMessage.warning("文本与文件合计至少需要 3 篇样本");
    return;
  }
  if (textSamples.some((sample) => sample.replace(/\s/g, "").length < 100)) {
    ElMessage.warning("每篇粘贴样本至少需要 100 个非空白字符");
    return;
  }

  creating.value = true;
  try {
    const profile = await stylesStore.createProfile({
      name: name.value.trim(),
      samples: textSamples,
      files,
    });
    ElMessage.success("风格档案创建成功");
    emit("created", profile);
    emit("update:modelValue", false);
  } catch {
    ElMessage.error("创建失败，请检查样本格式后重试");
  } finally {
    creating.value = false;
  }
}
</script>

<style scoped>
.section-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.section-heading strong,
.section-heading span {
  display: block;
}

.section-heading span {
  margin-top: 4px;
  color: #9ca3af;
  font-size: 12px;
}

.sample-list {
  display: grid;
  gap: 12px;
  margin-bottom: 22px;
}

.sample-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.upload-copy {
  display: grid;
  gap: 6px;
  color: #4b5563;
}

.upload-copy span {
  color: #9ca3af;
  font-size: 12px;
}
</style>
