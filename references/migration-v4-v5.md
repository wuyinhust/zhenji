# V4 → V5

V4 重点：无人值守运行时。

V5 在此基础上改变视频数据路径。

## 不变

- Watchdog（看门狗）
- Idle Calibration（空闲超时标定）
- Safe Keepalive（安全保活）
- Checkpoint（断点）
- Observation Cache（观察缓存）
- Card Map（卡片地图）
- Batch Write（批量写入）
- Pattern / Topic / Experiment / Review

## 改变

V4：

```text
视频 → iPhone 镜像播放 / 捕获 → 分析
```

V5：

```text
视频 → 分享链接 → 本地队列 → 下载 → 本地分析
```

## 数据表

新增：

```text
share_links
media_jobs
media_assets
```

`video_features` 增加本地媒体来源引用。

## 回退

如果分享链接采集或下载完全失败，可选择回退 V4 镜像视频流程；该流程不再是默认路径。
