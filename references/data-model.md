# 数据模型

四层：

```text
L0 Evidence → L1 Facts → L2 Features → L3 Knowledge
```

关系：

```text
accounts
├── account_snapshots
└── posts
    ├── post_snapshots
    ├── comments
    ├── content_features
    └── comment_features
            ↓
         knowledge
         ├── pattern
         ├── topic
         ├── review
         ├── experiment
         └── recommendation

所有可检索对象 → search_index
```

原则：事实与推断隔离；任何知识尽量回指 Evidence。
