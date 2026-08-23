# 风控与账号隔离（Risk Control & Account Isolation）

> zhenji v5.2.2
>
> 目标：保护高价值账号，把平台网络请求限制在最小必要范围；让高吞吐发生在 Mac 本地处理阶段，而不是平台请求阶段。

## 1. 核心原则

甄姬把整个流水线分成两个风险域：

```text
平台侧 / 有风控风险
真实 iPhone App 浏览、分享、复制链接
Mac 对平台的 metadata / media 网络请求

本地侧 / 不触发平台风控
FFmpeg 抽帧
Whisper / ASR 转录
OCR
本地 AI 分析
SQLite / 本地文件处理
```

Google Sheets / Drive 写入不是社交平台风控请求，但仍应批量化以减少不必要的外部 I/O。

默认原则：

```text
手机负责可信发现
Mac 负责低频获取
Mac 本地负责高并发理解
```

不要把“Mac 性能高”理解为“可以高并发请求平台”。

---

## 2. 账号隔离

### 2.1 iPhone：高价值长期账号

真实 iPhone 上可以使用正常长期账号 / 高价值老号，职责限制为：

```text
正常浏览
发现内容
进入作品
打开分享面板
复制真实分享链接
读取公开页面信息
```

默认不自动执行：

```text
点赞
收藏
关注
评论
私信
发布
删除
改账号设置
```

高价值账号不要作为 Mac 批量 API / 下载请求的默认认证来源。

### 2.2 Mac：无账号优先，固定研究号其次

Mac 网络获取按以下优先级选择身份：

```text
1. 无账号 / 无 Cookie 可以完成
   → 不登录

2. 平台要求登录
   → 使用独立、固定、长期的研究账号

3. 高价值老号
   → 默认只留在真实 iPhone App，不作为批量下载/API账号
```

研究账号应保持稳定环境：同一浏览器 profile、稳定 Cookie、稳定网络环境；不要为了恢复风控频繁换号。

### 2.3 不采用“日抛号池”

甄姬不得把以下策略作为自动恢复机制：

```text
验证码 → 换一个新号继续
429 → 轮换账号继续
IP block → 自动换代理 / VPN 继续
账号受限 → 自动创建 / 切换日抛号继续
```

原因不是保证账号间一定可关联，而是：频繁新号、频繁登录环境变化和持续请求会增加系统不稳定性，也会掩盖真实的风控信号。

需要隔离的是：

```text
高价值账号
vs
机器网络请求
```

而不是通过无限轮换账号来继续请求。

---

## 3. 网络窄管道，本地宽管道

默认并发：

```yaml
network_pool:
  download_workers: 1
  probe_workers: 1

local_pool:
  ffmpeg_workers: 4
  transcription_workers: 2
  analysis_workers: 4
```

这些只是保守默认值，可根据机器性能调整本地 worker；平台网络 worker 不应因为 CPU/GPU 空闲而自动扩容。

推荐架构：

```text
Share Link Queue
      ↓
RiskController
      ↓
Network Worker (1)
      ↓
Local Media
 ┌────┼───────────┐
FFmpeg Whisper OCR/AI
 └────┼───────────┘
      ↓
Batch Storage
```

---

## 4. RiskController

所有 Mac → 社交平台的请求应经过统一 RiskController，而不是每个 Adapter 自行无限重试。

最小状态：

```text
CLOSED       正常低速请求
BACKOFF      临时降速
OPEN         平台请求暂停
AUTH_REQUIRED 需要人工恢复登录
```

建议事件映射：

```yaml
signals:
  http_429:
    action: exponential_backoff

  http_5xx:
    action: bounded_retry

  network_timeout:
    action: bounded_retry

  captcha_or_verify:
    action: open_circuit

  ip_blocked:
    action: open_circuit

  session_expired:
    action: auth_required

  signature_error:
    action: open_circuit_and_diagnose
```

### 4.1 可重试错误

只对明确的临时错误做有限重试：

```text
429
500 / 502 / 503 / 504
网络 timeout / reset
```

使用指数退避并设置最大次数，例如：

```text
1s → 2s → 4s + jitter
最多 3 次
```

不要 tight loop（紧循环）。

### 4.2 验证码 / 安全验证

出现验证码、CAPTCHA、安全挑战或明确验证状态：

```text
立即停止该平台 Mac 网络请求
保存 checkpoint
标记 blocked / verification_required
通知用户
```

不得自动突破、代替用户完成或通过换号继续跑。

### 4.3 IP blocked

出现明确 IP block：

```text
OPEN circuit
停止平台网络队列
保留本地分析任务继续运行
等待人工诊断
```

不自动切换代理、VPN、热点或账号继续请求。

### 4.4 Session expired

```text
AUTH_REQUIRED
停止需要认证的网络请求
允许无需认证的本地处理继续
```

需要登录时恢复固定研究号，而不是切换到随机新账号。

---

## 5. 请求去重与缓存

降低风控最有效的方式之一是“不发重复请求”。

应缓存并复用：

```text
share_url
canonical_url
media_id / post_id
xsec_token / equivalent context
resolved metadata
ETag / Last-Modified（平台可用时）
已下载 asset hash
```

规则：

```text
已有本地媒体 → 不重新下载
已有可用 metadata → 不重复 probe
同一分享链接已经 resolve → TTL 内复用
同一 post 已入队 → merge / dedupe，不重复建 job
```

短时 token 有效期未知时，分享链接应尽快进入队列；不要先采几千条再数小时后统一解析。

---

## 6. 真机与 Mac 的职责边界

```text
iPhone / 高价值老号
        ↓
真实 App 正常发现
        ↓
分享 → 复制链接
        ↓
Mac Link Harvester
        ↓
RiskController
        ↓
无账号获取 / 固定研究号低频获取
        ↓
本地媒体
        ↓
FFmpeg / Whisper / OCR / AI
        ↓
入库
```

不要默认把 iPhone 登录态、老号 Cookie 或认证材料复制到 Mac 网络流水线。

---

## 7. 批量运行前检查

今晚或任何长批任务开始前至少确认：

```text
[ ] iPhone Mirroring ready
[ ] 高价值账号仅承担真机发现 / 分享职责
[ ] Mac 没有无意使用高价值账号 Cookie
[ ] 必须登录时使用固定研究号
[ ] network worker = 1（未验证前不要扩）
[ ] local workers 可按机器性能提高
[ ] 下载去重开启
[ ] checkpoint 可恢复
[ ] captcha / verify / IP block 会打开 circuit，而不是继续重试
[ ] 本地处理任务在平台 circuit open 后仍可继续
```

---

## 8. 与 xiaohongshu-cli 风控设计的关系

甄姬参考 `jackwener/xiaohongshu-cli` 中以下工程思想：

```text
请求节流
有限重试
指数退避
验证码后降载 / 停止
错误分类
稳定 session
token/context cache
```

但甄姬不需要完整复制其 Web API 浏览器模拟路线。甄姬已有真实 iPhone 作为可信发现入口，优先利用真实 App 交互，把 Mac 平台请求压缩到最低必要程度。

---

## 9. 最终准则

```text
老号留真机。
Mac 无账号优先，固定研究号其次。
不把日抛号池当风控恢复方案。
平台网络请求走窄管道。
本地计算走宽管道。
能缓存就不重复请求。
429 / 5xx 有界退避。
验证码、IP block、安全挑战立即开路器。
风控发生后停止平台请求，但继续已有素材的本地处理。
不自动换号、换 IP 或绕过验证继续跑。
```
