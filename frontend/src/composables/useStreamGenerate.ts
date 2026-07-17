import { onScopeDispose, ref } from "vue";

import { useUserStore } from "@/stores/user";
import type { GenerationQuality, StyleGenerationPayload } from "@/types";

type StreamEvent = "attempt" | "token" | "quality" | "retry" | "complete" | "error";
type EventData = Record<string, unknown>;

export function useStreamGenerate() {
  const userStore = useUserStore();
  const result = ref("");
  const generationId = ref("");
  const quality = ref<GenerationQuality>({});
  const generating = ref(false);
  const attempt = ref(0);
  const statusText = ref("");
  const error = ref("");
  let controller: AbortController | null = null;
  let timeoutId: ReturnType<typeof setTimeout> | null = null;
  let timedOut = false;

  async function generate(payload: StyleGenerationPayload) {
    cancel();
    controller = new AbortController();
    timedOut = false;
    timeoutId = setTimeout(() => {
      timedOut = true;
      controller?.abort();
    }, 30_000);
    result.value = "";
    generationId.value = "";
    quality.value = {};
    attempt.value = 0;
    error.value = "";
    statusText.value = "正在连接写作服务…";
    generating.value = true;

    try {
      const response = await fetch("/api/v1/styles/generate?stream=true", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "text/event-stream",
          Authorization: `Bearer ${userStore.accessToken}`,
        },
        body: JSON.stringify(payload),
        signal: controller.signal,
      });

      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(String(body.detail ?? `生成请求失败（${response.status}）`));
      }
      if (!response.body) {
        throw new Error("浏览器无法读取流式响应");
      }

      await consumeStream(response.body);
      if (!generationId.value) {
        throw new Error("生成连接意外中断，请重试");
      }
    } catch (reason) {
      if (reason instanceof DOMException && reason.name === "AbortError") {
        if (timedOut) {
          const message = "生成超过 30 秒，请精简要求后重试";
          error.value = message;
          statusText.value = message;
          throw new Error(message);
        }
        statusText.value = "已停止生成";
        return;
      }
      const message = reason instanceof Error ? reason.message : "生成失败，请稍后重试";
      error.value = message;
      statusText.value = message;
      throw reason;
    } finally {
      if (timeoutId) clearTimeout(timeoutId);
      timeoutId = null;
      generating.value = false;
      controller = null;
    }
  }

  async function consumeStream(stream: ReadableStream<Uint8Array>) {
    const reader = stream.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();
      buffer += decoder.decode(value, { stream: !done }).replace(/\r\n/g, "\n");
      const blocks = buffer.split("\n\n");
      buffer = blocks.pop() ?? "";

      for (const block of blocks) {
        handleEventBlock(block);
      }
      if (done) {
        if (buffer.trim()) handleEventBlock(buffer);
        break;
      }
    }
  }

  function handleEventBlock(block: string) {
    const lines = block.split("\n");
    const event = lines
      .find((line) => line.startsWith("event:"))
      ?.slice("event:".length)
      .trim() as StreamEvent | undefined;
    const rawData = lines
      .filter((line) => line.startsWith("data:"))
      .map((line) => line.slice("data:".length).trimStart())
      .join("\n");

    if (!event || !rawData) return;
    const data = JSON.parse(rawData) as EventData;

    if (event === "attempt") {
      attempt.value = Number(data.attempt ?? 1);
      if (data.reset) result.value = "";
      statusText.value =
        attempt.value > 1 ? `正在优化第 ${attempt.value} 版…` : "正在按你的风格写作…";
    } else if (event === "token") {
      result.value += String(data.text ?? "");
    } else if (event === "quality") {
      quality.value = data as GenerationQuality;
      statusText.value = "正在检查风格相似度…";
    } else if (event === "retry") {
      statusText.value = "初稿未达到质量标准，正在自动优化…";
    } else if (event === "complete") {
      generationId.value = String(data.generation_id ?? "");
      result.value = String(data.result ?? result.value);
      quality.value = (data.quality ?? quality.value) as GenerationQuality;
      statusText.value = "生成完成";
    } else if (event === "error") {
      throw new Error(String(data.detail ?? "生成失败，请稍后重试"));
    }
  }

  function cancel() {
    if (timeoutId) clearTimeout(timeoutId);
    timeoutId = null;
    timedOut = false;
    controller?.abort();
    controller = null;
  }

  onScopeDispose(cancel);

  return {
    result,
    generationId,
    quality,
    generating,
    attempt,
    statusText,
    error,
    generate,
    cancel,
  };
}
