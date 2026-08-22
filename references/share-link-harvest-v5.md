# V5 · 分享链接采集

## 标准流程

```text
确认当前作品详情页
↓
记录当前 Clipboard（剪贴板）指纹
↓
phone-harness 打开分享面板
↓
重新观察分享面板
↓
点击「复制链接」
↓
轮询 Mac Clipboard
↓
内容变化
↓
提取支持平台 URL
↓
Resolver probe
↓
与当前作品 hint 交叉校验
↓
接受
```

## 为什么必须做剪贴板指纹

Universal Clipboard（通用剪贴板）同步可能有延迟。

如果本次复制没有成功，而 Mac 里仍保留上一条合法小红书 URL，不做变化检查会产生严重的 post-link 错配。

因此：

```text
old_fingerprint == new_fingerprint
→ 不接受
```

## 当前作品提示

能获取时保留：

```text
post_key
note_id
title
author
note_type
```

probe 返回 metadata 后至少确认：

```text
是支持平台
是视频或符合预期作品类型
```

标题 / 作者可做弱匹配，不能因为文本略有差异误拒绝。

## 重试

最多默认重新执行一次“分享 → 复制链接”。

仍失败：

```text
share_link_failed
→ 保存 evidence
→ 手机继续下一条
```

不要无限点击。
