# 甄姬运行性能规范

## 1. 四个主要瓶颈

1. 重复 OCR（光学字符识别）。
2. 同一页面反复探索卡片位置。
3. 每条内容立即修改 Google Sheets（谷歌表格）。
4. 已经成功多次的导航动作仍由模型逐步重新规划。

## 2. Observe Once（一次观察）

一个稳定页面状态只创建一次 Observation（观察对象）。一次 Observation 应同时包含：

- screenshot（截图）
- OCR rows（文字与位置）
- page type（页面类型）
- security hits（安全词命中）
- anchors（锚点）
- card map（卡片地图，可选）

同一 generation（页面代数）内任何分析都复用它。

动作使 generation 失效，而分析不会。

## 3. 卡片地图

列表/网格页第一次识别后缓存：

- 列中心
- 行距
- 卡片尺寸
- 安全点击区
- 页面顶部/底部不可点击区
- OCR 锚点

缓存仅在当前设备、当前窗口尺寸、当前页面类型和当前会话有效。

返回列表页后先验证锚点，再复用布局。失败就重建。

## 4. 一屏批读

进入列表页后先完成：

```text
observe
→ scan all visible cards
→ local card table
→ choose cards
```

不要对每张卡片单独 OCR。

## 5. Sheets 批处理

所有写操作先进入本地 RunBuffer（运行缓冲区）。

写入阶段：

```text
Facts
→ Features
→ Knowledge/Search Index
→ Cursor Commit
```

Cursor Commit（游标提交）永远最后。

推荐以“一个账号的一次巡检”为默认批次边界。

## 6. 崩溃恢复

RunBuffer 应能序列化为本地 JSON，至少包含：

- run_id
- pending operations
- facts_persisted
- cursor_committed

如果进程中断，下次先检查 staging（暂存）记录，避免重复入库或漏游标。

## 7. 运行性能指标

每个 run 建议记录：

```text
screenshot_count
ocr_calls
ocr_cache_hits
card_map_rebuilds
card_map_hits
phone_actions
macro_hits
macro_fallbacks
sheet_batch_calls
sheet_operations
videos_lueying
videos_tinglan
videos_guanlan
```

这些字段用于判断优化是否真的有效。
