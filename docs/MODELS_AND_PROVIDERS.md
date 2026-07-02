# 多模型提供商 & 管理员模型池（MUST-READ for maintainers）

> 版本：v1 · 2026-07-02 · 对应功能：AI 生成题目 / 判分 / 帮助回答支持多提供商 + 管理员可用池 + DeepSeek OCR
>
> ⚠️ **给后来的维护者：本页的「管理员控制」契约是一条硬产品规则，改动前务必读完。**

---

## 1. 一句话

AI 的三类调用——**出题生成、答案判分、帮助/答疑**——都可由多个提供商的模型完成
（Claude / DeepSeek / GPT，可继续扩展）。**学生在管理员开放的"可用池"里自由选择自己
所用的模型**；**"哪些模型可用 / 是否强制某个模型"的开关只有管理员能控制，学生绝不能碰。**

## 2. ⚠️ 管理员控制契约（HARD RULE — 别破坏它）

- **可用/不可用、强制分配 = 管理员专属权限。** 后端所有写操作走
  `POST /admin/models`，由 `require_admin` 依赖（[main.py](../backend/app/main.py)）把关：
  未登录 → 401，非管理员 → 403。
- **学生只能"在池内选择"。** 学生调用的 `GET /models` 只返回"可用 ∧ 已启用"的池；
  即便学生伪造请求传入池外/被禁用/未配置的模型 id，后端在 `providers.resolve_model()`
  这个**唯一收口**处会把它夹回池内（被强制模型则一律覆盖为强制模型）。
  见 [providers.py](../backend/app/providers.py)、[claude_service.py](../backend/app/claude_service.py)。
- **前端不得把 enable/force 开关暴露给学生。** 管理面板
  [AdminModels.tsx](../frontend/src/components/ModelControls.tsx) 需管理员登录（`/auth/signin`
  + 账号在 `ADMIN_USERNAMES` 内）才可用；普通学生点开只会看到过不去的登录框。
  **新增任何模型控制 UI 时，务必确认它不会让学生改动池或强制项。**
- **管理员是谁？** 由 `.env` 的 `ADMIN_USERNAMES`（逗号分隔）决定，在注册时与每次启动时
  写入 `users.role`（[auth.py](../backend/app/auth.py)）。**没有任何应用内途径让学生自我提权。**

> 破坏上面任何一条，都会让"管理员强制分配"形同虚设——请勿。

## 3. 两层决定"学生能选什么"

```
学生可选池  =  usable（提供商已在 .env 配好 BASE_URL+API_KEY）  ∧  admin-enabled（管理员开关）
实际调用的模型 =  resolve_model(requested)
                = 若管理员强制了某模型(且 usable) → 强制模型
                  否则 requested 若在池内 → requested
                  否则 → 池默认
```

- **候选目录（.env）**：[config.py](../backend/app/config.py) 按提供商解析出全部候选模型，
  [providers.py](../backend/app/providers.py) 汇总成目录（含协议/连接信息/默认可用）。
- **运行时覆盖层（DB）**：[model_policy.py](../backend/app/model_policy.py)（SQLite
  `data/model_policy.db`）存每模型 `enabled` 覆盖 + 全局 `forced_model`，管理员可运行时改，
  重启留存。无覆盖行时回落到候选目录的默认可用。
- **`.env` 的 `LLM_FORCED_MODEL`** 只是首次启动时的强制默认；之后以 DB 里的运行时值为准。

## 4. 两种协议、一套传输层

`claude_service.complete(system, messages, model=…)` 是所有文本 LLM 调用的统一入口
（`reasoner.py` / `sympy_compute.py` / `main.py` 都用它，签名不变）。它按所选模型的**协议**分发：

| 协议 | 端点 | 提供商 | 鉴权 |
|------|------|--------|------|
| `anthropic` | `{base}/v1/messages` | Claude | `x-api-key` 或 `Authorization: Bearer`（`CLAUDE_AUTH_HEADER`）|
| `openai` | `{base}/v1/chat/completions` | DeepSeek、GPT、任何 OpenAI 兼容网关 | `Authorization: Bearer` |

- 断路器**按提供商分桶**：一个提供商故障不会连累其它。
- `system` 在 anthropic 走顶层 `system` 字段；在 openai 转成首条 `role:"system"` 消息。

## 5. 怎么加一个新提供商 / 新模型

1. 在 `.env` 里配好该提供商的 `*_BASE_URL` / `*_API_KEY` / `*_MODELS`（`id|Label` 逗号分隔）。
2. 若是全新提供商：在 [config.py](../backend/app/config.py) 加连接常量，在
   [providers.py](../backend/app/providers.py) `_catalogue()` 里追加该提供商的模型条目
   （指定 `protocol`：Anthropic 兼容用 `anthropic`，其余用 `openai`），并在 `PROVIDER_LABELS`
   加显示名。**无需改** `reasoner`/`main` 的调用点。
3. 已有提供商（DeepSeek/GPT）加模型：只改 `*_MODELS` 即可，无需改代码。
4. 模型 id 必须**全局唯一**（跨提供商）；重复以先出现者为准。

## 6. OCR 的 DeepSeek 识别

OCR 独立于文本模型池（见 [recognize.py](../backend/app/recognize.py) / `/recognize/models`）。
识别引擎 `method`：`nex`（默认，nex-n2-pro）、`deepseek`（新增，DeepSeek 视觉）、
`claude`（Claude 视觉）、`auto`（nex 失败回退 Claude）。

- DeepSeek OCR 走 OpenAI 兼容图像端点（`image_url`），配置见 `.env` 的 `DEEPSEEK_OCR_*`。
- **模型必须是多模态/视觉模型**（`DEEPSEEK_OCR_MODEL`，如 `deepseek-vl`）；纯文本模型读不了图。
- 未配置时 `available:false`，前端下拉照常列出但标注不可用，调用回落——与 nex 相同的优雅降级契约。

## 7. 相关接口

| 接口 | 用途 | 鉴权 |
|------|------|------|
| `GET /models` | 学生可选池 + 默认 + `forced_model`（锁定选择） | 公开 |
| `GET /claude/models` | `/models` 的向后兼容别名 | 公开 |
| `GET /admin/models` | 全量目录 + 每模型 usable/enabled + forced | **管理员** |
| `POST /admin/models` | 开关模型（`enable:{id:bool}`）/ 设或清强制（`forced_model` / `clear_forced`） | **管理员** |
| `GET /recognize/models` | OCR 引擎列表（nex/deepseek/claude/auto） | 公开 |

## 8. 快速验证

```bash
# 学生池
curl localhost:8000/models
# 管理员（账号需在 ADMIN_USERNAMES 内）：登录拿 token 后
curl localhost:8000/admin/models -H "Authorization: Bearer <TOKEN>"
curl -X POST localhost:8000/admin/models -H "Authorization: Bearer <TOKEN>" \
     -H 'Content-Type: application/json' -d '{"enable":{"gpt-4o":true},"forced_model":"deepseek-chat"}'
# 非管理员访问 /admin/models → 403（这是本功能的安全底线）
```
