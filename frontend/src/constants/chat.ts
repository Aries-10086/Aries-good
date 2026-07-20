import type { ChatScene } from "@/types";

export type ChatSceneOption = {
  value: ChatScene;
  icon: string;
  title: string;
  description: string;
  prompt: string;
  accent: string;
};

export const CHAT_SCENES: ChatSceneOption[] = [
  {
    value: "invite_dinner",
    icon: "🍲",
    title: "邀请聚餐",
    description: "自然发出邀请，不让对方感到压力",
    prompt: "邀请对方找个合适的时间一起吃饭",
    accent: "#f59e0b",
  },
  {
    value: "persuade_game",
    icon: "🎮",
    title: "约朋友开黑",
    description: "轻松说服朋友加入，避免生硬催促",
    prompt: "邀请朋友一起玩游戏，并尊重对方的安排",
    accent: "#8b5cf6",
  },
  {
    value: "comfort",
    icon: "🌤️",
    title: "安慰陪伴",
    description: "先接住情绪，再给出恰当的回应",
    prompt: "安慰正在经历低落或挫折的对方",
    accent: "#06b6d4",
  },
  {
    value: "urge",
    icon: "⏰",
    title: "礼貌催促",
    description: "明确推进事情，同时照顾关系距离",
    prompt: "礼貌确认进度和具体交付时间",
    accent: "#ef4444",
  },
  {
    value: "custom",
    icon: "✨",
    title: "自定义场景",
    description: "描述任何沟通难题，生成专属人设",
    prompt: "",
    accent: "#4f46e5",
  },
];

export const RELATIONSHIP_OPTIONS = [
  "朋友",
  "同事",
  "家人",
  "伴侣",
  "客户",
  "领导",
  "不太熟的人",
];
