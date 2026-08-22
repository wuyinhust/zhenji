# V3 → V4

V3 主要解决采集效率：三档视频模式、OCR 缓存、Card Map、批量写入和动作宏。

V4 主要解决无人值守：

- 新增 Idle Calibration（空闲超时标定），不猜 iPhone Mirroring 暂停时间；
- 新增真实 HID 输入时钟，截图和状态查询不再被视为活动；
- 新增 Safe Keepalive（安全保活），在实测暂停阈值前执行当前页面已验证的无副作用真实输入；
- `auto_connect` 成为无人值守默认恢复模式；
- 恢复后强制失效窗口偏移、Observation Cache、Card Map 和滚动位置假设；
- 新增 Unattended Supervisor（无人值守监督器），统一 Watchdog、Recovery、Keepalive、Checkpoint 与 Input Guard；
- 新增 runtime_calibration / runtime_events 运行观测数据。
