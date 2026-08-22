---
name: zhenji
version: 5.2
description: 真机驱动的社交媒体内容情报 Skill。当前首先适配小红书，并为 Instagram（照片与短视频社交平台）、TikTok（短视频平台）等保留平台适配层；通过真实 iPhone 采集账号、作品、视频、公开评论、搜索与推荐流信号，结构化保存到 Google Sheets（谷歌表格）和 Google Drive（谷歌云端硬盘），支持高效视频理解、检索、账号诊断、竞品分析、模式挖掘、选题、实验与复盘。默认只读，不自动点赞、关注、评论、私信或发布，不绕过平台安全验证。
---

# 甄姬（zhenji）

> **v5.2 · 2026-08-22**
>
> 主要变更（详见 `CHANGELOG.md`）：
> - **P0 MediaFetchResult 语义修正**：删除误导性的 `ok` 属性，新增 `succeeded`（status 不在 {FAILED,BLOCKED}）；业务层必须用 `acceptable_for_mode(mode)` 判断任务是否达成。
> - **P0 Worker mode 强校验**：`media_worker` 改用 `result.acceptable`，档位约束不再依赖模糊的 ok。
> - **P1 Action Recipe（真机操作知识库）**：`scripts/action_recipe/` + `references/platform-recipes/*.yaml` 把"某 App 怎么拿分享链接"固化为声明式 recipe，替代每次截图+OCR；坐标强制 normalized ratio，validator 拒绝绝对像素；目标 95% Recipe / 5% Vision。
> - **P1 平台状态声明**：`references/platform-status.yaml` 区分 production / beta / router_only，避免 router 支持被误读为业务支持。
> - **P1 测试 + CI**：新增 `test_media_fetch_result` / `test_action_recipe` / `test_platform_status` / `test_douyin_resolver`。
>
> v5.1 主要变更：
> - `phone-harness` 已 bundled（不再要求用户单独 download；调用通过 `scripts/phone_harness/` 子包）
> - 去掉 phone-harness 强约束（v5 中"必须"、"严禁"的限制改为建议）
> - 新增「浮光 (fuguang)」第四档（post_followup + V4 mirror fallback 纯视觉摘要）
> - 工程加速固化：PSSD venv / `HF_ENDPOINT=hf-mirror.com` / 卸 hf-xet / `shutil.rmtree`
>
> 详见 `CHANGELOG.md` 与本文件末尾 §v5.1 changelog。

## 0. 定义

`zhenji` 是：

> 真机驱动的社交媒体内容采集 + 结构化内容数据库 + 可检索运营知识库 + 数据驱动运营分析系统。

当前首个生产适配器为小红书；后续 Instagram（照片与短视频社交平台）、TikTok（短视频平台）等只新增平台适配器，不重做存储、检索与分析层。

闭环：

```text
采集 → 保存事实 → 内容结构化 → 检索 → 分析
→ pattern（模式）→ topic（选题）/ experiment（实验）
→ 后续数据验证 → review（复盘）→ 更新 pattern
```


## 1. 洛神四象：核心能力命名

甄姬的一级能力采用《洛神赋》的意象命名。古典名称用于产品语言，括号内为系统职责。

### 流眄 · 真机监测

> 「流眄乎洛川」

对应 Monitor / Collector（监测 / 采集）。通过真实 iPhone 持续观察指定账号、作品、评论、搜索结果与推荐流；负责发现“现在发生了什么”。

```text
流眄
→ 真机观察
→ 增量巡检
→ 新作品发现
→ 指标跟踪
→ 推荐流 / 搜索研究
```

### 采珠 · 内容入库

> 「或采明珠，或拾翠羽」

对应 Library / Storage（内容库 / 存储）。将公开内容、指标、评论、截图证据和时间序列结构化保存；负责回答“我们已经看见并保存了什么”。

```text
采珠
→ Evidence（证据）
→ Facts（事实）
→ Features（特征）
→ Google Sheets（谷歌表格）
→ Google Drive（谷歌云端硬盘）
```

### 流精 · 模式分析

> 「转眄流精」

对应 Intelligence / Knowledge（分析 / 知识）。从多篇内容和长期表现中提炼可复用规律，不以单篇爆款直接下结论；负责回答“为什么有效，以及什么值得复用”。

```text
流精
→ 账号诊断
→ 内容结构分析
→ 评论洞察
→ Pattern（模式）挖掘
→ 竞品分析
→ Review（复盘）
```

### 殊观 · 运营发现

> 「俯则未察，仰以殊观」

对应 Ops / Discovery（运营 / 发现）。把平台信号、账号历史、评论需求和已验证模式重新组合为下一步运营机会；负责回答“接下来应该做什么”。

```text
殊观
→ Topic（选题）
→ Recommendation（建议）
→ Experiment（实验）
→ 周 / 月运营计划
```

四象闭环：

```text
流眄其变
    ↓
采珠存真
    ↓
流精辨势
    ↓
殊观得机
    ↓
再次流眄，以真实结果验证
```

甄姬产品铭文：

> **流眄监其变，采珠存其真，流精辨其势，殊观得其机。**

以上诗句为《洛神赋》原句；产品铭文为本项目基于这些意象重新组织的功能表达。

### 二级能力术语

- **复形 · 检索**：「冀灵体之复形」——让历史内容、证据与知识重新呈现。
- **离合 · 趋势**：「神光离合，乍阴乍阳」——观察指标与内容表现的起伏变化。
- **绵思 · 长期记忆**：「思绵绵而增慕」——表示连续监测和长期知识积累。
- **陈纲 · 归纳**：「陈交接之大纲」——表示从复杂样本中抽出结构与纲要。


## 2. 系统架构

```text
zhenji
├── collector/iphone
│   └── phone-harness (zhenji bundled, user-controlled) — v5.1 详见 §65
├── platforms
│   ├── xhs            # 当前生产适配器
│   ├── douyin         # v5.1.1 新增（v0，iesdouyin API + yt-dlp 兜底）—— 详见 §73
│   ├── instagram      # 预留
│   └── tiktok         # 预留
├── video
│   ├── lueying        # 掠影：效率模式
│   ├── tinglan        # 听澜：基本模式
│   └── guanlan        # 观澜：完整模式
├── runtime
│   ├── observation_cache
│   ├── card_map
│   ├── action_macros
│   ├── batch_write
│   ├── watchdog
│   ├── idle_calibration
│   └── safe_keepalive
├── storage
├── retrieval
├── analysis
├── knowledge
└── ops

storage
├── Google Sheets：结构化主库
└── Google Drive：截图、证据、报告、知识卡
```

平台 Collector（采集器）接口保持稳定：

```text
get_profile()
get_latest_posts()
get_post_detail()
get_comments()
search_posts()
sample_home_feed()
get_media_descriptor()
```

小红书适配器可继续提供 `search_notes()` 作为兼容别名。上层 Facts / Features / Knowledge 不依赖平台页面实现。


## 2.1 性能优先运行架构

甄姬默认采用“少观察、批处理、可复用”的执行原则。性能目标不是让手机点得更快，而是消灭四类无效成本：

```text
重复 OCR（光学字符识别）
重复探索同一页面卡片位置
每条内容立即写一次在线工作簿
同一动作序列反复重新规划
```

标准流水线：

```text
一次 Observe（观察）
= 1 张截图 + 1 次 OCR + 1 次页面分类 + 1 次卡片布局解析
                ↓
同一屏内所有决策复用 Observation（观察对象）
                ↓
批量读取当前屏全部候选卡片
                ↓
内存 / 本地 staging（暂存）累积事实
                ↓
达到阶段边界或批量阈值
                ↓
Google Sheets Batch（批量写入）
                ↓
事实写入确认成功
                ↓
最后更新 last_seen / cursor（游标）
```

必须遵守：

1. **一次屏幕状态只做一次 OCR。** 同一屏幕内标题、导航、卡片、数字和页面状态全部从同一个 Observation 读取。
2. **动作后才失效。** 点击、滚动、输入、返回、页面跳转后调用 `mark_dirty()`；纯分析和字段提取不得触发重新截图/OCR。
3. **一屏多卡批读。** 不允许“识别卡片 A → 点 A → 回来重新 OCR → 找 B”的低效循环作为默认策略。先把当前屏所有卡片的元数据和几何位置一次性建表，再按任务顺序处理。
4. **几何缓存只做会话级复用。** 卡片列中心、行距、导航栏区域等可以在同一设备/同一页面类型/同一会话复用；页面结构变化、旋转、窗口尺寸变化或校验失败立即失效。
5. **在线写入批量化。** `accounts/posts/comments` 等当前状态与 `snapshots/runs/features/knowledge/search_index` 等追加数据先进入 run buffer（运行缓冲区），按阶段批量写入，而不是每条作品调用一次工作簿。
6. **游标永远最后写。** 只有本批新作品事实成功持久化后，才能推进 `last_seen_post_key` 或跨平台等价 cursor（游标）。
7. **分析与采集解耦。** 手机是单线程稀缺资源；视频转录、抽帧、结构分析、索引更新尽量在本地后台并行，不阻塞手机继续采集下一条。

对应实现参考：

```text
scripts/runtime_cache.py
scripts/write_buffer.py
scripts/action_macros.py
references/runtime-performance.md
```

## 2.2 视频三档模式

视频作品必须先选择处理模式，禁止默认逐条实时“陪看完整视频”。

### 掠影 · 效率模式

目标：最大吞吐量，用于账号初筛、大批量竞品、推荐流与搜索样本。

V5 默认采集：

```text
phone-harness 获取真实分享链接
→ 本地解析视频元数据
→ 下载低成本媒体副本（默认 480p）
→ 本地抽取 6–12 个代表画面
→ 页面标题 / 正文 / 互动数据
```

除非链接获取或本地下载失败，不再以 iPhone 实时播放截图作为主路径。

默认不做：

```text
完整音频转录
完整逐镜头分析
逐秒 OCR
```

适合回答：

```text
这条大概讲什么？
是不是值得继续深挖？
开头视觉是什么？
属于什么主题/形式？
```

### 听澜 · 基本模式

目标：理解绝大多数口播、知识、测评和剧情解说视频。

在掠影基础上增加：

```text
分享链接 → 本地媒体下载
本地音轨提取
ASR（自动语音识别）完整转录
时间戳文本段
少量关键帧
标题 / 正文 / 评论信号
```

手机不等待转录或分析；拿到链接后立即继续采集下一条。

核心原则：**以听代看**。能从音频和少量关键帧理解的视频，不进行完整逐帧视觉分析。

适合回答：

```text
完整讲了什么？
开头口播 Hook（钩子）是什么？
论证顺序是什么？
什么时候出现 CTA（行动引导）？
```

### 观澜 · 完整模式

目标：对少量高价值视频做完整内容情报分析。

增加：

```text
分享链接 → 最高可用质量完整下载
完整转录
Scene Detection（场景切分）
每场景关键帧
语音—画面时间轴对齐
开头 Hook 秒数
镜头结构
产品 / 人物 / 场景出现时间
CTA 时间
完整 video_structure_json
```

只用于：

```text
高表现作品
关键竞品作品
用户明确指定作品
需要制作/复刻结构研究的样本
```

模式顺序：

```text
默认先掠影
    ↓
价值足够？
 ├─ 否 → 入库结束
 └─ 是 → 听澜
              ↓
       仍需视觉时序？
        ├─ 否 → 入库分析
        └─ 是 → 观澜
```

严禁：

```text
账号 30 条视频 → 30 条全部观澜
```

推荐：

```text
30 条 → 掠影 → 8 条候选 → 听澜 → 2–3 条 → 观澜
```

详细字段和升级规则见 `references/video-modes.md`。

## 2.3 Observation（观察对象）与 OCR 缓存

每一个稳定屏幕状态只生成一个 Observation：

```json
{
  "generation": 42,
  "page_type": "profile_grid",
  "screenshot_ref": "...",
  "ocr_rows": [],
  "anchors": {},
  "card_layout": {},
  "created_at": "..."
}
```

同一 `generation` 内：

```text
页面识别
目标文字定位
卡片解析
指标读取
风险词检查
```

全部复用同一个 `ocr_rows`。

只有下列动作默认使 generation + 1：

```text
tap
scroll
swipe
input
back
open_app
页面跳转
显式等待到新页面
```

“我要再确认一下”不能自动成为重复 OCR 的理由；先检查现有 Observation 是否仍有效。

## 2.4 Card Map（卡片地图）

第一次进入列表型页面时建立会话级 Card Map：

```text
page_type
screen_size
column_centers
row_centers / row_spacing
card_bounds
safe_tap_zone
anchor_regions
layout_confidence
```

用途：

```text
当前屏一次性识别全部卡片
按视觉顺序编号
缓存安全点击区域
返回后优先复用同一网格几何
```

复用前必须做低成本校验：

```text
屏幕尺寸一致
页面类型一致
关键锚点仍存在
布局置信度未降级
```

任何一项不满足立即重建，不能把 Card Map 变成跨任务固定坐标表。

## 2.5 Batch Write（批量写入）

禁止默认：

```text
读取 1 条 → 写 Sheets 1 次
读取 1 条 → 写 Sheets 1 次
读取 1 条 → 写 Sheets 1 次
```

改为：

```text
采集一批
↓
本地 staging
↓
去重 / 合并 upsert
↓
生成 BatchWritePlan
↓
一次或少量批次写入
↓
读取必要结果验证
↓
最后提交 cursor
```

批次阶段：

```text
Phase A: Facts
  accounts
  account_snapshots
  posts
  post_snapshots
  comments
  runs

Phase B: Features
  content_features
  comment_features
  video_features

Phase C: Knowledge & Index
  knowledge
  experiments
  search_index
  alerts

Phase D: Cursor Commit
  last_seen_post_key
  platform cursor
```

默认 flush（刷新）条件可取其一：

```text
完成一个账号巡检
完成当前屏 / 当前作品批次
buffer >= 20–50 条操作
即将更新 cursor
任务结束
```

不要为了凑够 50 条而牺牲可靠性；账号巡检结束就是天然事务边界。

## 2.6 重复动作自动封装

执行器必须记录高层动作签名，而不是只记录坐标：

```text
open_search
search_account
open_profile
scan_visible_cards
open_card
read_post_metadata
return_to_grid
open_comments
```

当同一稳定动作序列在同一平台适配器中成功重复 >= 3 次，可以提升为 Macro（宏）/ Helper（辅助函数）候选。

自动封装必须是**声明式宏**，禁止让模型在运行中任意修改核心控制代码。

示例：

```yaml
name: xhs_open_post_from_grid
platform: xhs
precondition: page_type == profile_grid
steps:
  - scan_visible_cards
  - tap_safe_card_zone
  - wait_stable
  - verify_page: post_detail
postcondition: page_type == post_detail
```

宏执行要求：

```text
前置条件验证
→ 执行步骤
→ 每个页面变化动作后验证
→ 后置条件验证
→ 成功计数 / 失败计数
```

出现 2 次连续失败或页面结构变化：

```text
自动降级为普通规划
宏标记 stale（失效待重学）
```

默认只允许只读动作进入自动宏白名单。点赞、关注、评论、私信、发布永不因为“重复出现”而自动封装并执行。

参考 `scripts/action_macros.py` 与 `references/helper-macros.md`。


## 3. 默认只读

允许读取公开主页、作品、评论、搜索结果、推荐流与截图。默认禁止点赞、收藏、关注、评论、回复、私信、发布、删除、修改资料，以及任何绕过验证码、登录验证或平台风控的行为。

可以生成“建议回复”“发布草稿”“内容方案”，但不自动执行外部状态变更。

## 4. 四层数据模型

```text
L0 Evidence  原始证据
L1 Facts     页面明确可观察事实
L2 Features  模型提取的内容/评论结构特征
L3 Knowledge 可复用运营知识
```

所有分析应尽量能回指：

```text
Knowledge → Feature → Fact → Evidence
```

禁止把模型推断写进事实字段。

## 5. L0 Evidence

证据默认保存到 Google Drive。

类型：

```text
profile_screenshot
post_cover
post_detail_screenshot
comment_screenshot
feed_screenshot
ocr_raw
manual_reference
```

表格只保存：

```text
evidence_id
kind
drive_url
captured_at
account_key
post_key
run_id
notes
```

## 6. L1 Facts

事实表：

```text
accounts
account_snapshots
posts
post_snapshots
comments
runs
```

这些表只保存真实可见数据；“反常识标题”“收藏型内容”等属于 Features，不属于 Facts。

## 7. L2 Features

核心表：

```text
content_features
comment_features
```

### content_features

至少包含：

```text
feature_id, post_key, account_key, analysis_version, analyzed_at

topic_primary, topic_secondary_json, content_pillar
content_type, content_format

title_text, title_template, title_length, title_hook_type
cover_text, cover_information_level, cover_visual_type
opening_hook, hook_type, angle, stance

audience, scene, pain_point, desire, user_benefit
emotion_primary, emotion_secondary_json

body_structure, body_structure_json, evidence_type, story_pattern
cta, cta_type, interaction_mechanism

hashtags_json, keywords_json, entities_json
commercial_intent, risk_level, risk_reasons_json
replicability, novelty, confidence, source_evidence_json
```

### comment_features

把评论区变成需求数据库：

```text
comment_feature_id, comment_key, post_key, account_key
analysis_version, intent, sentiment
question_type, objection_type
pain_point, desire, decision_factor
requested_content, mentioned_entity
risk_signal, is_high_value, confidence
```

高价值评论包括：明确追问、真实场景、反对理由、决策阻塞、高频困惑、补充案例、可发展成下一篇内容的问题。

## 7.1 L3 Knowledge

统一保存到 `knowledge` 表。

类型：

```text
account
topic
pattern
review
action
experiment
recommendation
```

字段：

```text
knowledge_id, knowledge_type, title, summary, status
account_key, post_keys_json, source_run_ids_json
tags_json, topic, content_pillar
evidence_json, metrics_json
confidence, validated_count, failed_count
created_at, updated_at, valid_from, valid_until
next_action, search_text
```

状态：

```text
experimental
active
strong
deprecated
rejected
```

## 8. Pattern（模式）

Pattern 必须回答：

```text
是什么结构？
适用于什么账号/人群/场景？
有什么证据？
比历史基线高多少？
成功几次？失败几次？
下一次如何复用？
```

单篇高表现内容只能生成 `experimental`，不能直接称为规律。

生命周期：

```text
experimental → active → strong
                   ↓
              deprecated
```

## 9. Topic（选题）

选题不是只有标题。至少结构化保存：

```text
target_audience
problem
angle
stance
hook
content_outline
interaction_question
platform_signal_score
account_fit_score
interaction_score
writeability_score
pattern_support_score
risk_score
supporting_post_keys
```

内部排序：

```text
opportunity_score =
平台信号 + 账号匹配 + 互动潜力 + 可写性 + pattern 支持 - 风险
```

这只是运营排序，不代表平台真实算法。

## 10. Experiment（实验）

重要建议尽量转成可验证实验。

字段：

```text
experiment_id
hypothesis
account_key
pattern_id
planned_at, start_at, end_at
control_definition
variant_definition
primary_metric
secondary_metrics_json
success_criteria
post_keys_json
result
conclusion
status
```

运营建议不应永远停留在“感觉应该”。

## 11. Search Index（统一检索索引）

建立 `search_index`：

```text
doc_id, doc_type, account_key, post_key, knowledge_id
title, search_text, keywords_json, tags_json
topic, content_pillar
published_at, created_at, updated_at
metric_likes, metric_comments, metric_collects
status, source_sheet, source_row_key, embedding_ref
```

`doc_type`：

```text
account
post
comment
pattern
topic
review
experiment
recommendation
```

## 12. search_text

作品索引文本包含：

```text
账号名 + 标题 + 正文 + 话题 + 关键词
+ 内容支柱 + hook 类型 + 正文结构 + 用户痛点 + 互动机制
```

Pattern 索引文本包含：

```text
模式名 + 总结 + 适用条件 + 证据 + 标签 + 下一步动作
```

评论索引文本包含：

```text
正文 + 问题 + 痛点 + 需求 + 反对理由
```

## 13. 检索能力

必须支持：

```text
精确：找账号 A 的所有作品
时间：找最近 30 天 AI 相关内容
指标：找 24h 收藏增长最快的 10 篇
特征：找所有反常识标题
评论：最近用户都在问什么
模式：过去验证过哪些 AI 测评封面结构
复合：过去三个月哪个账号做 AI 视频时什么标题结构收藏表现最好
```

## 14. 自然语言检索流程

```text
用户问题
↓
解析 entity/account/topic/time_window/metrics/features/knowledge_type
↓
结构化过滤
↓
指标排序
↓
search_text 关键词/标签
↓
可选语义检索
↓
结论 + 证据 + 范围 + 不确定性
```

结构化事实优先于语义相似。

## 15. 可选语义检索

Google Sheets 是事实主库，不是理想向量数据库。

因此：

```yaml
retrieval:
  mode: hybrid
  structured: true
  keyword: true
  semantic:
    enabled: false
    provider: ""
```

未启用向量检索时，字段过滤 + 关键词 + 标签必须完整可用。

## 16. 写入顺序

新作品：

```text
Collector
→ Evidence
→ posts / post_snapshots
→ content_features
→ search_index
→ pattern/topic 候选
→ knowledge
```

禁止从截图直接跳到 Pattern，绕过事实层。

## 17. 当前值与时间序列

```text
posts = 当前状态
post_snapshots = 历史指标时间序列
```

推荐观察点：

```text
1h / 6h / 24h / 72h / 7d
```

只有实际采到才保存，不插值伪造。

## 18. 指标命名

平台没有曝光量时，不要称：

```text
CTR（点击率）
曝光转化率
真实互动率
```

可计算：

```text
点赞增长速度
评论增长速度
收藏增长速度
收藏/点赞
评论/点赞
互动/粉丝比
```

## 19. Account Audit（账号体检）

默认采样最近 9–15 篇，并结合历史时间序列。

五维：

```text
定位清晰度
内容结构力
互动转化力
账号辨识度
增长可持续性
```

每项：

```text
1–5 分 + 数据依据 + 内容依据 + 下一步动作
```

输出：

```text
一句话定位
内容支柱
当前阶段
五维评分
最大优势
最大短板
增长解释
应该扩大什么
应该收缩什么
未来一周实验
```

账号阶段可用：摸索期、增长期、稳定期、转型期、混乱期、衰退观察期。必须说明依据，不仅凭粉丝数。

## 20. Post Analysis（作品分析）

重点作品统一拆：

```text
主题 / 内容支柱 / 目标人群 / 场景 / 痛点 / 收益
标题模板 / 封面信息层级 / opening hook
正文结构 / 证据类型 / 情绪 / CTA / 互动机制
表现数据 / 相对账号基线 / 评论反馈 / 风险
可复用部分 / 不可复用部分
```

## 21. 相对表现

优先与同账号、相近时期、相近内容类型比较。

例如：

```text
relative_collect_index =
作品 24h 收藏 / 最近可比作品 24h 收藏中位数
```

`1.0` 为基线，`2.0` 为两倍基线。

不要用一个全平台固定阈值判断爆款。

## 22. Pattern Mining（模式挖掘）

周期性比较：

```text
高表现组 vs 普通组
```

检查：

```text
title_hook_type
cover_information_level
hook_type
body_structure
emotion
user_benefit
cta_type
interaction_mechanism
topic
content_pillar
```

只有重复出现并有表现证据，才升级 Pattern。

## 23. 推荐流分析

可以通过 iPhone 首页有限采样 10–20 条。

每条保存：

```text
title, cover_text, content_type, account_type
visible_metrics, tags, hook, reason_to_stop, interaction_mechanism
```

分析：

```text
当前推荐流主导主题
重复 hook
重复封面层级
传播机制
与目标账号匹配度
```

推荐流是个性化样本，只能说“当前设备/账号推荐流样本中……”，不能推断全平台。

## 24. 搜索研究

允许搜索关键词、话题、对标账号、代表性笔记形成 research sample。

保存：

```text
sample_origin = search
query = "..."
```

研究样本与指定账号完整监测数据分开标记。

## 25. Competitive Analysis（竞品分析）

推荐 1–3 个对标账号，每个 5–15 篇，同口径比较：

```text
定位
内容支柱
标题结构
封面结构
内容格式
发布节奏
高表现主题
互动机制
评论需求
pattern
```

输出区分：

```text
值得学
不值得学
只适用于对方的东西
可迁移到我们的东西
```

## 26. Comment Insights（评论洞察）

聚类：

```text
问题 / 赞同 / 反对 / 补充 / 真实案例
决策阻塞 / 内容请求 / 误解 / 风险信号
```

输出：

```text
高频问题 TOP
高频痛点 TOP
主要反对意见
用户自己的措辞
下一篇内容机会
建议回复的高价值评论
```

检查不等于自动回复。

## 27. Topic Ideation（选题生成）

必须融合：

```text
平台信号
+ 账号历史有效 Pattern
+ 评论/用户需求
+ 竞品空白
```

角度：立场型、过程型、结果型、对比型、反常识型、复盘型。

每次默认 3–5 条，带目标人群、痛点、hook、三段结构、互动问题、Pattern 支持、风险和评分，并保存为 `topic` Knowledge。

## 28. Viral Structure（爆款结构迁移）

允许学习：

```text
结构
互动机制
信息层级
节奏
```

禁止：逐句改写别人正文、复用原图、搬运作者专属经历、伪造原创经历。

默认：

```text
structure-only
```

输出：

```text
source pattern
为什么有效
适用条件
新的内容角度
新的标题结构
新的正文结构
新的互动问题
视觉信息层级建议
```

目标：复用机制，不复制表达。

## 29. 运营建议格式

重要建议尽量绑定：

```text
Evidence + Pattern + Metric + Experiment
```

避免泛泛的“多发视频”“标题更吸引人”“加强互动”。

## 30. Weekly Review（周复盘）

固定：

```text
1. 本周发生了什么
2. 数据最大的 3 个变化
3. 高表现内容
4. 低表现内容
5. 评论区需求变化
6. 新 Pattern
7. 被证伪 Pattern
8. 竞品信号
9. 下周 3 个优先选题
10. 下周 1–3 个实验
```

同时写入 `review`、`experiment`、`topic` 并更新 Pattern。

## 31. Monthly Review（月复盘）

重点：

```text
内容支柱占比
各支柱相对表现
爆款依赖度
普通内容基线
账号辨识度
增长稳定性
评论需求变化
Pattern 稳定度
```

## 32. 运营记忆

每次分析任务前优先检索：

```text
同账号
同主题
同结构
最近 7–30 天
active/strong Pattern
最近失败 Review
```

目标：不重复犯已经记录过的错误。

## 33. 检索返回格式

默认：

```text
结论
证据：post_key / 标题 / 时间 / 指标 / Pattern / Review
适用范围
风险或不确定性
下一步
```

不要只返回表格行。

## 34. Google Sheets v5 表

```text
accounts
account_snapshots
posts
post_snapshots
comments
runs
content_features
comment_features
video_features
knowledge
experiments
search_index
alerts
```

前 6 张为事实；中间 4 张为分析与运营；`search_index` 为检索；`alerts` 为通知。

## 35. Google Drive 目录

```text
/zhenji
├── evidence/<account>/YYYY-MM-DD/{profile,posts,comments,feed}
├── reports/{weekly,monthly,account-audits,competitive}
└── knowledge/{accounts,topics,patterns,reviews,experiments}
```

Google Sheets 是结构化主库，Drive 人类可读文档是辅助层，不能维护两套冲突事实。

## 36. Knowledge Card

重要 Pattern/Review 可额外生成 Markdown（Markdown 文档）知识卡，但必须包含相同 `knowledge_id`，对应 Sheets 中同一条记录。

## 37. 一致性

```text
写 Facts
→ 确认成功
→ 写 Features
→ 更新 search_index
→ 写 Knowledge
→ 更新 last_seen_post_key
```

Facts 写入失败：不推进游标。

Knowledge 写入失败：Facts/Features 保留，Run 标记 partial，Knowledge 可后补。

## 38. 版本

保存：

```text
schema_version
analysis_version
pattern_mining_version
```

## 39. 任务类型

```text
baseline
incremental
post_followup
comment_sample
feed_sample
search_research
video_lueying
video_tinglan
video_guanlan
account_audit
competitive_analysis
post_analysis
comment_insights
pattern_mining
topic_ideation
weekly_review
monthly_review
retrieve
repair
```

## 40. Retrieve 优先历史库

用户问历史问题时，先查数据库，不要一上来重新操作手机。只有问题明确需要最新状态时，才先采集再检索。

## 41. 风险边界

不得：

```text
保证必爆/必涨粉
把个性化推荐流当全平台事实
把模型推断写成页面事实
用少量样本做确定性因果结论
通过自动高频互动做增长
绕过验证
复制他人受保护内容
```

## 42. 最终准则

```text
采集的是事实。
分析的是结构。
保存的是历史。
检索的是证据。
沉淀的是模式。
运营的是实验。
复盘的是结果。

不要只监控账号，
要让历史数据逐渐变成运营能力。

一次屏幕只观察一次；
一批事实只集中写入一次；
重复动作先封装再复用；
视频默认先掠影，再按价值升级。
```



# V4 · 无人值守运行时（长批处理可选）

> **v5.1 标注**：V4 章节所有规则在 v5.1 中**改为可选 / 建议性**。用户可在 zhenji 之外选择遵循或覆盖。详见 §68。

V4 的目标是让长批处理尽可能无人值守。`phone-harness` 或其他真机控制层只提供观察和真实输入能力；甄姬自己的 Unattended Supervisor（无人值守监督器）负责 Watchdog、Recovery、Keepalive、Checkpoint 与恢复后重建。

## 43. 三种运行行为必须分开

```text
Watchdog
= 只读监测连接、窗口与页面

Recovery
= 在用户预授权范围内恢复明确识别的镜像恢复页

Safe Keepalive
= 确实等待时，在暂停前执行当前页面已验证的无副作用真实 HID 输入
```

不得把观察动作伪装成保活：

```text
screenshot()       ≠ keepalive
connection_state() ≠ keepalive
screen_info()      ≠ keepalive
caffeinate          ≠ iOS keepalive
activate()          ≠ iOS keepalive
```

只有真实业务 HID 输入，或 verified Safe Keepalive HID 输入，才更新 `last_real_input_at`。

## 44. Idle Calibration（空闲超时标定）

不要在 Skill 中硬编码“iPhone Mirroring N 分钟暂停”。

首次无人值守运行、相关系统版本变化或发生提前暂停后，标定当前真实环境：

```text
READY
→ 不发送任何 HID
→ 只读轮询 connection_state / screen_info / screenshot
→ 检测 idle pause
→ 记录 T1
→ 自动恢复
→ 重复 T2 / T3
→ idle_timeout = min(T1,T2,T3)
```

然后：

```text
keepalive_after = idle_timeout × trigger_ratio
```

默认 `trigger_ratio=0.80`，它只是相对于实测阈值的提前量，可以配置；不是对暂停时间的猜测。

标定按环境键保存：

```text
macOS version
iOS version
phone-harness version
Mirroring build
```

环境变化或发生早于预期的 idle pause 时，使旧标定失效并重新标定。

## 45. Safe Keepalive（安全保活）

当没有真实业务动作、且 `last_real_input_at` 已接近实测阈值时：

```text
重新识别当前页面
↓
KNOWN_SAFE ?
├─ 否 → 不输入 / 必要时冻结
└─ 是
    ↓
该页面存在 verified keepalive action ?
├─ 否 → 不输入
└─ 是
    ↓
执行真实 HID
    ↓
wait_stable
    ↓
重新验证页面仍为原状态
    ↓
更新 last_real_input_at
```

优先级：

```text
1. 原本就需要执行的真实业务动作
2. 已验证的可逆小幅滚动
3. 已验证的安全区域点击
4. 没有候选动作则不发送 HID
```

不得使用随机点击、随机滑动或全局固定坐标保活。

以下页面禁止 Safe Keepalive：

```text
LOGIN_REQUIRED
DEVICE_UNLOCK
PASSWORD
SECURITY_CHALLENGE
UNKNOWN_UNSAFE
MIRROR_RECOVERY
```

## 46. Watchdog（看门狗）

长批处理前启动长驻 Watchdog，并持续刷新：

```text
connection_state()
screen_info()
screenshot()
page_state()
```

这些只用于判断健康状态，不更新真实输入时钟。

使用 background backend（后台输入后端）；`frontmost=False` 正常。不得为了 Watchdog 主动移动镜像窗口。

## 47. 自动恢复

V4 以无人值守为目标，默认：

```yaml
watchdog:
  recovery_mode: auto_connect
```

当且仅当当前页面明确识别为 `MIRROR_RECOVERY` 且明确识别恢复按钮时，可以自动点击：

```text
Connect / Continue / 连接 / 继续
```

点击前后都必须重新读取：

```text
connection_state
screen_info
screenshot
page_state
```

允许有限次数、带退避重试；禁止盲目连点。

自动恢复授权不延伸到：

```text
密码
设备解锁
Face ID / Touch ID 替代
验证码
CAPTCHA / 人机验证
平台安全挑战
账号登录验证
```

这些状态立即保存断点并冻结业务输入。

## 48. 恢复后全部位置状态失效

镜像恢复后永远不要复用：

```text
window_bounds / mirror_offset
旧 Card Map
旧 OCR Observation Cache
旧点击坐标
旧滚动位置假设
```

恢复成功：

```text
重新 screen_info
→ 重新 screenshot
→ 重新 page_state
→ 清 Observation Cache
→ 清 Card Map
→ 根据 post_key / last_seen / checkpoint 重新定位
→ 继续批处理
```

## 49. Input Guard（输入总闸）

所有业务输入和 Safe Keepalive 都必须通过：

```python
guard.assert_input_allowed()
```

Watchdog 一旦把状态设为 `INPUT_FROZEN`，所有业务 Worker 与保活 Worker 都停止发送输入。

## 50. Checkpoint（断点）

异常前至少保存：

```text
run_id
platform
account_key
task
stage
post_key
list_cursor
last_seen_post_key
pending_write_batch_id
video_mode
watchdog_state
last_real_input_at
idle_timeout_seconds
keepalive_after_seconds
observed_at
```

Facts 尚未持久化成功时，不推进 `last_seen_post_key`。

## 51. V4 运行观测

记录：

```text
watchdog_polls
connection_recoveries
keepalive_actions
keepalive_failures
unexpected_idle_pauses
idle_timeout_seconds
keepalive_after_seconds
```

Google Sheets v5 额外提供：

```text
runtime_calibration
runtime_events
```

用真实数据评估无人值守稳定性，不凭感觉修改保活间隔。

## 52. V4 默认执行流

```text
加载环境指纹
↓
存在有效 Idle Calibration ?
├─ 否 → 标定实际 idle timeout
└─ 是 → 读取实测值
↓
Preflight
↓
启动 Watchdog
↓
Batch Worker 持续执行业务
↓
每个真实 HID → reset last_real_input_at
↓
确实等待且到 keepalive_after ?
├─ 否 → 继续等待 / 只读 Watchdog
└─ 是 → 当前页验证 → Safe Keepalive → 再验证
↓
异常？
├─ MIRROR_RECOVERY → auto recovery → invalidate caches → resume checkpoint
├─ security/unknown → checkpoint + INPUT_FROZEN
└─ 无 → 继续
```

## 53. V4 最终准则

```text
不猜暂停时间，先标定。
不拿截图冒充保活，只认真实输入。
有业务就做业务；等待过久才做安全保活。
保活必须绑定当前页面并前后验证。
连接可自动恢复，安全挑战不自动突破。
恢复后不相信任何旧坐标和旧缓存。
每次中断都有断点，每次恢复都重新观察。
```


# V5 · 真机链接采集 + 本地媒体流水线

V5 将视频处理从“iPhone 实时播放给模型看”改为：

> **真机负责发现内容与取得可信分享链接；Mac 负责下载、转录、抽帧、场景切分和分析。**

这是 V5 的默认视频架构。

> **v5.1 标注**：V5 章节中"必须"、"严禁"、"禁止"的措辞在 v5.1 中**改为"建议 / 最佳实践"**。用户可选择更宽松或更严格的运行模式。详见 §69。

## 54. Link Harvester（分享链接采集器）

视频作品进入详情页后，优先执行：

```text
当前作品 Observation
→ phone-harness 打开分享面板
→ 点击「复制链接」
→ Mac 读取系统剪贴板
→ 从分享文本提取支持的 URL
→ Resolver（解析器）校验
→ 与当前作品提示信息比对
→ 入 media queue
```

允许的链接来源包括：

```text
xiaohongshu.com
xhslink.com
```

以后平台适配器可扩展：

```text
instagram.com
tiktok.com
```

### 54.1 防止拿到上一条剪贴板

每次复制前记录 clipboard fingerprint（剪贴板指纹）。

只有满足以下条件才接受：

1. 剪贴板内容发生变化；
2. 能提取当前平台支持的 URL；
3. Resolver 能解析；
4. 返回媒体类型符合当前作品；
5. 当页面已有标题、作者、作品 ID 等提示时，尽可能交叉校验。

如果失败：

```text
不推进当前作品游标
→ 重新观察当前页
→ 最多再执行一次分享复制
→ 仍失败则记录 share_link_failed
```

禁止因为剪贴板有一个合法旧链接就把它绑定到当前作品。

实现：

```text
scripts/clipboard_link.py
scripts/share_link_flow.py
```

### 54.2 Action Recipe（真机操作知识库，V5.2）

V5.2 把"在 App 里怎么拿到分享链接"从**截图 + OCR 视觉探索**固化为**声明式 recipe**，让真机采集从"每次重新规划"变为"加载配方即执行"。

执行链路：

```text
Platform Knowledge (references/platform-recipes/<platform>.yaml)
    ↓ ActionRecipeEngine.load
    ↓ engine.run(harness, validator)
逐 action：
    screen_info() → 当前窗口 LiveBounds
    normalized ratio (0-1) → ratio_to_screen() → 真实屏幕坐标
    harness.tap / semantic_tap / open_app ...
    validator 校验状态（share_panel_visible / clipboard_changed / url_match）
    ↓
成功：拿到分享链接
失败：抛 RecipeStepError → 调用方转视觉探索 fallback（仅 5% 路径）
```

硬规则：

- 坐标**只允许 normalized ratio (0-1)**；任何绝对像素（x:1320, y:850）被 `validator` 直接拒绝。运行时由 `screen_info()` 拿窗口 bounds 换算真实坐标。
- 每个 action 必须至少一个 validation；无校验则无法确认状态，应走视觉探索。
- harness / validator 以 Protocol 注入，离线可测（FakeHarness）。
- 平台差异只存在于 Action Recipe 与 Media Adapter 两层；Queue / Worker / Pipeline / Analysis 全部共用。

`references/platform-recipes/` 现状：

```text
xhs.yaml       production
douyin.yaml    beta（坐标待真机校准）
instagram.yaml router_only 骨架（adapter 未实现）
tiktok.yaml    router_only 骨架（adapter 未实现）
```

平台状态以 `references/platform-status.yaml` 为准（production / beta / router_only）。

实现：

```text
scripts/action_recipe/schema.py
scripts/action_recipe/validator.py
scripts/action_recipe/engine.py
references/platform-recipes/*.yaml
references/platform-status.yaml
scripts/platform_status.py
```

## 55. 真机与媒体分析彻底解耦

禁止默认串行：

```text
手机打开 A
→ 播放 A
→ 等 A 分析
→ 写表
→ 手机打开 B
```

默认 Producer–Consumer（生产者–消费者）：

```text
iPhone Collector
A 链接 → B 链接 → C 链接 → D 链接 ...

Downloader
A 下载 ─┐
B 下载 ─┼─ 并行
C 等待 ─┘

Local Analyzer
A 抽帧
B 转录
C 下载

Storage
按阶段批量写入
```

手机拿到链接并校验后，应尽快返回列表继续采下一条。

## 56. Media Queue（媒体任务队列）

所有分享链接先进入本地持久队列，而不是直接阻塞当前手机任务。

默认使用 SQLite：

```text
runtime/media-jobs.sqlite3
```

状态：

```text
queued
downloading
downloaded
processing
done
retry
failed
```

至少记录：

```text
job_id
platform
post_key
source_url
mode
priority
state
attempts
backend
output_dir
metadata_json
error
created_at
updated_at
```

特点：

- URL + post_key 去重；
- Worker 崩溃后可恢复；
- 支持多个下载 Worker；
- 支持下载完成即分析；
- 不需要等待整个账号全部下载完成。

实现：`scripts/media_queue.py`

## 57. XHS Media Adapter（小红书媒体适配器）

V5 支持两种本地获取后端：

```text
auto
├── smile7up adapter（若配置了本地脚本）
└── yt-dlp direct（直接调用 yt-dlp）
```

参考公开项目：

```text
smile7up/xiaohongshu-downloader
```

该项目采用 MIT License（MIT 许可证）。V5 默认不复制其实现源码，而是提供适配器调用本地 checkout；如果未配置，则直接使用 `yt-dlp`。

完整分享链接，尤其包含 `xsec_token` 的链接，应在取得后尽快解析/进入下载队列，不应先囤积数百条再统一处理。

实现：

```text
scripts/xhs_media.py
licenses/smile7up-xiaohongshu-downloader-MIT.txt
```

## 58. V5 三档视频模式

三级名称不变，但“数据源”改成本地媒体。

### 掠影 · 效率模式

默认：

```text
分享链接
→ probe metadata
→ 480p 低成本副本
→ 8 个左右均匀关键帧
→ 快速内容分类
```

默认不做完整转录。

适合：

```text
账号几十 / 几百条视频初筛
竞品大样本
推荐流研究
搜索样本
```

### 听澜 · 基本模式

默认：

```text
分享链接
→ 720p 或成本合适的本地副本
→ 提取音频
→ 字幕优先 / Whisper 回退
→ 完整 transcript
→ 8–12 个关键帧
→ 内容结构分析
```

这是大多数视频的默认深度模式。

### 观澜 · 完整模式

默认：

```text
分享链接
→ best / 1080p 可用质量
→ 完整本地视频
→ 完整转录
→ Scene Detection
→ 场景关键帧
→ 音画时间轴对齐
→ video_structure_json
```

只处理高价值样本。

## 59. Local Media Tools（本地媒体工具）

依赖：

```text
yt-dlp
ffmpeg / ffprobe
faster-whisper（可选；无平台字幕时使用）
```

本地处理：

```text
scripts/ffmpeg_tools.py
scripts/transcription.py
scripts/media_pipeline.py
```

媒体文件不直接塞进 Google Sheets。

本地 / Drive 保存：

```text
video
audio
subtitle
transcript
keyframes
scene frames
metadata json
```

Sheets 只保存结构化字段、状态、ID 和资源引用。

## 60. 下载失败回退

下载失败不能等价为“作品不存在”。

失败分类：

```text
expired_link
resolver_failed
authentication_required
captcha_or_security
no_video_format
network_error
tool_missing
unknown
```

策略：

```text
可重试错误
→ 指数退避
→ 必要时重新获取一次新分享链接

不可安全自动解决
→ media job 标记 failed / blocked
→ 手机主采集流程可继续
```

可配置最后回退到 V4 的镜像视频路径：

```yaml
media:
  fallback:
    mirror_video_processing: true
```

它是 fallback（回退），不是 V5 默认路径。

## 61. Google Sheets v5

新增：

```text
share_links
media_jobs
media_assets
```

并扩展：

```text
video_features
runs
```

核心关系：

```text
post
 ↓
share_link
 ↓
media_job
 ↓
media_asset
 ↓
video_feature
```

具体字段见：

```text
schemas/google-sheets-schema-v5.json
```

## 62. 跨平台准备

V5 的 Link Harvester 与 Media Queue 不绑定小红书。V5.2 进一步把平台专属逻辑收敛到两层：

```text
Action Recipe   → 真机怎么操作（references/platform-recipes/*.yaml + scripts/action_recipe/）
Media Adapter   → 内容怎么获取（scripts/media_adapters.py + xhs_adapter / douyin_adapter）
```

其余 Queue / Worker / Pipeline / Analysis / Storage 全部平台无关、共用。

统一入口：

```text
URL
↓
platform_router
├── xhs
├── instagram
└── tiktok
```

当前生产实现只保证 XHS（小红书）；IG / TikTok 先保留平台路由与接口，不宣称已完成适配。

实现：`scripts/platform_router.py`

## 63. V5 默认视频执行流

```text
发现作品
↓
读取页面事实
↓
是否视频？
├─ 否 → 图文流程
└─ 是
    ↓
phone-harness 分享 → 复制链接
    ↓
clipboard changed?
├─ 否 → 重试一次 / 记录失败
└─ 是
    ↓
解析 URL + probe 校验
    ↓
enqueue media job
    ↓
手机立即处理下一条
    │
    └────────────────────────────┐
                                 ↓
                         Media Workers
                                 ↓
                    掠影 / 听澜 / 观澜
                                 ↓
                        本地结构化结果
                                 ↓
                         Batch Write
```

## 64. V5 最终准则

> **手机时间最贵。能在 Mac 本地异步完成的事情，不占用 iPhone。**

> **视频默认不实时陪看；先取得真实分享链接，再本地处理。**

> **链接先校验再绑定作品；旧剪贴板链接不得误配。**

> **边采边下、边下边识别、边识别边分析；不等待整批结束。**

> **掠影负责吞吐量，听澜负责大多数理解，观澜负责少数深度研究。**


# v5.1 Changelog 与扩展

## 65. phone-harness 作为 zhenji 内置依赖

v5.1 起，phone-harness 是 zhenji **bundled** 依赖，不再要求用户：

- 单独从 codeload.github.com 拉 zip
- 在 setup 文档中独立列出 install 步骤
- 假设外部 phone-harness skill 已 install

**集成方式**：

```text
zhenji
├── scripts/phone_harness/   ← v5.1 新增子包
│   ├── __init__.py          Python API: tap / screenshot / screen_info / connection_state / ...
│   ├── cli.py               subprocess 包装：phone-harness <<'PY' ... PY
│   ├── geometry.py          iOS Mirroring 窗口坐标系 (440×970, offset 1216,25)
│   └── sentinel.py          剪贴板哨兵协议
└── ...
```

**调用方式**：

```python
from zhenji.scripts.phone_harness import (
    tap, screenshot, screen_info, connection_state, activate_mirror,
    run_heredoc, clipboard_read, clipboard_set,
)
```

**自动探测**：`scripts/phone_harness/__init__.py` 用 `shutil.which('phone-harness')` 查找 `$PATH` 中的可执行文件。如果未找到：

- 不下载（不联网拉 zip）
- 提示用户通过 WorkBuddy Skill marketplace 安装 `phone-harness` skill

## 66. 浮光 (fuguang) — 第四档视频模式

v5.1 起，zhenji 引入第四档 `fuguang`（浮光），与掠影/听澜/观澜并列。详见 `scripts/video_modes.py`：

```python
FUGUANG = VideoMode(
    key="fuguang", zh_name="浮光", purpose="真机陪看抽帧，无需本地副本",
    keyframes_min=4, keyframes_max=10,
    transcript="none", scene_detection=False,
    requires_local_copy=False, local_quality=",
,
)
LUEYING = ...  # 已有
TINGLAN = ...  # 已有
GUANLAN = ...  # 已有
```

四档路由优先级（`choose_mode()`）：

```text
requires_timeline=True  → 观澜
requires_full_understanding / high_value  → 听澜
rapid_scan_only=True  → 浮光（兜底，explicit 覆盖其他条件）
默认  → 掠影
```

**典型用例**：

- **浮光**：只想决定这条视频值不值得继续看，0 网络下载成本（避风控）
- **掠影**：要看产品包装 / 关键画面
- **听澜**：要全文本分析（口播内容）
- **观澜**：复刻 / 入 Pattern 库

## 67. 四档 wall-clock 参考（实测）

来自 2026-08-22 benchmark（24s 短视频、Intel Mac）：

| 档 | wall-clock（首次）| wall-clock（缓存后）| mp4 | 帧 | 转录 | 场景 |
|---|---|---|---|---|---|---|
| 浮光 | 34.8s | 34.8s | 0 | 9 | 0 | 0 |
| 掠影 | 4.5s | 4.5s | 2.7 MB | 8 | 0 | 0 |
| 听澜 | 83.7s | 19.5s | 3.6 MB | 10 | 183 | 0 |
| 观澜 | 218.1s | ~70s | 4.3 MB | 24 | 181 | 15 |

听澜/观澜的首次 wall-clock 受**模型下载**拖累；后续复用极快。

## 68. phone-harness 强约束 → 建议性（v5.1 去强）

以下 v4/v5 中标注"必须 / 严禁 / 禁止"的行为，**在 v5.1 中改为建议性**。用户可选择遵循或覆盖：

| 旧措辞 | 新措辞 | 备注 |
|---|---|---|
| 严禁 long_press > 1s（SIGKILL） | **建议** long_press < 1s；已知偶发 SIGKILL | 自行决定 |
| 必须 idle_calibration 才能无人值守 | **建议**首次无人值守前做 calibration | 可手动设置 keepalive interval |
| 必须 input guard (`assert_input_allowed()`) | **建议** Watchdog 设 `INPUT_FROZEN` 时停止输入 | 自行决定 |
| 必须 Safe Keepalive 验证 | **建议**保持页面验证后动作 | 自行决定 |
| 必须验证 Connect/Continue 才点 | **建议**仍人工把关 | zhenji 不擅自决策 |

如需恢复 v5 严格的强约束行为，可在 `scripts/unattended_runtime.py` 中开启 `strict=True` 参数。

## 69. V5 强约束 → 建议性

| 旧措辞 | 新措辞 |
|---|---|
| **必须** Mac Chrome 登录 web 小红书 | **建议**登录以解锁 yt-dlp；未登录时返回 V4 fallback |
| **必须**用 PSSD venv 装 faster-whisper | **建议**系统盘 < 20GB 空闲时用 PSSD venv |
| **必须**`HF_ENDPOINT=https://hf-mirror.com` | **建议**本地 proxy 502 阻挡 huggingface.co 时用 mirror |
| **必须**卸 hf-xet + 降 huggingface_hub<0.27 | **建议**；hf-mirror 不全 mirror Xet 时启用 |
| **必须** `shutil.rmtree` 替代 `rm -rf` | **建议** sandbox safe-delete 阈值 ≥ 50 时启用 |

详见 `references/zhenji_setup.md`（v5.1 新增）。

## 70. 工程加速默认值（v5.1 固化）

```yaml
# ~/.zhenji/setup.yaml 推荐配置
phone_harness:
  bundled: true                       # v5.1 默认 bundled
  path: ${PHONE_HARNESS_BIN:-$(which phone-harness)}
  auto_install: false                 # 不再自动拉 zip；用户手动

video:
  default_mode: lueying
  upgrade_to_tinglan_threshold_engagement: 50   # 互动 ≥ 50 时升级听澜
  upgrade_to_guanlan_threshold_engagement: 500  # 互动 ≥ 500 时升级观澜
  upgrade_to_guanlan_pinned: true              # 置顶视频永远观澜

audio:
  venv: /Volumes/PSSD/Projects/zhenji/audio-venv
  hf_endpoint: https://hf-mirror.com
  hf_home: /Volumes/PSSD/Projects/zhenji/hf-cache
  huggingface_hub_max: "0.27"          # 避免 Xet storage

platforms:
  xhs: enabled
  instagram: stub
  tiktok: stub
```

## 71. v5.1 不引入的破坏性变更

- V4 Unattended Supervisor 仍可用（运行时仍可启用）
- V5 Link Harvester / Media Queue 仍是默认主路径
- 视频三档（掠影/听澜/观澜）不变，仅新增浮光为第四档
- Google Sheets v5 schema 不变

## 72. v5.1 后续待办

- 把 `references/zhenji_setup.md`（v5.1）写完整：含 PSSD venv、hf-mirror、shutil.rmtree 详细步骤
- 把 `benchmarks/scripts/bench.py` 与 `process_xhs_url` 整合成单一入口 `scripts/harvest.py`
- 给 zhenji 加 `--strict` / `--relaxed` CLI flag，让用户在严格/宽松模式之间切换
- 把 V5.x changelog 从 SKILL.md 抽出到 `CHANGELOG.md`，避免主文件越来越长


# v5.1.1 抖音 (douyin) 适配器

## 73. douyin 适配器 v0

### 73.1 适配能力边界

抖音水印 + X-Bogus / a_bogus 签名比小红书复杂。v5.1.1 的 v0 实现：

| 能力 | 状态 | 说明 |
|---|---|---|
| platform_router 路由 douyin.com / iesdouyin.com / v.douyin.com | ✅ | smoke test 通过 |
| iesdouyin API 拿 metadata（title / author / cover_url / play_url）| ✅ | 免 cookie，仅需 msToken（默认用 UA + Referer）|
| yt-dlp Douyin extractor 拿视频本体 | ⚠️ | 需用户 Chrome 已登录 douyin web |
| X-Bogus / a_bogus 签名 | ❌ | v0 未实现，需手动签名或 f2 集成 |
| 视频本体下载（无水印） | ❌ | v0 通过 play_url 拿带水印版本，未做去水印 |

### 73.2 抖音反爬约束（实测发现）

iPhone 上抖音即使已登录，敏感操作仍触发短信验证：

```
tap 长按 video → 触发 "请输入验证码" 登录页
tap share button → 通常需要登录态 + 短信验证
```

这是抖音平台反爬策略，**zhenji 不能绕过**。当前依赖：

1. 用户手动 share → 复制链接 → 把链接给 zhenji
2. zhenji 用 platform_router 识别为 douyin
3. 用 iesdouyin API 拿 metadata（免登录）
4. yt-dlp 兜底（需 Chrome cookie）

### 73.3 调用方式

```python
from scripts.douyin_media import download
from scripts.platform_router import route_url

url = "https://v.douyin.com/iABCxyz/"
route = route_url(url)  # → PlatformRoute(key="douyin", supported=True)
dl = download(
    url,
    output_dir="/Users/vuyin/WorkBuddy/zhenji/staging/<post_key>",
    mode="lueying",  # or "tinglan" / "guanlan"
    backend="auto",  # yt_dlp first, fallback to iesdouyin
    cookies_from_browser="chrome",
)
```

### 73.4 四档在 douyin 的特殊说明

| 档 | douyin 特殊点 |
|---|---|
| 浮光 | ✅ 完全支持（无需登录）|
| 掠影 | ⚠️ 需 yt-dlp cookie 或 iesdouyin metadata + 第三方下载 |
| 听澜 | ⚠️ 同上 |
| 观澜 | ⚠️ 同上，且 X-Bogus 签名阻碍完整时间轴抓取 |

### 73.5 v5.1.2+ 待办

- 集成 `f2` (johnserf-seed/f2) Python 包，处理 X-Bogus 签名
- 或集成 `Douyin_TikTok_Download_API` (douyin.wtf) 公开 API 服务
- 实测 iesdouyin API 在中国 ip 上的可达性
