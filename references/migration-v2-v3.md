# v2 → v3 性能版迁移

v3 不要求删除 v2 数据。

新增：

```text
video_features
platform 字段
runs 性能指标字段
Observation（观察）缓存
Card Map（卡片地图）缓存
Batch Write（批量写入）
Learned Macro（学习宏）
```

推荐迁移：

1. 保留现有六张事实表和知识表。
2. 按 `google-sheets-schema-v3.json` 补字段，不重建旧表。
3. 新建 `video_features`。
4. 旧数据 `platform` 默认补 `xhs`，但只在来源明确为小红书时补写。
5. 启用批量写入后，继续遵守“事实成功持久化后才提交游标”。
6. 旧 `content_features` 无需重新全量分析；新作品按 v3 写入，重点旧作品按需补齐视频字段。
