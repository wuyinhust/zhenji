# 设计参考

运营能力设计参考公开仓库：

```text
Xiangyu-CAS/xiaohongshu-ops-skill
```

参考的是功能与工作流思想，包括账号分析、首页推荐流分析、选题生成、知识库、爆款结构拆解、评论检查与运营边界。

本项目未直接复制或打包该仓库文件。设计时该 GitHub 仓库元数据未声明许可证，因此采用独立实现，只借鉴公开描述的功能思想。

未来若把 `phone-harness` 代码直接 vendoring（内置第三方源码）进本项目，应单独保留其原许可证与版权声明。


## V5 视频获取参考

公开仓库：

```text
smile7up/xiaohongshu-downloader
https://github.com/smile7up/xiaohongshu-downloader
```

用途：参考其小红书分享 URL → `yt-dlp` 下载、资源包、字幕与 Whisper 回退的工作流。

许可证：MIT License，Copyright (c) 2025 smile7up。

V5 默认不复制该仓库实现源码；`scripts/xhs_media.py` 为独立适配层，可调用用户本地 checkout，也可直接调用系统 `yt-dlp`。若未来 vendoring（内置）其源码，必须保留 MIT 版权与许可文本。

许可文本副本：

```text
licenses/smile7up-xiaohongshu-downloader-MIT.txt
```
