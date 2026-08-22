# V5 · 本地媒体流水线

## 目标

把 iPhone 从“视频播放器”变成“可信内容发现器 + 分享链接采集器”。

```text
phone-harness
→ 当前作品
→ 分享 / 复制链接
→ URL 校验
→ SQLite 队列
→ 本地下载
→ 本地抽帧 / 音频 / 转录
→ 内容分析
→ 批量入库
```

## 为什么更快

旧流程的串行瓶颈：

```text
手机播放视频
→ 等视频时长
→ 反复截图
→ OCR
→ 模型分析
→ 下一条
```

V5：

```text
手机：A 链接 → B 链接 → C 链接 → D 链接

Mac Worker 1：A 下载 → C 下载
Mac Worker 2：B 下载 → D 下载
Analyzer：A 抽帧 / B 转录 / C 分类
```

手机不等待媒体分析。

## 流水线阶段

1. `harvested`：取得并校验分享 URL。
2. `queued`：进入持久队列。
3. `downloading`：本地获取媒体。
4. `downloaded`：已有本地资产。
5. `processing`：抽帧、音频、字幕、Whisper、场景分析。
6. `done`：结构化结果完成。
7. `failed`：保留错误类型，可重试或重新获取链接。

## 三档模式

### 掠影

- 480p；
- 6–12 个代表画面；
- metadata；
- 默认无完整 transcript。

### 听澜

- 720p；
- 音频；
- 字幕优先；
- Whisper 回退；
- 完整 transcript；
- 8–12 个关键帧。

### 观澜

- best；
- 完整视频；
- 完整 transcript；
- Scene Detection（场景切分）；
- 音画时间轴；
- `video_structure_json`。

## 下载优先级

新作品和高价值竞品可以提升 priority。

队列不能因为一条失败阻塞后续作品。

## 链接时效

小红书分享链接可能包含时效参数。取得 URL 后立即：

```text
probe
→ enqueue
→ worker 尽快下载
```

不要先收集大量链接，数小时后才处理。
