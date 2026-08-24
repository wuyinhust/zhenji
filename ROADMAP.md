# zhenji Roadmap

> 当前稳定版本：5.2.2  
> 本文件描述未来版本计划，不代表相关功能已经实现。

甄姬未来从“观察与内容情报”扩展到完整的 **Observe → Understand → Decide → Act** 闭环。

核心原则：

```text
设备能力决定能不能做
权限模型决定允不允许做
Action Recipe 决定具体怎么做
功能代码完成 ≠ 功能开发完成
```

当前以后只保留三种运行模式：

```text
A. Real Device iOS
B. Real Device Android
C. Browser Intelligence
```

不规划 Headless Mode。

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
分析对标账号近期内容，提炼可迁移选题
读取自己的帖子与评论，寻找下一篇内容机会
```

L0 属于读取 / 研究平面，默认可以无人值守执行，但仍受平台与 Backend 能力限制。

---

## L1 · 应和 / 互动

目标：对经过 L0 判断后的高价值内容进行轻量、可逆互动。

能力范围：

```text
点赞
取消赞
收藏
取消收藏
评论点赞 / 取消评论点赞
```

默认权限：用户显式开启后执行。

L1 不用于批量制造互动量；行为预算是甄姬自己的产品约束，不代表平台“安全阈值”。

---

## L2 · 成言 / 表达

目标：让 AI 参与公开表达，同时默认保留人工控制。

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
→ 执行
→ 验证发布结果
→ 写入审计记录
```

默认权限：`confirm`。

自己的帖子评论运营优先于主动对外评论。

---

## L3 · 布篇 / 发布

目标：建立完整 Creator / Publishing 能力。

能力范围：

```text
发布内容
删除自己发布的内容
未来扩展：编辑、草稿、定时、图片 / 视频 / 多素材发布
```

默认权限：`confirm`。

L3 的核心价值不是单篇代发，而是为未来多账号内容运营提供统一执行层：

```text
内容策略 / 素材库
→ 多账号内容计划
→ 审核
→ 发布队列
→ 按账号执行
→ 回收真实表现
→ 回到 L0 分析
```

“批量”指工作流和队列层面的批处理，不意味着绕过平台限制、验证码或安全挑战。

---

# 2. 三种 Device Backend

v5.3 开始，甄姬不再把 iPhone 写死为唯一入口，而是通过统一 Device Backend 暴露能力。

详细架构见：

```text
references/v5.3-device-backend-interface.md
```

## A. Real Device iOS

```text
backend: ios_mirror
mode: real_device_ios
```

旗舰执行后端：真实 iPhone + iPhone Mirroring + phone-harness。

适合：

```text
真实 App 浏览
推荐流研究
高价值账号使用
分享链接获取
未来 L1 / L2 / L3
```

---

## B. Real Device Android

```text
backend: android_device
mode: real_device_android
```

真实 Android 执行后端。

要求：

```text
Android 与 iOS 分别录制 Action Recipe
不得直接复用 iOS 坐标或状态假设
同一动作分别验收
```

例如：

```text
xhs.share_link.ios
xhs.share_link.android
```

Android Backend 的接口与框架进入 v5.3，但实际平台支持必须等待真实 Android Recipe 验收；Android 不阻塞 v5.3 发布。

---

## C. Browser Intelligence

```text
backend: browser
mode: browser_intelligence
```

Browser 不是手机模拟器，而是公开 Web Intelligence 后端。

重点支持：

```text
公开搜索
公开账号研究
公开帖子读取
公开评论读取（平台允许时）
对标账号分析
竞品分析
URL / 媒体进入现有分析流水线
```

明确限制：

```text
不等价于 App 推荐流
不假装拥有真实设备行为
不自动继承手机 Action Recipe
不把浏览器认证视为 iPhone 账号认证
```

**Browser Intelligence 是 v5.3 的 P0 实际开发目标。**

---

# 3. 四个核心产品场景

## 场景 A · 搜索选题

```text
主题 / 品类 / 人群 / 问题
→ 搜索关键词 / 话题
→ 读取代表作品
→ 读取评论
→ 聚类用户问题 / 痛点 / 争议 / 高互动结构
→ 结合历史 Pattern
→ Topic Pool（选题池）
```

目标不是返回搜索结果，而是：

```text
Search → Evidence → Pattern → Topic
```

优先通过 Browser Intelligence 实现；真机模式则使用各平台对应 Action Recipe。

---

## 场景 B · 对标账号选题

```text
指定 1–N 个对标账号
→ 采样近期内容 + 高表现内容
→ 读取重点评论
→ 比较主题 / Hook / 封面 / 结构 / 互动
→ 提炼可迁移 Pattern
→ 生成自己的选题
```

重点输出：

```text
值得学
不值得学
只适合对方账号
可迁移结构
内容空白区
下一轮实验选题
```

目标是复用结构、用户需求与已验证模式，不是复制内容。

---

## 场景 C · 自己的帖子：评论运营

这是 L0 + L1 + L2 的组合场景。

```text
自己的帖子
→ L0 读取新增评论 / 回复
→ AI 分类
   ├─ 普通互动
   ├─ 问题
   ├─ 购买意向
   ├─ 投诉 / 风险
   ├─ 高价值用户
   ├─ 内容请求
   └─ spam / 无需处理
→ Decide
   ├─ 值得点赞 → L1
   ├─ 需要针对性回复 → L2
   ├─ 点赞 + 回复 → L1 + L2
   └─ 忽略 / 人工升级
```

未来形成 Comment Inbox（评论工作台）：

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

---

## 场景 D · 发布 / 多账号起号

L3 必须具备发布能力，即使初期主要价值不是单篇代发。

长期流程：

```text
账号定位
→ 批量生成选题
→ 内容生产 / 素材准备
→ 账号级审核队列
→ L3 发布
→ 监测表现
→ 更新账号策略
```

未来扩展：

```text
多账号内容日历
账号 × 内容一一映射
发布队列
素材完整性校验
最终预览
人工批准
真机发布
结果回读
失败重试 / 人工接管
```

---

# 4. Action Recipe 是开发完成的硬门槛

任何真机动作统一采用：

```text
Platform Knowledge
→ Action Recipe
→ Backend Execution
→ State Validation
→ Failure Fallback
→ Metrics
```

不允许出现：

```text
功能代码已经写了
但每次仍然截图 → 猜按钮 → 临时点击
→ 就宣称平台已经支持
```

一个真机动作只有满足以下 DoD（Definition of Done）才算开发完成：

```text
[ ] Recipe ID 已定义
[ ] Backend 已明确（ios / android）
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

Browser Intelligence 不要求“真机录制”，但也必须有等价的可重复执行定义、页面状态验证、失败状态和平台能力声明。

不同平台、不同 Backend 分别验收：

```text
xhs.like.ios
xhs.like.android
douyin.like.ios
douyin.like.android
```

不能因为一个平台 / Backend 已完成，就把其他平台 / Backend 标成完成。

---

# 5. 5.2.2 之后的正式版本计划

## v5.3 · Device Backend + L0 Topic Intelligence

v5.3 合并两个原本分开的目标：

```text
Device Backend Layer
+
L0 Topic Intelligence
```

### P0 · Device Backend Interface

统一三种 Backend：

```text
A. Real Device iOS
B. Real Device Android
C. Browser Intelligence
```

统一接口目标：

```text
connect
health_check / state
screenshot（适用时）
navigate
click / tap
swipe（适用时）
input
extract
```

现有 iPhone Mirror 接入统一接口；Android 建立正式接口与 Recipe 规范；不保留 Headless Mode。

### P0 · Browser Intelligence

这是 v5.3 最优先实际开发能力：

```text
小红书 Web 搜索
公开帖子读取
公开账号主页研究
公开评论读取（可用时）
对标账号采集
URL / 媒体接入现有 Pipeline
```

Browser 模式首先服务 L0，不优先承担 L1–L3。

### P1 · L0 Topic Intelligence

重点把“选题”做完整：

```text
搜索选题
对标账号选题
自己的帖子 / 评论读取
跨样本 Topic Pool
```

完成条件：

```text
DeviceBackend 可工作
+
Browser Intelligence 核心路径可工作
+
对应真机路径拥有 Action Recipe
+
搜索 / 账号 / 评论进入现有 Facts / Features / Knowledge
```

Android 实际平台支持不阻塞 5.3，但任何 Android 能力对外标记 supported 前必须完成 Android 真机 Recipe 验收。

---

## v5.4 · L1 Interaction Plane · 应和

新增：

```text
点赞 / 取消赞
收藏 / 取消收藏
评论点赞 / 取消评论点赞
```

增加：

```text
权限开关
幂等判断
行为审计
账号级行为预算
```

每个平台、每个 Backend 的动作 Recipe 完成后才开放对应能力。

---

## v5.5 · L2 Expression Plane · 成言

新增：

```text
评论
针对具体评论的回复
Comment Inbox
AI 草稿 → 用户确认 → 执行
```

优先级：

```text
自己的帖子评论运营 > 外部帖子主动评论
```

必须验证 target comment identity、文本内容和最终发布状态。

---

## v6.0 · L3 Publishing Plane · 布篇

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

# 6. 当前与未来能力边界

当前 5.2.2 仍以**读取、采集、媒体理解、知识沉淀**为主。

本路线图中的：

```text
v5.3 Browser Intelligence / L0 扩展
v5.4 L1 点赞 / 收藏
v5.5 L2 评论 / 回复
v6.0 L3 发布 / 删除
```

均属于未来能力，不应因为本文件存在就被 Agent 解释为“已经可以执行”。

平台状态仍以：

```text
references/platform-status.yaml
```

为准。

未来只有同时满足对应能力所需的：

```text
Backend ready
+
Adapter / business logic ready
+
Action Recipe 或 Browser execution definition ready
+
validation ready
+
platform-status promoted
```

才算真正完成一个平台能力。
