# 检索设计

检索顺序：

```text
1. 结构化字段过滤
2. 指标排序
3. search_text 关键词
4. 标签/实体扩展
5. 可选语义检索
```

自然语言解析为：

```yaml
intent:
doc_types:
accounts:
topics:
time_window:
metrics:
features:
knowledge_status:
sort:
limit:
```

回答必须包含：结论、证据、时间范围、样本范围、不确定性。
