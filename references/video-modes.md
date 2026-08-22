# 视频三档模式

## 掠影 · 效率模式

用途：批量筛选。

目标：用最少手机占用获得“是否值得继续看”的答案。

默认输出：

```text
metadata
cover / first frame
6–12 representative frames
visible subtitle snippets
visible engagement metrics
short summary
content_type
topic
hook_guess
```

不要求完整 transcript（转录文本）。

## 听澜 · 基本模式

用途：绝大多数值得理解的口播、知识、测评、剧情解说视频。

输出：

```text
掠影全部字段
full transcript（能力可用时）
timestamped segments
spoken hooks
spoken CTA
small keyframe set
body structure
```

策略：音频优先，视觉只补足语音无法说明的信息。

如果当前环境不能可靠捕获应用音频：

1. 不伪造 transcript；
2. 降级为字幕 OCR + 关键帧；
3. 标记 `transcript_status=unavailable|partial`。

## 观澜 · 完整模式

用途：重点作品的时序/镜头级分析。

输出：

```text
full capture reference
transcript
scene boundaries
scene keyframes
visual events
spoken events
hook_start / hook_end
product_appearance_timestamps
cta_timestamps
video_structure_json
shot_change_rate（可可靠计算时）
```

## 自动模式选择

默认：掠影。

升级到听澜的信号：

- 新作品且需要内容理解
- 互动明显高于账号基线
- 主题命中当前研究目标
- 评论区显示强需求/争议
- 用户明确要求理解视频内容

升级到观澜的信号：

- 需要镜头结构或时间线
- 需要研究前 3 秒/前 5 秒 Hook
- 需要研究产品出现时点
- 需要用于视频制作结构复盘
- 属于关键竞品高表现作品
- 用户明确要求完整模式

## 批量建议

```text
100 条候选
→ 100 条掠影
→ 15–25 条听澜
→ 3–8 条观澜
```

实际比例由任务价值决定，不作为硬阈值。

## 采集与分析解耦

手机线程：

```text
打开 → 捕获/采样 → 返回 → 下一条
```

本地分析线程：

```text
转录 → 抽帧 → 场景切分 → 特征提取 → 入库
```

不要让手机等待模型完成上一条视频的全部分析。
