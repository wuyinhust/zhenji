# V4 · 无人值守运行时与真实输入保活

V4 的目标不是“更频繁地操作手机”，而是让长批处理在真实 iPhone Mirroring 环境中可持续、自愈、可断点恢复。

## 三个独立概念

```text
Watchdog（看门狗）
= 只读判断连接与页面是否健康

Recovery（恢复）
= 在预授权范围内恢复明确识别的镜像恢复页

Keepalive（保活）
= 在确实需要等待时，执行当前页面已经验证的无副作用真实 HID 输入
```

`screenshot()`、`connection_state()`、`screen_info()` 不属于真实输入。`caffeinate` 只负责 Mac 侧防休眠，`activate()` 只处理窗口/输入路径。它们都不计入 iOS 保活时钟。

## Idle Calibration（空闲超时标定）

不硬编码“iPhone Mirroring 几分钟暂停”。首次无人值守运行或环境变化后，实际测量当前环境：

```text
READY
→ 不发送任何 HID
→ 只读轮询连接状态
→ 第一次出现 idle pause
→ 记录 T1
→ 自动恢复
→ 重复得到 T2 / T3
→ idle_timeout = min(T1,T2,T3)
```

保活触发时间由实测值计算：

```text
keepalive_after = idle_timeout × trigger_ratio
```

默认 `trigger_ratio=0.80` 是安全提前量，不是对暂停时间的猜测；可以配置。

标定结果按以下环境键保存：

```text
macOS version
iOS version
phone-harness version
Mirroring build
```

环境变化、发生早于预期的 idle pause、或用户主动要求时重新标定。

## Safe Keepalive（安全保活）

只有以下条件同时成立才允许：

1. 当前页面重新识别成功；
2. 页面属于 `KNOWN_SAFE`；
3. 该页面已经注册 verified keepalive action（已验证保活动作）；
4. 动作为真实 HID 输入；
5. `side_effect=none`；
6. 动作后页面再次验证仍为原状态。

优先顺序：

```text
真实业务动作
> 可逆小幅滚动
> 已验证安全区域点击
> 无可验证动作则不输入
```

禁止在以下页面保活：登录、密码、设备解锁、安全挑战、验证码、未知页面、镜像恢复页。

## 真实输入时钟

只有业务 HID 或 verified keepalive HID 才重置 `last_real_input_at`。

```text
screenshot            ×
connection_state      ×
screen_info           ×
caffeinate            ×
activate               ×
业务 tap/scroll        ✓
verified keepalive HID ✓
```

## 自愈

```text
MIRROR_RECOVERY
→ auto_connect（预授权）
→ 重新 connection_state/screen_info/screenshot
→ READY
→ 清除旧窗口偏移、OCR Cache、Card Map、滚动假设
→ 从 checkpoint 继续
```

密码、解锁、安全挑战仍然冻结业务输入并保存断点。
