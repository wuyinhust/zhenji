# 甄姬 zhenji

> **真机驱动的社交媒体内容情报 Skill**  
> 流眄监其变，采珠存其真，流精辨其势，殊观得其机。

甄姬（`zhenji`，取“真机”谐音）让 AI 通过一台真实 iPhone 观察社交媒体 App，把账号、作品、公开视频、评论和互动信号转成可检索、可复盘的结构化内容情报。

它不是一个单纯的“下载器”，也不是一个网页爬虫。它把两类能力组合在一起：

1. **真机操作层**：通过 iPhone Mirroring + `phone-harness` 看到真实 App、执行点击/滑动/复制链接，并用 Action Recipe 复用稳定动作；
2. **媒体与情报层**：拿到分享链接后，在 Mac 本地异步下载、抽帧、转录、分析，再进入账号监控、竞品研究、选题和复盘流程。

当前版本：**5.2.2**。

## 视觉形象

<p align="center">
  <img src="assets/character/zhenji-luoshen-character-sheet.png" alt="甄姬·洛神古装三视图" width="900" />
</p>

---

## 适合做什么

甄姬适合需要“真实 App 环境 + 大批量内容研究”的任务，例如：

- 持续监控一组小红书账号的新增作品和互动变化；
- 批量浏览抖音账号/推荐流，快速取得视频分享链接并在 Mac 本地分析；
- 建立竞品内容数据库：标题、正文、视频结构、评论需求、互动快照；
- 从几十到几百条视频里先快速筛选，再对高价值内容做完整转录和镜头分析；
- 将长期观察结果沉淀为 Pattern（模式）、Topic（选题）、Experiment（实验）和 Review（复盘）；
- 为后续 Instagram / TikTok 海外内容研究复用同一套真机操作与媒体处理架构。

如果任务可以直接通过稳定网页/API 完成，没有必要使用真机；甄姬的价值在于**需要真实手机 App 状态、真实账号环境或移动端界面时**。

---

## 当前平台支持

| 平台 | 当前状态 | 真机 Action Recipe | Media Adapter | 说明 |
|---|---|---:|---:|---|
| 小红书 XHS | **production** | ✅ | ✅ | 当前主要生产平台 |
| 抖音 Douyin | **beta** | ✅ | ✅ / 部分能力受平台登录与验证影响 | 已接入统一流水线 |
| Instagram | **router_only** | 骨架 | 未完成 | URL 路由与 Recipe 结构已预留 |
| TikTok | **router_only** | 骨架 | 未完成 | URL 路由与 Recipe 结构已预留 |

平台状态的机器可读定义见：`references/platform-status.yaml`。

> `router_only` 不等于“已经支持采集”。它表示平台已经进入统一架构，但生产 Adapter 尚未完成。

---

## 它是怎么工作的

```text
真实 iPhone App
     ↓
phone-harness
看屏幕 / OCR / 点击 / 滑动 / 复制链接
     ↓
Action Recipe
已知动作直接执行；异常时才视觉探索
     ↓
Share Link Harvester
校验剪贴板变化 + 平台 URL
     ↓
Platform Router
     ↓
Media Adapter Registry
XHS / Douyin / future IG / TikTok
     ↓
SQLite Media Queue
     ↓
Mac 本地 Worker 并行处理
下载 / 抽帧 / 音频 / Whisper / Scene Detection
     ↓
浮光 / 掠影 / 听澜 / 观澜
     ↓
Facts → Features → Knowledge
     ↓
Google Sheets / Google Drive / 本地证据
```

### 为什么不让 AI 一直“看手机视频”

手机时间是整个系统最贵的资源。V5 开始，视频默认流程是：

```text
手机只负责：发现作品 → 分享 → 复制真实链接 → 继续下一条
Mac 负责：下载 → 转录 → 抽帧 → 分析 → 入库
```

这样可以边采链接、边下载、边识别、边分析，而不是让 iPhone 等完整视频播放完再处理下一条。

---

## 四档视频理解

甄姬不会对所有视频都做最重的分析，而是按成本分四档：

| 模式 | 用途 | 本地媒体要求 |
|---|---|---|
| **浮光 fuguang** | 真机快速判断“值不值得继续看” | 可仅 metadata / 真机视觉 |
| **掠影 lueying** | 大样本批量初筛 | 低成本本地视频 + 6–12 个代表帧 |
| **听澜 tinglan** | 大多数口播、知识、测评、剧情解说 | 本地视频 + 完整音频转录 + 少量关键帧 |
| **观澜 guanlan** | 高价值样本、镜头结构、复刻研究 | 完整视频 + 转录 + Scene Detection + 时间轴 |

默认升级路径：

```text
全部样本
  ↓
浮光 / 掠影
  ↓ 高价值
听澜
  ↓ 需要镜头级研究
观澜
```

## 四档视频理解（图示）

<table>
  <tr>
    <td align="center"><img src="assets/icons/modes/fuguang.png" width="220" alt="浮光" /><br/><strong>浮光</strong></td>
    <td align="center"><img src="assets/icons/modes/lueying.png" width="220" alt="掠影" /><br/><strong>掠影</strong></td>
    <td align="center"><img src="assets/icons/modes/tinglan.png" width="220" alt="听澜" /><br/><strong>听澜</strong></td>
    <td align="center"><img src="assets/icons/modes/guanlan.png" width="220" alt="观澜" /><br/><strong>观澜</strong></td>
  </tr>
</table>

---

# 安装

## 1. 环境要求

当前真机 iPhone 工作流要求：

- macOS Sequoia 或更新版本；
- 可正常使用 Apple **iPhone Mirroring（iPhone 镜像）**；
- Python 3.10+；
- 一台已经与 Mac 配对的 iPhone；
- Terminal / Codex / Claude Code 所在进程获得 macOS **Accessibility（辅助功能）** 与 **Screen Recording（屏幕录制）** 权限。

媒体流水线建议安装：

```bash
brew install yt-dlp ffmpeg
```

需要本地 Whisper 转录时：

```bash
python3 -m pip install faster-whisper
```

Action Recipe YAML 建议安装：

```bash
python3 -m pip install pyyaml
```

---

## 2. Clone 甄姬

```bash
git clone https://github.com/wuyinhust/zhenji.git
cd zhenji
```

---

## 3. phone-harness 已完整包含在仓库里

从 5.2.2 起，甄姬不再只放一个 wrapper。

仓库内完整包含固定版本：

```text
vendor/phone-harness/
```

上游来源：

```text
https://github.com/ShawnPana/phone-harness
pinned commit: 47f37a6dd5baae9f10f16e21e50a6898ee42cd22
license: MIT
```

包含上游的：

```text
README.md
SKILL.md
install.md
onboarding.md
phone-harness launcher
pyproject.toml
agent-workspace/
src/phone_harness/
LICENSE
```

也就是说，一次 clone 就已经取得甄姬所需的完整 phone-harness 源码快照。

安装它的 Python 依赖：

```bash
python3 -m pip install -e vendor/phone-harness
```

然后检查：

```bash
./vendor/phone-harness/phone-harness --doctor ios
```

甄姬运行时的 phone-harness 查找顺序为：

```text
1. PHONE_HARNESS_BIN 显式指定
2. vendor/phone-harness/phone-harness（默认）
3. $PATH 中其他 phone-harness
```

因此正常使用本仓库时不需要再单独 clone phone-harness。

---

## 4. 第一次连接 iPhone

1. 在 Mac 上手动打开一次 **iPhone Mirroring** 并完成 Apple 的首次配对；
2. 给运行甄姬的 Terminal / Agent 进程授权：
   - System Settings → Privacy & Security → Accessibility
   - System Settings → Privacy & Security → Screen Recording
3. 如果刚开启 Screen Recording 权限，重启 Terminal / Agent；
4. 执行：

```bash
./vendor/phone-harness/phone-harness --doctor ios
```

通过后，甄姬才能可靠执行截图、OCR 与真实 HID 输入。

完整 phone-harness 原始说明仍保留在 `vendor/phone-harness/README.md`、`install.md` 和 `onboarding.md`。

---

# 作为 Agent Skill 使用

仓库根目录的 `SKILL.md` 是甄姬的 Agent Skill 入口。

以 Codex 为例，可以把整个仓库放入 skill 目录，或建立软链接：

```bash
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
ln -s "$(pwd)" "${CODEX_HOME:-$HOME/.codex}/skills/zhenji"
```

如果目标位置已经存在，请先自行处理旧目录/软链接。

也可以直接告诉 Codex / Claude Code：

```text
Read README.md and SKILL.md in this zhenji repository. Install the vendored
phone-harness from vendor/phone-harness, run its iOS doctor, then use zhenji's
Action Recipes and media pipeline for the requested social-media research task.
Do not rediscover known fixed UI actions unless the recipe fails validation.
```

---

# 批量运行前建议检查

如果准备长时间、批量运行，建议先完成以下检查：

```text
[ ] iPhone Mirroring 已连接并稳定
[ ] phone-harness --doctor ios 通过
[ ] Mac 不会自动睡眠
[ ] yt-dlp / ffmpeg 可用
[ ] 需要听澜/观澜时，Whisper 已安装且模型可用
[ ] 当前平台 Recipe 已真机校准
[ ] runtime/ 有足够磁盘空间
[ ] Media Queue 可写
```

V4/V5 运行时还提供：

- Watchdog（看门狗）
- Checkpoint（断点）
- Idle Calibration（空闲暂停标定）
- Safe Keepalive（安全保活）
- Observation Cache（观察缓存）
- Card Map（卡片地图）
- Batch Write（批量写入）

这些能力用于长批处理时恢复连接、减少重复 OCR/探索和避免游标错误推进。

---

# Action Recipe：不要每次重新找按钮

V5.2 的关键变化是 **Action Recipe（动作配方）**。

对固定 App 页面，甄姬不应该每次：

```text
截图 → OCR → 猜按钮 → 点击 → 再猜
```

而应该：

```text
Platform Recipe
→ 直接执行已知动作
→ 每一步验证
→ Recipe 失败时才进入视觉探索
```

Recipe 位于：

```text
references/platform-recipes/
├── xhs.yaml
├── douyin.yaml
├── instagram.yaml
└── tiktok.yaml
```

坐标使用 0–1 的 normalized ratio（归一化比例），运行时根据最新 `screen_info()` 动态换算，避免把某一台 Mac 的绝对屏幕坐标写死。

---

# 媒体 Adapter

平台差异只保留在两层：

```text
Action Recipe：App 里怎么操作
Media Adapter：分享 URL 怎么解析/获取媒体
```

之后的模块全部复用：

```text
Queue
Worker
FFmpeg
Whisper
Analysis
Storage
```

统一 Adapter 接口见：

```text
scripts/media_adapter_protocol.py
scripts/media_adapters.py
```

当前注册：

```text
xhs_adapter.py
douyin_adapter.py
```

---

# 数据模型

甄姬把数据分四层：

```text
L0 Evidence   原始证据
L1 Facts      可直接观察的事实
L2 Features   内容/评论/视频结构特征
L3 Knowledge  可复用的运营知识
```

典型 Fact：

```text
accounts
account_snapshots
posts
post_snapshots
comments
runs
share_links
media_jobs
media_assets
```

分析层包括：

```text
content_features
comment_features
video_features
knowledge
experiments
search_index
alerts
```

Google Sheets schema 演进记录位于 `schemas/`。

---

# 目录速览

```text
zhenji/
├── SKILL.md
├── README.md
├── CHANGELOG.md
├── VERSION
├── LICENSE
├── SOURCES.md
│
├── vendor/
│   └── phone-harness/          # 完整固定上游源码快照
│       ├── README.md
│       ├── SKILL.md
│       ├── install.md
│       ├── onboarding.md
│       ├── phone-harness
│       ├── pyproject.toml
│       ├── agent-workspace/
│       ├── src/phone_harness/
│       └── LICENSE
│
├── scripts/
│   ├── phone_harness/          # zhenji 对 vendored runtime 的适配层
│   ├── action_recipe/          # 真机动作配方引擎
│   ├── platform_router.py
│   ├── platform_status.py
│   ├── xhs_adapter.py
│   ├── douyin_adapter.py
│   ├── media_adapter_protocol.py
│   ├── media_adapters.py
│   ├── media_queue.py
│   ├── media_worker.py
│   ├── media_pipeline.py
│   ├── ffmpeg_tools.py
│   ├── transcription.py
│   ├── watchdog.py
│   └── unattended_runtime.py
│
├── references/
│   ├── platform-status.yaml
│   ├── platform-recipes/
│   ├── media-pipeline-v5.md
│   ├── unattended-runtime-v4.md
│   └── ...
│
├── schemas/
├── examples/
├── assets/                 # 视觉素材：角色三视图 + 技能/模式/路线图图标
└── tests/
```

---

# 许可证与上游

甄姬仓库自身使用 MIT License。

`vendor/phone-harness/` 来源于 `ShawnPana/phone-harness`，上游同样使用 MIT License；原始版权与许可文本完整保留在：

```text
vendor/phone-harness/LICENSE
```

小红书媒体获取流程还参考/兼容 `smile7up/xiaohongshu-downloader`，其许可说明保存在 `licenses/` 与 `SOURCES.md`。

---

# 当前边界

- 真机 UI 会随 App 版本变化，Recipe 必须通过状态验证，不能把坐标当永久事实；
- 登录、验证码、设备解锁、平台安全挑战可能要求用户介入；
- Douyin 当前仍是 beta，部分媒体获取能力依赖登录态/平台接口可用性；
- Instagram / TikTok 目前不是 production Adapter；
- 本项目不保证平台内部非公开接口长期稳定；
- 批量运行前应先用少量样本验证当前 App 版本、Recipe 和媒体下载链路。

---

## 洛神四象

甄姬内部用《洛神赋》意象命名四类核心能力：

| 名称 | 职责 |
|---|---|
| **流眄** | 真机监测 |
| **采珠** | 内容入库 |
| **流精** | 模式分析 |
| **殊观** | 运营发现 |

> **流眄监其变，采珠存其真，流精辨其势，殊观得其机。**

## 核心技能

<table>
  <tr>
    <td align="center"><img src="assets/icons/skills/liumian.png" width="220" alt="流眄" /><br/><strong>流眄</strong><br/>真机监测</td>
    <td align="center"><img src="assets/icons/skills/caizhu.png" width="220" alt="采珠" /><br/><strong>采珠</strong><br/>内容入库</td>
    <td align="center"><img src="assets/icons/skills/liujing.png" width="220" alt="流精" /><br/><strong>流精</strong><br/>模式分析</td>
    <td align="center"><img src="assets/icons/skills/shuguan.png" width="220" alt="殊观" /><br/><strong>殊观</strong><br/>运营发现</td>
  </tr>
</table>

## 风控与账号隔离

批量运行时，甄姬默认采用“真机高价值账号 + Mac 低频网络获取 + 本地高并发分析”的隔离策略。高价值账号留在 iPhone；Mac 优先无账号，必须认证时使用固定研究号；不使用日抛号池、自动换号或自动换 IP 作为风控恢复。429/5xx 采用有界退避，验证码、IP block、安全挑战直接暂停平台网络队列。详见 `references/risk-control-and-account-isolation.md`。

## 路线图能力

<table>
  <tr>
    <td align="center"><img src="assets/icons/roadmap/xunti.png" width="220" alt="寻题" /><br/><strong>寻题</strong><br/>v5.3 · L0 Topic Intelligence</td>
    <td align="center"><img src="assets/icons/roadmap/yinghe.png" width="220" alt="应和" /><br/><strong>应和</strong><br/>v5.4 · L1 Interaction Plane</td>
    <td align="center"><img src="assets/icons/roadmap/chengyan.png" width="220" alt="成言" /><br/><strong>成言</strong><br/>v5.5 · L2 Expression Plane</td>
    <td align="center"><img src="assets/icons/roadmap/bupian.png" width="220" alt="布篇" /><br/><strong>布篇</strong><br/>v6.0 · L3 Publishing Plane</td>
  </tr>
</table>
