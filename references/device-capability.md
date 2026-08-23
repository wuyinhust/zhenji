# Device Capability Layer（设备能力层）

> zhenji v5.2.3 roadmap

## 定位

甄姬不是 iPhone 自动化工具，而是真机驱动的社交媒体情报 Skill。

设备只是执行后端。系统根据用户环境自动选择能力等级。

```text
Device Capability 决定能做什么
Permission Layer 决定允许做什么
```

## 三种运行模式

### Mode A：iPhone Mirror（旗舰模式）

条件：
- iPhone Mirror 可用
- phone-harness 可连接

```yaml
mode: real_device_ios
```

能力：★★★★★

支持：真实 App 浏览、账号观察、搜索、推荐流研究、分享链接获取，以及未来 L1/L2/L3 行动能力。

原则：高价值长期账号优先留在真实 iPhone，Mac 不默认承载高价值账号认证。

---

### Mode B：Android Device（兼容模式）

条件：
- Android 手机可连接
- phone-harness Android backend 可用

```yaml
mode: real_device_android
```

能力：★★★★☆

支持：真实 App 浏览、截图、点击、滑动、分享、复制链接、内容采集。

规则：Android 与 iOS 必须拥有独立 Action Recipe，不复用 iOS 坐标。

---

### Mode C：No Device（无设备模式）

```yaml
mode: device_less
```

能力：★★☆☆☆

支持：
- 已有素材分析
- 视频转录
- 抽帧
- OCR
- 内容结构化
- 知识库检索
- 账号分析
- 运营分析

不支持：
- App 浏览
- 搜索
- 点赞
- 收藏
- 评论
- 回复
- 发布

---

## Capability Detection

启动时执行环境检测：

```text
zhenji doctor

检测：
1. phone-harness
2. iPhone Mirror
3. Android ADB
4. 本地媒体库
5. 账号配置
```

---

## Device Backend Interface

统一接口：

```python
class DeviceBackend:
    connect()
    state()
    screenshot()
    tap()
    swipe()
    input()
    back()
```

实现：

```text
device/
├── ios_mirror.py
├── android_adb.py
└── headless.py
```

---

## Action Recipe 规则

动作必须绑定设备类型：

```text
xhs.share_link.ios
xhs.share_link.android
```

开发完成标准：

```text
Recipe
+
真实设备录制
+
状态验证
+
失败恢复
+
重复测试
```

---

## 优先级

```text
1. iPhone Mirror
2. Android Device
3. No Device
```

降级原则：设备能力下降时减少能力，不模拟不存在的设备能力。
