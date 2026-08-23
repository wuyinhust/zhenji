# zhenji Roadmap

> 当前稳定版本：5.2.2  
> 本文件仅描述未来版本计划，不代表相关功能已经实现。

甄姬未来从“观察与内容情报”逐步扩展到完整的 **Observe → Understand → Decide → Act** 闭环。

核心原则：

```text
观察权限 ≠ 行动权限
功能代码完成 ≠ 功能开发完成
```

任何真机能力，只有在对应平台上完成 **Action Recipe 录制、状态校验、失败回退和真机验证** 后，才允许从 roadmap 标记为 implemented / production。

---

# 1. 四级权限模型

## L0 · 选题 / 观察

目标：找到值得研究、值得生产、值得互动的内容机会。

能力范围：

```text
搜索
读取作品
读取评论 / 子评论
账号研究
对标账号研究
推荐流 / 热门样本研究
自己的帖子与评论读取
```

典型任务：

```text
搜索某个关键词，形成选题池
分析某个对标账号最近 30 条内容，提炼选题
读取自己的帖子表现与评论，寻找下一篇内容机会
```

L0 默认可以无人值守执行，因为它属于读取 / 研究平面。

### L0 Action Recipe 最低集合

每个平台至少需要：

```text
open_search
input_query
submit_search
apply_supported_filters
scroll_results
open_post
back_to_results
open_comments
scroll_comments
open_profile
scroll_profile_posts
open_own_post
```

只有这些 Recipe 经过真实 App 验证，平台 L0 才算开发完成。

---

## L1 · 互动

目标：对已经筛选出的高价值内容进行轻量、可逆互动。

能力范围：

```text
点赞
取消赞
收藏
取消收藏
```

L1 不用于批量制造互动量。它服务于“经过 L0 判断后，对少量真正相关内容做精准互动”。

默认权限模型：

```text
L1 = 用户显式开启后可执行
```

未来可以支持行为预算、幂等检查和审计日志，但预算不是“不会触发平台风控”的保证。

### L1 Action Recipe 最低集合

```text
like
unlike
favorite
unfavorite
```

每个动作都必须有：

```text
前置状态识别
动作执行
后置状态验证
幂等判断
失败回退
```

例如：已经点赞时再次执行 `like` 不应造成状态翻转或重复误判。

---

## L2 · 表达

目标：让 AI 参与公开表达，但默认保持人工控制。

能力范围：

```text
评论
回复评论
```

默认流程：

```text
读取上下文
→ AI 生成候选表达
→ 用户确认
→ 真机执行
→ 读取页面确认发布结果
→ 写入审计记录
```

默认权限模型：

```text
L2 = confirm
```

不把自动批量评论作为默认产品模式。

### L2 Action Recipe 最低集合

```text
open_comment_editor
input_comment
submit_comment
open_reply_editor
input_reply
submit_reply
verify_comment_visible
verify_reply_visible
```

必须处理：

```text
键盘状态
输入框焦点
文本是否真正写入
发送按钮状态
发布后页面变化
重复提交保护
```

---

## L3 · 发布

目标：具备完整 Creator / Publishing 能力。

能力范围：

```text
发布内容
删除自己发布的内容
未来扩展：编辑、草稿、定时、图片 / 视频 / 多素材发布
```

默认权限模型：

```text
L3 = confirm
```

发布属于高影响动作，默认流程必须包含最终预览和明确确认。

### 为什么 L3 必须存在

L3 的价值不只是“偶尔帮用户发一篇帖子”。它让甄姬从情报系统成为完整运营系统，并为后续多账号内容运营提供统一执行层。

核心长期场景之一：

```text
内容策略 / 素材库
↓
为多个新账号生成各自内容计划
↓
审核
↓
按账号执行发布
↓
回收真实表现
↓
重新进入 L0 分析
```

也就是说，未来可以支持**批量起号 / 多账号发布工作流**，但必须通过账号级权限、发布队列、内容差异化、人工审批、风控和审计来管理，而不是简单的无差别批量灌入。

### L3 Action Recipe 最低集合

```text
open_create
select_content_type
select_media
verify_media_selected
input_title
input_body
set_topics_or_tags
preview_post
submit_post
verify_publish_success
open_own_post
open_post_menu
delete_post
confirm_delete
verify_delete_success
```

图片发布、视频发布如果 UI 流程不同，应分别拥有独立 Recipe。

---

# 2. 四个核心产品场景

## 场景 A · 搜索选题

```text
用户给主题 / 品类 / 人群 /问题
↓
L0 搜索关键词 / 话题
↓
读取代表作品
↓
读取评论
↓
聚类：用户问题 / 痛点 / 争议 / 高互动结构
↓
结合历史 Pattern
↓
输出 Topic Pool（选题池）
```

目标不是简单返回搜索结果，而是完成：

```text
Search → Evidence → Pattern → Topic
```

验收需要完整的 Search Action Recipe，而不是每次依赖视觉临时探索。

---

## 场景 B · 对标账号选题

```text
指定 1–N 个对标账号
↓
L0 打开账号主页
↓
采样近期内容 + 高表现内容
↓
读取重点作品评论
↓
比较主题 / Hook / 封面 /结构 / 互动
↓
提炼可迁移 Pattern
↓
生成自己的选题
```

重点输出：

```text
值得学
不值得学
只适合对方账号
可迁移到自己的结构
内容空白区
下一轮实验选题
```

不能把“复制对标内容”作为目标；复用的是结构、用户需求和已验证模式。

---

## 场景 C · 自己的帖子：评论运营

这是 L0 + L1 + L2 的组合场景。

```text
自己的帖子
↓
L0 读取新增评论 / 回复
↓
AI 分类
├─ 普通互动
├─ 问题
├─ 购买意向
├─ 投诉 / 风险
├─ 高价值用户
├─ 内容请求
└─ spam / 无需处理
↓
Decide
├─ 值得点赞 → L1
├─ 需要针对性回复 → L2
├─ 点赞 + 回复 → L1 + L2
└─ 忽略 / 人工升级
```

建议未来形成 **Comment Inbox（评论工作台）**：

```text
新评论
→ 分类
→ 建议动作
→ AI 回复草稿
→ 用户确认 L2
→ 执行
→ 验证
→ 保存审计与结果
```

这里的目标是“针对性互动”，不是自动群发模板回复。

需要录制的 Recipe 除 L1/L2 基础动作外，还包括：

```text
open_own_post_comments
locate_comment
like_comment
unlike_comment
reply_to_specific_comment
verify_target_comment_identity
```

尤其必须验证“回复的是哪一条评论”，不能只依赖固定坐标。

---

## 场景 D · 发布 / 多账号起号

L3 必须具备发布能力，即使初期主要价值不是单篇代发。

长期核心场景：

```text
账号定位
↓
批量生成选题
↓
内容生产 / 素材准备
↓
账号级审核队列
↓
L3 真机发布
↓
监测表现
↓
更新账号策略
```

未来可以扩展为：

```text
多账号内容日历
账号 × 内容的一一映射
发布队列
素材完整性校验
最终预览
人工批准
真机发布
发布结果回读
失败重试 / 人工接管
```

“批量”意味着工作流和队列层面的批处理，不意味着绕过平台限制、验证码或安全挑战。

---

# 3. Action Recipe 是开发完成的硬门槛

未来所有真机能力统一采用：

```text
Platform Knowledge
→ Action Recipe
→ Harness Execution
→ State Validation
→ Failure Fallback
→ Metrics
```

不允许出现：

```text
功能代码已经写了
但每次运行仍然截图 → 猜按钮 → 临时点击
→ 就宣称平台已经支持
```

一个动作只有满足以下 DoD（Definition of Done）才算开发完成：

```text
[ ] Recipe ID 已定义
[ ] 目标页面 / 前置状态已定义
[ ] 操作步骤已录制
[ ] 坐标使用可校准 normalized ratio 或语义定位
[ ] 每一步都有 post-condition
[ ] 失败状态可识别
[ ] 有受限 visual fallback
[ ] Recipe 在真实设备上重复验证
[ ] 记录成功率 / 失败原因
[ ] App UI 变化后能够失效而不是误点
[ ] 风控 / CAPTCHA / 登录挑战不会被自动越过
```

对于不同平台，即使语义相同，也分别验收：

```text
xhs.like
Douyin.like
instagram.like
tiktok.like
```

不能因为小红书 `like` 已完成，就把 TikTok `like` 标成完成。

---

# 4. 建议未来版本顺序

以下只是 roadmap，不是当前实现状态。

## v5.3 · L0 Topic Intelligence

重点先把“选题”做完整：

```text
搜索选题
对标账号选题
自己的帖子 / 评论读取
跨样本 Topic Pool
```

开发完成条件：

```text
L0 所需 Action Recipe 真机验收完成
+ 搜索 / 账号 / 评论数据进入现有 Facts / Features / Knowledge
```

---

## v5.4 · L1 Interaction Plane

新增：

```text
点赞 / 取消赞
收藏 / 取消收藏
评论点赞（自己的帖子评论运营场景）
```

增加：

```text
权限开关
幂等判断
行为审计
账号级行为预算
```

每个动作 Recipe 完成后才开放对应能力。

---

## v5.5 · L2 Expression Plane

新增：

```text
评论
针对具体评论的回复
Comment Inbox
AI 草稿 → 用户确认 → 执行
```

核心场景优先级：

```text
自己的帖子评论运营 > 外部帖子主动评论
```

必须确保 target comment identity、文本内容和最终发布状态都可验证。

---

## v6.0 · L3 Publishing Plane

新增完整发布层：

```text
发布
删除
图片 / 视频 Recipe
发布预览
账号级发布队列
发布审计
```

再向上构建：

```text
多账号起号
内容日历
批量内容准备
逐账号审批
批量发布队列
表现回收
策略迭代
```

L3 完成后，甄姬形成：

```text
Discover
→ Research
→ Topic
→ Create
→ Approve
→ Publish
→ Engage
→ Measure
→ Learn
```

---

# 5. 当前与未来能力边界

当前 5.2.2 仍以**读取、采集、媒体理解、知识沉淀**为主。

本路线图中的：

```text
L1 点赞 / 收藏
L2 评论 / 回复
L3 发布 / 删除
```

均属于未来能力，不应因为本文件存在就被 Agent 解释为“已经可以执行”。

平台状态仍以：

```text
references/platform-status.yaml
```

为准。

未来只有同时满足：

```text
Adapter / business logic ready
+
Action Recipe ready
+
real-device validation ready
+
platform-status promoted
```

才算真正完成一个平台能力。
