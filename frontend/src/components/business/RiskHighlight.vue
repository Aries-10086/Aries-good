<template>
  <div class="risk-highlight">
    <div
      v-for="(segment, index) in segments"
      :key="`${segment.start}-${segment.end}-${index}`"
      :class="['segment', segment.level ? `segment--${levelClass(segment.level)}` : '']"
      :title="segment.title"
    >
      {{ segment.text }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";

import type { DocumentRisk } from "@/types";

const props = defineProps<{
  text: string;
  risks: DocumentRisk[];
}>();

type Segment = {
  text: string;
  start: number;
  end: number;
  level?: string;
  title?: string;
};

const segments = computed(() => {
  const sorted = [...props.risks].sort((left, right) => left.start - right.start);
  const result: Segment[] = [];
  let cursor = 0;

  for (const risk of sorted) {
    const start = Math.max(0, Math.min(props.text.length, risk.start));
    const end = Math.max(start, Math.min(props.text.length, risk.end));
    if (start > cursor) {
      result.push({
        text: props.text.slice(cursor, start),
        start: cursor,
        end: start,
      });
    }
    if (end > start) {
      result.push({
        text: props.text.slice(start, end),
        start,
        end,
        level: risk.level,
        title: `${risk.type} · ${risk.level}`,
      });
      cursor = end;
    }
  }

  if (cursor < props.text.length) {
    result.push({
      text: props.text.slice(cursor),
      start: cursor,
      end: props.text.length,
    });
  }

  return result.length ? result : [{ text: props.text, start: 0, end: props.text.length }];
});

function levelClass(level: string) {
  if (level === "高") return "high";
  if (level === "低") return "low";
  return "medium";
}
</script>

<style scoped>
.risk-highlight {
  line-height: 1.85;
  white-space: pre-wrap;
  word-break: break-word;
  color: #334155;
}

.segment {
  border-radius: 4px;
}

.segment--high {
  background: rgb(254 226 226 / 90%);
  box-shadow: inset 0 -2px 0 #ef4444;
}

.segment--medium {
  background: rgb(254 243 199 / 90%);
  box-shadow: inset 0 -2px 0 #f59e0b;
}

.segment--low {
  background: rgb(219 234 254 / 90%);
  box-shadow: inset 0 -2px 0 #3b82f6;
}
</style>
