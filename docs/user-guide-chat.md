# 沟通助手用户指南

## 使用前准备

服务端需完成数据库迁移并配置 `DATABASE_URL`、`OPENAI_API_KEY`、
`REDIS_URL` 和 `DJANGO_SECRET_KEY`。聊天实时输出依赖 Django Channels
和 Redis；前端开发服务器会将 `/ws` 代理到 `localhost:8000`。

可通过以下环境变量调整回复行为：

- `CHAT_MAX_REPLY_LENGTH`：单条回复硬上限，默认 150 字。
- `CHAT_HISTORY_MESSAGE_LIMIT`：送入模型的历史消息上限，默认 40 条。
- `CHAT_REPLY_BASE_TEMPERATURE`：普通回复温度，默认 0.7。
- `CHAT_REGENERATE_TEMPERATURE`：换一条时的温度，默认 1.0。

## 创建会话

1. 登录后进入“沟通助手”（`/chat`）。
2. 选择邀请聚餐、说服朋友打游戏、安慰、催促或自定义场景。
3. 选择双方关系，填写本轮目标；需要时绑定已有风格档案。
4. 确认后进入 `/chat/{session_id}`。系统会依据场景、关系和目标生成固定人设卡片。

不要输入身份证号、住址、账号密码等敏感信息。沟通助手提供的是回复草稿，
涉及医疗、法律、财务或人身安全时应寻求专业帮助。

## 生成和调整回复

- 在底部输入“对方说的话”并发送，左侧将流式显示建议回复。
- “生成 3 条建议”会用共情、直接选择和轻松口语三种策略生成候选内容。
- “太 AI 了，换一条”保留当前上下文和人设，以更高温度更换措辞与切入方式。
- 点击复制按钮可将建议复制到剪贴板，再自行确认和发送。

系统会优先处理“累、烦、不想”等负面情绪。负面场景下，回复应先承接情绪，
弱化或暂停目标推进。所有模型回复仍可能出错，发送前请检查事实、称呼和关系距离。

## 场景调优原则

- 邀请聚餐：给出具体邀约，同时保留拒绝空间。
- 说服朋友打游戏：保持轻松，可建议低成本试玩，不激将或施压。
- 安慰：先接住情绪，不急着讲道理、给方案或强行积极。
- 催促：说清事项、时间点和下一步，不指责或阴阳怪气。
- 自定义：严格遵循创建会话时的人设、关系和目标。

回复通常控制在 1—3 个短句、20—80 字，硬上限为 150 字；最多提出一个问题。
四场景十轮脚本位于 `docs/eval/chat_scenarios.json`，回归 bad case 位于
`docs/eval/chat_bad_cases.json`。

## 接口联调

REST 接口均需携带 JWT：

- `POST /api/v1/chat/sessions`：创建会话。
- `GET /api/v1/chat/sessions`：会话列表。
- `GET /api/v1/chat/sessions/{id}`：会话详情及消息历史。
- `DELETE /api/v1/chat/sessions/{id}`：删除会话。
- `POST /api/v1/chat/sessions/{id}/messages`：生成一条完整回复。
- `POST /api/v1/chat/sessions/{id}/suggestions`：生成三条建议；传
  `{"regenerate": true}` 可换一条。

流式聊天地址：

```text
ws://127.0.0.1:8000/ws/chat/{session_id}/?token={JWT_ACCESS_TOKEN}
```

发送消息：

```json
{"action": "message", "content": "对方说的话"}
```

换一条：

```json
{"action": "regenerate"}
```

服务端依次返回 `start`、若干 `token`、`complete` 事件；失败时返回 `error`。

## 验收

自动化回归覆盖四个预设场景各 10 轮对话，检查人设持续注入、场景规则、
消息历史窗口、负面情绪标记和 150 字硬上限：

```bash
cd QuillMind/backend
python manage.py test apps.chat.tests_messaging
```

发布前还需使用真实模型人工抽检至少 5 个会话。每个会话应检查：

1. 连续多轮后身份、关系、称呼和边界没有漂移。
2. 负面情绪先被回应，没有强行推进目标。
3. 回复口语自然，无客服腔、清单腔和总结腔。
4. 没有捏造事实、连续追问、操控或道德绑架。
5. 回复可直接发送，且不超过 150 字。
