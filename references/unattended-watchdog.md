# 无人值守 Watchdog

该文档在 V4 中由 `unattended-runtime-v4.md` 扩展。Watchdog 仍负责连接、窗口和页面健康监测；V4 另外加入 Idle Calibration（空闲超时标定）、Safe Keepalive（安全保活）、自动恢复与真实 HID 输入时钟。

关键原则：

- `connection_state()` / `screen_info()` / `screenshot()` 是观察，不计入保活。
- background backend 下 `frontmost=False` 正常。
- `auto_connect` 是无人值守默认恢复模式，但只处理明确识别的镜像恢复页。
- 密码、设备解锁、验证码、安全挑战、未知危险页冻结业务输入。
- 恢复后旧窗口偏移、Observation Cache、Card Map、坐标和滚动位置全部失效。
- 所有业务输入与 Safe Keepalive 都经过 `guard.assert_input_allowed()`。
