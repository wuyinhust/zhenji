# 甄姬（zhenji）

> **流眄监其变，采珠存其真，流精辨其势，殊观得其机。**

「甄姬」取“真机”谐音，是一个以真实 iPhone 为观察入口的社交媒体内容情报技能。当前首个生产适配器为小红书，后续可扩展到 Instagram（照片与短视频社交平台）、TikTok（短视频平台）等。

## 洛神四象

| 能力 | 《洛神赋》意象 | 系统职责 |
|---|---|---|
| **流眄** | 「流眄乎洛川」 | 真机监测：观察账号、作品、评论、搜索与推荐流 |
| **采珠** | 「或采明珠，或拾翠羽」 | 内容入库：结构化保存事实、时间序列和证据 |
| **流精** | 「转眄流精」 | 模式分析：账号诊断、内容归因、评论洞察、模式挖掘 |
| **殊观** | 「俯则未察，仰以殊观」 | 运营发现：选题、建议、实验与周期复盘 |

```text
流眄 → 真机观察
  ↓
采珠 → 结构化保存
  ↓
流精 → 模式与规律
  ↓
殊观 → 选题与实验
  ↓
真实结果重新进入流眄
```

二级术语：**复形 · 检索**、**离合 · 趋势**、**绵思 · 长期记忆**、**陈纲 · 归纳**。



## 视频模式（V5.1+ 四档体系）

V5.1.1 起，V5 的「掠影 / 听澜 / 观澜」扩充为四档：

```text
浮光 fuguang
真机快速陪看，不下载，0 网络，0 风控，~35s/视频
    适用：决定值不值得看
    ↓
掠影 lueying
480p 本地副本 + 6–12 关键帧
    ~4.5s/视频（含本地副本已缓存）
    适用：批量筛选 + 看产品包装 / OCR
    ↓
听澜 tinglan
720p + 本地音频 + 完整转录（faster-whisper small）
    ~20s/视频（模型已缓存）
    适用：要全文本分析、口播抓字
    ↓
观澜 guanlan
best 视频 + medium 转录 + 24 帧 + scene detection
    ~70s/视频（模型已缓存）
    适用：复刻结构、入 Pattern 库
```

四档对 `MediaFetchResult.status` 的最低要求：

| 档 | 接受状态 |
|---|---|
| fuguang | `metadata_only` 或 `media_ready` |
| lueying | `media_ready` |
| tinglan | `media_ready` |
| guanlan | `media_ready` |

运行时同时启用：

```text
Observation Cache（观察缓存）  → 同一屏只 OCR 一次
Card Map（卡片地图）           → 同一列表布局不重复探索
Batch Write（批量写入）        → 一批内容集中修改工作簿
Helper Macro（辅助宏）          → 重复成功动作自动复用
```

对应文件：

```text
references/video-modes.md
references/runtime-performance.md
references/helper-macros.md
scripts/runtime_cache.py
scripts/write_buffer.py
scripts/action_macros.py
scripts/video_modes.py
scripts/phone_helpers.py
schemas/google-sheets-schema-v3.json
```


## V5.1 · phone-harness 内置 adapter

V5.1 把 phone-harness 接入方式重新定义：

- 不再要求用户从 codeload.github.com 单独 download
- zhenji 内置 `scripts/phone_harness/` adapter，运行时探测外部 CLI
- 找不到 phone-harness 时给清晰提示让用户从 WorkBuddy Skill marketplace 安装
- v5 中"必须 idle calibration / 必须 input guard"等强约束改为可配置，
  `PHONE_HARNESS_STRICT=1` 恢复严格行为

V5.1.2 重要修正：

- "bundled" 措辞改为"内置 adapter"——实际仍依赖外部 CLI
- dynamic geometry：默认常量仅 fallback，运行时必须 `screen_info()` 拿真实窗口
- 移除运行时固定镜像偏移作为 global coordinate

V4 在 V3 性能优化之上新增真正的长批处理运行时：

```text
Idle Calibration  → 实测当前 iPhone Mirroring 空闲暂停阈值
Real Input Clock   → 只统计真实 HID 输入
Safe Keepalive     → 暂停前执行当前页面已验证的无副作用真实输入
Watchdog           → 持续监测镜像与页面状态
Auto Recovery      → 明确恢复页自动 Connect / Continue
Checkpoint         → 异常保存断点
Cache Invalidate   → 恢复后重建窗口、OCR 与卡片状态
```

不把 `screenshot()`、`connection_state()`、`screen_info()`、`caffeinate` 或 `activate()` 当作 iOS 保活保证。

无人值守默认使用 `auto_connect`；密码、设备解锁、验证码、安全挑战和未知页面仍然冻结业务输入。

对应新增：

```text
references/unattended-runtime-v4.md
references/migration-v3-v4.md
scripts/idle_calibration.py
scripts/keepalive.py
scripts/unattended_runtime.py
schemas/google-sheets-schema-v4.json
```


## 平台支持（V5.1+ 多平台）

| 平台 | 状态 | Adapter |
|---|---|---|
| XHS 小红书 | Production | `scripts/xhs_adapter.py` |
| Douyin 抖音 | Experimental v0 | `scripts/douyin_adapter.py` |
| Instagram | Planned | router_ready |
| TikTok | Planned | router_ready |

平台架构：

```text
phone-harness (内置 adapter)
    ↓
Share Link Harvester
    ↓
platform_router         (scripts/platform_router.py)
    ↓
URL Resolver            (DouyinAdapter.resolve_url)
    ↓
Adapter Registry        (scripts/media_adapters.py)
 ┌─────────┼──────────┐
 XHS    Douyin       (future IG/TT)
  ↓        ↓
MediaFetchResult       (scripts/media_adapter_protocol.py)
    ↓
Media Queue            (scripts/media_queue.py)
    ↓
Generic Media Worker   (scripts/media_worker.py)
    ↓
Local Media Pipeline   (scripts/media_pipeline.py)
    ↓
浮光 / 掠影 / 听澜 / 观澜
    ↓
Batch Storage (Sheets / Drive / 本地)
```

核心原则：平台差异只留在 Adapter 层；Queue / Worker / FFmpeg / Whisper / Analysis 全部共用。

## V5 · 真机拿链接，本地看视频

V5 把视频主路径改成：

```text
iPhone + phone-harness
发现作品 → 分享 → 复制链接
                ↓
            本地队列
                ↓
        下载 / 转录 / 抽帧
                ↓
        掠影 / 听澜 / 观澜
                ↓
            批量入库
```

核心变化：

- iPhone 不再默认实时播放完整视频给模型看；
- `phone-harness` 主要负责取得当前作品的真实分享链接；
- 复制前后校验 Mac 剪贴板变化，避免把上一条链接绑定到当前作品；
- 分享链接立即解析并进入 SQLite 媒体队列；
- 下载、Whisper 转录、FFmpeg 抽帧和场景切分在 Mac 后台并行；
- 支持“边采链接、边下载、边识别、边分析”，不等整个账号全部下载完成；
- 小红书下载支持 `smile7up/xiaohongshu-downloader` 适配器或直接 `yt-dlp`；
- 原来的镜像播放分析降级为下载失败时的可选 fallback（回退）。

三档视频模式的数据源也改为本地媒体：

```text
掠影 · 效率：480p + 6–12 关键帧
听澜 · 基本：本地音频 + 完整转录 + 少量关键帧
观澜 · 完整：完整视频 + 转录 + 场景切分 + 时间轴
```

新增核心文件：

```text
scripts/platform_router.py
scripts/clipboard_link.py
scripts/share_link_flow.py
scripts/media_queue.py
scripts/xhs_media.py
scripts/ffmpeg_tools.py
scripts/transcription.py
scripts/media_pipeline.py

references/media-pipeline-v5.md
references/share-link-harvest-v5.md
references/migration-v4-v5.md
schemas/google-sheets-schema-v5.json
```

## 系统能力

```text
真实 iPhone 采集
→ Google Sheets（谷歌表格）结构化数据库
→ Google Drive（谷歌云端硬盘）证据
→ 内容与评论结构化
→ 结构化 / 关键词 / 可选语义检索
→ 账号、作品、评论、竞品分析
→ Pattern（模式）
→ Topic（选题）
→ Experiment（实验）
→ Review（复盘）
```

核心数据分为四层：

```text
L0 Evidence  原始证据
L1 Facts     可观察事实
L2 Features  内容与评论结构特征
L3 Knowledge 可复用运营知识
```

## 目录

```text
zhenji/
├── SKILL.md
├── README.md
├── CHANGELOG.md
├── VERSION
├── SOURCES.md
├── examples/
│   ├── config.example.yaml
│   └── query-examples.md
├── references/
│   ├── data-model.md
│   ├── knowledge-loop.md
│   ├── ops-analysis.md
│   ├── retrieval.md
│   ├── luoshen-naming.md
│   ├── runtime-performance.md
│   ├── video-modes.md
│   ├── helper-macros.md
│   ├── media-pipeline-v5.md
│   ├── share-link-harvest-v5.md
│   ├── unattended-watchdog.md
│   ├── unattended-runtime-v4.md
│   ├── migration-v2-v3.md
│   ├── migration-v3-v4.md
│   ├── migration-v4-v5.md
│   └── zhenji_setup.md       ← V5.1+ (PSSD venv, HF mirror, etc.)
├── scripts/
│   ├── action_macros.py
│   ├── checkpoint.py
│   ├── clipboard_link.py
│   ├── douyin_adapter.py     ← V5.1+ Douyin MediaAdapter
│   ├── douyin_media.py       ← V5.1+ low-level 抖音 utilities
│   ├── ffmpeg_tools.py
│   ├── idle_calibration.py
│   ├── keepalive.py
│   ├── media_adapter_protocol.py  ← V5.1+ MediaFetchResult + Protocol
│   ├── media_adapters.py     ← V5.1+ ADAPTERS registry
│   ├── media_pipeline.py     ← V5.1+ generic, no platform hardcode
│   ├── media_queue.py
│   ├── media_worker.py       ← V5.1+ generic, registry-based
│   ├── phone_harness/        ← V5.1+ built-in phone-harness adapter
│   │   ├── __init__.py
│   │   ├── geometry.py       ← dynamic 窗口坐标
│   │   └── sentinel.py       ← 剪贴板哨兵
│   ├── phone_helpers.py
│   ├── platform_router.py    ← V5.1+ strict 域名匹配
│   ├── runtime_cache.py
│   ├── share_link_flow.py
│   ├── transcription.py
│   ├── unattended_runtime.py
│   ├── video_modes.py        ← V5.1+ 四档体系
│   ├── watchdog.py
│   ├── write_buffer.py
│   ├── xhs_adapter.py        ← V5.1+ XhsAdapter (wraps xhs_media)
│   └── xhs_media.py
├── schemas/
│   ├── google-sheets-schema-v2.json
│   ├── google-sheets-schema-v3.json
│   ├── google-sheets-schema-v4.json
│   └── google-sheets-schema-v5.json
├── tests/
│   ├── test_v4_runtime.py
│   ├── test_v5_media_pipeline.py
│   ├── test_platform_router.py        ← V5.1+
│   ├── test_douyin_media.py           ← V5.1+
│   ├── test_media_adapter_registry.py ← V5.1+
│   └── test_phone_harness_geometry.py ← V5.1+
└── .github/workflows/test.yml          ← V5.1+ minimal CI
```

## 安装

```bash
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills/zhenji"
cp SKILL.md "${CODEX_HOME:-$HOME/.codex}/skills/zhenji/SKILL.md"
cp -R references schemas examples scripts "${CODEX_HOME:-$HOME/.codex}/skills/zhenji/"
```


## 无人值守默认策略

长批处理先执行 Preflight（预检）并启动 Watchdog。无业务动作且接近实测 idle timeout（空闲超时）时，才执行当前页面已注册、已验证的 Safe Keepalive（安全保活）真实 HID 输入。

镜像进入明确恢复页时，默认 `auto_connect` 自动恢复；恢复成功后所有位置相关缓存全部失效并重新观察，再从 checkpoint（断点）继续。


### V5 运行依赖

```bash
brew install yt-dlp ffmpeg
```

需要本地 Whisper（可选）：

```bash
python -m pip install faster-whisper
```

如使用 `smile7up/xiaohongshu-downloader`：

```yaml
media:
  downloader:
    backend: auto
    smile7up_script: "/path/to/xiaohongshu-downloader/scripts/download_xiaohongshu.py"
```

未配置该脚本时，`auto` 自动回退到直接调用 `yt-dlp`。
